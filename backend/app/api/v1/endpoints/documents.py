import json
from typing import Union
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from app.core.config import settings
from app.core.security import verify_api_key
from app.db.session import get_db_connection
from app.schemas.document import (
    ChunkItem,
    ChunkingConfig,
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
    TabularAnalyticsSummary,
)
from app.services.chunker import chunker_service, RecursiveCharacterChunker
from app.services.tabular import tabular_service
from app.services.vision import vision_service
from app.services.pdf import pdf_service
from app.services.embedding import embedding_service

router = APIRouter()

# Tipos MIME aceitos
ALLOWED_TEXT_TYPES = {"text/plain", "text/markdown", "text/csv", "application/csv"}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_MIME_TYPES = ALLOWED_TEXT_TYPES | ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}


@router.post(
    "/preview-chunks",
    response_model=list[ChunkItem],
    summary="Pré-visualizar fatiamento de texto",
    description="Testa os parâmetros de chunk_size e chunk_overlap sobre um texto sem salvar no banco.",
    dependencies=[Depends(verify_api_key)],
)
async def preview_text_chunks(
    text: str = Form(..., description="Texto a ser fatiado"),
    chunk_size: int = Form(default=800, ge=100, le=4000),
    chunk_overlap: int = Form(default=150, ge=0, le=1000),
) -> list[ChunkItem]:
    config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    custom_chunker = RecursiveCharacterChunker(config=config)
    return custom_chunker.split_text(text)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Ingestão de arquivo (TXT, MD, CSV, Imagens PNG/JPG/WEBP)",
    description="Faz upload de um arquivo, executa OCR/parsing e chunking inteligente, e persiste no banco de dados com opção de embeddings automáticos.",
    dependencies=[Depends(verify_api_key)],
)
async def upload_document(
    file: UploadFile = File(...),
    title: Union[str, None] = Form(default=None),
    chunk_size: int = Form(default=800, ge=100, le=4000),
    chunk_overlap: int = Form(default=150, ge=0, le=1000),
    auto_embed: bool = Form(
        default=True,
        description="Gera automaticamente os embeddings com Gemini se a chave de API estiver configurada",
    ),
    conn: AsyncConnection = Depends(get_db_connection),
) -> DocumentUploadResponse:
    content_bytes = await file.read()
    filename = file.filename or "unknown_file"
    doc_title = title or filename
    file_type = file.content_type or "text/plain"
    file_size = len(content_bytes)

    # Validação de tamanho de arquivo
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Limite máximo: {settings.MAX_UPLOAD_SIZE_MB} MB. Tamanho recebido: {file_size / 1024 / 1024:.1f} MB.",
        )

    # Validação de extensão permitida
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extensão de arquivo não suportada: '{extension}'. Tipos aceitos: TXT, MD, CSV, PNG, JPG, WEBP.",
        )

    tabular_summary: Union[TabularAnalyticsSummary, None] = None
    text_content = ""
    is_image = (
        file_type in ALLOWED_IMAGE_TYPES
        or filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
    )
    is_pdf = file_type in ALLOWED_PDF_TYPES or filename.lower().endswith(".pdf")

    # 1. Pipeline de Ingestão por Tipo de Arquivo
    if is_pdf:
        # Extraição inteligente: texto digital + OCR Gemini para páginas escaneadas
        try:
            text_content = await pdf_service.extract_from_bytes(
                pdf_bytes=content_bytes,
                filename=filename,
                vision_service=vision_service if vision_service.is_configured else None,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao processar PDF com PyMuPDF: {str(exc)}",
            )
    elif is_image:
        try:
            text_content = await vision_service.extract_text_from_image(
                image_bytes=content_bytes,
                mime_type=file_type if file_type in ALLOWED_IMAGE_TYPES else "image/png",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro na extração visual de imagem com Gemini Vision: {str(exc)}",
            )
    elif filename.endswith(".csv") or file_type in {"text/csv", "application/csv"}:
        try:
            tabular_summary, text_content = tabular_service.analyze_csv_bytes(content_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao processar arquivo CSV com Polars: {str(exc)}",
            )
    else:
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = content_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não foi possível decodificar o arquivo de texto (esperado UTF-8 ou Latin-1).",
                )

    # 2. Pipeline de Chunking
    config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    custom_chunker = RecursiveCharacterChunker(config=config)
    base_metadata = {
        "filename": filename,
        "file_type": file_type,
        "is_tabular": bool(tabular_summary is not None),
        "is_multimodal_image": is_image,
        "is_pdf": is_pdf,
    }
    chunks = custom_chunker.split_text(text_content, base_metadata=base_metadata)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio ou não gerou fragmentos de texto válidos.",
        )

    # 3. Persistência Transacional no PostgreSQL (Supabase)
    async with conn.transaction():
        doc_row = await conn.execute(
            """
            insert into documents (title, filename, file_type, file_size_bytes, total_chunks, status, metadata)
            values (%s, %s, %s, %s, %s, 'pending', %s)
            returning id, title, filename, file_type, file_size_bytes, total_chunks, status, metadata, created_at, updated_at;
            """,
            (
                doc_title,
                filename,
                file_type,
                file_size,
                len(chunks),
                Jsonb(base_metadata),
            ),
        )
        saved_doc = await doc_row.fetchone()
        if not saved_doc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao salvar metadados do documento.",
            )

        doc_id = saved_doc["id"]

        embeddings: Union[list[list[float]], None] = None
        if auto_embed and embedding_service.is_configured:
            try:
                texts = [c.content for c in chunks]
                embeddings = await embedding_service.embed_documents(texts=texts, title=doc_title)
            except Exception:
                embeddings = None

        async with conn.cursor() as cur:
            if embeddings and len(embeddings) == len(chunks):
                chunk_tuples = [
                    (
                        doc_id,
                        c.chunk_index,
                        c.content,
                        emb,
                        Jsonb(c.metadata),
                    )
                    for c, emb in zip(chunks, embeddings)
                ]
                await cur.executemany(
                    """
                    insert into document_chunks (document_id, chunk_index, content, embedding, metadata)
                    values (%s, %s, %s, %s, %s);
                    """,
                    chunk_tuples,
                )
                await cur.execute(
                    """
                    update documents
                    set status = 'completed', updated_at = now()
                    where id = %s;
                    """,
                    (doc_id,),
                )
                saved_status = "completed"
            else:
                chunk_tuples_no_emb = [
                    (
                        doc_id,
                        c.chunk_index,
                        c.content,
                        Jsonb(c.metadata),
                    )
                    for c in chunks
                ]
                await cur.executemany(
                    """
                    insert into document_chunks (document_id, chunk_index, content, metadata)
                    values (%s, %s, %s, %s);
                    """,
                    chunk_tuples_no_emb,
                )
                saved_status = "pending"

    doc_response = DocumentResponse(
        id=saved_doc["id"],
        title=saved_doc["title"],
        filename=saved_doc["filename"],
        file_type=saved_doc["file_type"],
        file_size_bytes=saved_doc["file_size_bytes"],
        total_chunks=saved_doc["total_chunks"],
        status=saved_status,
        metadata=saved_doc["metadata"] if isinstance(saved_doc["metadata"], dict) else {},
        created_at=saved_doc["created_at"],
        updated_at=saved_doc["updated_at"],
    )

    return DocumentUploadResponse(
        document=doc_response,
        chunks=chunks,
        tabular_summary=tabular_summary,
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="Listar documentos ingeridos (com paginação)",
    dependencies=[Depends(verify_api_key)],
)
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    conn: AsyncConnection = Depends(get_db_connection),
) -> list[DocumentResponse]:
    result = await conn.execute(
        """
        select id, title, filename, file_type, file_size_bytes, total_chunks, status, metadata, created_at, updated_at
        from documents
        order by created_at desc
        limit %s offset %s;
        """,
        (limit, skip),
    )
    rows = await result.fetchall()
    return [
        DocumentResponse(
            id=r["id"],
            title=r["title"],
            filename=r["filename"],
            file_type=r["file_type"],
            file_size_bytes=r["file_size_bytes"],
            total_chunks=r["total_chunks"],
            status=r["status"],
            metadata=r["metadata"] if isinstance(r["metadata"], dict) else {},
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get(
    "/{document_id}/chunks",
    response_model=list[ChunkItem],
    summary="Listar chunks de um documento específico",
    dependencies=[Depends(verify_api_key)],
)
async def get_document_chunks(
    document_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> list[ChunkItem]:
    result = await conn.execute(
        """
        select chunk_index, content, metadata
        from document_chunks
        where document_id = %s
        order by chunk_index asc;
        """,
        (document_id,),
    )
    rows = await result.fetchall()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum fragmento encontrado para o documento especificado.",
        )

    return [
        ChunkItem(
            chunk_index=r["chunk_index"],
            content=r["content"],
            character_count=len(r["content"]),
            token_estimate=max(1, len(r["content"]) // 4),
            metadata=r["metadata"] if isinstance(r["metadata"], dict) else {},
        )
        for r in rows
    ]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar documento e todos os seus chunks (cascade)",
    dependencies=[Depends(verify_api_key)],
)
async def delete_document(
    document_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    async with conn.transaction():
        result = await conn.execute(
            "delete from documents where id = %s returning id;",
            (document_id,),
        )
        deleted = await result.fetchone()
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado.",
            )
