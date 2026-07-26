from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from models.base import Base


class LogicScript(Base):
    __tablename__ = "logic_scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    code: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    interval_seconds: Mapped[int] = mapped_column(Integer(), nullable=False, default=10)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="stopped")
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    executions: Mapped[list["ScriptExecution"]] = relationship(  # noqa: F821
        back_populates="script", cascade="all, delete-orphan"
    )
