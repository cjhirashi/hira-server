"""Router de Pruebas Funcionales — CRUD de scripts, ejecución, historial y logs."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text

from adapters.factory import get_db_adapter
from core.config import settings
from core.logger import get_logger
from core.rbac import require_permission

logger = get_logger(__name__)

router = APIRouter(prefix="/tests", tags=["Tests"])


class TestScriptCreate(BaseModel):
    name: str
    description: str | None = None
    code: str = ""


class TestScriptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    code: str | None = None


# ── Scripts CRUD ────────────────────────────────────────────────────────────


@router.get("/scripts")
async def list_scripts(_: dict = Depends(require_permission("tests:read"))):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("SELECT id, name, description, code, created_at, updated_at FROM test_scripts ORDER BY id")
        )
        rows = result.fetchall()
    return [_script_row(r) for r in rows]


@router.post("/scripts", status_code=status.HTTP_201_CREATED)
async def create_script(
    body: TestScriptCreate,
    _: dict = Depends(require_permission("tests:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO test_scripts (name, description, code) VALUES (:name, :desc, :code) "
                "RETURNING id, name, description, code, created_at, updated_at"
            ),
            {"name": body.name, "desc": body.description, "code": body.code},
        )
        row = result.fetchone()
    logger.info("Test script creado", extra={"script_name": body.name})
    return _script_row(row)


@router.get("/scripts/{script_id}")
async def get_script(
    script_id: int,
    _: dict = Depends(require_permission("tests:read")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("SELECT id, name, description, code, created_at, updated_at FROM test_scripts WHERE id = :id"),
            {"id": script_id},
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Script no encontrado")
    return _script_row(row)


@router.put("/scripts/{script_id}")
async def update_script(
    script_id: int,
    body: TestScriptUpdate,
    _: dict = Depends(require_permission("tests:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        existing = await session.execute(
            text("SELECT id, name, description, code FROM test_scripts WHERE id = :id"),
            {"id": script_id},
        )
        row = existing.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Script no encontrado")

        new_name = body.name if body.name is not None else row[1]
        new_desc = body.description if body.description is not None else row[2]
        new_code = body.code if body.code is not None else row[3]

        result = await session.execute(
            text(
                "UPDATE test_scripts SET name=:name, description=:desc, code=:code, updated_at=NOW() "
                "WHERE id=:id RETURNING id, name, description, code, created_at, updated_at"
            ),
            {"name": new_name, "desc": new_desc, "code": new_code, "id": script_id},
        )
        row = result.fetchone()
    return _script_row(row)


@router.delete("/scripts/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: int,
    _: dict = Depends(require_permission("tests:write")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("DELETE FROM test_scripts WHERE id=:id RETURNING id"),
            {"id": script_id},
        )
        deleted = result.scalar()
    if not deleted:
        raise HTTPException(status_code=404, detail="Script no encontrado")


# ── Ejecución ────────────────────────────────────────────────────────────────


@router.post("/scripts/{script_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_script(
    script_id: int,
    _: dict = Depends(require_permission("tests:write")),
):
    if settings.hira_deploy_mode == "studio":
        raise HTTPException(status_code=503, detail="Pruebas no disponibles en modo Studio")

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text("SELECT id, code FROM test_scripts WHERE id=:id"),
            {"id": script_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Script no encontrado")

        # Check for active running execution
        running = await session.execute(
            text("SELECT id FROM test_executions WHERE script_id=:sid AND status='running' LIMIT 1"),
            {"sid": script_id},
        )
        if running.fetchone():
            raise HTTPException(status_code=409, detail="El script ya tiene una ejecución en curso")

        # Create execution record
        exec_result = await session.execute(
            text(
                "INSERT INTO test_executions (script_id, status) VALUES (:sid, 'running') "
                "RETURNING id"
            ),
            {"sid": script_id},
        )
        execution_id = exec_result.scalar()

    code = row[1]

    from workers.test_worker import run_test_script
    run_test_script.apply_async(
        args=[execution_id, script_id, code],
        queue="high",
    )

    logger.info("Test script encolado", extra={"script_id": script_id, "execution_id": execution_id})
    return {"execution_id": execution_id, "status": "running"}


# ── Historial de ejecuciones ─────────────────────────────────────────────────


@router.get("/scripts/{script_id}/executions")
async def list_executions(
    script_id: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    _: dict = Depends(require_permission("tests:read")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        check = await session.execute(
            text("SELECT id FROM test_scripts WHERE id=:id"), {"id": script_id}
        )
        if not check.fetchone():
            raise HTTPException(status_code=404, detail="Script no encontrado")

        result = await session.execute(
            text(
                "SELECT id, script_id, started_at, ended_at, status, output, error_message, passed, failed "
                "FROM test_executions WHERE script_id=:sid ORDER BY started_at DESC LIMIT :limit"
            ),
            {"sid": script_id, "limit": limit},
        )
        rows = result.fetchall()
    return [_exec_row(r) for r in rows]


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: int,
    _: dict = Depends(require_permission("tests:read")),
):
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, script_id, started_at, ended_at, status, output, error_message, passed, failed "
                "FROM test_executions WHERE id=:id"
            ),
            {"id": execution_id},
        )
        exec_row = result.fetchone()
        if not exec_row:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")

        logs_result = await session.execute(
            text(
                "SELECT id, level, message, created_at FROM test_logs "
                "WHERE execution_id=:eid ORDER BY created_at ASC"
            ),
            {"eid": execution_id},
        )
        log_rows = logs_result.fetchall()

    data = _exec_row(exec_row)
    data["logs"] = [_log_row(r) for r in log_rows]
    return data


# ── helpers ──────────────────────────────────────────────────────────────────


def _script_row(r) -> dict:
    return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "code": r[3],
        "created_at": r[4].isoformat() if r[4] else None,
        "updated_at": r[5].isoformat() if r[5] else None,
    }


def _exec_row(r) -> dict:
    return {
        "id": r[0],
        "script_id": r[1],
        "started_at": r[2].isoformat() if r[2] else None,
        "ended_at": r[3].isoformat() if r[3] else None,
        "status": r[4],
        "output": r[5],
        "error_message": r[6],
        "passed": r[7],
        "failed": r[8],
    }


def _log_row(r) -> dict:
    return {
        "id": r[0],
        "level": r[1],
        "message": r[2],
        "created_at": r[3].isoformat() if r[3] else None,
    }
