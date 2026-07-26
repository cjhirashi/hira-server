from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import invalidate_user_permissions, require_permission
from core.security import get_current_user, hash_password
from models.roles import Role
from models.user_roles import UserRole
from models.users import User
from schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger(__name__)


async def _fetch_user_response(session, user_id: int) -> UserResponse | None:
    """Carga User + primer Role y devuelve UserResponse o None."""
    result = await session.execute(
        select(User, UserRole, Role)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.id == user_id)
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    user, user_role, role = row
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_id=role.id,
        role_name=role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    _: dict[str, Any] = Depends(require_permission("users:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            select(User, UserRole, Role)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .offset(skip)
            .limit(min(limit, 100))
        )
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role_id=role.id,
                role_name=role.name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            for user, user_role, role in result.all()
        ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    _: dict[str, Any] = Depends(require_permission("users:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        existing = await session.scalar(select(User).where(User.email == body.email))
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")

        role = await session.get(Role, body.role_id)
        if role is None:
            raise HTTPException(status_code=400, detail=f"Rol {body.role_id} no existe")

        user = User(
            email=body.email,
            full_name=body.full_name,
            password_hash=hash_password(body.password),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        session.add(UserRole(user_id=user.id, role_id=body.role_id))
        await session.flush()

    logger.info("Usuario creado", extra={"user_id": user.id, "email": user.email})

    async with adapter.get_session() as session:
        return await _fetch_user_response(session, user.id)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    requesting_user_id = int(current_user["sub"])
    # Un usuario siempre puede ver su propio perfil
    if requesting_user_id != user_id:
        # Verificar permiso users:read para ver otros usuarios
        from core.rbac import get_user_permissions
        permissions = await get_user_permissions(requesting_user_id, current_user.get("role", ""))
        if "users:read" not in permissions:
            raise HTTPException(status_code=403, detail="Permiso requerido: users:read")

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        response = await _fetch_user_response(session, user_id)

    if response is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return response


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    _: dict[str, Any] = Depends(require_permission("users:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        if body.full_name is not None:
            user.full_name = body.full_name
        if body.is_active is not None:
            user.is_active = body.is_active

        role_changed = False
        if body.role_id is not None:
            role = await session.get(Role, body.role_id)
            if role is None:
                raise HTTPException(status_code=400, detail=f"Rol {body.role_id} no existe")

            user_role = await session.scalar(select(UserRole).where(UserRole.user_id == user_id))
            if user_role:
                user_role.role_id = body.role_id
            else:
                session.add(UserRole(user_id=user_id, role_id=body.role_id))
            role_changed = True

    if role_changed:
        await invalidate_user_permissions(user_id)
        logger.info("Rol de usuario actualizado — RBAC invalidado", extra={"user_id": user_id})

    adapter2 = get_db_adapter()
    async with adapter2.get_session() as session:
        return await _fetch_user_response(session, user_id)


@router.patch("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    requesting_user_id = int(current_user["sub"])
    if requesting_user_id == user_id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.is_active = False

    await invalidate_user_permissions(user_id)
    logger.info("Usuario desactivado (disable endpoint)", extra={"user_id": user_id})

    async with adapter.get_session() as session:
        return await _fetch_user_response(session, user_id)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(require_permission("users:write")),
) -> dict[str, str]:
    requesting_user_id = int(current_user["sub"])
    if requesting_user_id == user_id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.is_active = False

    await invalidate_user_permissions(user_id)
    logger.info("Usuario desactivado", extra={"user_id": user_id})
    return {"message": "Usuario desactivado"}
