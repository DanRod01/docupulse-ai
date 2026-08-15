from fastapi import APIRouter
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from app.core.config import settings

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Status operacional do serviço")
    project: str = Field(..., description="Nome do projeto")
    version: str = Field(default="0.1.0", description="Versão da API")
    timestamp: datetime = Field(..., description="Timestamp ISO UTC da checagem")
    environment_checks: dict[str, bool] = Field(
        ..., description="Verificação de configuração de chaves e variáveis essenciais"
    )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check do sistema",
    description="Retorna o status de saúde da API e valida se variáveis de ambiente essenciais estão presentes.",
)
async def check_health() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        environment_checks={
            "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
            "database_url_configured": bool(settings.DATABASE_URL),
        },
    )
