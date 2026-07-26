"""
API interna inyectada en el sandbox de scripts de lógica.

La instancia `hira` se pone disponible en el contexto de ejecución de cada
script Python. Provee acceso controlado a Redis (valores de puntos) y
PostgreSQL (lookup por nombre de punto).
"""
import asyncio
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

    def __init__(self, db_session_factory: Any, redis_client: Any) -> None:
        self._db = db_session_factory
        self._redis = redis_client
        self._output_lines: list[str] = []
        self._point_id_cache: dict[str, int | None] = {}

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S")

    def log(self, message: str) -> None:
        line = f"[{self._ts()}] {message}"
        self._output_lines.append(line)

    def get_output(self) -> str:
        return "\n".join(self._output_lines)

    def clear_output(self) -> None:
        self._output_lines = []

    def _run_async(self, coro: Any) -> Any:
        """Ejecuta una coroutine desde código síncrono (scripts corren en thread)."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _resolve_point_id(self, point_name: str) -> int | None:
        if point_name in self._point_id_cache:
            return self._point_id_cache[point_name]

        from sqlalchemy import select, text as sa_text
        from models.points import Point

        async with self._db() as session:
            result = await session.scalar(
                select(Point.id).where(Point.name == point_name).limit(1)
            )
        self._point_id_cache[point_name] = result
        return result

    def read(self, point_name: str) -> float | None:
        """Lee el valor actual del punto desde Redis. Retorna None si no disponible."""
        async def _read() -> float | None:
            point_id = await self._resolve_point_id(point_name)
            if point_id is None:
                self.log(f"read: punto '{point_name}' no encontrado")
                return None
            raw = await self._redis.get(f"point:{point_id}:value")
            if raw is None:
                return None
            data = json.loads(raw)
            val = data.get("value")
            return float(val) if val is not None else None

        return self._run_async(_read())

    def write(self, point_name: str, value: float) -> bool:
        """
        Escribe un valor en Redis y publica en el canal de actualización
        para que el WebSocket lo propague al dashboard.
        """
        async def _write() -> bool:
            point_id = await self._resolve_point_id(point_name)
            if point_id is None:
                self.log(f"write: punto '{point_name}' no encontrado")
                return False
            payload = json.dumps({
                "value": value,
                "quality": "good",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "logic",
            })
            key = f"point:{point_id}:value"
            await self._redis.set(key, payload)
            await self._redis.publish(f"point:{point_id}:update", payload)
            return True

        return self._run_async(_write())

    def subscribe(self, point_name: str, callback: Any) -> None:
        """
        Registra un callback a ejecutar cuando el valor del punto cambie.
        Solo disponible dentro del ciclo del script — no persiste entre ciclos.
        """
        async def _subscribe() -> None:
            point_id = await self._resolve_point_id(point_name)
            if point_id is None:
                self.log(f"subscribe: punto '{point_name}' no encontrado")
                return
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(f"point:{point_id}:update")
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    data = json.loads(msg["data"])
                    callback(data.get("value"))
                    break
            await pubsub.unsubscribe()

        self._run_async(_subscribe())
