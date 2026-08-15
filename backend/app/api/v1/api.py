from fastapi import APIRouter
from app.api.v1.endpoints import health, documents, search, rag

api_router = APIRouter()

# Registro dos roteadores de cada domínio/módulo
api_router.include_router(health.router, tags=["Health & Monitoring"])
api_router.include_router(
    documents.router, prefix="/documents", tags=["Documents & Ingestion"]
)
api_router.include_router(
    search.router, prefix="/search", tags=["Search & Embeddings"]
)
api_router.include_router(
    rag.router, prefix="/rag", tags=["RAG & Intelligence Engine"]
)
