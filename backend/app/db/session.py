import logging
from collections.abc import AsyncGenerator
from typing import Optional
import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pgvector.psycopg import register_vector_async
from app.core.config import settings

logger = logging.getLogger("docupulse.db")

# Pool singleton para o ciclo de vida da aplicação
_db_pool: Optional[AsyncConnectionPool] = None


async def configure_connection(conn: AsyncConnection) -> None:
    """Configura cada nova conexão do pool com o tipo de linha em dicionário e suporte a pgvector."""
    conn.row_factory = dict_row
    await register_vector_async(conn)


async def init_db_pool() -> None:
    """Inicializa o pool de conexões assíncrono com o PostgreSQL / Supabase."""
    global _db_pool
    if not settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL não configurada. O pool de banco de dados não foi inicializado."
        )
        return

    try:
        _db_pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            configure=configure_connection,
            open=False,
        )
        await _db_pool.open()
        logger.info("Pool de conexões assíncrono com PostgreSQL inicializado com sucesso.")
    except Exception as exc:
        logger.error(f"Erro ao inicializar pool de conexões com PostgreSQL: {exc}")
        _db_pool = None


async def close_db_pool() -> None:
    """Fecha todas as conexões ativas do pool de forma segura."""
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None
        logger.info("Pool de conexões com PostgreSQL encerrado.")


from fastapi import HTTPException, status

async def get_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Dependency Injection do FastAPI para obter uma conexão segura do pool."""
    global _db_pool
    if _db_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O banco de dados PostgreSQL (Supabase) não está conectado. Configure a variável DATABASE_URL no arquivo backend/.env.",
        )

    async with _db_pool.connection() as conn:
        yield conn

