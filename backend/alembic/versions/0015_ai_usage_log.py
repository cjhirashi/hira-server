"""Tabla ai_usage_log para registrar invocaciones del Agente IA

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("query_preview", sa.String(200), nullable=True),
    )
    op.create_index("ix_ai_usage_log_timestamp", "ai_usage_log", ["timestamp"])
    op.create_index("ix_ai_usage_log_user_id", "ai_usage_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_log_user_id", table_name="ai_usage_log")
    op.drop_index("ix_ai_usage_log_timestamp", table_name="ai_usage_log")
    op.drop_table("ai_usage_log")
