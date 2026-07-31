"""
Router de Sesión de Ingeniería Remota (ADR-016).

POST   /engineering-sessions/          → abrir sesión (Admin)
GET    /engineering-sessions/active    → sesión activa o null (todos)
POST   /engineering-sessions/{id}/heartbeat → renovar heartbeat (solo el engineer)
POST   /engineering-sessions/{id}/close    → cerrar sesión (Admin o dueño)
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from core.logger import get_logger
from core.rbac import require_permission
from core.security import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/engineering-sessions", tags=["Engineering Sessions"])


@router.post("/", status_code=201)
async def open_session(
    notes: str | None = Query(default=None, max_length=500),
    user: dict = Depends(require_permission("config:write")),
) -> Any:
    """Abre una nueva sesión de ingeniería. Solo puede existir una activa a la vez."""
    from adapters.factory import get_db_adapter
    from models.engineering_session import EngineeringSession, SessionStatus
    import uuid

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        existing = await session.scalar(
            select(EngineeringSession).where(EngineeringSession.status == SessionStatus.active)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe una sesión de ingeniería activa")

        now = datetime.now(timezone.utc)
        new_session = EngineeringSession(
            session_token=str(uuid.uuid4()),
            engineer_user_id=int(user["sub"]),
            started_at=now,
            expires_at=now + timedelta(hours=8),
            last_heartbeat_at=now,
            status=SessionStatus.active,
            notes=notes,
        )
        session.add(new_session)
        await session.flush()
        session_id = new_session.id
        session_token = new_session.session_token
        expires_at = new_session.expires_at

    logger.info(
        "Sesión de ingeniería abierta",
        extra={"session_id": session_id, "engineer_user_id": int(user["sub"])},
    )
    return {
        "session_id": session_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/active")
async def get_active_session(
    user: dict = Depends(get_current_user),
) -> Any:
    """Retorna la sesión activa actual, o null si no hay ninguna."""
    from adapters.factory import get_db_adapter
    from models.engineering_session import EngineeringSession, SessionStatus
    from models.users import User

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        active = await session.scalar(
            select(EngineeringSession).where(EngineeringSession.status == SessionStatus.active)
        )
        if not active:
            return None

        engineer = await session.get(User, active.engineer_user_id)
        engineer_name = engineer.full_name or engineer.email if engineer else "Desconocido"

    return {
        "session_id": active.id,
        "engineer_user_id": active.engineer_user_id,
        "engineer_name": engineer_name,
        "started_at": active.started_at.isoformat(),
        "expires_at": active.expires_at.isoformat(),
        "last_heartbeat_at": active.last_heartbeat_at.isoformat(),
        # session_token NO se expone aquí
    }


@router.post("/{session_id}/heartbeat")
async def heartbeat(
    session_id: int,
    user: dict = Depends(get_current_user),
) -> Any:
    """Renueva el heartbeat de la sesión. Solo el engineer que la abrió puede hacerlo."""
    from adapters.factory import get_db_adapter
    from models.engineering_session import EngineeringSession, SessionStatus

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        eng_session = await session.get(EngineeringSession, session_id)
        if not eng_session or eng_session.status != SessionStatus.active:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o no activa")
        if eng_session.engineer_user_id != int(user["sub"]):
            raise HTTPException(
                status_code=403,
                detail="Solo el ingeniero que abrió la sesión puede enviar heartbeat",
            )
        now = datetime.now(timezone.utc)
        eng_session.last_heartbeat_at = now
        await session.flush()
        last_hb = eng_session.last_heartbeat_at

    return {"last_heartbeat_at": last_hb.isoformat()}


@router.post("/{session_id}/close")
async def close_session(
    session_id: int,
    user: dict = Depends(get_current_user),
) -> Any:
    """Cierra la sesión. Permitido para Admin o el engineer que la abrió."""
    from adapters.factory import get_db_adapter
    from models.engineering_session import EngineeringSession, SessionStatus

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        eng_session = await session.get(EngineeringSession, session_id)
        if not eng_session or eng_session.status != SessionStatus.active:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o no activa")

        is_admin = user.get("role", "") == "Admin"
        is_owner = eng_session.engineer_user_id == int(user["sub"])
        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Sin permisos para cerrar esta sesión")

        eng_session.status = SessionStatus.closed
        await session.flush()

    logger.info(
        "Sesión de ingeniería cerrada",
        extra={"session_id": session_id, "closed_by": int(user["sub"])},
    )
    return {"status": "closed"}
