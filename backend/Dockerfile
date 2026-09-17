# ==============================================================================
# DocuPulse AI - Backend Dockerfile (FastAPI + Python 3.11)
# ==============================================================================
FROM python:3.11-slim AS base

# Configurações de ambiente Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalação de dependências de sistema necessárias para compilação (se houver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cópia do código da aplicação
COPY app ./app

# Exposição da porta do servidor Uvicorn
EXPOSE 8000

# Verificação de integridade (Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
