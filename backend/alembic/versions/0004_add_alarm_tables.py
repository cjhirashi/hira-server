"""add_alarm_columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26

Las tablas alarm_definitions y alarms ya existen (creadas en 0001).
Esta migración agrega las columnas faltantes necesarias para el motor de alarmas
de Sprint 5 (nombre, threshold_high, enabled, timestamps en definitions;
status y triggered_value en alarms).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── alarm_definitions: agregar columnas faltantes ──────────────────────
    op.add_column("alarm_definitions", sa.Column("name", sa.String(255), nullable=False, server_default="Alarma"))
    op.add_column("alarm_definitions", sa.Column("threshold_high", sa.Float(), nullable=True))
    op.add_column("alarm_definitions", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("alarm_definitions", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("alarm_definitions", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_alarm_definitions_enabled", "alarm_definitions", ["enabled"])

    # ── alarms: agregar status y triggered_value ───────────────────────────
    # triggered_value es alias de value_at_trigger (mantenemos ambas por compat)
    op.add_column("alarms", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("alarms", sa.Column("triggered_value", sa.Float(), nullable=False, server_default="0"))
    op.create_index("ix_alarms_status", "alarms", ["status"])
    op.create_index("ix_alarms_triggered_at", "alarms", ["triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_alarms_triggered_at", "alarms")
    op.drop_index("ix_alarms_status", "alarms")
    op.drop_column("alarms", "triggered_value")
    op.drop_column("alarms", "status")

    op.drop_index("ix_alarm_definitions_enabled", "alarm_definitions")
    op.drop_column("alarm_definitions", "updated_at")
    op.drop_column("alarm_definitions", "created_at")
    op.drop_column("alarm_definitions", "enabled")
    op.drop_column("alarm_definitions", "threshold_high")
    op.drop_column("alarm_definitions", "name")
