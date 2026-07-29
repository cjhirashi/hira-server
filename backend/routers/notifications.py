"""Router de notificaciones — reglas de eventos y historial."""
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_VALID_EVENT_TYPES = {"device_offline", "worker_down", "disk_full", "alarm_flood", "backup_failed"}
_VALID_CHANNELS = {"email", "webhook"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RuleCreate(BaseModel):
    event_type: str
    channel: str
    destination: str
    threshold_minutes: int = 5
    enabled: bool = True

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in _VALID_EVENT_TYPES:
            raise ValueError(f"event_type debe ser uno de: {', '.join(_VALID_EVENT_TYPES)}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in _VALID_CHANNELS:
            raise ValueError("channel debe ser 'email' o 'webhook'")
        return v

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str, info) -> str:
        return v  # validación cruzada en el endpoint


class RulePatch(BaseModel):
    enabled: bool


@router.get("/rules")
async def list_rules(
    _: dict = Depends(require_permission("notifications:read")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("SELECT id, event_type, channel, destination, threshold_minutes, enabled, created_at FROM notification_rules ORDER BY id")
        )
        rows = result.fetchall()
    return [_rule_row(r) for r in rows]


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: RuleCreate,
    _: dict = Depends(require_permission("notifications:write")),
):
    _validate_destination(body.channel, body.destination)

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO notification_rules (event_type, channel, destination, threshold_minutes, enabled) "
                "VALUES (:et, :ch, :dst, :th, :en) RETURNING id, event_type, channel, destination, threshold_minutes, enabled, created_at"
            ),
            {"et": body.event_type, "ch": body.channel, "dst": body.destination, "th": body.threshold_minutes, "en": body.enabled},
        )
        row = result.fetchone()

    logger.info("Regla de notificación creada", extra={"event_type": body.event_type, "channel": body.channel})
    return _rule_row(row)


@router.patch("/rules/{rule_id}")
async def patch_rule(
    rule_id: int,
    body: RulePatch,
    _: dict = Depends(require_permission("notifications:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                "UPDATE notification_rules SET enabled = :en WHERE id = :id "
                "RETURNING id, event_type, channel, destination, threshold_minutes, enabled, created_at"
            ),
            {"en": body.enabled, "id": rule_id},
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return _rule_row(row)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    _: dict = Depends(require_permission("notifications:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("DELETE FROM notification_rules WHERE id = :id RETURNING id"),
            {"id": rule_id},
        )
        deleted = result.scalar()

    if not deleted:
        raise HTTPException(status_code=404, detail="Regla no encontrada")


@router.get("/events")
async def list_events(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    severity: str | None = None,
    _: dict = Depends(require_permission("notifications:read")),
):
    adapter = get_db_adapter()
    where = "WHERE severity = :sev" if severity else ""
    params: dict = {"limit": limit, "offset": offset}
    if severity:
        params["sev"] = severity

    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                f"SELECT id, event_type, severity, message, metadata, notified, created_at "
                f"FROM system_events {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        rows = result.fetchall()
    return [_event_row(r) for r in rows]


@router.patch("/events/{event_id}/resolve")
async def resolve_event(
    event_id: int,
    _: dict = Depends(require_permission("notifications:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                "UPDATE system_events SET notified = true WHERE id = :id AND notified = false "
                "RETURNING id, event_type, severity, message, metadata, notified, created_at"
            ),
            {"id": event_id},
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Evento no encontrado o ya resuelto")
    return _event_row(row)


# ── helpers ────────────────────────────────────────────────────────────────

def _validate_destination(channel: str, destination: str) -> None:
    if channel == "email":
        if not _EMAIL_RE.match(destination):
            raise HTTPException(status_code=422, detail="Destino debe ser un email válido")
    elif channel == "webhook":
        if not destination.startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail="Destino webhook debe comenzar con http:// o https://")


def _rule_row(r) -> dict:
    return {
        "id": r[0],
        "event_type": r[1],
        "channel": r[2],
        "destination": r[3],
        "threshold_minutes": r[4],
        "enabled": r[5],
        "created_at": r[6].isoformat() if r[6] else None,
    }


def _event_row(r) -> dict:
    return {
        "id": r[0],
        "event_type": r[1],
        "severity": r[2],
        "message": r[3],
        "metadata": r[4],
        "notified": r[5],
        "created_at": r[6].isoformat() if r[6] else None,
    }
