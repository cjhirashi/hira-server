"""Tabla engineering_sessions para Sesión de Ingeniería Remota (ADR-016)

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engineering_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_token", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "engineer_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "expired", "closed", name="session_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.String(500), nullable=True),
    )
    op.create_index("ix_engineering_sessions_token", "engineering_sessions", ["session_token"])
    op.create_index("ix_engineering_sessions_status", "engineering_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_engineering_sessions_status", table_name="engineering_sessions")
    op.drop_index("ix_engineering_sessions_token", table_name="engineering_sessions")
    op.drop_table("engineering_sessions")
    op.execute("DROP TYPE IF EXISTS session_status_enum")
