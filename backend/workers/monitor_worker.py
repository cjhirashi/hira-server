"""
monitor_worker.py — Task Celery de monitoreo del sistema.
Se ejecuta cada 60 segundos vía Celery Beat.
Detecta eventos críticos y los registra en system_events.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)

_EVENT_TYPES = frozenset({"device_offline", "worker_down", "disk_full", "alarm_flood", "backup_failed"})


@celery_app.task(name="workers.monitor_worker.monitor_system")
def monitor_system() -> None:
    """Detecta eventos del sistema y los registra + notifica."""
    try:
        asyncio.run(_run_monitor())
    except Exception as exc:
        logger.error("monitor_system falló", extra={"error": str(exc)})


async def _run_monitor() -> None:
    from services.health_service import get_detailed_health

    health = await get_detailed_health()
    components = health.get("components", {})

    events_to_insert = []

    # device_offline
    devices = components.get("devices", {})
    for device_name in devices.get("offline_names", []):
        if await _should_insert_event("device_offline", device_name, minutes=5):
            events_to_insert.append({
                "event_type": "device_offline",
                "severity": "critical",
                "message": f"Dispositivo {device_name} sin actualización > 5 minutos",
                "metadata": {"device_name": device_name},
            })

    # worker_down
    celery_info = components.get("celery", {})
    if settings.deploy_mode == "server" and celery_info.get("status") == "degraded":
        if await _should_insert_event("worker_down", "celery", minutes=5):
            events_to_insert.append({
                "event_type": "worker_down",
                "severity": "critical",
                "message": "No hay workers Celery activos",
                "metadata": {},
            })

    # disk_full
    disk = components.get("disk", {})
    percent = disk.get("percent_used", 0) or 0
    if percent > 80:
        severity = "critical" if percent > 90 else "warning"
        if await _should_insert_event("disk_full", "disk", minutes=60):
            events_to_insert.append({
                "event_type": "disk_full",
                "severity": severity,
                "message": f"Disco al {percent}% de uso",
                "metadata": {"percent_used": percent, "free_gb": disk.get("free_gb")},
            })

    # alarm_flood
    if await _check_alarm_flood():
        if await _should_insert_event("alarm_flood", "alarms", minutes=5):
            events_to_insert.append({
                "event_type": "alarm_flood",
                "severity": "warning",
                "message": "Más de 50 alarmas generadas en los últimos 5 minutos",
                "metadata": {},
            })

    # Insertar y notificar
    for event_data in events_to_insert:
        event_id = await _insert_event(event_data)
        if event_id:
            await _notify_event(event_id, event_data)


async def _should_insert_event(event_type: str, key: str, minutes: int) -> bool:
    """Retorna True si no existe un evento del mismo tipo en los últimos `minutes` minutos."""
    from adapters.factory import get_db_adapter
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    try:
        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            result = await session.execute(
                text(
                    "SELECT id FROM system_events "
                    "WHERE event_type = :et AND created_at > :cutoff "
                    "AND metadata::text LIKE :key "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"et": event_type, "cutoff": cutoff, "key": f"%{key}%"},
            )
            return result.scalar() is None
    except Exception as exc:
        logger.error("Error checking dedup", extra={"error": str(exc)})
        return False


async def _insert_event(event_data: dict) -> int | None:
    from adapters.factory import get_db_adapter
    from sqlalchemy import text
    import json

    try:
        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            result = await session.execute(
                text(
                    "INSERT INTO system_events (event_type, severity, message, metadata, notified) "
                    "VALUES (:et, :sv, :msg, :meta::jsonb, false) RETURNING id"
                ),
                {
                    "et": event_data["event_type"],
                    "sv": event_data["severity"],
                    "msg": event_data["message"],
                    "meta": json.dumps(event_data.get("metadata", {})),
                },
            )
            event_id = result.scalar()
            logger.info(
                "Evento de sistema registrado",
                extra={"event_type": event_data["event_type"], "id": event_id},
            )
            return event_id
    except Exception as exc:
        logger.error("Error insertando system_event", extra={"error": str(exc)})
        return None


async def _notify_event(event_id: int, event_data: dict) -> None:
    from adapters.factory import get_db_adapter
    from services import notification_service
    from sqlalchemy import text

    try:
        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            result = await session.execute(
                text(
                    "SELECT id, event_type, channel, destination, threshold_minutes, enabled "
                    "FROM notification_rules "
                    "WHERE event_type = :et AND enabled = true"
                ),
                {"et": event_data["event_type"]},
            )
            rules = result.fetchall()

        notified = False
        for rule in rules:
            rule_dict = {
                "id": rule[0],
                "event_type": rule[1],
                "channel": rule[2],
                "destination": rule[3],
                "threshold_minutes": rule[4],
                "enabled": rule[5],
            }
            event_dict = {**event_data, "created_at": datetime.now(timezone.utc).isoformat()}
            ok = notification_service.send(rule_dict, event_dict)
            if ok:
                notified = True

        if notified:
            async with adapter.get_session() as session:
                await session.execute(
                    text("UPDATE system_events SET notified = true WHERE id = :id"),
                    {"id": event_id},
                )
    except Exception as exc:
        logger.error("Error notificando evento", extra={"error": str(exc)})


async def _check_alarm_flood() -> bool:
    """Retorna True si hay más de 50 alarmas en los últimos 5 minutos."""
    from adapters.factory import get_db_adapter
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    try:
        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM alarm_events WHERE created_at > :cutoff"),
                {"cutoff": cutoff},
            )
            count = result.scalar() or 0
            return count > 50
    except Exception:
        return False
