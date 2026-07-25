"""init_schema

Revision ID: 0001
Revises:
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── roles ──────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Sembrar roles fijos
    op.execute(
        "INSERT INTO roles (name, description) VALUES "
        "('Admin', 'Acceso completo al sistema'), "
        "('Operador', 'Lectura y control de puntos'), "
        "('Visor', 'Solo lectura')"
    )

    # ── permissions ────────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("area", sa.String(100), nullable=False, server_default="*"),
        sa.Column("access_level", sa.String(20), nullable=False, server_default="read"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── user_roles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # ── devices ────────────────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("area", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("is_simulator", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_start", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── points ─────────────────────────────────────────────────────────────
    op.create_table(
        "points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("object_type", sa.String(100), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default=""),
        sa.Column("writable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("log_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("log_interval_ms", sa.Integer(), nullable=False, server_default="60000"),
        sa.Column("area", sa.String(255), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_points_device_id", "points", ["device_id"])

    # ── alarm_definitions ──────────────────────────────────────────────────
    op.create_table(
        "alarm_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("point_id", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(20), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("message", sa.String(500), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["point_id"], ["points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alarm_definitions_point_id", "alarm_definitions", ["point_id"])

    # ── alarms ─────────────────────────────────────────────────────────────
    op.create_table(
        "alarms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("point_id", sa.Integer(), nullable=False),
        sa.Column("value_at_trigger", sa.Float(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["definition_id"], ["alarm_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["point_id"], ["points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alarms_definition_id", "alarms", ["definition_id"])
    op.create_index("ix_alarms_point_id", "alarms", ["point_id"])

    # ── point_history (hypertable TimescaleDB) ─────────────────────────────
    op.create_table(
        "point_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("point_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Double(), nullable=False),
        sa.Column("quality", sa.String(20), nullable=False, server_default="ok"),
        sa.ForeignKeyConstraint(["point_id"], ["points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("time", "point_id"),
    )
    op.create_index("ix_point_history_point_id_time", "point_history", ["point_id", "time"])

    # Convertir a hypertable de TimescaleDB
    op.execute("SELECT create_hypertable('point_history', 'time', if_not_exists => TRUE)")

    # ── logic_scripts ──────────────────────────────────────────────────────
    op.create_table(
        "logic_scripts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("code", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="paused"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── script_executions ─────────────────────────────────────────────────
    op.create_table(
        "script_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("script_type", sa.String(20), nullable=False, server_default="logic"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("log", sa.Text(), nullable=False, server_default=""),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["script_id"], ["logic_scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_executions_script_id", "script_executions", ["script_id"])

    # ── mimics ─────────────────────────────────────────────────────────────
    op.create_table(
        "mimics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canvas_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── notifications ──────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("sent_via", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── engineering_sessions ───────────────────────────────────────────────
    op.create_table(
        "engineering_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("integrator_user_id", sa.Integer(), nullable=True),
        sa.Column("studio_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("studio_ip", sa.String(50), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(["integrator_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("engineering_sessions")
    op.drop_table("notifications")
    op.drop_table("mimics")
    op.drop_table("script_executions")
    op.drop_table("logic_scripts")
    op.drop_table("point_history")
    op.drop_table("alarms")
    op.drop_table("alarm_definitions")
    op.drop_table("points")
    op.drop_table("devices")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
