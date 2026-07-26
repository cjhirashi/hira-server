"""
Worker Celery — polling BACnet periódico.

Por cada dispositivo BACnet activo lee todos sus puntos con log_enabled=True,
almacena el valor en Redis (`point:{id}:value`) y publica en pub/sub
(`point:{id}:updates`) para que el WebSocket de Sprint 3 lo retransmita.

Si N lecturas consecutivas fallan, el dispositivo se marca como offline.
"""
import asyncio
import json
from datetime import datetime, timezone

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)

_OFFLINE_THRESHOLD = 3  # fallos consecutivos para marcar offline
_POINT_TTL = 60         # segundos TTL en Redis


@celery_app.task(name="workers.bacnet_poller.poll_all_devices", queue="protocols")
def poll_all_devices() -> dict:
    """Tarea periódica: itera todos los dispositivos BACnet activos y sondea sus puntos."""
    return asyncio.run(_async_poll_all())


async def _async_poll_all() -> dict:
    import redis.asyncio as aioredis
    from adapters.factory import get_db_adapter, get_protocol_adapter
    from core.config import settings
    from models.devices import Device
    from models.points import Point
    from sqlalchemy import select, update

    adapter = get_db_adapter()
    redis = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True,
        socket_connect_timeout=5, socket_timeout=5,
    )
    results: dict = {"polled": 0, "errors": 0}

    async with adapter.get_session() as session:
        devices = (await session.execute(
            select(Device).where(Device.protocol == "bacnet", Device.status != "offline")
        )).scalars().all()

    try:
        for device in devices:
            bacnet = get_protocol_adapter("bacnet")
            try:
                await bacnet.connect(device.config_json or {})
                await _poll_device(bacnet, device, redis, adapter)
                results["polled"] += 1
            except Exception as exc:
                logger.error("Poll device error", extra={"device_id": device.id, "error": str(exc)})
                results["errors"] += 1
            finally:
                try:
                    await bacnet.disconnect()
                except Exception:
                    pass
    finally:
        await redis.aclose()

    return results


async def _poll_device(bacnet, device, redis, db_adapter) -> None:
    from models.points import Point
    from services.history_writer import history_writer
    from sqlalchemy import select, update

    async with db_adapter.get_session() as session:
        points = (await session.execute(
            select(Point).where(Point.device_id == device.id, Point.log_enabled == True)  # noqa: E712
        )).scalars().all()

    fail_count = 0
    for point in points:
        result = await bacnet.read_point(str(device.id), point.address or "")
        quality = result.get("quality", "bad")
        ts_str = result.get("timestamp", datetime.now(timezone.utc).isoformat())
        ts = datetime.fromisoformat(ts_str) if isinstance(ts_str, str) else datetime.now(timezone.utc)
        value = result.get("value")

        entry = json.dumps({
            "id": point.id,
            "name": point.name,
            "value": value,
            "unit": point.unit,
            "quality": quality,
            "timestamp": ts_str,
        })

        await redis.setex(f"point:{point.id}:value", _POINT_TTL, entry)
        await redis.publish(f"point:{point.id}:updates", entry)

        if value is not None and quality != "bad":
            async with db_adapter.get_session() as session:
                await history_writer.record(
                    point_id=point.id,
                    value=float(value),
                    quality=quality,
                    timestamp=ts,
                    interval_seconds=point.history_interval_seconds,
                    session=session,
                    redis=redis,
                )

        if quality == "bad":
            fail_count += 1

    # Marcar offline si todos los puntos fallaron (o si supera el umbral)
    if len(points) > 0 and fail_count >= min(_OFFLINE_THRESHOLD, len(points)):
        async with db_adapter.get_session() as session:
            from models.devices import Device
            from sqlalchemy import update
            await session.execute(
                update(Device).where(Device.id == device.id).values(status="offline")
            )
        logger.warning("Dispositivo marcado offline", extra={"device_id": device.id})
