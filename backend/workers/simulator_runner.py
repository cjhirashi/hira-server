"""
Tareas Celery para correr los simuladores de protocolo.
Cada función es un wrapper síncrono que llama asyncio.run()
sobre la corrutina del servicio simulador correspondiente.
"""
import asyncio
from typing import Any

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="workers.simulator_runner.run_bacnet",
    queue="protocols",
    bind=True,
    max_retries=None,
)
def run_bacnet(self, device_id: int, config: dict[str, Any]) -> None:
    from services.simulators.bacnet_sim import run_bacnet_simulator
    logger.info("Celery: iniciando simulador BACnet", extra={"device_id": device_id})
    asyncio.run(run_bacnet_simulator(device_id, config))


@celery_app.task(
    name="workers.simulator_runner.run_modbus",
    queue="protocols",
    bind=True,
    max_retries=None,
)
def run_modbus(self, device_id: int, config: dict[str, Any]) -> None:
    from services.simulators.modbus_sim import run_modbus_simulator
    logger.info("Celery: iniciando simulador Modbus", extra={"device_id": device_id})
    asyncio.run(run_modbus_simulator(device_id, config))


@celery_app.task(
    name="workers.simulator_runner.run_mqtt",
    queue="protocols",
    bind=True,
    max_retries=None,
)
def run_mqtt(self, device_id: int, config: dict[str, Any]) -> None:
    from services.simulators.mqtt_sim import run_mqtt_simulator
    logger.info("Celery: iniciando simulador MQTT", extra={"device_id": device_id})
    asyncio.run(run_mqtt_simulator(device_id, config))
