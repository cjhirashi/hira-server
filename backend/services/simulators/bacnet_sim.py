"""
Simulador BACnet — dispositivo virtual usando BAC0.

BAC0 2024.x (bacpypes3) es async-nativo: BAC0.lite() llama asyncio.create_task()
internamente, por lo que DEBE invocarse desde dentro de un event loop activo
(directamente en una corrutina, no en run_in_executor).

Se registra en la BD con is_simulator=True y protocol="bacnet".
"""
import asyncio
import random
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


async def run_bacnet_simulator(device_id: int, config: dict[str, Any]) -> None:
    """
    Arranca el simulador BACnet. Diseñado para correr como tarea Celery
    via asyncio.run(). BAC0.lite() se llama directamente en la corrutina
    para que asyncio.create_task() encuentre el loop activo.
    """
    import BAC0

    bacnet_device_id = config.get("deviceId", config.get("device_id", 9000 + device_id))
    points_cfg = config.get("points", [
        {"name": "temp_supply", "object_type": "analogInput", "value_range": [18.0, 26.0]},
        {"name": "temp_return", "object_type": "analogInput", "value_range": [16.0, 24.0]},
        {"name": "fan_status", "object_type": "binaryInput", "value_range": [0, 1]},
        {"name": "temp_setpoint", "object_type": "analogValue", "value_range": [20.0, 22.0]},
    ])

    logger.info("Iniciando simulador BACnet",
                extra={"device_id": device_id, "bacnet_id": bacnet_device_id})

    # BAC0.lite() usa asyncio.create_task() internamente — el loop debe estar activo
    bacnet = BAC0.lite(deviceId=bacnet_device_id)
    await asyncio.sleep(1)  # deja que las tareas de socket UDP completen

    # BAC0 2024.x usa ObjectFactory + add_objects_to_application en lugar de newObject()
    from BAC0.core.devices.local.factory import ObjectFactory
    from bacpypes3.local.analog import AnalogInputObject, AnalogValueObject
    from bacpypes3.local.binary import BinaryInputObject

    _obj_type_map = {
        "analogInput": AnalogInputObject,
        "analogValue": AnalogValueObject,
        "binaryInput": BinaryInputObject,
    }

    # ObjectFactory.objects es un dict de clase — limpiar antes de crear nuevos objetos
    ObjectFactory.clear_objects()

    for idx, pt in enumerate(points_cfg, start=1):
        obj_class = _obj_type_map.get(pt["object_type"], AnalogInputObject)
        is_analog = "analog" in pt.get("object_type", "analog")
        props = {"units": "noUnits"} if is_analog else {}
        lo, hi = pt["value_range"]
        raw_val = random.uniform(lo, hi)
        pv = raw_val if is_analog else int(round(raw_val))
        try:
            factory = ObjectFactory(
                objectType=obj_class,
                instance=idx,
                objectName=pt["name"],
                properties=props,
                presentValue=pv,
            )
            factory.add_objects_to_application(bacnet)
        except Exception as exc:
            logger.warning("Error creando punto simulado",
                           extra={"point_name": pt["name"], "error": str(exc)})

    logger.info("Simulador BACnet activo", extra={"bacnet_id": bacnet_device_id})

    try:
        while True:
            await asyncio.sleep(5)
            for pt in points_cfg:
                lo, hi = pt["value_range"]
                new_val = random.uniform(lo, hi)
                try:
                    bacnet[f"{bacnet_device_id}:{pt['name']}"] = new_val
                except Exception:
                    pass
    except asyncio.CancelledError:
        pass
    finally:
        try:
            bacnet.disconnect()
        except Exception:
            pass
        logger.info("Simulador BACnet detenido", extra={"bacnet_id": bacnet_device_id})


def run_bacnet_simulator_blocking(device_id: int, config: dict[str, Any]) -> None:
    """Wrapper síncrono para compatibilidad con código no-async."""
    asyncio.run(run_bacnet_simulator(device_id, config))
