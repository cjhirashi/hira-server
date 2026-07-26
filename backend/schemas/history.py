from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PointHistoryRecord(BaseModel):
    timestamp: datetime
    value: float
    quality: Literal["good", "bad", "uncertain"]


class PointHistoryResponse(BaseModel):
    point_id: int
    point_name: str
    unit: str | None
    from_dt: datetime
    to_dt: datetime
    interval: Literal["raw", "1min", "5min", "1hour", "1day"]
    records: list[PointHistoryRecord]
    count: int
