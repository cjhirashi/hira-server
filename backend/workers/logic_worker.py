"""
Worker Celery para ejecución de scripts de lógica Python en sandbox RestrictedPython.

Cada script corre en un bucle con `interval_seconds` de pausa entre ciclos.
La instancia `hira` se inyecta en el contexto de ejecución.
"""
import asyncio
import time
from datetime import datetime, timezone
from io import StringIO

from celery import Task
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.PrintCollector import PrintCollector

from core.logger import get_logger
from workers.celery_app import celery_app

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
    # Bloquear nombres peligrosos
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


async def _run_cycle(script_id: int, code: str, hira_instance: object) -> dict:
    """Ejecuta un ciclo del script y retorna {status, output, error_message}."""
    from adapters.factory import get_db_adapter
    from models.script_executions import ScriptExecution
    from sqlalchemy.sql import text as sa_text

    started_at = datetime.now(timezone.utc)

    try:
        byte_code = compile_restricted(code, filename="<script>", mode="exec")
    except Exception as exc:
        return {"status": "error", "output": None, "error_message": str(exc)}

    globs = _build_sandbox_globals(hira_instance)
    hira_instance.clear_output()  # type: ignore[attr-defined]

    try:
        exec(byte_code, globs)  # noqa: S102 — intentional sandbox exec
        # Collect print output if PrintCollector was used
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

    # Persistir ejecución en BD
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        execution = ScriptExecution(
            script_id=script_id,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            output=output or None,
            error_message=error_message,
        )
        session.add(execution)

    return {"status": status, "output": output, "error_message": error_message}


@celery_app.task(bind=True, name="workers.logic_worker.run_logic_script")
def run_logic_script(self: Task, script_id: int) -> None:
    """
    Tarea Celery: ejecuta un script de lógica en bucle hasta ser revocada.
    """
    from adapters.factory import get_db_adapter
    from core.hira_api import HiraAPI
    from core.redis import get_redis
    from models.logic_scripts import LogicScript
    from sqlalchemy.sql import text as sa_text

    logger.info("Logic script iniciado", extra={"script_id": script_id, "task_id": self.request.id})

    async def _main() -> None:
        adapter = get_db_adapter()
        redis = await get_redis()
        hira = HiraAPI(adapter.get_session, redis)

        async with adapter.get_session() as session:
            script = await session.get(LogicScript, script_id)
            if script is None:
                logger.error("Script no encontrado", extra={"script_id": script_id})
                return
            code = script.code
            interval = script.interval_seconds

        while True:
            # Verificar si la tarea fue revocada
            if self.is_aborted():
                logger.info("Script revocado", extra={"script_id": script_id})
                break

            await _run_cycle(script_id, code, hira)

            # Recargar intervalo por si fue editado (requiere restart para aplicar)
            await asyncio.sleep(interval)

    asyncio.run(_main())

    # Marcar como stopped al salir limpiamente
    async def _mark_stopped() -> None:
        from adapters.factory import get_db_adapter
        from models.logic_scripts import LogicScript

        adapter = get_db_adapter()
        async with adapter.get_session() as session:
            script = await session.get(LogicScript, script_id)
            if script and script.status == "running":
                script.status = "stopped"
                script.celery_task_id = None
        logger.info("Script detenido", extra={"script_id": script_id})

    asyncio.run(_mark_stopped())
