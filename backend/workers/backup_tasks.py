"""
Tarea Celery para backup L2 — pg_dump automatizado.

Se ejecuta a las 3:00 AM UTC diariamente vía Celery Beat.
También puede dispararse manualmente desde POST /backups/run.

Genera archivos .dump en formato custom (-Fc) en /backups/.
Retención: máximo 30 backups (elimina el más antiguo si se supera).
"""
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from core.config import settings
from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/backups"))
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "30"))


@celery_app.task(name="workers.backup_tasks.run_database_backup", queue="normal")
def run_database_backup() -> str:
    import asyncio
    return asyncio.run(_run_backup_async())


async def _run_backup_async() -> str:
    from sqlalchemy import select

    from adapters.factory import get_db_adapter
    from models.backup_log import BackupLog, BackupStatus

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"hira_backup_{timestamp}.dump"
    backup_path = BACKUP_DIR / filename
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    db_url = settings.sync_database_url.replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    log_entry: BackupLog
    try:
        result = subprocess.run(
            ["pg_dump", "-Fc", "-d", db_url, "-f", str(backup_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "pg_dump retornó código no-cero")

        size_bytes = backup_path.stat().st_size
        log_entry = BackupLog(
            filename=filename,
            size_bytes=size_bytes,
            status=BackupStatus.success,
        )
        _cleanup_old_backups()
        logger.info(
            "Backup completado",
            extra={"filename": filename, "size_bytes": size_bytes},
        )

    except Exception as exc:
        error_msg = str(exc)[:500]
        log_entry = BackupLog(
            filename=filename,
            status=BackupStatus.failed,
            error_message=error_msg,
        )
        if backup_path.exists():
            backup_path.unlink()
        logger.error("Backup fallido", extra={"filename": filename, "error": error_msg})

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        session.add(log_entry)
        await session.flush()

    return f"Backup {log_entry.status.value}: {filename}"


def _cleanup_old_backups() -> None:
    backups = sorted(BACKUP_DIR.glob("hira_backup_*.dump"))
    while len(backups) > MAX_BACKUPS:
        oldest = backups.pop(0)
        oldest.unlink()
        logger.info("Backup antiguo eliminado (retención)", extra={"file": str(oldest)})
