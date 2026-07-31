"""
Tarea Celery que expira automáticamente sesiones de ingeniería sin heartbeat.

Se ejecuta cada 30s vía Celery Beat.
Una sesión expira si no recibió heartbeat en los últimos 120 segundos.
"""
import asyncio

from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="workers.engineering_session_tasks.expire_engineering_sessions", queue="normal")
def expire_engineering_sessions() -> str:
    return asyncio.run(_expire_async())


async def _expire_async() -> str:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from adapters.factory import get_db_adapter
    from models.engineering_session import EngineeringSession, SessionStatus

    threshold = datetime.now(timezone.utc) - timedelta(seconds=120)

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        stale = (
            await session.scalars(
                select(EngineeringSession).where(
                    EngineeringSession.status == SessionStatus.active,
                    EngineeringSession.last_heartbeat_at < threshold,
                )
            )
        ).all()

        count = len(stale)
        for s in stale:
            s.status = SessionStatus.expired
            logger.info(
                "Sesión de ingeniería expirada por inactividad",
                extra={"session_id": s.id, "engineer_user_id": s.engineer_user_id},
            )

        if count:
            await session.flush()

    return f"Expiradas: {count} sesiones"
