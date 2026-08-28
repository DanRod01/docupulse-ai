from typing import Literal, Union
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.document import MetadataValue


class RAGQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Pergunta do usuário a ser respondida com base nos documentos",
    )
    document_id: Union[UUID, None] = Field(
        default=None,
        description="Filtro opcional para limitar o RAG a um único documento",
    )
    model_name: str = Field(
        default="gemini-3.5-flash-lite",
        description="Modelo do Google Gemini a ser utilizado (ex: gemini-3.5-flash-lite, gemini-3.5-flash, gemini-3.7-flash)",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Temperatura de amostragem (menor = mais determinístico e factual)",
    )
    match_count: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Quantidade de fragmentos recuperados para compor o contexto",
    )
    vec_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Peso da busca semântica no RRF",
    )
    text_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Peso da busca textual no RRF",
    )


class RAGSourceItem(BaseModel):
    source_index: int = Field(..., description="Número ordinal da fonte (ex: 1 para [Fonte 1])")
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    score: float
    metadata: dict[str, MetadataValue]


class RAGResponse(BaseModel):
    query: str
    answer: str
    sources: list[RAGSourceItem]
    model_used: str
    execution_time_ms: float


class SSEEventPayload(BaseModel):
    event_type: Literal["sources", "token", "error", "done"]
    data: Union[str, list[RAGSourceItem], dict[str, MetadataValue]]
