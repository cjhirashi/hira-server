"""
Worker de alarmas — tarea Celery que evalúa condiciones cada 10s via Celery Beat.

Lee todos los puntos con al menos una alarm_definition habilitada, obtiene
el valor actual de Redis, y delega la evaluación a AlarmEngine.
"""
import asyncio
import json

import redis as sync_redis

from core.config import settings
from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="workers.alarm_worker.evaluate_alarms", queue="normal")
def evaluate_alarms() -> None:
    asyncio.run(_evaluate_alarms_async())


async def _evaluate_alarms_async() -> None:
    import redis.asyncio as aioredis
    from sqlalchemy import select, distinct

    from adapters.factory import get_db_adapter
    from models.alarm_definitions import AlarmDefinition
    from services.alarm_engine import alarm_engine

    adapter = get_db_adapter()
    # Create a fresh Redis client per invocation — avoids event-loop conflicts
    # when asyncio.run() creates a new loop on each Celery task execution.
    redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    try:
        async with adapter.get_session() as session:
            point_ids = (
                await session.execute(
                    select(distinct(AlarmDefinition.point_id)).where(AlarmDefinition.enabled == True)  # noqa: E712
                )
            ).scalars().all()

            if not point_ids:
                return

            for point_id in point_ids:
                raw = await redis.get(f"point:{point_id}:value")
                if raw is None:
                    continue
                try:
                    data = json.loads(raw)
                    value = data.get("value")
                    if value is None:
                        continue
                    value = float(value)
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue

                try:
                    await alarm_engine.evaluate(point_id, value, session, redis)
                except Exception as exc:
                    logger.error(
                        "Error evaluando alarmas para punto",
                        extra={"point_id": point_id, "error": str(exc)},
                    )
    finally:
        await redis.aclose()
