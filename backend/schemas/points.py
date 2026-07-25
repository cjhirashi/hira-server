from datetime import datetime
from typing import Any
from pydantic import BaseModel


class PointValue(BaseModel):
    id: int
    name: str
    value: Any
    unit: str | None
    quality: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class PointWriteRequest(BaseModel):
    value: Any


class PointWriteResponse(BaseModel):
    success: bool
    value: Any
    timestamp: datetime
