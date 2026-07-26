"""add agent_type to ai_config

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_config",
        sa.Column(
            "agent_type",
            sa.String(20),
            nullable=False,
            server_default="integrador",
        ),
    )
    # Marcar el registro existente id=1 como integrador
    op.execute("UPDATE ai_config SET agent_type = 'integrador' WHERE id = 1")
    # Crear registro para el agente cliente
    op.execute(
        "INSERT INTO ai_config (provider, model, agent_type) "
        "VALUES ('claude', 'claude-sonnet-4-6', 'cliente') "
        "ON CONFLICT DO NOTHING"
    )
    # Unique constraint: un solo registro por tipo de agente
    op.create_unique_constraint("uq_ai_config_agent_type", "ai_config", ["agent_type"])


def downgrade() -> None:
    op.drop_constraint("uq_ai_config_agent_type", "ai_config", type_="unique")
    op.drop_column("ai_config", "agent_type")
