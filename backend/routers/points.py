import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from adapters.factory import get_db_adapter, get_protocol_adapter
from core.logger import get_logger
from core.rbac import require_permission
from core.redis import get_redis
from models.points import Point
from schemas.points import PointValue, PointWriteRequest, PointWriteResponse

router = APIRouter(prefix="/points", tags=["Points"])
logger = get_logger(__name__)


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
