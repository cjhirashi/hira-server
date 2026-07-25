from typing import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Devuelve el cliente Redis singleton. Inicializa en el primer uso."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        logger.info("Cliente Redis inicializado", extra={"url": settings.redis_url.split("@")[-1]})
    return _redis_client


async def close_redis() -> None:
    """Cierra la conexión Redis. Llamar en el shutdown de la app."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Cliente Redis cerrado")


def get_rbac_key(user_id: int) -> str:
    """Clave Redis para el caché de permisos RBAC de un usuario."""
    return f"rbac:{user_id}"


def get_refresh_key(jti: str) -> str:
    """Clave Redis para un refresh token activo (identificado por su JTI)."""
    return f"refresh:{jti}"
