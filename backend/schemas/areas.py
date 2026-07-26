from datetime import datetime
from pydantic import BaseModel, Field


class AreaCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)


class AreaResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}
