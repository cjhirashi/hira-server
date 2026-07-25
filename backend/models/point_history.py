from datetime import datetime
from sqlalchemy import DateTime, Double, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class PointHistory(Base):
    """Hypertable de TimescaleDB para históricos de valores de puntos.

    La conversión a hypertable se realiza en la migración de Alembic
    con: SELECT create_hypertable('point_history', 'time');
    """

    __tablename__ = "point_history"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    value: Mapped[float] = mapped_column(Double, nullable=False)
    # ok | bad | uncertain
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")

    __table_args__ = (
        Index("ix_point_history_point_id_time", "point_id", "time"),
    )
