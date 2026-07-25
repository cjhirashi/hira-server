"""
SimulatorService — orquesta el ciclo de vida de los simuladores.

Lanza y detiene tareas Celery por protocolo. Almacena el celery_task_id
en la tabla devices para poder revocar la tarea al detener el simulador.
"""
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

# Nombre de tarea Celery por protocolo
_CELERY_TASKS: dict[str, str] = {
    "bacnet": "workers.simulator_runner.run_bacnet",
    "modbus": "workers.simulator_runner.run_modbus",
    "mqtt":   "workers.simulator_runner.run_mqtt",
}


async def start_simulator(simulator_id: int) -> dict[str, Any]:
    """
    Lanza la tarea Celery del simulador y actualiza su estado en BD.
    Retorna el registro actualizado del dispositivo.
    """
    from adapters.factory import get_db_adapter
    from models.devices import Device
    from sqlalchemy import select
    from workers.simulator_runner import run_bacnet, run_modbus, run_mqtt

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
        if device is None:
            raise ValueError(f"Simulador {simulator_id} no encontrado")
        if not device.is_simulator:
            raise ValueError(f"El dispositivo {simulator_id} no es un simulador")
        if device.status == "running":
            raise ValueError(f"El simulador {simulator_id} ya está en ejecución")

        config = device.config_json or {}

        _task_fn = {"bacnet": run_bacnet, "modbus": run_modbus, "mqtt": run_mqtt}.get(device.protocol)
        if _task_fn is None:
            raise ValueError(f"Protocolo '{device.protocol}' no tiene simulador disponible")

        task = _task_fn.delay(simulator_id, config)

        device.status = "running"
        # Guardamos el task_id en config_json para poder revocarlo
        config["_celery_task_id"] = task.id
        device.config_json = config

    logger.info("Simulador arrancado",
                extra={"simulator_id": simulator_id, "task_id": task.id})
    return {"id": simulator_id, "celery_task_id": task.id, "status": "running"}


async def stop_simulator(simulator_id: int) -> dict[str, Any]:
    """
    Revoca la tarea Celery y actualiza el estado en BD.
    """
    from adapters.factory import get_db_adapter
    from models.devices import Device
    from workers.celery_app import celery_app

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
        if device is None:
            raise ValueError(f"Simulador {simulator_id} no encontrado")
        if device.status != "running":
            raise ValueError(f"El simulador {simulator_id} no está en ejecución")

        config = device.config_json or {}
        task_id = config.get("_celery_task_id")

        if task_id:
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            config.pop("_celery_task_id", None)

        device.status = "stopped"
        device.config_json = config

    logger.info("Simulador detenido", extra={"simulator_id": simulator_id, "task_id": task_id})
    return {"id": simulator_id, "celery_task_id": None, "status": "stopped"}


async def get_simulator_status(simulator_id: int) -> dict[str, Any]:
    """Consulta el estado actual del simulador en BD."""
    from adapters.factory import get_db_adapter
    from models.devices import Device

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        device = await session.get(Device, simulator_id)
        if device is None:
            raise ValueError(f"Simulador {simulator_id} no encontrado")

    config = device.config_json or {}
    return {
        "id": device.id,
        "status": device.status,
        "celery_task_id": config.get("_celery_task_id"),
    }
