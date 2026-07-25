from typing import Any
from pydantic import BaseModel, Field


class SimulatorCreate(BaseModel):
    name: str = Field(max_length=255)
    protocol: str = Field(pattern=r"^(bacnet|modbus|mqtt)$")
    config_json: dict[str, Any] | None = None


class SimulatorResponse(BaseModel):
    id: int
    name: str
    protocol: str
    status: str
    is_simulator: bool = True
    config_json: dict[str, Any] | None
    celery_task_id: str | None = None

    model_config = {"from_attributes": True}
