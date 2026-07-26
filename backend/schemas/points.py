from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


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


class PointCreate(BaseModel):
    device_id: int
    name: str = Field(max_length=255)
    description: str = Field(default="", max_length=500)
    object_type: str = Field(max_length=100)
    address: str = Field(max_length=255)
    unit: str = Field(default="", max_length=50)
    writable: bool = False
    log_enabled: bool = False
    history_interval_seconds: int = Field(default=60, ge=1)
    area_id: int | None = None


class PointUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    unit: str | None = Field(default=None, max_length=50)
    writable: bool | None = None
    log_enabled: bool | None = None
    history_interval_seconds: int | None = Field(default=None, ge=1)
    area_id: int | None = None


class PointResponse(BaseModel):
    id: int
    device_id: int
    name: str
    description: str
    object_type: str
    address: str
    unit: str
    writable: bool
    log_enabled: bool
    history_interval_seconds: int
    area_id: int | None
    area_name: str | None = None

    model_config = {"from_attributes": True}
