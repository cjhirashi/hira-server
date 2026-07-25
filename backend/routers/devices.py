import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from adapters.factory import get_db_adapter, get_protocol_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.devices import Device
from models.points import Point
from schemas.devices import DeviceCreate, DeviceResponse, DeviceScanResult, DeviceUpdate
from schemas.points import PointValue

router = APIRouter(prefix="/devices", tags=["Devices"])
logger = get_logger(__name__)


def _device_to_response(d: Device) -> DeviceResponse:
    return DeviceResponse(
        id=d.id, name=d.name, protocol=d.protocol, address=d.address,
        port=d.port, config_json=d.config_json, area=d.area,
        status=d.status, is_simulator=d.is_simulator, auto_start=d.auto_start,
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    protocol: str | None = None,
    status: str | None = None,
    _: dict[str, Any] = Depends(require_permission("devices:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        q = select(Device)
        if protocol:
            q = q.where(Device.protocol == protocol)
        if status:
            q = q.where(Device.status == status)
        devices = (await session.execute(q)).scalars().all()
    return [_device_to_response(d) for d in devices]


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    body: DeviceCreate,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = Device(
            name=body.name, protocol=body.protocol, address=body.address,
            port=body.port, config_json=body.config_json,
            area=body.area or "", auto_start=body.auto_start,
            status="unknown", is_simulator=False,
        )
        session.add(device)
        await session.flush()
        device_id = device.id

    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
    logger.info("Dispositivo creado", extra={"device_id": device_id})
    return _device_to_response(device)


@router.post("/scan", response_model=DeviceScanResult)
async def scan_devices(
    body: dict[str, Any],
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    proto = body.get("protocol", "bacnet")
    timeout_s = min(int(body.get("timeout_s", 5)), 30)

    t0 = time.monotonic()
    try:
        protocol_adapter = get_protocol_adapter(proto)
        await protocol_adapter.connect()
        raw_devices = await protocol_adapter.scan()
        await protocol_adapter.disconnect()
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Scan error", extra={"protocol": proto, "error": str(exc)})
        raise HTTPException(status_code=503, detail=f"Error de escaneo: {exc}")

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    db_adapter = get_db_adapter()
    result_devices: list[DeviceResponse] = []

    for raw in raw_devices:
        async with db_adapter.get_session() as session:
            existing = await session.scalar(
                select(Device).where(
                    Device.protocol == proto,
                    Device.address == raw.get("ip", raw.get("topic", "")),
                )
            )
            if existing is None:
                device = Device(
                    name=raw.get("name", f"{proto}-{raw.get('instance', 'unknown')}"),
                    protocol=proto, address=raw.get("ip", raw.get("topic", "")),
                    port=None, config_json=raw, area="", status="online",
                    is_simulator=False, auto_start=False,
                )
                session.add(device)
                await session.flush()
                existing = device

        result_devices.append(_device_to_response(existing))

    return DeviceScanResult(discovered=result_devices, scan_duration_ms=elapsed_ms)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    _: dict[str, Any] = Depends(require_permission("devices:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return _device_to_response(device)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

        # Protección: no se puede cambiar is_simulator a False
        if body.is_simulator is not None and not body.is_simulator and device.is_simulator:
            raise HTTPException(
                status_code=422,
                detail="No se puede cambiar is_simulator a false sin validación explícita",
            )

        if body.name is not None:
            device.name = body.name
        if body.address is not None:
            device.address = body.address
        if body.port is not None:
            device.port = body.port
        if body.config_json is not None:
            device.config_json = body.config_json
        if body.area is not None:
            device.area = body.area
        if body.auto_start is not None:
            device.auto_start = body.auto_start

    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
    return _device_to_response(device)


@router.get("/{device_id}/points", response_model=list[PointValue])
async def list_device_points(
    device_id: int,
    _: dict[str, Any] = Depends(require_permission("points:read")),
) -> Any:
    from core.redis import get_redis
    import json
    from datetime import datetime, timezone

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        points = (await session.execute(
            select(Point).where(Point.device_id == device_id)
        )).scalars().all()

    redis = await get_redis()
    result = []
    for pt in points:
        raw = await redis.get(f"point:{pt.id}:value")
        if raw:
            data = json.loads(raw)
        else:
            data = {
                "value": None, "quality": "uncertain",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        result.append(PointValue(
            id=pt.id, name=pt.name, value=data.get("value"),
            unit=pt.unit, quality=data.get("quality", "uncertain"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        ))
    return result
