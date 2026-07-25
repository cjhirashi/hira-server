from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.logger import get_logger
from core.redis import get_rbac_key, get_redis, get_refresh_key

logger = get_logger(__name__)

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 15
_REFRESH_TOKEN_EXPIRE_DAYS = 7

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Contraseñas ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _build_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def create_access_token(user_id: int, email: str, role: str) -> str:
    return _build_token(
        {"sub": str(user_id), "email": email, "role": role, "type": "access"},
        timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


async def create_refresh_token(user_id: int) -> str:
    """Crea refresh token y lo registra en Redis con TTL de 7 días."""
    jti = str(uuid4())
    token = _build_token(
        {"sub": str(user_id), "jti": jti, "type": "refresh"},
        timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    redis = await get_redis()
    ttl = _REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(get_refresh_key(jti), ttl, str(user_id))
    return token


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza HTTPException 401 si es inválido."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning("Token JWT inválido", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependencia FastAPI ───────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """
    Dependencia de FastAPI que extrae y valida el JWT Bearer.
    Devuelve el payload del token (sub, email, role).
    Lanza 401 si el token falta o es inválido.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


ACCESS_TOKEN_EXPIRE_SECONDS = _ACCESS_TOKEN_EXPIRE_MINUTES * 60
