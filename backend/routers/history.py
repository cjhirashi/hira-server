"""
Router de históricos — GET /points/{id}/history

Soporta datos crudos (interval=raw) y agregación TimescaleDB con time_bucket.
Responde JSON (PointHistoryResponse) o CSV (StreamingResponse).
"""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.points import Point
from schemas.history import PointHistoryRecord, PointHistoryResponse

router = APIRouter(prefix="/points", tags=["Historicals"])
logger = get_logger(__name__)

_BUCKET_MAP = {
    "1min": "1 minute",
    "5min": "5 minutes",
    "1hour": "1 hour",
    "1day": "1 day",
}


@router.get("/{point_id}/history")
async def get_point_history(
    point_id: int,
    from_dt: datetime | None = Query(default=None, description="Inicio del rango (ISO8601 UTC)"),
    to_dt: datetime | None = Query(default=None, description="Fin del rango (ISO8601 UTC)"),
    interval: str = Query(default="raw", pattern="^(raw|1min|5min|1hour|1day)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=1000, ge=1, le=10000),
    _: dict[str, Any] = Depends(require_permission("historicals:read")),
) -> Any:
    now = datetime.now(timezone.utc)
    if from_dt is None:
        from_dt = now - timedelta(hours=1)
    if to_dt is None:
        to_dt = now

    # Normalizar a UTC si llegan sin timezone
    if from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=timezone.utc)
    if to_dt.tzinfo is None:
        to_dt = to_dt.replace(tzinfo=timezone.utc)

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        point = await session.get(Point, point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Punto no encontrado")

        if interval == "raw":
            sql = text(
                "SELECT time AS timestamp, value, quality "
                "FROM point_history "
                "WHERE point_id = :pid AND time BETWEEN :from_dt AND :to_dt "
                "ORDER BY time DESC LIMIT :limit"
            )
            rows = (
                await session.execute(sql, {"pid": point_id, "from_dt": from_dt, "to_dt": to_dt, "limit": limit})
            ).fetchall()
        else:
            bucket = _BUCKET_MAP[interval]
            sql = text(
                f"SELECT time_bucket('{bucket}', time) AS timestamp, "
                "AVG(value) AS value, "
                "'good' AS quality "
                "FROM point_history "
                "WHERE point_id = :pid AND time BETWEEN :from_dt AND :to_dt "
                "GROUP BY timestamp ORDER BY timestamp DESC LIMIT :limit"
            )
            rows = (
                await session.execute(sql, {"pid": point_id, "from_dt": from_dt, "to_dt": to_dt, "limit": limit})
            ).fetchall()

    records = [
        PointHistoryRecord(
            timestamp=row.timestamp if row.timestamp.tzinfo else row.timestamp.replace(tzinfo=timezone.utc),
            value=float(row.value),
            quality=row.quality,
        )
        for row in rows
    ]

    logger.info(
        "Histórico consultado",
        extra={"point_id": point_id, "interval": interval, "count": len(records)},
    )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "value", "quality"])
        for r in records:
            writer.writerow([r.timestamp.isoformat(), r.value, r.quality])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=point_{point_id}_history.csv"},
        )

    return PointHistoryResponse(
        point_id=point_id,
        point_name=point.name,
        unit=point.unit or None,
        from_dt=from_dt,
        to_dt=to_dt,
        interval=interval,
        records=records,
        count=len(records),
    )
