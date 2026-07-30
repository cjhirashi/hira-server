from datetime import datetime
from typing import Any
from pydantic import BaseModel


class MimicCreate(BaseModel):
    name: str
    description: str | None = None
    canvas: dict[str, Any] | None = None
    elements: list[dict[str, Any]] = []
    connections: list[dict[str, Any]] = []


class MimicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    canvas: dict[str, Any] | None = None
    elements: list[dict[str, Any]] | None = None
    connections: list[dict[str, Any]] | None = None


class MimicResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    schema_version: str
    canvas: dict[str, Any] | None
    elements: list[dict[str, Any]]
    connections: list[dict[str, Any]]
    updated_at: datetime

    model_config = {"from_attributes": True}
