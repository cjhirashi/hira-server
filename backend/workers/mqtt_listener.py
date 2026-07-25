"""
Worker Celery — listener MQTT persistente.

Mantiene la conexión MQTT abierta con suscripción wildcard `#`.
Por cada mensaje recibido almacena en Redis y publica en pub/sub.
Si el topic no está registrado en la BD lo agrega como topic descubierto.

Este worker corre indefinidamente (no es periódico) — se lanza una vez
al arrancar el sistema y se mantiene vivo hasta que se detenga explícitamente.
"""
import asyncio
import time

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="workers.mqtt_listener.start_listener",
    queue="protocols",
    bind=True,
    max_retries=None,
)
def start_listener(self) -> None:
    """Tarea persistente: conecta a MQTT y procesa mensajes hasta cancelación."""
    asyncio.run(_async_listener())


async def _async_listener() -> None:
    from adapters.factory import get_protocol_adapter

    mqtt = get_protocol_adapter("mqtt")
    await mqtt.connect()
    logger.info("MQTT listener arrancado")

    try:
        while True:
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    finally:
        await mqtt.disconnect()
        logger.info("MQTT listener detenido")
