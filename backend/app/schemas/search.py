from typing import Literal, Union
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.document import MetadataValue


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Texto da pergunta do usuário")
    match_count: int = Field(default=5, ge=1, le=20, description="Quantidade de fragmentos mais relevantes a retornar")
    rrf_k: int = Field(default=60, ge=1, le=100, description="Constante de suavização do algoritmo RRF (padrão 60)")
    vec_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="Peso da busca semântica (vetores)")
    text_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Peso da busca textual (palavras-chave)")
    document_id: Union[UUID, None] = Field(default=None, description="Filtro opcional para limitar a busca a um único documento")


class SearchResultChunk(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, MetadataValue]
    combined_score: float = Field(..., description="Score final de relevância normalizado pelo algoritmo RRF")


class HybridSearchResponse(BaseModel):
    query: str
    match_count: int
    total_results: int
    results: list[SearchResultChunk]
    execution_time_ms: float


class EmbedDocumentResponse(BaseModel):
    document_id: UUID
    total_chunks: int
    embedded_chunks: int
    status: str
