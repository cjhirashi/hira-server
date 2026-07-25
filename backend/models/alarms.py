from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    definition_id: Mapped[int] = mapped_column(
        ForeignKey("alarm_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value_at_trigger: Mapped[float] = mapped_column(Float, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    definition: Mapped["AlarmDefinition"] = relationship(back_populates="alarms")  # noqa: F821
