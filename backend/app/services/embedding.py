import asyncio
import logging
from typing import Literal, Union
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger("docupulse.embeddings")

TaskType = Literal[
    "RETRIEVAL_QUERY",
    "RETRIEVAL_DOCUMENT",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
]


class GeminiEmbeddingService:
    """Serviço assíncrono para geração de embeddings utilizando o SDK moderno google-genai."""

    def __init__(self, model_name: Union[str, None] = None) -> None:
        self._model_name = model_name
        self._client: Union[genai.Client, None] = None
        self._setup_client()

    @property
    def model_name(self) -> str:
        return self._model_name or settings.GEMINI_EMBEDDING_MODEL or "gemini-embedding-001"

    def _setup_client(self) -> None:
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Cliente Google GenAI para Embeddings inicializado com sucesso.")
        else:
            logger.warning(
                "GEMINI_API_KEY não configurada. Geração de embeddings estará inativa até a definição da chave."
            )
            self._client = None

    @property
    def is_configured(self) -> bool:
        if self._client is None and settings.GEMINI_API_KEY:
            self._setup_client()
        return self._client is not None

    async def embed_query(self, text: str) -> list[float]:
        """Gera embedding vetorial de 768 dimensões para a pergunta do usuário de forma assíncrona."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente no backend/.env."
            )

        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        )
        response = await self._client.aio.models.embed_content(
            model=self.model_name,
            contents=text,
            config=config,
        )
        if response.embeddings and len(response.embeddings) > 0 and response.embeddings[0].values:
            return list(response.embeddings[0].values)
        if hasattr(response, "embedding") and response.embedding and response.embedding.values:
            return list(response.embedding.values)
        raise ValueError("Resposta de embedding vazia retornada pela API do Gemini.")

    async def embed_documents(
        self,
        texts: list[str],
        batch_size: int = 30,
        title: Union[str, None] = None,
    ) -> list[list[float]]:
        """Gera embeddings em lote de 768 dimensões para fragmentos de documentos de forma assíncrona."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente no backend/.env."
            )

        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            title=title,
            output_dimensionality=768,
        )

        # Processamento em lotes para otimização de latência
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.aio.models.embed_content(
                model=self.model_name,
                contents=batch,
                config=config,
            )
            if response.embeddings:
                for item in response.embeddings:
                    if item.values:
                        all_embeddings.append(list(item.values))
            elif hasattr(response, "embedding") and response.embedding and response.embedding.values:
                all_embeddings.append(list(response.embedding.values))

        return all_embeddings


embedding_service = GeminiEmbeddingService()

