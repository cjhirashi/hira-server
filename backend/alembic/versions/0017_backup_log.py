"""Tabla backup_log para Backup L2 (pg_dump automatizado)

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("success", "failed", name="backup_status_enum"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_backup_log_created_at", "backup_log", ["created_at"])
    op.create_index("ix_backup_log_status", "backup_log", ["status"])


def downgrade() -> None:
    op.drop_index("ix_backup_log_status", table_name="backup_log")
    op.drop_index("ix_backup_log_created_at", table_name="backup_log")
    op.drop_table("backup_log")
    op.execute("DROP TYPE IF EXISTS backup_status_enum")
