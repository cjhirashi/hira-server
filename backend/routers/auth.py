from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.redis import get_redis, get_refresh_key
from core.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    verify_password,
)
from models.user_roles import UserRole
from models.users import User
from schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserInToken

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = get_logger(__name__)


async def _get_user_with_role(session, email: str) -> tuple[User, str] | None:
    """Devuelve (User, role_name) o None si no existe."""
    result = await session.execute(
        select(User, UserRole)
        .join(UserRole, UserRole.user_id == User.id)
        .where(User.email == email)
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    user, user_role = row

    from models.roles import Role
    role = await session.get(Role, user_role.role_id)
    return user, (role.name if role else "")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await _get_user_with_role(session, body.email)
        if result is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        user, role_name = result

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        if not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        from datetime import datetime, timezone
        await session.execute(
            update(User).where(User.id == user.id).values(last_login=datetime.now(timezone.utc))
        )

        access_token = create_access_token(user.id, user.email, role_name)
        refresh_token = await create_refresh_token(user.id)

    logger.info("Login exitoso", extra={"user_id": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        user=UserInToken(id=user.id, email=user.email, full_name=user.full_name, role=role_name),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> Any:
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    jti = payload.get("jti", "")
    user_id = int(payload["sub"])

    redis = await get_redis()
    stored = await redis.get(get_refresh_key(jti))
    if stored is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    await redis.delete(get_refresh_key(jti))

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            select(User, UserRole)
            .join(UserRole, UserRole.user_id == User.id)
            .where(User.id == user_id)
            .limit(1)
        )
        row = result.first()
        if row is None or not row[0].is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

        user, user_role = row
        from models.roles import Role
        role = await session.get(Role, user_role.role_id)
        role_name = role.name if role else ""

    access_token = create_access_token(user.id, user.email, role_name)
    new_refresh = await create_refresh_token(user.id)

    logger.info("Token renovado", extra={"user_id": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        user=UserInToken(id=user.id, email=user.email, full_name=user.full_name, role=role_name),
    )


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    payload = decode_token(body.refresh_token)
    jti = payload.get("jti", "")

    if jti:
        redis = await get_redis()
        await redis.delete(get_refresh_key(jti))

    logger.info("Logout", extra={"user_id": current_user["sub"]})
    return {"message": "Sesión cerrada"}
