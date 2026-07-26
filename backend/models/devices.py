from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # bacnet | modbus | mqtt
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    area: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"), nullable=True
    )
    # online | offline | error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    is_simulator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_start: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    points: Mapped[list["Point"]] = relationship(back_populates="device")  # noqa: F821
    area_obj: Mapped["Area | None"] = relationship(back_populates="devices")  # noqa: F821
