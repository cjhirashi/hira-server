from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Point(Base):
    __tablename__ = "points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    writable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    log_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    log_interval_ms: Mapped[int] = mapped_column(Integer, default=60000, nullable=False)
    history_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    area: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    device: Mapped["Device"] = relationship(back_populates="points")  # noqa: F821
    alarm_definitions: Mapped[list["AlarmDefinition"]] = relationship(back_populates="point")  # noqa: F821
