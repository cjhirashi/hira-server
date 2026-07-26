"""
Servicio de escritura de históricos en TimescaleDB (point_history).

Respeta el intervalo mínimo configurado por punto (history_interval_seconds)
usando Redis como registro de la última escritura. Si el intervalo aún no
se ha cumplido para un punto, la llamada a record() es un no-op silencioso.
"""
from datetime import datetime, timezone

from core.logger import get_logger

logger = get_logger(__name__)

_LAST_RECORDED_TTL = 3600  # segundos — limpia claves huérfanas en Redis


class HistoryWriter:
    async def record(
        self,
        point_id: int,
        value: float,
        quality: str,
        timestamp: datetime,
        interval_seconds: int,
        session,
        redis,
    ) -> None:
        """Inserta un registro en point_history si ha pasado el intervalo mínimo."""
        key = f"point:{point_id}:last_recorded"

        last_raw = await redis.get(key)
        if last_raw is not None:
            last_ts = float(last_raw)
            now_ts = timestamp.timestamp()
            if now_ts - last_ts < interval_seconds:
                return

        try:
            from models.point_history import PointHistory

            record = PointHistory(
                time=timestamp,
                point_id=point_id,
                value=value,
                quality=quality,
            )
            session.add(record)
            await session.flush()

            await redis.setex(key, _LAST_RECORDED_TTL, str(timestamp.timestamp()))
            logger.debug(
                "Histórico registrado",
                extra={"point_id": point_id, "value": value, "quality": quality},
            )
        except Exception as exc:
            logger.error(
                "Error al registrar histórico",
                extra={"point_id": point_id, "error": str(exc)},
            )


history_writer = HistoryWriter()
