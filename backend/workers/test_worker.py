"""
Worker Celery para ejecución de scripts de prueba funcional.

Corre en la queue 'high' (concurrencia 2). A diferencia del logic_worker,
cada script se ejecuta UNA sola vez (no en bucle). Persiste la ejecución
y los logs de assertions en BD.
"""
from datetime import datetime, timezone

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.PrintCollector import PrintCollector

from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)

_BLOCKED_NAMES = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "builtins", "__import__", "open", "exec", "eval",
    "compile", "globals", "locals", "vars", "dir",
})


def _build_sandbox_globals(hira_instance: object) -> dict:
    globs = safe_globals.copy()
    globs["_print_"] = PrintCollector
    globs["_getiter_"] = iter
    globs["_getattr_"] = getattr
    globs["hira"] = hira_instance
    for name in _BLOCKED_NAMES:
        globs.pop(name, None)
    return globs


@celery_app.task(bind=False, name="workers.test_worker.run_test_script")
def run_test_script(execution_id: int, script_id: int, code: str) -> None:
    """
    Tarea Celery: ejecuta un script de prueba funcional una sola vez.
    Persiste resultado y logs en BD.
    """
    from core.hira_test_api import HiraTestAPI
    from sqlalchemy import create_engine, text as sa_text
    from core.config import settings

    logger.info("Test script iniciado", extra={"execution_id": execution_id, "script_id": script_id})

    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)

    hira = HiraTestAPI()
    started_at = datetime.now(timezone.utc)
    status = "error"
    error_message = None

    try:
        byte_code = compile_restricted(code, filename="<test_script>", mode="exec")
    except Exception as exc:
        error_message = f"SyntaxError: {exc}"
        _finalize(engine, execution_id, started_at, "error", "", error_message, 0, 0, [])
        return

    globs = _build_sandbox_globals(hira)
    hira.clear_output()

    try:
        exec(byte_code, globs)  # noqa: S102 — sandbox intencional
        printed = globs.get("_print", None)
        if printed and hasattr(printed, "_get_prints"):
            extra_output = "\n".join(printed._get_prints())
            if extra_output:
                hira.log(extra_output)

        passed, failed = hira.get_counts()
        status = "failure" if failed > 0 else "success"
        error_message = None
    except Exception as exc:
        passed, failed = hira.get_counts()
        status = "error"
        error_message = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "Error en test script",
            extra={"execution_id": execution_id, "error": error_message},
        )

    _finalize(
        engine, execution_id, started_at, status,
        hira.get_output(), error_message,
        passed, failed, hira.get_test_logs(),
    )
    engine.dispose()


def _finalize(
    engine,
    execution_id: int,
    started_at: datetime,
    status: str,
    output: str,
    error_message: str | None,
    passed: int,
    failed: int,
    test_logs: list[dict],
) -> None:
    from sqlalchemy import text as sa_text

    ended_at = datetime.now(timezone.utc)

    with engine.connect() as conn:
        conn.execute(
            sa_text(
                "UPDATE test_executions SET ended_at=:ended_at, status=:status, output=:output, "
                "error_message=:error_message, passed=:passed, failed=:failed WHERE id=:id"
            ),
            {
                "ended_at": ended_at,
                "status": status,
                "output": output or None,
                "error_message": error_message,
                "passed": passed,
                "failed": failed,
                "id": execution_id,
            },
        )
        for entry in test_logs:
            conn.execute(
                sa_text(
                    "INSERT INTO test_logs (execution_id, level, message) VALUES (:eid, :level, :msg)"
                ),
                {"eid": execution_id, "level": entry["level"], "msg": entry["message"]},
            )
        conn.commit()

    logger.info(
        "Test script finalizado",
        extra={"execution_id": execution_id, "status": status, "passed": passed, "failed": failed},
    )
