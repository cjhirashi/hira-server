from datetime import datetime
from sqlalchemy import String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    devices: Mapped[list["Device"]] = relationship(back_populates="area_obj")  # noqa: F821
    points: Mapped[list["Point"]] = relationship(back_populates="area_obj")  # noqa: F821
