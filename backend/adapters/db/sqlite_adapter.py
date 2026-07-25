from typing import Any, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from core.logger import get_logger

logger = get_logger(__name__)


class SQLiteAdapter:
    """Implementación de DatabasePort para SQLite (modo Studio offline).

    Solo se instancia cuando HIRA_DEPLOY_MODE=studio.
    """

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./hira_studio.db") -> None:
        self._engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("SQLiteAdapter inicializado", extra={"url": database_url})

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        async with self._session_factory() as session:
            result = await session.execute(text(query), params or {})
            return result

    async def create_tables(self) -> None:
        from models.base import Base
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tablas creadas (SQLite)")

    async def health_check(self) -> bool:
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.error("SQLite health check falló", exc_info=exc)
            return False

    async def dispose(self) -> None:
        await self._engine.dispose()
        logger.info("SQLiteAdapter: engine cerrado")
