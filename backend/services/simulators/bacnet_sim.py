"""
Simulador BACnet — dispositivo virtual usando BAC0.

Crea un dispositivo BACnet/IP virtual que responde a Who-Is broadcasts
y expone puntos analógicos con valores aleatorios dentro de un rango
configurable. Coexiste con dispositivos BACnet reales en la misma red.

Se registra en la BD con is_simulator=True y protocol="bacnet".
"""
import asyncio
import random
import time
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


async def run_bacnet_simulator(device_id: int, config: dict[str, Any]) -> None:
    """
    Arranca el simulador BACnet. Bloqueante — diseñado para correr
    como tarea Celery (via asyncio.run en el worker).

    config esperada:
    {
        "device_id": 9001,           # BACnet device instance
        "points": [
            {"name": "temp_supply", "object_type": "analogInput",
             "value_range": [18.0, 26.0]}
        ]
    }
    """
    import BAC0

    bacnet_device_id = config.get("device_id", 9000 + device_id)
    points_cfg = config.get("points", [
        {"name": "temp_supply", "object_type": "analogInput", "value_range": [18.0, 26.0]},
        {"name": "temp_return", "object_type": "analogInput", "value_range": [16.0, 24.0]},
        {"name": "fan_status", "object_type": "binaryInput", "value_range": [0, 1]},
    ])

    logger.info("Iniciando simulador BACnet",
                extra={"device_id": device_id, "bacnet_id": bacnet_device_id})

    def _run_sim():
        bacnet = BAC0.lite(deviceId=bacnet_device_id)
        # Crear puntos en el dispositivo virtual
        for pt in points_cfg:
            try:
                bacnet.newObject(
                    objectType=pt["object_type"],
                    objectName=pt["name"],
                    presentValue=random.uniform(*pt["value_range"]),
                )
            except Exception as exc:
                logger.warning("Error creando punto simulado",
                               extra={"name": pt["name"], "error": str(exc)})

        logger.info("Simulador BACnet activo", extra={"bacnet_id": bacnet_device_id})

        try:
            while True:
                # Actualizar valores con deriva aleatoria
                for pt in points_cfg:
                    lo, hi = pt["value_range"]
                    new_val = random.uniform(lo, hi)
                    try:
                        bacnet[f"{bacnet_device_id}:{pt['name']}"] = new_val
                    except Exception:
                        pass
                time.sleep(5)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            bacnet.disconnect()
            logger.info("Simulador BACnet detenido", extra={"bacnet_id": bacnet_device_id})

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_sim)
