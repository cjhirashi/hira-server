"""
Adaptador MQTT — implementa ProtocolPort usando paho-mqtt.

El loop de suscripción wildcard almacena cada mensaje recibido en Redis
(`mqtt:topic:{path}`) con TTL de 300s, y publica en el canal pub/sub
`mqtt:topic:{path}:updates` para los consumidores WebSocket (Sprint 3).
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

from core.config import settings
from core.logger import get_logger
from core.redis import get_redis

logger = get_logger(__name__)

_MQTT_TOPIC_TTL = 300  # segundos


class MQTTAdapter:
    """Adaptador MQTT con paho-mqtt en thread + asyncio bridge."""

    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._discovered_topics: set[str] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        host = cfg.get("host", settings.mqtt_broker_host)
        port = cfg.get("port", settings.mqtt_broker_port)
        self._loop = asyncio.get_event_loop()

        client = mqtt.Client(client_id="hira-backend-adapter", protocol=mqtt.MQTTv5)
        client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
        client.on_message = self._on_message
        client.on_connect = self._on_connect

        def _connect():
            client.connect(host, port, keepalive=60)
            client.loop_start()

        await asyncio.get_event_loop().run_in_executor(None, _connect)
        self._client = client
        logger.info("MQTT conectado", extra={"host": host, "port": port})

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe("#", qos=1)
            logger.info("MQTT suscrito a wildcard #")
        else:
            logger.error("MQTT conexión fallida", extra={"rc": rc})

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            payload = str(msg.payload)

        self._discovered_topics.add(topic)

        entry = json.dumps({
            "value": payload,
            "quality": "good",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "topic": topic,
        })

        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._store_in_redis(topic, entry), self._loop
            )

    async def _store_in_redis(self, topic: str, entry: str) -> None:
        try:
            redis = await get_redis()
            key = f"mqtt:topic:{topic}"
            await redis.setex(key, _MQTT_TOPIC_TTL, entry)
            await redis.publish(f"{key}:updates", entry)
        except Exception as exc:
            logger.warning("MQTT → Redis error", extra={"error": str(exc)})

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            logger.info("MQTT desconectado")

    async def scan(self) -> list[dict[str, Any]]:
        """Devuelve los topics descubiertos desde la conexión activa."""
        await asyncio.sleep(5)  # ventana de descubrimiento
        return [{"topic": t, "protocol": "mqtt"} for t in sorted(self._discovered_topics)]

    async def read_point(self, device_id: str, point_address: str) -> dict[str, Any]:
        """
        Lee el último valor del topic desde Redis.
        device_id es ignorado en MQTT; point_address es el topic path.
        """
        redis = await get_redis()
        raw = await redis.get(f"mqtt:topic:{point_address}")
        if raw is None:
            return {"value": None, "quality": "uncertain",
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}
        return json.loads(raw)

    async def write_point(self, device_id: str, point_address: str, value: Any) -> bool:
        """Publica al topic MQTT con QoS 1."""
        if self._client is None:
            raise RuntimeError("MQTT no conectado")

        payload = json.dumps({"value": value,
                              "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds")})

        def _pub():
            result = self._client.publish(point_address, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS

        ok = await asyncio.get_event_loop().run_in_executor(None, _pub)
        logger.info("MQTT publish", extra={"topic": point_address, "ok": ok})
        return ok

    async def health_check(self) -> bool:
        return self._client is not None and self._client.is_connected()
