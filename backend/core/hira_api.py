"""
API interna inyectada en el sandbox de scripts de lógica.

Usa drivers síncronos (redis-py, psycopg2) para ser compatible con el
entorno de workers Celery prefork sin conflictos de event loops.
"""
import json
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class HiraAPI:
    """
    Interfaz disponible para scripts de lógica bajo el nombre `hira`.

    Métodos:
        read(point_name)       → float | None
        write(point_name, val) → bool
        log(message)           → None
    """

    def __init__(self) -> None:
        self._output_lines: list[str] = []
        self._point_id_cache: dict[str, int | None] = {}
        self._redis: Any = None
        self._engine: Any = None

    def _get_redis(self) -> Any:
        if self._redis is None:
            import redis as redis_sync
            from core.config import settings
            self._redis = redis_sync.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=5
            )
        return self._redis

    def _get_engine(self) -> Any:
        if self._engine is None:
            from sqlalchemy import create_engine
            from core.config import settings
            # Convertir URL asyncpg → psycopg2 para uso síncrono
            sync_url = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://"
            )
            self._engine = create_engine(sync_url, pool_pre_ping=True)
        return self._engine

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S")

    def log(self, message: str) -> None:
        line = f"[{self._ts()}] {message}"
        self._output_lines.append(line)

    def get_output(self) -> str:
        return "\n".join(self._output_lines)

    def clear_output(self) -> None:
        self._output_lines = []

    def _resolve_point_id(self, point_name: str) -> int | None:
        if point_name in self._point_id_cache:
            return self._point_id_cache[point_name]
        from sqlalchemy import text
        with self._get_engine().connect() as conn:
            result = conn.execute(
                text("SELECT id FROM points WHERE name = :name LIMIT 1"),
                {"name": point_name},
            ).scalar()
        self._point_id_cache[point_name] = result
        return result

    def read(self, point_name: str) -> float | None:
        """Lee el valor actual del punto desde Redis. Retorna None si no disponible."""
        point_id = self._resolve_point_id(point_name)
        if point_id is None:
            self.log(f"read: punto '{point_name}' no encontrado")
            return None
        raw = self._get_redis().get(f"point:{point_id}:value")
        if raw is None:
            return None
        data = json.loads(raw)
        val = data.get("value")
        return float(val) if val is not None else None

    def write(self, point_name: str, value: float) -> bool:
        """
        Escribe un valor en Redis y publica en el canal de actualización
        para que el WebSocket lo propague al dashboard.
        """
        point_id = self._resolve_point_id(point_name)
        if point_id is None:
            self.log(f"write: punto '{point_name}' no encontrado")
            return False
        payload = json.dumps({
            "value": value,
            "quality": "good",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "logic",
        })
        r = self._get_redis()
        r.set(f"point:{point_id}:value", payload)
        r.publish(f"point:{point_id}:update", payload)
        return True
