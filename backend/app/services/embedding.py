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

    def __init__(self, model_name: str = "gemini-embedding-001") -> None:
        self.model_name = model_name
        self._client: Union[genai.Client, None] = None
        self._setup_client()

    def _setup_client(self) -> None:
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Cliente Google GenAI inicializado com sucesso.")
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
        """Gera embedding vetorial de 768 dimensões para a pergunta do usuário."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente no backend/.env."
            )

        return await asyncio.to_thread(
            self._generate_single_embedding,
            text=text,
            task_type="RETRIEVAL_QUERY",
        )

    async def embed_documents(
        self,
        texts: list[str],
        batch_size: int = 30,
        title: Union[str, None] = None,
    ) -> list[list[float]]:
        """Gera embeddings em lote de 768 dimensões para fragmentos de documentos."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente no backend/.env."
            )

        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Processamento em lotes para otimização de latência
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_result = await asyncio.to_thread(
                self._generate_batch_embeddings,
                texts=batch,
                task_type="RETRIEVAL_DOCUMENT",
                title=title,
            )
            all_embeddings.extend(batch_result)

        return all_embeddings

    def _generate_single_embedding(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[float]:
        """Execução síncrona com output_dimensionality=768."""
        assert self._client is not None
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=768,
        )
        response = self._client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=config,
        )
        if response.embeddings and len(response.embeddings) > 0 and response.embeddings[0].values:
            return list(response.embeddings[0].values)
        if hasattr(response, "embedding") and response.embedding and response.embedding.values:
            return list(response.embedding.values)
        raise ValueError("Resposta de embedding vazia retornada pela API do Gemini.")

    def _generate_batch_embeddings(
        self,
        texts: list[str],
        task_type: TaskType = "RETRIEVAL_DOCUMENT",
        title: Union[str, None] = None,
    ) -> list[list[float]]:
        """Execução em lote com output_dimensionality=768."""
        assert self._client is not None
        config = types.EmbedContentConfig(
            task_type=task_type,
            title=title,
            output_dimensionality=768,
        )
        response = self._client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=config,
        )
        results: list[list[float]] = []
        if response.embeddings:
            for item in response.embeddings:
                if item.values:
                    results.append(list(item.values))
        elif hasattr(response, "embedding") and response.embedding and response.embedding.values:
            results.append(list(response.embedding.values))
        return results


embedding_service = GeminiEmbeddingService()
