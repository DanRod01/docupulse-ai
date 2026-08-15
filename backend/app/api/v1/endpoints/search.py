import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection
from app.core.security import verify_api_key
from app.db.session import get_db_connection
from app.schemas.search import (
    EmbedDocumentResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResultChunk,
)
from app.services.embedding import embedding_service

router = APIRouter()


@router.post(
    "/hybrid",
    response_model=HybridSearchResponse,
    summary="Busca Híbrida (Semântica + Palavras-Chave)",
    description="Executa busca híbrida combinando embedding vetorial (Gemini) e Full-Text Search com algoritmo RRF.",
    dependencies=[Depends(verify_api_key)],
)
async def perform_hybrid_search(
    request: HybridSearchRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> HybridSearchResponse:
    start_time = time.perf_counter()

    # 1. Geração do embedding assimétrico para a pergunta do usuário
    try:
        query_embedding = await embedding_service.embed_query(request.query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar embedding da consulta com Google Gemini: {str(exc)}",
        )

    # 2. Execução da função SQL de Busca Híbrida com RRF no PostgreSQL
    try:
        # Se houver filtro de documento específico, adaptamos a query
        if request.document_id:
            sql_query = """
            select id, document_id, chunk_index, content, metadata, combined_score
            from hybrid_search_chunks(%s, %s, %s, %s, %s, %s)
            where document_id = %s;
            """
            params = (
                request.query,
                query_embedding,
                request.match_count,
                request.rrf_k,
                request.vec_weight,
                request.text_weight,
                request.document_id,
            )
        else:
            sql_query = """
            select id, document_id, chunk_index, content, metadata, combined_score
            from hybrid_search_chunks(%s, %s, %s, %s, %s, %s);
            """
            params = (
                request.query,
                query_embedding,
                request.match_count,
                request.rrf_k,
                request.vec_weight,
                request.text_weight,
            )

        result = await conn.execute(sql_query, params)
        rows = await result.fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar busca híbrida no PostgreSQL: {str(exc)}",
        )

    execution_time_ms = (time.perf_counter() - start_time) * 1000

    results: list[SearchResultChunk] = [
        SearchResultChunk(
            id=r["id"],
            document_id=r["document_id"],
            chunk_index=r["chunk_index"],
            content=r["content"],
            metadata=r["metadata"] if isinstance(r["metadata"], dict) else {},
            combined_score=float(r["combined_score"]),
        )
        for r in rows
    ]

    return HybridSearchResponse(
        query=request.query,
        match_count=request.match_count,
        total_results=len(results),
        results=results,
        execution_time_ms=round(execution_time_ms, 2),
    )


@router.post(
    "/documents/{document_id}/embed",
    response_model=EmbedDocumentResponse,
    summary="Gerar embeddings para um documento existente",
    description="Gera vetores para todos os chunks não indexados de um documento específico e atualiza no banco de dados.",
    dependencies=[Depends(verify_api_key)],
)
async def generate_document_embeddings(
    document_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> EmbedDocumentResponse:
    # 1. Recupera chunks pendentes
    result = await conn.execute(
        """
        select id, chunk_index, content
        from document_chunks
        where document_id = %s
        order by chunk_index asc;
        """,
        (document_id,),
    )
    chunks = await result.fetchall()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem fragmentos cadastrados.",
        )

    texts = [c["content"] for c in chunks]
    chunk_ids = [c["id"] for c in chunks]

    # 2. Geração em lote com Gemini
    try:
        embeddings = await embedding_service.embed_documents(texts=texts)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar embeddings dos chunks com Gemini: {str(exc)}",
        )

    # 3. Atualização no banco em lote
    async with conn.transaction():
        async with conn.cursor() as cur:
            update_data = list(zip(embeddings, chunk_ids))
            await cur.executemany(
                """
                update document_chunks
                set embedding = %s
                where id = %s;
                """,
                update_data,
            )

            await cur.execute(
                """
                update documents
                set status = 'completed', updated_at = now()
                where id = %s;
                """,
                (document_id,),
            )

    return EmbedDocumentResponse(
        document_id=document_id,
        total_chunks=len(chunks),
        embedded_chunks=len(embeddings),
        status="completed",
    )
