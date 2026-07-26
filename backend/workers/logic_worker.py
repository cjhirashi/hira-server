"""
Worker Celery para ejecución de scripts de lógica Python en sandbox RestrictedPython.

Cada script corre en un bucle con `interval_seconds` de pausa entre ciclos.
La instancia `hira` se inyecta en el contexto de ejecución.
Todo el worker es síncrono para evitar conflictos con el event loop del proceso Celery.
"""
import time
from datetime import datetime, timezone

from celery import Task
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.PrintCollector import PrintCollector

from core.logger import get_logger
from workers.celery_app import celery_app
import models  # noqa: F401 — ensures all ORM models are registered before any query

logger = get_logger(__name__)

# Módulos bloqueados en el sandbox
_BLOCKED_NAMES = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "builtins", "__import__", "open", "exec", "eval",
    "compile", "globals", "locals", "vars", "dir",
})


def _build_sandbox_globals(hira_instance: object) -> dict:
    """Construye el entorno global seguro para el script."""
    globs = safe_globals.copy()
    globs["_print_"] = PrintCollector
    globs["_getiter_"] = iter
    globs["_getattr_"] = getattr
    globs["hira"] = hira_instance
    for name in _BLOCKED_NAMES:
        globs.pop(name, None)
    return globs


def _validate_syntax(code: str) -> str | None:
    """Compila el código con RestrictedPython. Retorna mensaje de error o None si OK."""
    try:
        compile_restricted(code, filename="<script>", mode="exec")
        return None
    except SyntaxError as exc:
        return f"SyntaxError en línea {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return str(exc)


def _run_cycle(script_id: int, code: str, hira_instance: object) -> dict:
    """Ejecuta un ciclo del script y persiste en BD. Retorna {status, output, error_message}."""
    from sqlalchemy import create_engine, text as sa_text
    from core.config import settings

    started_at = datetime.now(timezone.utc)

    try:
        byte_code = compile_restricted(code, filename="<script>", mode="exec")
    except Exception as exc:
        return {"status": "error", "output": None, "error_message": str(exc)}

    globs = _build_sandbox_globals(hira_instance)
    hira_instance.clear_output()  # type: ignore[attr-defined]

    try:
        exec(byte_code, globs)  # noqa: S102 — intentional sandbox exec
        printed = globs.get("_print", None)
        if printed and hasattr(printed, "_get_prints"):
            extra = "\n".join(printed._get_prints())
            if extra:
                hira_instance.log(extra)  # type: ignore[attr-defined]
        output = hira_instance.get_output()  # type: ignore[attr-defined]
        status = "success"
        error_message = None
    except Exception as exc:
        output = hira_instance.get_output()  # type: ignore[attr-defined]
        status = "error"
        error_message = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "Error en ejecución de script",
            extra={"script_id": script_id, "error": error_message},
        )

    ended_at = datetime.now(timezone.utc)

    # Persistir ejecución en BD (síncrono)
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(
            sa_text(
                "INSERT INTO script_executions (script_id, started_at, ended_at, status, output, error_message) "
                "VALUES (:script_id, :started_at, :ended_at, :status, :output, :error_message)"
            ),
            {
                "script_id": script_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "status": status,
                "output": output or None,
                "error_message": error_message,
            },
        )
        conn.commit()
    engine.dispose()

    return {"status": status, "output": output, "error_message": error_message}


@celery_app.task(bind=True, name="workers.logic_worker.run_logic_script")
def run_logic_script(self: Task, script_id: int) -> None:
    """
    Tarea Celery: ejecuta un script de lógica en bucle hasta ser revocada.
    """
    from core.hira_api import HiraAPI
    from sqlalchemy import create_engine, text as sa_text
    from core.config import settings

    logger.info("Logic script iniciado", extra={"script_id": script_id, "task_id": self.request.id})

    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)

    with engine.connect() as conn:
        row = conn.execute(
            sa_text("SELECT code, interval_seconds FROM logic_scripts WHERE id = :id"),
            {"id": script_id},
        ).fetchone()

    engine.dispose()

    if row is None:
        logger.error("Script no encontrado", extra={"script_id": script_id})
        return

    code = row[0]
    interval = row[1]
    hira = HiraAPI()

    while True:
        _run_cycle(script_id, code, hira)
        time.sleep(interval)
