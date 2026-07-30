"""Router /project — Exportación e importación de proyecto Hira (.hira)."""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from core.config import settings
from core.logger import get_logger
from core.rbac import require_permission
import services.project_service as project_service

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["Project"])


def _sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with Session(engine) as session:
        with session.begin():
            yield session


@router.get("/export/preview")
async def export_preview(_: dict = Depends(require_permission("config:write"))):
    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        with Session(engine) as session:
            return project_service.get_export_preview(session)

    return await asyncio.to_thread(_run)


@router.get("/export")
async def export_project(_: dict = Depends(require_permission("config:write"))):
    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        with Session(engine) as session:
            return project_service.export_project(session)

    data = await asyncio.to_thread(_run)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"hira_project_{timestamp}.hira"
    return Response(
        content=data,
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
async def import_project(
    file: UploadFile = File(...),
    mode: str = Form(...),
    confirm: bool = Form(False),
    _: dict = Depends(require_permission("config:write")),
):
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=400, detail="mode debe ser 'merge' o 'replace'")
    if mode == "replace" and not confirm:
        raise HTTPException(status_code=400, detail="mode=replace requiere confirm=true")

    data = await file.read()

    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        with Session(engine) as session:
            with session.begin():
                return project_service.import_project(data, mode, session)

    try:
        result = await asyncio.to_thread(_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result
