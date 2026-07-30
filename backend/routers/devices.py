import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.devices import Device
from models.points import Point
from schemas.devices import DeviceCreate, DeviceResponse, DeviceUpdate, ScanRequest, ScanResponse
from schemas.points import PointValue

router = APIRouter(prefix="/devices", tags=["Devices"])
logger = get_logger(__name__)


def _device_to_response(d: Device) -> DeviceResponse:
    return DeviceResponse(
        id=d.id, name=d.name, protocol=d.protocol, address=d.address,
        port=d.port, config_json=d.config_json, area=d.area,
        status=d.status, is_simulator=d.is_simulator, auto_start=d.auto_start,
        modbus_unit_id=d.modbus_unit_id,
        modbus_transport=d.modbus_transport,
        modbus_baudrate=d.modbus_baudrate,
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
            modbus_unit_id=body.modbus_unit_id,
            modbus_transport=body.modbus_transport,
            modbus_baudrate=body.modbus_baudrate,
        )
        session.add(device)
        await session.flush()
        device_id = device.id

    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
    logger.info("Dispositivo creado", extra={"device_id": device_id})
    return _device_to_response(device)


@router.post("/scan", response_model=ScanResponse)
async def scan_devices(
    body: ScanRequest,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    import asyncio as _asyncio
    from services import scan_service

    opts = body.options or {}
    t0 = time.monotonic()

    if body.protocol == "bacnet":
        timeout = int(opts.get("timeout_seconds", 5))
        candidates = await _asyncio.to_thread(scan_service.scan_bacnet, timeout)

    elif body.protocol == "modbus":
        ip_range = str(opts.get("ip_range", "192.168.1.1-254"))
        port = int(opts.get("port", 502))
        timeout_per_host = float(opts.get("timeout_per_host", 1.0))
        try:
            candidates = await _asyncio.to_thread(
                scan_service.scan_modbus, ip_range, port, timeout_per_host
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    else:  # mqtt
        duration = int(opts.get("duration_seconds", 10))
        candidates = await _asyncio.to_thread(scan_service.scan_mqtt, duration)

    logger.info(
        "Scan completado",
        extra={"protocol": body.protocol, "found": len(candidates)},
    )
    return ScanResponse(
        protocol=body.protocol,
        duration_seconds=round(time.monotonic() - t0, 2),
        candidates=candidates,
    )


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
        if "modbus_unit_id" in body.model_fields_set:
            device.modbus_unit_id = body.modbus_unit_id
        if "modbus_transport" in body.model_fields_set:
            device.modbus_transport = body.modbus_transport
        if "modbus_baudrate" in body.model_fields_set:
            device.modbus_baudrate = body.modbus_baudrate

    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
    return _device_to_response(device)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    force: bool = False,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

        if not force:
            point_count = await session.scalar(
                select(Point).where(Point.device_id == device_id).limit(1)
            )
            if point_count is not None:
                raise HTTPException(
                    status_code=409,
                    detail="El dispositivo tiene puntos activos. Use ?force=true para eliminar junto con sus puntos.",
                )

        await session.delete(device)
    logger.info("Dispositivo eliminado", extra={"device_id": device_id, "force": force})


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
