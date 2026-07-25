import logging
import json
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ContextVar que el middleware de Correlation ID llena por cada request
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": "hira-backend",
            "module": record.name,
            "trace_id": trace_id_var.get(),
            "message": record.getMessage(),
            "extra": {},
        }

        # Campos extra pasados mediante record.__dict__
        reserved = logging.LogRecord.__dict__.keys() | {
            "message", "asctime", "args", "exc_info", "exc_text", "stack_info",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                log["extra"][key] = value

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False, default=str)


def _configure_root_logger(level: str) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # Ya configurado

    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(module_name: str) -> logging.Logger:
    """Retorna un logger JSON estructurado para el módulo dado."""
    # La configuración se hace una sola vez; importar settings aquí evita
    # ciclos de importación si config.py aún no está inicializado.
    try:
        from core.config import settings
        level = settings.log_level
    except Exception:
        level = "INFO"

    _configure_root_logger(level)
    return logging.getLogger(module_name)
