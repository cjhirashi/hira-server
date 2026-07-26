"""add ai_config table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False, server_default="claude"),
        sa.Column("model", sa.String(100), nullable=False, server_default="claude-sonnet-4-6"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.execute(
        "INSERT INTO ai_config (id, provider, model) VALUES (1, 'claude', 'claude-sonnet-4-6') "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("ai_config")
