import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import init_db_pool, close_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida da aplicação (startup e shutdown)."""
    # 1. Startup: Inicializa pool assíncrono de banco de dados
    await init_db_pool()
    yield
    # 2. Shutdown: Fecha pool de banco de dados de forma limpa
    await close_db_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    description="Motor de Inteligência Artificial, Ingestão de Dados e RAG Híbrido com Google Gemini e PostgreSQL pgvector.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuração de CORS para permitir requisições do Nuxt 3
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": f"Bem-vindo ao backend do {settings.PROJECT_NAME}.",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }
