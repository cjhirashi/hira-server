from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.logic_scripts import LogicScript
from models.script_executions import ScriptExecution
from schemas.logic import (
    LogicScriptCreate,
    LogicScriptResponse,
    LogicScriptUpdate,
    ScriptExecutionResponse,
)

router = APIRouter(prefix="/logic", tags=["Logic"])
logger = get_logger(__name__)


def _validate_syntax(code: str) -> str | None:
    """Retorna mensaje de error de sintaxis, o None si el código es válido."""
    try:
        from RestrictedPython import compile_restricted
        compile_restricted(code, filename="<script>", mode="exec")
        return None
    except SyntaxError as exc:
        return f"SyntaxError en línea {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return str(exc)


def _to_response(s: LogicScript) -> LogicScriptResponse:
    return LogicScriptResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        code=s.code,
        interval_seconds=s.interval_seconds,
        status=s.status,
        celery_task_id=s.celery_task_id,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/scripts", response_model=list[LogicScriptResponse])
async def list_scripts(
    _: dict[str, Any] = Depends(require_permission("logic:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        scripts = (await session.execute(select(LogicScript))).scalars().all()
    return [_to_response(s) for s in scripts]


@router.post("/scripts", response_model=LogicScriptResponse, status_code=201)
async def create_script(
    body: LogicScriptCreate,
    _: dict[str, Any] = Depends(require_permission("logic:write")),
) -> Any:
    err = _validate_syntax(body.code)
    if err:
        raise HTTPException(status_code=422, detail=f"Error de sintaxis: {err}")

    adapter = get_db_adapter()
    try:
        async with adapter.get_session() as session:
            script = LogicScript(
                name=body.name,
                description=body.description,
                code=body.code,
                interval_seconds=body.interval_seconds,
                status="stopped",
            )
            session.add(script)
            await session.flush()
            script_id = script.id

        async with adapter.get_session() as session:
            script = await session.get(LogicScript, script_id)
    except IntegrityError:
        raise HTTPException(status_code=400, detail=f"Ya existe un script con el nombre '{body.name}'")

    logger.info("Script creado", extra={"script_id": script_id})
    return _to_response(script)


@router.get("/scripts/{script_id}", response_model=LogicScriptResponse)
async def get_script(
    script_id: int,
    _: dict[str, Any] = Depends(require_permission("logic:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="Script no encontrado")
    return _to_response(script)


@router.put("/scripts/{script_id}", response_model=LogicScriptResponse)
async def update_script(
    script_id: int,
    body: LogicScriptUpdate,
    _: dict[str, Any] = Depends(require_permission("logic:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail="Script no encontrado")
        if script.status == "running":
            raise HTTPException(status_code=409, detail="El script está en ejecución — detenerlo antes de editar")

        if body.code is not None:
            err = _validate_syntax(body.code)
            if err:
                raise HTTPException(status_code=422, detail=f"Error de sintaxis: {err}")
            script.code = body.code

        if body.name is not None:
            script.name = body.name
        if body.description is not None:
            script.description = body.description
        if body.interval_seconds is not None:
            script.interval_seconds = body.interval_seconds

        script.updated_at = datetime.now(timezone.utc)

    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
    return _to_response(script)


@router.delete("/scripts/{script_id}", status_code=204)
async def delete_script(
    script_id: int,
    _: dict[str, Any] = Depends(require_permission("logic:write")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail="Script no encontrado")
        if script.status == "running":
            raise HTTPException(status_code=409, detail="El script está en ejecución — detenerlo antes de eliminar")
        await session.delete(script)
    logger.info("Script eliminado", extra={"script_id": script_id})


@router.post("/scripts/{script_id}/start", response_model=LogicScriptResponse)
async def start_script(
    script_id: int,
    _: dict[str, Any] = Depends(require_permission("logic:write")),
) -> Any:
    from workers.logic_worker import run_logic_script

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail="Script no encontrado")
        if script.status == "running":
            raise HTTPException(status_code=409, detail="El script ya está en ejecución")

        task = run_logic_script.apply_async(args=[script_id], queue="normal")
        script.celery_task_id = task.id
        script.status = "running"
        script.updated_at = datetime.now(timezone.utc)

    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
    logger.info("Script iniciado", extra={"script_id": script_id, "task_id": task.id})
    return _to_response(script)


@router.post("/scripts/{script_id}/stop", response_model=LogicScriptResponse)
async def stop_script(
    script_id: int,
    _: dict[str, Any] = Depends(require_permission("logic:write")),
) -> Any:
    from workers.celery_app import celery_app as app

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail="Script no encontrado")

        if script.celery_task_id:
            app.control.revoke(script.celery_task_id, terminate=True, signal="SIGTERM")
            logger.info("Tarea Celery revocada", extra={"task_id": script.celery_task_id})

        script.status = "stopped"
        script.celery_task_id = None
        script.updated_at = datetime.now(timezone.utc)

    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
    return _to_response(script)


@router.get("/scripts/{script_id}/logs", response_model=list[ScriptExecutionResponse])
async def get_script_logs(
    script_id: int,
    limit: int = 50,
    _: dict[str, Any] = Depends(require_permission("logic:read")),
) -> Any:
    if limit < 1:
        limit = 50
    if limit > 500:
        limit = 500

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        script = await session.get(LogicScript, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail="Script no encontrado")

        executions = (
            await session.execute(
                select(ScriptExecution)
                .where(ScriptExecution.script_id == script_id)
                .order_by(ScriptExecution.started_at.desc())
                .limit(limit)
            )
        ).scalars().all()

    return [
        ScriptExecutionResponse(
            id=e.id,
            script_id=e.script_id,
            started_at=e.started_at,
            ended_at=e.ended_at,
            status=e.status,
            output=e.output,
            error_message=e.error_message,
        )
        for e in executions
    ]
