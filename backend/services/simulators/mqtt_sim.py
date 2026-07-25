"""
Simulador MQTT — publisher periódico a Mosquitto.

Publica mensajes a los topics configurados a intervalos regulares
con valores que simulan drift de sensor real. Se registra en la BD
con is_simulator=True y protocol="mqtt".
"""
import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


async def run_mqtt_simulator(device_id: int, config: dict[str, Any]) -> None:
    """
    Publica mensajes periódicos a Mosquitto.

    config esperada:
    {
        "name": "sim01",
        "topics": [
            {"path": "sim/sim01/temp",     "interval_s": 5, "value_range": [18.0, 26.0]},
            {"path": "sim/sim01/humidity", "interval_s": 10, "value_range": [30.0, 70.0]}
        ]
    }
    """
    import paho.mqtt.client as mqtt_client

    name = config.get("name", f"sim{device_id}")
    topics = config.get("topics", [
        {"path": f"sim/{name}/temp",     "interval_s": 5, "value_range": [18.0, 26.0]},
        {"path": f"sim/{name}/humidity", "interval_s": 10, "value_range": [30.0, 70.0]},
        {"path": f"sim/{name}/co2",      "interval_s": 15, "value_range": [400.0, 1200.0]},
    ])

    client = mqtt_client.Client(
        client_id=f"hira-sim-{device_id}",
        protocol=mqtt_client.MQTTv5,
    )
    client.username_pw_set(settings.mqtt_user, settings.mqtt_password)

    loop = asyncio.get_event_loop()
    connected_event = asyncio.Event()

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            loop.call_soon_threadsafe(connected_event.set)
            logger.info("Simulador MQTT conectado", extra={"device_id": device_id})
        else:
            logger.error("Simulador MQTT conexión fallida", extra={"rc": rc})

    client.on_connect = on_connect

    def _connect():
        client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
        client.loop_start()

    await loop.run_in_executor(None, _connect)
    await asyncio.wait_for(connected_event.wait(), timeout=10)

    logger.info("Simulador MQTT activo", extra={"device_id": device_id, "topics": len(topics)})

    # Estado de deriva por topic para simular sensor real
    current_values: dict[str, float] = {
        t["path"]: random.uniform(*t["value_range"]) for t in topics
    }

    async def _publish_topic(topic_cfg: dict) -> None:
        path = topic_cfg["path"]
        interval = topic_cfg.get("interval_s", 5)
        lo, hi = topic_cfg["value_range"]
        drift = (hi - lo) * 0.05  # 5% drift máximo por ciclo

        while True:
            current = current_values[path]
            new_val = max(lo, min(hi, current + random.uniform(-drift, drift)))
            current_values[path] = new_val

            payload = json.dumps({
                "value": round(new_val, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "simulator": True,
                "device_id": device_id,
            })

            def _pub(p=path, pay=payload):
                client.publish(p, pay, qos=1)

            await loop.run_in_executor(None, _pub)
            await asyncio.sleep(interval)

    try:
        await asyncio.gather(*[_publish_topic(t) for t in topics])
    except asyncio.CancelledError:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Simulador MQTT detenido", extra={"device_id": device_id})
