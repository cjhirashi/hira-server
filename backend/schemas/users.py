from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=150)
    password: str = Field(min_length=8)
    role_id: int = Field(ge=1)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    role_id: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    role_id: int
    role_name: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}
