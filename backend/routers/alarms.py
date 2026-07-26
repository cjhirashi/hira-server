import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from core.redis import get_redis
from models.alarm_definitions import AlarmDefinition
from models.alarms import AlarmEvent
from models.points import Point
from models.users import User
from schemas.alarms import AlarmEventResponse

router = APIRouter(prefix="/alarms", tags=["Alarms"])
logger = get_logger(__name__)


async def _to_response(event: AlarmEvent, session: Any) -> AlarmEventResponse:
    point = await session.get(Point, event.point_id)
    defn = await session.get(AlarmDefinition, event.definition_id)
    acknowledged_by_name: str | None = None
    if event.acknowledged_by is not None:
        user = await session.get(User, event.acknowledged_by)
        if user:
            acknowledged_by_name = user.full_name or user.email

    return AlarmEventResponse(
        id=event.id,
        alarm_definition_id=event.definition_id,
        point_id=event.point_id,
        point_name=point.name if point else f"point:{event.point_id}",
        triggered_value=event.triggered_value,
        priority=defn.priority if defn else "low",
        message=defn.message if defn else "",
        status=event.status,
        triggered_at=event.triggered_at,
        acknowledged_at=event.acknowledged_at,
        acknowledged_by=acknowledged_by_name,
        resolved_at=event.resolved_at,
    )


@router.get("", response_model=list[AlarmEventResponse])
async def list_active_alarms(
    _: dict[str, Any] = Depends(require_permission("alarms:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        rows = (
            await session.execute(
                select(AlarmEvent)
                .where(AlarmEvent.status == "active")
                .order_by(AlarmEvent.triggered_at.desc())
            )
        ).scalars().all()
        return [await _to_response(e, session) for e in rows]


@router.get("/history", response_model=list[AlarmEventResponse])
async def get_alarm_history(
    point_id: int | None = Query(default=None),
    priority: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0),
    _: dict[str, Any] = Depends(require_permission("alarms:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        q = select(AlarmEvent).order_by(AlarmEvent.triggered_at.desc())
        if point_id is not None:
            q = q.where(AlarmEvent.point_id == point_id)
        if status is not None:
            q = q.where(AlarmEvent.status == status)
        if from_dt is not None:
            q = q.where(AlarmEvent.triggered_at >= from_dt)
        if to_dt is not None:
            q = q.where(AlarmEvent.triggered_at <= to_dt)
        if priority is not None:
            q = q.join(AlarmDefinition, AlarmEvent.definition_id == AlarmDefinition.id).where(AlarmDefinition.priority == priority)
        q = q.limit(limit).offset(offset)
        rows = (await session.execute(q)).scalars().all()

        results = []
        for e in rows:
            results.append(await _to_response(e, session))
        return results


@router.post("/{alarm_id}/acknowledge", response_model=AlarmEventResponse)
async def acknowledge_alarm(
    alarm_id: int,
    current_user: dict[str, Any] = Depends(require_permission("alarms:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        event = await session.get(AlarmEvent, alarm_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Alarma no encontrada")
        if event.status != "active":
            raise HTTPException(status_code=422, detail=f"Alarma ya está en estado '{event.status}'")

        user_id = int(current_user["sub"])
        now = datetime.now(timezone.utc)
        event.status = "acknowledged"
        event.acknowledged_at = now
        event.acknowledged_by = user_id
        await session.flush()

        response = await _to_response(event, session)

    redis = await get_redis()
    await redis.publish(
        "alarm:updates",
        json.dumps({
            "type": "acknowledged",
            "alarm_id": alarm_id,
            "acknowledged_by": current_user.get("sub"),
            "acknowledged_at": now.isoformat(),
        }),
    )
    logger.info("Alarma reconocida", extra={"alarm_id": alarm_id, "user_id": user_id})
    return response
