from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    # embedding almacenado como texto serializado; pgvector lo maneja nativamente
    # No usar pgvector.sqlalchemy aquí para evitar dependencia en studio/SQLite
    embedding: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
