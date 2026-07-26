"""add_history_interval_and_retention

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26

point_history ya existe como hypertable desde migración 0001.
Esta migración:
1. Agrega history_interval_seconds a points (default 60s)
2. Configura política de retención en point_history según HISTORY_RETENTION_DAYS
"""
import os

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "points",
        sa.Column("history_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
    )

    retention_days = int(os.environ.get("HISTORY_RETENTION_DAYS", "90"))
    op.execute(
        f"SELECT add_retention_policy('point_history', INTERVAL '{retention_days} days', if_not_exists => true)"
    )


def downgrade() -> None:
    op.execute("SELECT remove_retention_policy('point_history', if_not_exists => true)")
    op.drop_column("points", "history_interval_seconds")
