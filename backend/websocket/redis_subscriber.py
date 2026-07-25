"""
Redis pub/sub subscriber — tarea asyncio que corre en el lifespan de FastAPI.

Escucha los canales:
  - point:*:updates  → retransmite como evento point:update a todos los clientes WS
  - alarm:updates    → retransmite como alarm:new o alarm:resolved según campo "type"

El subscriber arranca con asyncio.create_task() en el lifespan y se cancela
en el shutdown para liberar la conexión Redis.
"""
import asyncio
import json

import redis.asyncio as aioredis

from core.config import settings
from core.logger import get_logger
from websocket.manager import manager

logger = get_logger(__name__)


async def _subscribe_loop() -> None:
    client: aioredis.Redis | None = None
    pubsub: aioredis.client.PubSub | None = None
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.psubscribe("point:*:updates", "alarm:updates")
        logger.info("Redis subscriber iniciado", extra={"patterns": ["point:*:updates", "alarm:updates"]})

        async for raw in pubsub.listen():
            if raw["type"] not in ("pmessage", "message"):
                continue
            try:
                data = json.loads(raw["data"])
                channel: str = raw.get("channel", raw.get("pattern", ""))

                if "alarm:updates" in channel:
                    alarm_type = data.get("type", "new")
                    event_name = "alarm:resolved" if alarm_type == "resolved" else "alarm:new"
                    await manager.broadcast({"event": event_name, "data": data})
                else:
                    await manager.broadcast({"event": "point:update", "data": data})

            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("Redis subscriber: error procesando mensaje", extra={"error": str(exc)})

    except asyncio.CancelledError:
        logger.info("Redis subscriber cancelado — shutdown")
    except Exception as exc:
        logger.error("Redis subscriber error fatal", extra={"error": str(exc)})
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:
                pass
        if client:
            try:
                await client.aclose()
            except Exception:
                pass


_task: asyncio.Task | None = None


def start_subscriber() -> None:
    global _task
    _task = asyncio.create_task(_subscribe_loop(), name="redis-ws-subscriber")


def stop_subscriber() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None
