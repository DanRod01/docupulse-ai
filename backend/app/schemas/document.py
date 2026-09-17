from typing import Literal, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator

DocumentStatus = Literal["pending", "processing", "completed", "failed"]
MetadataValue = Union[str, int, float, bool, None]


class ChunkingConfig(BaseModel):
    chunk_size: int = Field(
        default=800,
        ge=100,
        le=4000,
        description="Tamanho aproximado de cada fragmento em caracteres",
    )
    chunk_overlap: int = Field(
        default=150,
        ge=0,
        le=1000,
        description="Quantidade de caracteres sobrepostos entre fragmentos adjacentes",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap deve ser estritamente menor que chunk_size")
        return self


class ChunkItem(BaseModel):
    chunk_index: int = Field(..., description="Índice sequencial do chunk no documento")
    content: str = Field(..., description="Texto limpo e formatado do chunk")
    character_count: int = Field(..., description="Quantidade de caracteres no chunk")
    token_estimate: int = Field(
        ..., description="Estimativa de tokens (aprox. 4 caracteres por token)"
    )
    metadata: dict[str, MetadataValue] = Field(
        default_factory=dict, description="Metadados contextuais específicos do chunk"
    )


class TabularColumnStats(BaseModel):
    column_name: str
    data_type: str
    null_count: int
    unique_count: int
    mean: Union[float, None] = None
    min_value: Union[str, float, int, None] = None
    max_value: Union[str, float, int, None] = None


class TabularAnalyticsSummary(BaseModel):
    row_count: int
    column_count: int
    columns: list[str]
    column_stats: list[TabularColumnStats]
    sample_records: list[dict[str, MetadataValue]]


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., description="Extensão ou MIME type do arquivo")
    file_size_bytes: int = Field(..., ge=0)
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    total_chunks: int
    status: DocumentStatus
    metadata: dict[str, MetadataValue]
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    chunks: list[ChunkItem]
    tabular_summary: Union[TabularAnalyticsSummary, None] = None
