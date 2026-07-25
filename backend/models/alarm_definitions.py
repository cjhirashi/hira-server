from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class AlarmDefinition(Base):
    __tablename__ = "alarm_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # gt | lt | eq | ne | between
    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    # critical | high | medium | low
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    point: Mapped["Point"] = relationship(back_populates="alarm_definitions")  # noqa: F821
    alarms: Mapped[list["Alarm"]] = relationship(back_populates="definition")  # noqa: F821
