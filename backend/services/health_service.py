"""
health_service.py — Recopila métricas de todos los componentes del sistema.
"""
import asyncio
import shutil
import time
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


async def get_detailed_health() -> dict:
    """
    Retorna un dict con el estado de todos los componentes.
    Nunca lanza excepción — los fallos se reportan como 'error' en el componente.
    """
    results = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_celery(),
        _check_disk(),
        _check_devices(),
        return_exceptions=True,
    )

    db_info = results[0] if not isinstance(results[0], Exception) else {"status": "error", "error": str(results[0])}
    redis_info = results[1] if not isinstance(results[1], Exception) else {"status": "error", "error": str(results[1])}
    celery_info = results[2] if not isinstance(results[2], Exception) else {"status": "error", "error": str(results[2])}
    disk_info = results[3] if not isinstance(results[3], Exception) else {"status": "error", "error": str(results[3])}
    devices_info = results[4] if not isinstance(results[4], Exception) else {"total": 0, "online": 0, "offline": 0, "offline_names": []}

    # Status global
    status = "healthy"
    if db_info.get("status") == "error" or redis_info.get("status") == "error" or disk_info.get("percent_used", 0) > 90:
        status = "critical"
    elif (
        celery_info.get("status") == "degraded"
        or devices_info.get("offline", 0) > 0
        or disk_info.get("percent_used", 0) > 80
    ):
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_info,
            "redis": redis_info,
            "celery": celery_info,
            "disk": disk_info,
            "devices": devices_info,
        },
    }


async def _check_database() -> dict:
    from adapters.factory import get_db_adapter
    from sqlalchemy import text

    try:
        t0 = time.monotonic()
        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            await session.execute(text("SELECT 1"))
            latency_ms = round((time.monotonic() - t0) * 1000, 2)

            size_mb = 0.0
            point_history_rows = 0

            if settings.deploy_mode == "server":
                row = await session.execute(
                    text("SELECT pg_database_size(current_database()) AS sz")
                )
                size_bytes = row.scalar() or 0
                size_mb = round(size_bytes / (1024 * 1024), 2)

                row2 = await session.execute(
                    text("SELECT COUNT(*) FROM point_history")
                )
                point_history_rows = row2.scalar() or 0

        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "size_mb": size_mb,
            "point_history_rows": point_history_rows,
        }
    except Exception as exc:
        logger.error("DB health check failed", extra={"error": str(exc)})
        return {"status": "error", "latency_ms": None, "size_mb": None, "point_history_rows": None}


async def _check_redis() -> dict:
    from core.redis import get_redis

    try:
        redis = await get_redis()
        t0 = time.monotonic()
        await redis.ping()
        latency_ms = round((time.monotonic() - t0) * 1000, 2)

        info = await redis.info("memory")
        used_memory = info.get("used_memory", 0)
        memory_used_mb = round(used_memory / (1024 * 1024), 2)

        return {"status": "ok", "latency_ms": latency_ms, "memory_used_mb": memory_used_mb}
    except Exception as exc:
        logger.error("Redis health check failed", extra={"error": str(exc)})
        return {"status": "error", "latency_ms": None, "memory_used_mb": None}


async def _check_celery() -> dict:
    if settings.deploy_mode == "studio":
        return {"status": "not_applicable", "workers": []}

    try:
        from workers.celery_app import celery_app

        def _inspect():
            insp = celery_app.control.inspect(timeout=3)
            return insp.active_queues() or {}

        loop = asyncio.get_event_loop()
        queues = await loop.run_in_executor(None, _inspect)

        workers = [
            {
                "name": name,
                "queues": [q["name"] for q in queue_list],
                "active_tasks": 0,
            }
            for name, queue_list in queues.items()
        ]

        status = "ok" if workers else "degraded"
        return {"status": status, "workers": workers}
    except Exception as exc:
        logger.error("Celery health check failed", extra={"error": str(exc)})
        return {"status": "degraded", "workers": []}


async def _check_disk() -> dict:
    try:
        usage = shutil.disk_usage("/")
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        percent_used = round(usage.used / usage.total * 100, 1)

        if percent_used > 90:
            disk_status = "critical"
        elif percent_used > 80:
            disk_status = "warning"
        else:
            disk_status = "ok"

        return {
            "status": disk_status,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "percent_used": percent_used,
        }
    except Exception as exc:
        logger.error("Disk health check failed", extra={"error": str(exc)})
        return {"status": "error", "total_gb": None, "used_gb": None, "free_gb": None, "percent_used": 0}


async def _check_devices() -> dict:
    try:
        from adapters.factory import get_db_adapter
        from sqlalchemy import text

        adapter = get_db_adapter()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

        async with adapter.get_session() as session:
            result = await session.execute(
                text("SELECT id, name FROM devices WHERE is_active = true")
            )
            devices = result.fetchall()

        if not devices:
            return {"total": 0, "online": 0, "offline": 0, "offline_names": []}

        from core.redis import get_redis
        redis = await get_redis()

        online = 0
        offline_names = []

        for device_id, device_name in devices:
            # Check if any point of this device was updated recently
            keys = await redis.keys(f"point:*:value")
            device_online = False
            for key in keys:
                raw = await redis.get(key)
                if raw:
                    import json
                    try:
                        data = json.loads(raw)
                        if data.get("device_id") == device_id:
                            ts_str = data.get("timestamp")
                            if ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts > cutoff:
                                    device_online = True
                                    break
                    except Exception:
                        pass

            if device_online:
                online += 1
            else:
                offline_names.append(device_name)

        return {
            "total": len(devices),
            "online": online,
            "offline": len(offline_names),
            "offline_names": offline_names,
        }
    except Exception as exc:
        logger.error("Devices health check failed", extra={"error": str(exc)})
        return {"total": 0, "online": 0, "offline": 0, "offline_names": []}
