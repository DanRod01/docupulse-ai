import logging
from fastapi import Header, HTTPException, status
from app.core.config import settings

logger = logging.getLogger("docupulse.security")

_DEV_MODE_WARNED = False


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """
    Dependency FastAPI para validar o header X-Api-Key em todas as rotas protegidas.

    - Se API_KEY não estiver configurada no .env → modo desenvolvimento permissivo (apenas aviso).
    - Se API_KEY estiver configurada → validação estrita (401 em caso de falha).
    """
    global _DEV_MODE_WARNED

    if not settings.API_KEY:
        if not _DEV_MODE_WARNED:
            logger.warning(
                "API_KEY não configurada. Rodando em modo permissivo de desenvolvimento. "
                "Configure API_KEY no backend/.env para habilitar autenticação em produção."
            )
            _DEV_MODE_WARNED = True
        return

    if not x_api_key or x_api_key != settings.API_KEY:
        logger.warning(
            "Tentativa de acesso com API Key inválida ou ausente. "
            "Header X-Api-Key recebido: %s",
            x_api_key[:8] + "..." if x_api_key else "(vazio)",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key ausente ou inválida. Forneça o header X-Api-Key correto.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
