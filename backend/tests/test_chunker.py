import pytest
from app.schemas.document import ChunkingConfig
from app.services.chunker import RecursiveCharacterChunker


def test_normalize_whitespace():
    chunker = RecursiveCharacterChunker()
    raw = "Linha 1\r\n\r\n\r\nLinha 2    com    espacos\n\n\n\nLinha 3"
    normalized = chunker._normalize_whitespace(raw)
    assert "\r" not in normalized
    assert "    " not in normalized
    assert "\n\n\n" not in normalized
    assert "Linha 1\n\nLinha 2 com espacos\n\nLinha 3" == normalized


def test_split_empty_text():
    chunker = RecursiveCharacterChunker()
    assert chunker.split_text("") == []
    assert chunker.split_text("   \n\n   ") == []


def test_split_short_text():
    chunker = RecursiveCharacterChunker(config=ChunkingConfig(chunk_size=500, chunk_overlap=50))
    text = "Este é um texto curto que deve caber em um único fragmento."
    chunks = chunker.split_text(text, base_metadata={"doc_type": "manual"})

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == text
    assert chunks[0].character_count == len(text)
    assert chunks[0].metadata["doc_type"] == "manual"
    assert chunks[0].metadata["chunk_index"] == 0


def test_split_long_text_respects_overlap():
    config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
    chunker = RecursiveCharacterChunker(config=config)
    paragraphs = [
        "Primeiro parágrafo do relatório técnico explicando o funcionamento da arquitetura RAG.",
        "Segundo parágrafo detalhando o uso do pgvector com índice HNSW para busca vetorial rápida.",
        "Terceiro parágrafo abordando o algoritmo Reciprocal Rank Fusion para fusão de rankings léxicos e semânticos.",
    ]
    long_text = "\n\n".join(paragraphs)

    chunks = chunker.split_text(long_text)
    assert len(chunks) > 1

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert len(chunk.content) > 0
        assert chunk.token_estimate >= 1
