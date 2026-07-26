"""
Motor de evaluación de alarmas.

Evalúa condiciones contra el valor actual de un punto y gestiona el ciclo de vida:
active → resolved si la condición ya no se cumple.

Mantiene un caché en memoria de las AlarmDefinition con TTL de 60s para
no consultar la BD en cada ciclo de polling.
"""
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.alarm_definitions import AlarmDefinition
from models.alarms import AlarmEvent

logger = get_logger(__name__)

_TTL = 60  # segundos de caché para definiciones


class AlarmEngine:
    def __init__(self) -> None:
        self._cache: dict[int, list[AlarmDefinition]] = {}
        self._cache_ts: dict[int, float] = {}

    async def _get_definitions(self, point_id: int, session: AsyncSession) -> list[AlarmDefinition]:
        import time

        now = time.monotonic()
        if point_id in self._cache and now - self._cache_ts.get(point_id, 0) < _TTL:
            return self._cache[point_id]

        rows = (
            await session.execute(
                select(AlarmDefinition)
                .where(AlarmDefinition.point_id == point_id, AlarmDefinition.enabled == True)  # noqa: E712
            )
        ).scalars().all()
        self._cache[point_id] = list(rows)
        self._cache_ts[point_id] = now
        return self._cache[point_id]

    def _condition_met(self, defn: AlarmDefinition, value: float) -> bool:
        if defn.condition == "gt":
            return value > defn.threshold
        if defn.condition == "lt":
            return value < defn.threshold
        if defn.condition == "eq":
            return abs(value - defn.threshold) < 1e-9
        if defn.condition == "between" and defn.threshold_high is not None:
            return defn.threshold <= value <= defn.threshold_high
        return False

    def invalidate_cache(self, point_id: int | None = None) -> None:
        if point_id is None:
            self._cache.clear()
            self._cache_ts.clear()
        else:
            self._cache.pop(point_id, None)
            self._cache_ts.pop(point_id, None)

    async def evaluate(self, point_id: int, value: float, session: AsyncSession, redis: Any) -> None:
        """
        Evalúa todas las definiciones habilitadas para point_id contra value.
        Crea eventos nuevos o resuelve eventos existentes según corresponda.
        """
        definitions = await self._get_definitions(point_id, session)
        if not definitions:
            return

        for defn in definitions:
            condition_met = self._condition_met(defn, value)
            existing_active = (
                await session.execute(
                    select(AlarmEvent)
                    .where(
                        AlarmEvent.definition_id == defn.id,
                        AlarmEvent.status == "active",
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

            now = datetime.now(timezone.utc)

            if condition_met and existing_active is None:
                event = AlarmEvent(
                    definition_id=defn.id,
                    point_id=point_id,
                    triggered_value=value,
                    value_at_trigger=value,
                    status="active",
                    triggered_at=now,
                )
                session.add(event)
                await session.flush()

                payload = {
                    "type": "new",
                    "alarm_id": event.id,
                    "alarm_definition_id": defn.id,
                    "point_id": point_id,
                    "triggered_value": value,
                    "priority": defn.priority,
                    "message": defn.message,
                    "status": "active",
                    "triggered_at": now.isoformat(),
                }
                await redis.publish("alarm:updates", json.dumps(payload))
                logger.info(
                    "Alarma disparada",
                    extra={"definition_id": defn.id, "point_id": point_id, "value": value, "priority": defn.priority},
                )

            elif not condition_met and existing_active is not None:
                existing_active.status = "resolved"
                existing_active.resolved_at = now
                await session.flush()

                payload = {
                    "type": "resolved",
                    "alarm_id": existing_active.id,
                    "point_id": point_id,
                    "resolved_at": now.isoformat(),
                }
                await redis.publish("alarm:updates", json.dumps(payload))
                logger.info(
                    "Alarma resuelta",
                    extra={"alarm_id": existing_active.id, "point_id": point_id},
                )


alarm_engine = AlarmEngine()
