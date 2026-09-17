import pytest
from pydantic import ValidationError
from app.schemas.search import HybridSearchRequest
from app.schemas.rag import RAGQueryRequest
from app.schemas.document import ChunkingConfig


def test_chunking_config_defaults():
    config = ChunkingConfig()
    assert config.chunk_size == 800
    assert config.chunk_overlap == 150


def test_chunking_config_invalid():
    with pytest.raises(ValidationError):
        # chunk_overlap não pode ser maior ou igual a chunk_size
        ChunkingConfig(chunk_size=100, chunk_overlap=150)


def test_hybrid_search_request_defaults():
    req = HybridSearchRequest(query="Qual o faturamento do último trimestre?")
    assert req.query == "Qual o faturamento do último trimestre?"
    assert req.match_count == 5
    assert req.rrf_k == 60
    assert req.vec_weight == 0.6
    assert req.text_weight == 0.4
    assert req.document_id is None


def test_hybrid_search_request_weights_validation():
    # Pesos devem estar entre 0.0 e 1.0
    with pytest.raises(ValidationError):
        HybridSearchRequest(query="teste", vec_weight=1.5)

    with pytest.raises(ValidationError):
        HybridSearchRequest(query="teste", text_weight=-0.2)


def test_rag_query_request_defaults():
    req = RAGQueryRequest(query="Explique os riscos descritos na cláusula 4.")
    assert req.temperature == 0.2
    assert req.model_name == "gemini-3.5-flash-lite"
    assert req.match_count == 5
