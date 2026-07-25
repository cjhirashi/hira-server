import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class EngineeringSession(Base):
    __tablename__ = "engineering_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    integrator_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    studio_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    studio_ip: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    # active | closed | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
