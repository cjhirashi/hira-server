import asyncio
import socket

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.logger import get_logger, trace_id_var
from core.config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["Monitor"])

VERSION = "0.0.1-skeleton"


async def _check_postgres() -> str:
    try:
        from adapters.factory import get_db_adapter
        adapter = get_db_adapter()
        ok = await adapter.health_check()
        return "ok" if ok else "error"
    except Exception as exc:
        logger.warning("Health check postgres falló", extra={"error": str(exc)})
        return "error"


async def _check_redis() -> str:
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:
        logger.warning("Health check redis falló", extra={"error": str(exc)})
        return "error"


async def _check_mosquitto() -> str:
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: socket.create_connection(
                (settings.mqtt_broker_host, settings.mqtt_broker_port), timeout=2
            ).close(),
        )
        return "ok"
    except Exception as exc:
        logger.warning("Health check mosquitto falló", extra={"error": str(exc)})
        return "error"


@router.get("/health")
async def get_health() -> JSONResponse:
    trace_id = trace_id_var.get()

    postgres_status, redis_status, mosquitto_status = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_mosquitto(),
    )

    services = {
        "postgres": postgres_status,
        "redis": redis_status,
        "mosquitto": mosquitto_status,
    }
    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    http_status = 200 if overall == "ok" else 503

    body = {
        "status": overall,
        "services": services,
        "version": VERSION,
        "trace_id": trace_id,
    }

    logger.info(
        "Health check completado",
        extra={"overall": overall, "services": services},
    )

    return JSONResponse(content=body, status_code=http_status)
