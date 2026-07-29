"""Motor de Pruebas Funcionales — test_scripts, test_executions, test_logs

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_scripts (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            description TEXT,
            code        TEXT NOT NULL DEFAULT '',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS test_executions (
            id            SERIAL PRIMARY KEY,
            script_id     INTEGER NOT NULL REFERENCES test_scripts(id) ON DELETE CASCADE,
            started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at      TIMESTAMPTZ,
            status        VARCHAR(20) NOT NULL DEFAULT 'running',
            output        TEXT,
            error_message TEXT,
            passed        INTEGER,
            failed        INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS test_logs (
            id           SERIAL PRIMARY KEY,
            execution_id INTEGER NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
            level        VARCHAR(10) NOT NULL DEFAULT 'info',
            message      TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_script_id ON test_executions(script_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_started_at ON test_executions(started_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_test_logs_execution_id ON test_logs(execution_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS test_logs")
    op.execute("DROP TABLE IF EXISTS test_executions")
    op.execute("DROP TABLE IF EXISTS test_scripts")
