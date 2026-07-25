from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class ScriptExecution(Base):
    __tablename__ = "script_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("logic_scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # logic | test
    script_type: Mapped[str] = mapped_column(String(20), nullable=False, default="logic")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # running | success | error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    script: Mapped["LogicScript"] = relationship(back_populates="executions")  # noqa: F821
