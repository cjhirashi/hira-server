"""
Servicio de configuración del agente IA.

Gestiona la configuración singleton (tabla ai_config, id=1) incluyendo
el cifrado Fernet de la API key con AI_ENCRYPTION_KEY.
"""
import base64
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SYNC_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


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


def get_config() -> dict[str, Any]:
    """Retorna configuración actual. Nunca incluye la API key en claro."""
    engine = create_engine(_SYNC_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT provider, model, api_key_encrypted, updated_at FROM ai_config WHERE id = 1")
            ).fetchone()
    finally:
        engine.dispose()

    if row is None:
        return {"provider": "claude", "model": "claude-sonnet-4-6", "has_api_key": False, "updated_at": None}

    return {
        "provider": row[0],
        "model": row[1],
        "has_api_key": row[2] is not None,
        "updated_at": row[3].isoformat() if row[3] else None,
    }


def save_config(provider: str, model: str, api_key: str) -> None:
    """Cifra la API key y persiste configuración."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode()).decode()
    now = datetime.now(timezone.utc)

    engine = create_engine(_SYNC_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE ai_config SET provider=:provider, model=:model, "
                    "api_key_encrypted=:key, updated_at=:now WHERE id=1"
                ),
                {"provider": provider, "model": model, "key": encrypted, "now": now},
            )
            conn.commit()
    finally:
        engine.dispose()

    logger.info("Configuración IA guardada", extra={"provider": provider, "model": model})


def get_decrypted_key() -> str | None:
    """Descifra y retorna la API key. Retorna None si no hay key."""
    engine = create_engine(_SYNC_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT api_key_encrypted FROM ai_config WHERE id = 1")
            ).fetchone()
    finally:
        engine.dispose()

    if row is None or row[0] is None:
        return None

    fernet = _get_fernet()
    return fernet.decrypt(row[0].encode()).decode()


def delete_api_key() -> None:
    """Borra la API key cifrada."""
    engine = create_engine(_SYNC_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE ai_config SET api_key_encrypted=NULL, updated_at=NOW() WHERE id=1")
            )
            conn.commit()
    finally:
        engine.dispose()

    logger.info("API key de IA eliminada")
