"""
crash_reporter.py — Envía reporte sanitizado al endpoint del desarrollador.
Solo metadatos técnicos — nunca datos del proyecto.
"""
import traceback

import httpx
from fastapi import Request

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


async def send_crash_report(request: Request, exc: Exception) -> None:
    """
    Envía reporte técnico sanitizado.
    NUNCA incluye valores de puntos, usuarios ni configuración del proyecto.
    """
    payload = {
        "version": "0.10",
        "deploy_mode": settings.deploy_mode,
        "path": request.url.path,  # sin query params
        "method": request.method,
        "exception_type": type(exc).__name__,
        "exception_module": type(exc).__module__,
        "stack_frames": [
            {"file": f.filename.split("/")[-1], "line": f.lineno, "name": f.name}
            for f in traceback.extract_tb(exc.__traceback__)
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(settings.crash_reporter_url, json=payload)
        logger.debug("Crash report enviado", extra={"exception_type": payload["exception_type"]})
    except Exception:
        pass  # el reporter nunca debe romper el flujo principal
