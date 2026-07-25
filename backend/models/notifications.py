from datetime import datetime
from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # info | warning | error | critical
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sent_via: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
