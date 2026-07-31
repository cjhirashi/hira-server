"""
Router de Backup L2.

GET  /backups/             → historial de backups (Admin)
POST /backups/run          → trigger manual de backup (Admin) → 202
GET  /backups/{id}/download → descarga archivo .dump (Admin)
"""
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from core.logger import get_logger
from core.rbac import require_permission

logger = get_logger(__name__)

router = APIRouter(prefix="/backups", tags=["Backups"])

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/backups"))


@router.get("/")
async def list_backups(
    limit: int = Query(20, ge=1, le=100),
    _: dict = Depends(require_permission("backup:read")),
) -> Any:
    """Lista el historial de backups ordenado por fecha descendente."""
    from adapters.factory import get_db_adapter
    from models.backup_log import BackupLog

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        logs = (
            await session.scalars(
                select(BackupLog).order_by(BackupLog.created_at.desc()).limit(limit)
            )
        ).all()

    return [
        {
            "id": log.id,
            "filename": log.filename,
            "size_bytes": log.size_bytes,
            "status": log.status.value,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/run", status_code=202)
async def trigger_backup(
    _: dict = Depends(require_permission("backup:write")),
) -> Any:
    """Dispara un backup inmediato vía Celery. Retorna task_id."""
    from workers.backup_tasks import run_database_backup

    task = run_database_backup.delay()
    logger.info("Backup manual iniciado", extra={"task_id": task.id})
    return {
        "task_id": task.id,
        "message": "Backup iniciado. Consulta el historial en unos segundos.",
    }


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    _: dict = Depends(require_permission("backup:read")),
) -> FileResponse:
    """Descarga el archivo .dump de un backup exitoso."""
    from adapters.factory import get_db_adapter
    from models.backup_log import BackupLog, BackupStatus

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        log = await session.get(BackupLog, backup_id)

    if not log or log.status != BackupStatus.success:
        raise HTTPException(status_code=404, detail="Backup no encontrado o fallido")

    backup_path = BACKUP_DIR / log.filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Archivo de backup no encontrado en disco")

    return FileResponse(
        path=str(backup_path),
        filename=log.filename,
        media_type="application/octet-stream",
    )
