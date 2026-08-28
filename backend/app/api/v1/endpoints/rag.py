import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from psycopg import AsyncConnection
from app.core.security import verify_api_key
from app.db.session import get_db_connection
from app.schemas.rag import RAGQueryRequest, RAGResponse, RAGSourceItem
from app.services.embedding import embedding_service
from app.services.rag import rag_service

router = APIRouter()


async def retrieve_sources_for_rag(
    request: RAGQueryRequest,
    conn: AsyncConnection,
) -> list[RAGSourceItem]:
    """Recupera os fragmentos mais relevantes via busca híbrida e mapeia com metadados dos documentos."""
    query_embedding = await embedding_service.embed_query(request.query)

    if request.document_id:
        sql = """
        select 
            c.id, c.document_id, c.chunk_index, c.content, c.metadata, h.combined_score,
            d.filename as doc_filename, d.title as doc_title
        from hybrid_search_chunks(%s::text, %s::vector, %s::int, 60, %s::float8, %s::float8) h
        join document_chunks c on h.id = c.id
        join documents d on c.document_id = d.id
        where c.document_id = %s;
        """
        params = (
            request.query,
            query_embedding,
            request.match_count,
            request.vec_weight,
            request.text_weight,
            request.document_id,
        )
    else:
        sql = """
        select 
            c.id, c.document_id, c.chunk_index, c.content, c.metadata, h.combined_score,
            d.filename as doc_filename, d.title as doc_title
        from hybrid_search_chunks(%s::text, %s::vector, %s::int, 60, %s::float8, %s::float8) h
        join document_chunks c on h.id = c.id
        join documents d on c.document_id = d.id;
        """
        params = (
            request.query,
            query_embedding,
            request.match_count,
            request.vec_weight,
            request.text_weight,
        )

    result = await conn.execute(sql, params)
    rows = await result.fetchall()

    sources: list[RAGSourceItem] = []
    for idx, r in enumerate(rows, start=1):
        meta = r["metadata"] if isinstance(r["metadata"], dict) else {}
        meta["filename"] = r["doc_filename"]
        meta["title"] = r["doc_title"]
        sources.append(
            RAGSourceItem(
                source_index=idx,
                chunk_id=r["id"],
                document_id=r["document_id"],
                chunk_index=r["chunk_index"],
                content=r["content"],
                score=float(r["combined_score"]),
                metadata=meta,
            )
        )
    return sources


@router.post(
    "/stream",
    summary="Chat RAG com Streaming SSE",
    description="Executa busca híbrida e transmite a resposta do Google Gemini token a token via Server-Sent Events (SSE).",
    dependencies=[Depends(verify_api_key)],
)
async def rag_chat_stream(
    request: RAGQueryRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> StreamingResponse:
    try:
        sources = await retrieve_sources_for_rag(request, conn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na recuperação de contexto no PostgreSQL: {str(exc)}",
        )

    event_generator = rag_service.stream_rag_response(
        query=request.query,
        sources=sources,
        model_name=request.model_name,
        temperature=request.temperature,
    )

    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desativa buffer em proxies reversos Nginx
        },
    )


@router.post(
    "/query",
    response_model=RAGResponse,
    summary="Chat RAG Síncrono (JSON)",
    description="Retorna a resposta completa e fundamentada de uma vez (para integrações de API clássicas sem stream).",
    dependencies=[Depends(verify_api_key)],
)
async def rag_chat_query(
    request: RAGQueryRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> RAGResponse:
    start_time = time.perf_counter()
    try:
        sources = await retrieve_sources_for_rag(request, conn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na recuperação de contexto no PostgreSQL: {str(exc)}",
        )

    try:
        answer = await rag_service.generate_sync_response(
            query=request.query,
            sources=sources,
            model_name=request.model_name,
            temperature=request.temperature,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na geração de resposta com o Gemini: {str(exc)}",
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return RAGResponse(
        query=request.query,
        answer=answer,
        sources=sources,
        model_used=request.model_name,
        execution_time_ms=round(elapsed_ms, 2),
    )
