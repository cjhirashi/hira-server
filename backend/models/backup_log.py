from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class BackupStatus(str, PyEnum):
    success = "success"
    failed = "failed"


class BackupLog(Base):
    __tablename__ = "backup_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[BackupStatus] = mapped_column(
        SAEnum(BackupStatus, name="backup_status_enum"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
