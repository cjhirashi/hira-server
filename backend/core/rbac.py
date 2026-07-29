"""
RBAC — carga, caché y validación de permisos.

Los permisos se almacenan en BD (tabla permissions) y se cachean en Redis
bajo la clave `rbac:{user_id}` como JSON serializado (lista de strings
en formato `{module}:{access_level}`, e.g. `users:read`, `points:write`).

TTL del caché: 7 días. Se invalida explícitamente al cambiar el rol del usuario.
"""
import json
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.redis import get_rbac_key, get_redis
from core.security import get_current_user

logger = get_logger(__name__)

_RBAC_TTL = 7 * 86400  # 7 días en segundos

# Permisos por rol (fuente de verdad complementaria al seed en BD)
_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Admin": [
        "users:read", "users:write",
        "points:read", "points:write",
        "devices:read", "devices:write",
        "alarms:read", "alarms:write",
        "logic:read", "logic:write",
        "historicals:read",
        "backup:read", "backup:write",
        "config:read", "config:write",
        "ai:read", "ai:write",
        "system:read",
        "notifications:read", "notifications:write",
    ],
    "Operador": [
        "users:read",
        "points:read", "points:write",
        "devices:read", "devices:write",
        "alarms:read", "alarms:write",
        "logic:read", "logic:write",
        "historicals:read",
        "config:read", "config:write",
        "ai:read", "ai:write",
        "system:read",
        "notifications:read",
    ],
    "Visor": [
        "points:read",
        "devices:read",
        "alarms:read",
        "historicals:read",
        "config:read",
    ],
}


async def get_user_permissions(user_id: int, role: str) -> list[str]:
    """
    Devuelve los permisos del usuario. Lee del caché Redis; si no existe,
    los construye desde la tabla de permisos del rol y los cachea.
    """
    redis = await get_redis()
    key = get_rbac_key(user_id)

    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    permissions = _ROLE_PERMISSIONS.get(role, [])
    await redis.setex(key, _RBAC_TTL, json.dumps(permissions))
    logger.info(
        "RBAC cargado y cacheado",
        extra={"user_id": user_id, "role": role, "permissions_count": len(permissions)},
    )
    return permissions


async def invalidate_user_permissions(user_id: int) -> None:
    """Elimina el caché RBAC del usuario. Llamar al cambiar su rol."""
    redis = await get_redis()
    key = get_rbac_key(user_id)
    deleted = await redis.delete(key)
    if deleted:
        logger.info("RBAC invalidado", extra={"user_id": user_id})


def require_permission(permission: str):
    """
    Dependencia FastAPI que verifica que el usuario autenticado tenga
    el permiso requerido. Formato: `{module}:{access_level}`.

    Ejemplo:
        @router.post("/users", dependencies=[Depends(require_permission("users:write"))])
    """
    async def _check(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_id = int(current_user["sub"])
        role = current_user.get("role", "")
        permissions = await get_user_permissions(user_id, role)
        if permission not in permissions:
            logger.warning(
                "Acceso denegado",
                extra={"user_id": user_id, "role": role, "required": permission},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission}",
            )
        return current_user

    return _check
