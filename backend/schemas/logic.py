from datetime import datetime

from pydantic import BaseModel, Field


class LogicScriptCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None
    code: str
    interval_seconds: int = Field(default=10, ge=1)


class LogicScriptUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    code: str | None = None
    interval_seconds: int | None = Field(default=None, ge=1)


class LogicScriptResponse(BaseModel):
    id: int
    name: str
    description: str | None
    code: str
    interval_seconds: int
    status: str
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptExecutionResponse(BaseModel):
    id: int
    script_id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    output: str | None
    error_message: str | None

    model_config = {"from_attributes": True}
