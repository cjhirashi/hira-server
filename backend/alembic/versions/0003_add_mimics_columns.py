"""add_mimics_columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-26

Agrega las columnas faltantes a la tabla mimics:
schema_version, elements_json, connections_json, updated_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mimics", sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0"))
    op.add_column("mimics", sa.Column("elements_json", sa.JSON(), nullable=True))
    op.add_column("mimics", sa.Column("connections_json", sa.JSON(), nullable=True))
    op.add_column("mimics", sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    ))


def downgrade() -> None:
    op.drop_column("mimics", "updated_at")
    op.drop_column("mimics", "connections_json")
    op.drop_column("mimics", "elements_json")
    op.drop_column("mimics", "schema_version")
