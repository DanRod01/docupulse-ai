import asyncio
import logging
import time
from typing import Union
from fastapi import HTTPException, status
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger("docupulse.vision")

VISION_EXTRACTION_PROMPT = """Você é um especialista em OCR inteligente e extração de dados de documentos visuais do DocuPulse AI.
Analise a imagem fornecida (que pode ser uma nota fiscal, recibo, gráfico, relatório financeiro, contrato escaneado, infográfico ou diagrama) e faça uma extração completa e estruturada.

Diretrizes de Extração:
1. Transcreva com máxima fidelidade todo o texto visível, títulos, cláusulas, datas, CNPJs, códigos, nomes e valores numéricos.
2. Converta quaisquer tabelas, demonstrativos ou formulários presentes na imagem em Tabelas Markdown estruturadas (| Coluna 1 | Coluna 2 | ...).
3. Se houver gráficos (barras, linhas, pizza), descreva a tendência, os eixos, as legendas e os números representados de forma detalhada.
4. Organize a resposta em seções Markdown claras e limpas.
5. Nunca invente dados que não estejam legíveis na imagem. Se algo estiver ilegível, indique [ilegível].
"""


class GeminiVisionService:
    """Serviço de extração visual e OCR multimodal com Google Gemini."""

    def __init__(self, model_name: Union[str, None] = None) -> None:
        self._model_name = model_name
        self._client: Union[genai.Client, None] = None
        self._setup_client()

    @property
    def model_name(self) -> str:
        return self._model_name or settings.GEMINI_MODEL_NAME or "gemini-3.5-flash-lite"

    def _setup_client(self) -> None:
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Cliente Gemini Vision inicializado com sucesso.")
        else:
            self._client = None

    @property
    def is_configured(self) -> bool:
        if self._client is None and settings.GEMINI_API_KEY:
            self._setup_client()
        return self._client is not None

    async def extract_text_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
    ) -> str:
        """Processa uma imagem e retorna a transcrição textual estruturada em Markdown de forma assíncrona."""
        if not self.is_configured or self._client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A chave GEMINI_API_KEY não está configurada no backend/.env. Obtenha sua chave gratuita no Google AI Studio (aistudio.google.com) para habilitar o OCR e RAG Multimodal.",
            )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        candidate_models = [self.model_name, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-lite-latest"]
        # Remove duplicatas preservando a ordem
        unique_models = list(dict.fromkeys(candidate_models))

        last_error: Union[Exception, None] = None

        for model in unique_models:
            for attempt in range(2):
                try:
                    response = await self._client.aio.models.generate_content(
                        model=model,
                        contents=[image_part, VISION_EXTRACTION_PROMPT],
                    )
                    return response.text or "Nenhum texto pôde ser extraído da imagem fornecida."
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Falha no modelo '%s' (tentativa %d): %s",
                        model,
                        attempt + 1,
                        exc,
                    )
                    if attempt == 0 and self._is_retryable_error(exc):
                        await asyncio.sleep(1.0)
                    else:
                        break  # Tenta o próximo modelo candidato

        logger.error("Todos os modelos de visão falharam: %s", last_error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro na extração visual de imagem com o Gemini: {str(last_error)}",
        )

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            return status_code in {429, 500, 502, 503, 504}
        return any(
            f"{code} " in str(exc) or f'"code": {code}' in str(exc)
            for code in (429, 500, 502, 503, 504)
        )


vision_service = GeminiVisionService()

