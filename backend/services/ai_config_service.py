"""
Servicio de configuración del agente IA.

Gestiona la tabla ai_config con soporte para dos agentes independientes:
- agent_type='integrador' → Agente del Integrador (herramientas de construcción)
- agent_type='cliente'    → Agente del Cliente (herramientas de operación)

La API key se cifra con Fernet usando AI_ENCRYPTION_KEY.
"""
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SYNC_URL = settings.sync_database_url


def _get_engine():
    return create_engine(_SYNC_URL, pool_pre_ping=True)


def _get_fernet():
    from cryptography.fernet import Fernet

    key = os.environ.get("AI_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError(
            "AI_ENCRYPTION_KEY no está definida. "
            "Genera una con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise RuntimeError(f"AI_ENCRYPTION_KEY inválida: {exc}") from exc


def get_config(agent_type: str = "integrador") -> dict[str, Any]:
    """Retorna configuración del agente indicado. Nunca incluye la API key en claro."""
    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT provider, model, api_key_encrypted, updated_at "
                    "FROM ai_config WHERE agent_type = :agent_type"
                ),
                {"agent_type": agent_type},
            ).fetchone()
    finally:
        engine.dispose()

    if row is None:
        return {
            "provider": "claude",
            "model": "claude-sonnet-4-6",
            "has_api_key": False,
            "updated_at": None,
            "agent_type": agent_type,
        }

    return {
        "provider": row[0],
        "model": row[1],
        "has_api_key": row[2] is not None,
        "updated_at": row[3].isoformat() if row[3] else None,
        "agent_type": agent_type,
    }


def save_config(provider: str, model: str, api_key: str, agent_type: str = "integrador") -> None:
    """Cifra la API key y persiste configuración del agente indicado."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode()).decode()
    now = datetime.now(timezone.utc)

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE ai_config SET provider=:provider, model=:model, "
                    "api_key_encrypted=:key, updated_at=:now "
                    "WHERE agent_type=:agent_type"
                ),
                {"provider": provider, "model": model, "key": encrypted, "now": now, "agent_type": agent_type},
            )
            conn.commit()
    finally:
        engine.dispose()

    logger.info("Configuración IA guardada", extra={"provider": provider, "model": model, "agent_type": agent_type})


def get_decrypted_key(agent_type: str = "integrador") -> str | None:
    """Descifra y retorna la API key del agente indicado. Retorna None si no hay key."""
    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT api_key_encrypted FROM ai_config WHERE agent_type = :agent_type"),
                {"agent_type": agent_type},
            ).fetchone()
    finally:
        engine.dispose()

    if row is None or row[0] is None:
        return None

    fernet = _get_fernet()
    return fernet.decrypt(row[0].encode()).decode()


def delete_api_key(agent_type: str = "integrador") -> None:
    """Borra la API key cifrada del agente indicado."""
    engine = _get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE ai_config SET api_key_encrypted=NULL, updated_at=:now "
                    "WHERE agent_type=:agent_type"
                ),
                {"now": datetime.now(timezone.utc), "agent_type": agent_type},
            )
            conn.commit()
    finally:
        engine.dispose()

    logger.info("API key de IA eliminada", extra={"agent_type": agent_type})
