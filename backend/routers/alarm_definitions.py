from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.alarm_definitions import AlarmDefinition
from schemas.alarms import AlarmDefinitionCreate, AlarmDefinitionResponse

router = APIRouter(prefix="/alarm-definitions", tags=["Alarms"])
logger = get_logger(__name__)


def _to_response(d: AlarmDefinition) -> AlarmDefinitionResponse:
    return AlarmDefinitionResponse(
        id=d.id,
        point_id=d.point_id,
        name=d.name,
        condition=d.condition,
        threshold=d.threshold,
        threshold_high=d.threshold_high,
        priority=d.priority,
        message=d.message,
        enabled=d.enabled,
        created_at=d.created_at,
    )


@router.get("", response_model=list[AlarmDefinitionResponse])
async def list_alarm_definitions(
    _: dict[str, Any] = Depends(require_permission("alarms:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        rows = (await session.execute(select(AlarmDefinition).order_by(AlarmDefinition.id))).scalars().all()
    return [_to_response(d) for d in rows]


@router.post("", response_model=AlarmDefinitionResponse, status_code=201)
async def create_alarm_definition(
    body: AlarmDefinitionCreate,
    _: dict[str, Any] = Depends(require_permission("alarms:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        defn = AlarmDefinition(
            point_id=body.point_id,
            name=body.name,
            condition=body.condition,
            threshold=body.threshold,
            threshold_high=body.threshold_high,
            priority=body.priority,
            message=body.message,
            enabled=body.enabled,
        )
        session.add(defn)
        await session.flush()
        defn_id = defn.id

    async with adapter.get_session() as session:
        defn = await session.get(AlarmDefinition, defn_id)

    logger.info("AlarmDefinition creada", extra={"defn_id": defn_id, "defn_name": body.name})
    return _to_response(defn)


@router.put("/{defn_id}", response_model=AlarmDefinitionResponse)
async def update_alarm_definition(
    defn_id: int,
    body: AlarmDefinitionCreate,
    _: dict[str, Any] = Depends(require_permission("alarms:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        defn = await session.get(AlarmDefinition, defn_id)
        if defn is None:
            raise HTTPException(status_code=404, detail="Definición no encontrada")
        defn.point_id = body.point_id
        defn.name = body.name
        defn.condition = body.condition
        defn.threshold = body.threshold
        defn.threshold_high = body.threshold_high
        defn.priority = body.priority
        defn.message = body.message
        defn.enabled = body.enabled
        await session.flush()

    async with adapter.get_session() as session:
        defn = await session.get(AlarmDefinition, defn_id)

    logger.info("AlarmDefinition actualizada", extra={"id": defn_id})
    return _to_response(defn)


@router.delete("/{defn_id}", status_code=204)
async def delete_alarm_definition(
    defn_id: int,
    _: dict[str, Any] = Depends(require_permission("alarms:admin")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        defn = await session.get(AlarmDefinition, defn_id)
        if defn is None:
            raise HTTPException(status_code=404, detail="Definición no encontrada")
        await session.delete(defn)
    logger.info("AlarmDefinition eliminada", extra={"id": defn_id})
