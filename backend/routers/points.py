import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from adapters.factory import get_db_adapter, get_protocol_adapter
from core.logger import get_logger
from core.rbac import require_permission
from core.redis import get_redis
from models.areas import Area
from models.devices import Device
from models.points import Point
from schemas.points import PointCreate, PointResponse, PointUpdate, PointValue, PointWriteRequest, PointWriteResponse

router = APIRouter(prefix="/points", tags=["Points"])
logger = get_logger(__name__)


def _to_response(p: Point, area_name: str | None = None) -> PointResponse:
    return PointResponse(
        id=p.id,
        device_id=p.device_id,
        name=p.name,
        description=p.description,
        object_type=p.object_type,
        address=p.address,
        unit=p.unit,
        writable=p.writable,
        log_enabled=p.log_enabled,
        history_interval_seconds=p.history_interval_seconds,
        area_id=p.area_id,
        area_name=area_name,
        modbus_register_type=p.modbus_register_type,
        modbus_data_type=p.modbus_data_type,
    )


@router.post("", response_model=PointResponse, status_code=201, tags=["Configurator"])
async def create_point(
    body: PointCreate,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, body.device_id)
        if device is None:
            raise HTTPException(status_code=400, detail=f"Dispositivo {body.device_id} no existe")

        area_name: str | None = None
        if body.area_id is not None:
            area = await session.get(Area, body.area_id)
            if area is None:
                raise HTTPException(status_code=400, detail=f"Área {body.area_id} no existe")
            area_name = area.name

        point = Point(
            device_id=body.device_id,
            name=body.name,
            description=body.description,
            object_type=body.object_type,
            address=body.address,
            unit=body.unit,
            writable=body.writable,
            log_enabled=body.log_enabled,
            history_interval_seconds=body.history_interval_seconds,
            area_id=body.area_id,
            modbus_register_type=body.modbus_register_type,
            modbus_data_type=body.modbus_data_type,
        )
        session.add(point)
        await session.flush()
        point_id = point.id

    logger.info("Punto creado", extra={"point_id": point_id, "device_id": body.device_id})

    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
    return _to_response(point, area_name)


@router.get("/{point_id}", response_model=PointResponse, tags=["Points"])
async def get_point(
    point_id: int,
    _: dict[str, Any] = Depends(require_permission("points:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Punto no encontrado")
        area_name: str | None = None
        if point.area_id is not None:
            area = await session.get(Area, point.area_id)
            area_name = area.name if area else None
    return _to_response(point, area_name)


@router.put("/{point_id}", response_model=PointResponse, tags=["Configurator"])
async def update_point(
    point_id: int,
    body: PointUpdate,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Punto no encontrado")

        area_name: str | None = None
        if body.area_id is not None:
            area = await session.get(Area, body.area_id)
            if area is None:
                raise HTTPException(status_code=400, detail=f"Área {body.area_id} no existe")
            area_name = area.name
        elif point.area_id is not None:
            area = await session.get(Area, point.area_id)
            area_name = area.name if area else None

        if body.name is not None:
            point.name = body.name
        if body.description is not None:
            point.description = body.description
        if body.unit is not None:
            point.unit = body.unit
        if body.writable is not None:
            point.writable = body.writable
        if body.log_enabled is not None:
            point.log_enabled = body.log_enabled
        if body.history_interval_seconds is not None:
            point.history_interval_seconds = body.history_interval_seconds
        if "area_id" in body.model_fields_set:
            point.area_id = body.area_id
        if "modbus_register_type" in body.model_fields_set:
            point.modbus_register_type = body.modbus_register_type
        if "modbus_data_type" in body.model_fields_set:
            point.modbus_data_type = body.modbus_data_type

    logger.info("Punto actualizado", extra={"point_id": point_id})

    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
        if point.area_id is not None and area_name is None:
            area = await session.get(Area, point.area_id)
            area_name = area.name if area else None
    return _to_response(point, area_name)


@router.delete("/{point_id}", status_code=204, tags=["Configurator"])
async def delete_point(
    point_id: int,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Punto no encontrado")
        await session.delete(point)
    logger.info("Punto eliminado", extra={"point_id": point_id})


@router.get("/{point_id}/value", response_model=PointValue)
async def get_point_value(
    point_id: int,
    _: dict[str, Any] = Depends(require_permission("points:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="Punto no encontrado")

    redis = await get_redis()
    raw = await redis.get(f"point:{point_id}:value")
    if raw:
        data = json.loads(raw)
    else:
        data = {
            "value": None,
            "quality": "uncertain",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return PointValue(
        id=point.id,
        name=point.name,
        value=data.get("value"),
        unit=point.unit,
        quality=data.get("quality", "uncertain"),
        timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


@router.post("/{point_id}/write", response_model=PointWriteResponse)
async def write_point(
    point_id: int,
    body: PointWriteRequest,
    current_user: dict[str, Any] = Depends(require_permission("points:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from models.devices import Device

        point = await session.get(Point, point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Punto no encontrado")
        if not point.writable:
            raise HTTPException(status_code=422, detail="El punto no es escribible")

        device = await session.get(Device, point.device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo del punto no encontrado")

    if device.status == "offline":
        raise HTTPException(status_code=503, detail="Dispositivo offline — escritura no disponible")

    try:
        protocol_adapter = get_protocol_adapter(device.protocol)
        await protocol_adapter.connect(device.config_json)
        success = await protocol_adapter.write_point(
            device_id=str(device.id),
            point_address=point.address,
            value=body.value,
        )
        await protocol_adapter.disconnect()
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Error al escribir punto",
            extra={"point_id": point_id, "device_id": device.id, "error": str(exc)},
        )
        raise HTTPException(status_code=503, detail=f"Error de escritura: {exc}")

    timestamp = datetime.now(timezone.utc).isoformat()

    if success:
        redis = await get_redis()
        await redis.set(
            f"point:{point_id}:value",
            json.dumps({"value": body.value, "quality": "good", "timestamp": timestamp}),
            ex=60,
        )
        logger.info(
            "Punto escrito",
            extra={"point_id": point_id, "value": body.value, "user": current_user.get("sub")},
        )

    return PointWriteResponse(success=success, value=body.value if success else None, timestamp=timestamp)
