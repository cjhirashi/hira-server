from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.devices import Device
from schemas.simulators import SimulatorCreate, SimulatorResponse

router = APIRouter(prefix="/simulators", tags=["Simulators"])
logger = get_logger(__name__)

_VALID_PROTOCOLS = {"bacnet", "modbus", "mqtt"}


def _device_to_simulator_response(d: Device) -> SimulatorResponse:
    config = d.config_json or {}
    return SimulatorResponse(
        id=d.id,
        name=d.name,
        protocol=d.protocol,
        status=d.status,
        is_simulator=True,
        config_json=config,
        celery_task_id=config.get("_celery_task_id"),
    )


@router.get("", response_model=list[SimulatorResponse])
async def list_simulators(
    _: dict[str, Any] = Depends(require_permission("devices:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        devices = (
            await session.execute(select(Device).where(Device.is_simulator.is_(True)))
        ).scalars().all()
    return [_device_to_simulator_response(d) for d in devices]


@router.post("", response_model=SimulatorResponse, status_code=201)
async def create_simulator(
    body: SimulatorCreate,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    if body.protocol not in _VALID_PROTOCOLS:
        raise HTTPException(
            status_code=422,
            detail=f"Protocolo '{body.protocol}' no soportado. Válidos: {sorted(_VALID_PROTOCOLS)}",
        )

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = Device(
            name=body.name,
            protocol=body.protocol,
            address="127.0.0.1",
            port=None,
            config_json=body.config_json or {},
            area="simuladores",
            status="stopped",
            is_simulator=True,
            auto_start=False,
        )
        session.add(device)
        await session.flush()
        device_id = device.id

    async with adapter.get_session() as session:
        device = await session.get(Device, device_id)

    logger.info("Simulador creado", extra={"simulator_id": device_id, "protocol": body.protocol})
    return _device_to_simulator_response(device)


@router.post("/{simulator_id}/start", response_model=SimulatorResponse)
async def start_simulator(
    simulator_id: int,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    from services.simulators.simulator_service import start_simulator as svc_start

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Simulador no encontrado")
    if not device.is_simulator:
        raise HTTPException(
            status_code=422, detail="El dispositivo no es un simulador"
        )

    try:
        await svc_start(simulator_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Error al iniciar simulador", extra={"simulator_id": simulator_id, "error": str(exc)})
        raise HTTPException(status_code=503, detail=f"Error iniciando simulador: {exc}")

    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
    return _device_to_simulator_response(device)


@router.post("/{simulator_id}/stop", response_model=SimulatorResponse)
async def stop_simulator(
    simulator_id: int,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    from services.simulators.simulator_service import stop_simulator as svc_stop

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Simulador no encontrado")
    if not device.is_simulator:
        raise HTTPException(
            status_code=422, detail="El dispositivo no es un simulador"
        )

    try:
        await svc_stop(simulator_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Error al detener simulador", extra={"simulator_id": simulator_id, "error": str(exc)})
        raise HTTPException(status_code=503, detail=f"Error deteniendo simulador: {exc}")

    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
    return _device_to_simulator_response(device)
