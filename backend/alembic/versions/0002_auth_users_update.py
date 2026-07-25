"""Auth — actualiza tabla users y siembra permisos por rol.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tabla users: renombrar name → full_name (nullable), añadir last_login ─
    op.alter_column("users", "name", new_column_name="full_name", nullable=True)
    op.alter_column("users", "full_name", type_=sa.String(150), existing_nullable=True)
    op.add_column("users", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))

    # ── Seed de permisos por rol ───────────────────────────────────────────────
    permissions_table = sa.table(
        "permissions",
        sa.column("role_id", sa.Integer),
        sa.column("module", sa.String),
        sa.column("area", sa.String),
        sa.column("access_level", sa.String),
    )

    # Rol 1 = Admin
    admin_permissions = [
        ("users", "*", "read"), ("users", "*", "write"),
        ("points", "*", "read"), ("points", "*", "write"),
        ("devices", "*", "read"), ("devices", "*", "write"),
        ("alarms", "*", "read"), ("alarms", "*", "write"),
        ("logic", "*", "read"), ("logic", "*", "write"),
        ("historicals", "*", "read"),
        ("backup", "*", "read"), ("backup", "*", "write"),
    ]
    # Rol 2 = Operador
    operador_permissions = [
        ("users", "*", "read"),
        ("points", "*", "read"), ("points", "*", "write"),
        ("devices", "*", "read"),
        ("alarms", "*", "read"), ("alarms", "*", "write"),
        ("logic", "*", "read"),
        ("historicals", "*", "read"),
    ]
    # Rol 3 = Visor
    visor_permissions = [
        ("points", "*", "read"),
        ("devices", "*", "read"),
        ("alarms", "*", "read"),
        ("historicals", "*", "read"),
    ]

    rows = (
        [{"role_id": 1, "module": m, "area": a, "access_level": al} for m, a, al in admin_permissions]
        + [{"role_id": 2, "module": m, "area": a, "access_level": al} for m, a, al in operador_permissions]
        + [{"role_id": 3, "module": m, "area": a, "access_level": al} for m, a, al in visor_permissions]
    )
    op.bulk_insert(permissions_table, rows)


def downgrade() -> None:
    op.execute("DELETE FROM permissions")
    op.drop_column("users", "last_login")
    op.alter_column("users", "full_name", new_column_name="name", nullable=False)
