import pytest
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import verify_api_key


def test_verify_api_key_success(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "segredo-super-secreto-123")
    # Não deve lançar exceção
    verify_api_key(x_api_key="segredo-super-secreto-123")


def test_verify_api_key_invalid(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "segredo-super-secreto-123")
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(x_api_key="chave-errada")

    assert exc_info.value.status_code == 401
    assert "API Key ausente ou inválida" in exc_info.value.detail


def test_verify_api_key_empty(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "segredo-super-secreto-123")
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(x_api_key="")

    assert exc_info.value.status_code == 401


def test_verify_api_key_dev_mode_permissive(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "")
    # Em modo desenvolvimento permissivo (API_KEY vazia), qualquer chave ou ausência passa
    verify_api_key(x_api_key="")
    verify_api_key(x_api_key="qualquer-coisa")
