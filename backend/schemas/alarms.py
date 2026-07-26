from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class AlarmDefinitionCreate(BaseModel):
    point_id: int
    name: str
    condition: str
    threshold: float
    threshold_high: float | None = None
    priority: str
    message: str
    enabled: bool = True

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        if v not in ("gt", "lt", "eq", "between"):
            raise ValueError("condition debe ser gt, lt, eq o between")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ("critical", "high", "medium", "low"):
            raise ValueError("priority debe ser critical, high, medium o low")
        return v


class AlarmDefinitionResponse(BaseModel):
    id: int
    point_id: int
    name: str
    condition: str
    threshold: float
    threshold_high: float | None
    priority: str
    message: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlarmEventResponse(BaseModel):
    id: int
    alarm_definition_id: int
    point_id: int
    point_name: str
    triggered_value: float
    priority: str
    message: str
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class AlarmHistoryParams(BaseModel):
    point_id: int | None = None
    priority: str | None = None
    status: str | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    limit: int = 100
    offset: int = 0
