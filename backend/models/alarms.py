from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class AlarmEvent(Base):
    """Evento de alarma disparado. Tabla física: 'alarms' (nombre heredado de Sprint 0)."""

    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("alarm_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    point_id: Mapped[int] = mapped_column(ForeignKey("points.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_value: Mapped[float] = mapped_column(Float, nullable=False)
    value_at_trigger: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    definition: Mapped["AlarmDefinition"] = relationship("AlarmDefinition", back_populates="alarms")  # noqa: F821
