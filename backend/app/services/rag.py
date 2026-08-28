import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import List, Union
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.rag import RAGSourceItem

logger = logging.getLogger("docupulse.rag")

DEFAULT_SYSTEM_INSTRUCTION = """Você é o Assistente Especialista de Inteligência do DocuPulse AI.
Sua missão é responder à pergunta do usuário de forma clara, precisa, técnica e estritamente fundamentada no contexto dos documentos fornecidos.

Diretrizes Obrigatórias:
1. Responda APENAS com base nos trechos de contexto fornecidos abaixo.
2. Sempre cite a fonte correspondente usando a notação [Fonte X] onde a informação foi extraída (ex: "Conforme o relatório financeiro [Fonte 1], o lucro cresceu 25%").
3. Se a informação não estiver presente nos fragmentos de contexto, declare honestamente: "Não encontrei informações suficientes nos documentos fornecidos para responder a essa pergunta com precisão."
4. Mantenha um tom profissional, corporativo e formate a resposta com Markdown (tabelas, listas e negrito) quando apropriado.
5. Nunca invente dados, datas, valores ou fatos que não constem expressamente nas fontes.
"""


class RAGService:
    """Orquestrador do pipeline de RAG (Geração Aumentada por Recuperação) e streaming SSE."""

    def __init__(self) -> None:
        self._client: Union[genai.Client, None] = None
        self._setup_client()

    def _setup_client(self) -> None:
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Cliente Google GenAI para RAG inicializado.")
        else:
            logger.warning("GEMINI_API_KEY não configurada. Serviço RAG estará inativo.")
            self._client = None

    @property
    def is_configured(self) -> bool:
        if self._client is None and settings.GEMINI_API_KEY:
            self._setup_client()
        return self._client is not None

    def build_augmented_prompt(self, query: str, sources: list[RAGSourceItem]) -> str:
        """Monta o prompt com os fragmentos de contexto e seus respectivos índices de citação."""
        if not sources:
            context_block = "Nenhum documento ou fragmento relevante foi encontrado na base de dados."
        else:
            context_pieces: List[str] = []
            for src in sources:
                filename = src.metadata.get("filename", "Documento")
                header = f"--- [Fonte {src.source_index}] (Arquivo: {filename}, Chunk #{src.chunk_index}, Relevância RRF: {src.score:.4f}) ---"
                context_pieces.append(f"{header}\n{src.content}")
            context_block = "\n\n".join(context_pieces)

        return f"""## Fragmentos de Contexto Recuperados:
{context_block}

## Pergunta do Usuário:
{query}

## Sua Resposta Fundamentada:"""

    async def stream_rag_response(
        self,
        query: str,
        sources: list[RAGSourceItem],
        model_name: Union[str, None] = None,
        temperature: float = 0.2,
        system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
    ) -> AsyncIterator[str]:
        """Gera a resposta em streaming transmitindo eventos SSE no formato data: JSON\\n\\n de forma assíncrona."""
        if not self.is_configured or self._client is None:
            err_payload = json.dumps(
                {
                    "event_type": "error",
                    "data": "GEMINI_API_KEY não configurada. Defina a chave no arquivo backend/.env.",
                }
            )
            yield f"data: {err_payload}\n\n"
            return

        active_model = model_name or settings.GEMINI_MODEL_NAME or "gemini-3.5-flash-lite"

        # 1. Primeiro evento SSE: Envia todas as fontes recuperadas para renderização de citações
        sources_payload = json.dumps(
            {
                "event_type": "sources",
                "data": [s.model_dump(mode="json") for s in sources],
            }
        )
        yield f"data: {sources_payload}\n\n"

        prompt = self.build_augmented_prompt(query, sources)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        )

        start_time = time.perf_counter()
        total_tokens_estimated = 0

        try:
            # 2. Executa a stream assíncrona do Gemini
            stream_response = await self._client.aio.models.generate_content_stream(
                model=active_model,
                contents=prompt,
                config=config,
            )

            async for chunk in stream_response:
                if chunk.text:
                    token_payload = json.dumps(
                        {
                            "event_type": "token",
                            "data": chunk.text,
                        }
                    )
                    total_tokens_estimated += max(1, len(chunk.text) // 4)
                    yield f"data: {token_payload}\n\n"

            # 3. Evento final SSE: Sinaliza término e métricas
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            done_payload = json.dumps(
                {
                    "event_type": "done",
                    "data": {
                        "model_used": active_model,
                        "execution_time_ms": round(elapsed_ms, 2),
                        "total_tokens_estimated": total_tokens_estimated,
                    },
                }
            )
            yield f"data: {done_payload}\n\n"

        except Exception as exc:
            logger.error("Erro durante streaming do Gemini com modelo %s: %s", active_model, exc)
            err_payload = json.dumps(
                {
                    "event_type": "error",
                    "data": f"Erro na geração da resposta com o modelo Gemini ({active_model}): {str(exc)}",
                }
            )
            yield f"data: {err_payload}\n\n"

    async def generate_sync_response(
        self,
        query: str,
        sources: list[RAGSourceItem],
        model_name: Union[str, None] = None,
        temperature: float = 0.2,
        system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
    ) -> str:
        """Gera resposta completa de forma assíncrona/unificada (sem stream)."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente no backend/.env."
            )

        active_model = model_name or settings.GEMINI_MODEL_NAME or "gemini-3.5-flash-lite"
        prompt = self.build_augmented_prompt(query, sources)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        )

        response = await self._client.aio.models.generate_content(
            model=active_model,
            contents=prompt,
            config=config,
        )
        return response.text or ""


rag_service = RAGService()
