"""add_areas_and_area_id

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-25

Sprint 7 — Configurador:
1. Crea tabla `areas`
2. Agrega `area_id` (FK nullable, SET NULL) a `devices`
3. Agrega `area_id` (FK nullable, SET NULL) a `points`
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint("uq_areas_name", "areas", ["name"])

    op.add_column(
        "devices",
        sa.Column(
            "area_id",
            sa.Integer(),
            sa.ForeignKey("areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "points",
        sa.Column(
            "area_id",
            sa.Integer(),
            sa.ForeignKey("areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("points", "area_id")
    op.drop_column("devices", "area_id")
    op.drop_constraint("uq_areas_name", "areas", type_="unique")
    op.drop_table("areas")
