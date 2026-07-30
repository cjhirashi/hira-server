"""Modbus fields en devices y points

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("modbus_unit_id", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("modbus_transport", sa.String(10), nullable=True))
    op.add_column("devices", sa.Column("modbus_baudrate", sa.Integer(), nullable=True, server_default="9600"))
    op.add_column("points", sa.Column("modbus_register_type", sa.String(30), nullable=True))
    op.add_column("points", sa.Column("modbus_data_type", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("points", "modbus_data_type")
    op.drop_column("points", "modbus_register_type")
    op.drop_column("devices", "modbus_baudrate")
    op.drop_column("devices", "modbus_transport")
    op.drop_column("devices", "modbus_unit_id")
