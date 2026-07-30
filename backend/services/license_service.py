"""
Cliente de licencias Hira Hub — activación y verificación periódica.

Hira Server llama a Hub al startup para activar la licencia.
Si Hub no responde, entra en grace period de 72h (usando cache Redis).
Si la licencia expira y el grace period también, el server pasa a modo lectura.
"""
import hashlib
import json
import socket
from datetime import datetime, timezone, timedelta

import httpx

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_REDIS_KEY = "license:status"
_REDIS_TTL = 60 * 60 * 25        # 25 horas
_GRACE_PERIOD_HOURS = 72


def get_fingerprint() -> str:
    """Fingerprint estable de esta instalación: hash(hostname + LICENSE_KEY)."""
    raw = f"{socket.gethostname()}:{settings.license_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _cache_status(status_dict: dict) -> None:
    """Guarda el estado de licencia en Redis con TTL de 25h."""
    try:
        import redis as redis_sync
        r = redis_sync.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)
        r.setex(_REDIS_KEY, _REDIS_TTL, json.dumps(status_dict))
        r.close()
    except Exception as exc:
        logger.warning("No se pudo cachear estado de licencia en Redis", extra={"error": str(exc)})


def _read_cache() -> dict | None:
    """Lee el estado de licencia cacheado en Redis. Retorna None si no hay cache."""
    try:
        import redis as redis_sync
        r = redis_sync.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)
        raw = r.get(_REDIS_KEY)
        r.close()
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def activate_license() -> dict:
    """
    Llama POST {HUB_URL}/api/v1/licenses/activate.
    Guarda resultado en Redis. Si Hub no responde, inicia grace period.
    """
    if not settings.license_key or not settings.hub_url:
        logger.info("Modo desarrollo — sin LICENSE_KEY ni HUB_URL configurados")
        return {"valid": True, "dev_mode": True}

    fingerprint = get_fingerprint()
    payload = {
        "license_key": settings.license_key,
        "fingerprint": fingerprint,
        "hostname": socket.gethostname(),
        "ip_address": None,
    }

    try:
        response = httpx.post(
            f"{settings.hub_url}/api/v1/licenses/activate",
            json=payload,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            data["_cached_at"] = datetime.now(timezone.utc).isoformat()
            _cache_status(data)
            logger.info("Licencia activada", extra={"plan": data.get("plan"), "days_remaining": data.get("days_remaining")})
            return data
        elif response.status_code == 402:
            logger.error("Licencia expirada — servidor en modo lectura")
            expired_status = {"valid": False, "expired": True, "_cached_at": datetime.now(timezone.utc).isoformat()}
            _cache_status(expired_status)
            return expired_status
        else:
            raise RuntimeError(f"Hub respondió {response.status_code}: {response.text[:200]}")

    except (httpx.ConnectError, httpx.TimeoutException, RuntimeError) as exc:
        logger.warning("Hub no disponible — iniciando grace period", extra={"error": str(exc)})
        cached = _read_cache()
        if cached:
            logger.info("Grace period con cache existente", extra={"cached_at": cached.get("_cached_at")})
            return {**cached, "grace_period": True}

        grace_status = {
            "valid": True,
            "grace_period": True,
            "grace_expires_at": (datetime.now(timezone.utc) + timedelta(hours=_GRACE_PERIOD_HOURS)).isoformat(),
            "_cached_at": datetime.now(timezone.utc).isoformat(),
        }
        _cache_status(grace_status)
        return grace_status


def verify_license() -> dict:
    """
    Heartbeat periódico — llama POST {HUB_URL}/api/v1/licenses/verify.
    Actualiza cache en Redis.
    """
    if not settings.license_key or not settings.hub_url:
        return {"valid": True, "dev_mode": True}

    fingerprint = get_fingerprint()
    try:
        response = httpx.post(
            f"{settings.hub_url}/api/v1/licenses/verify",
            json={"license_key": settings.license_key, "fingerprint": fingerprint},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            data["_cached_at"] = datetime.now(timezone.utc).isoformat()
            _cache_status(data)
            return data
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    cached = _read_cache()
    if cached:
        return {**cached, "grace_period": True}
    return {"valid": False, "grace_period": False}


def get_license_status() -> dict:
    """
    Lee estado de licencia desde Redis.

    Retorna {valid, plan, max_points, max_users, days_remaining, grace_period, dev_mode}.
    grace_period=True si Hub no responde pero hay cache reciente (<72h).
    """
    if not settings.license_key or not settings.hub_url:
        return {"valid": True, "dev_mode": True, "grace_period": False}

    cached = _read_cache()
    if cached is None:
        return {"valid": False, "grace_period": False, "dev_mode": False}

    # Verificar si el grace period expiró
    if cached.get("grace_period") and cached.get("grace_expires_at"):
        expires = datetime.fromisoformat(cached["grace_expires_at"])
        if datetime.now(timezone.utc) > expires:
            return {"valid": False, "grace_period": False, "grace_expired": True}

    return {
        "valid": cached.get("valid", False),
        "plan": cached.get("plan"),
        "max_points": cached.get("max_points"),
        "max_users": cached.get("max_users"),
        "days_remaining": cached.get("days_remaining"),
        "grace_period": cached.get("grace_period", False),
        "dev_mode": cached.get("dev_mode", False),
    }


def is_write_allowed() -> bool:
    """
    Retorna False solo si la licencia expiró Y el grace period también expiró.
    En modo dev (sin LICENSE_KEY) siempre retorna True.
    """
    if not settings.license_key:
        return True

    status = get_license_status()
    return bool(status.get("valid")) or bool(status.get("grace_period"))
