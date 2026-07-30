"""Módulo de Documentación — tabla documents

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id               SERIAL PRIMARY KEY,
            title            VARCHAR(255) NOT NULL,
            type             VARCHAR(30)  NOT NULL,
            source_type      VARCHAR(30),
            source_id        INTEGER,
            content_markdown TEXT         NOT NULL DEFAULT '',
            generated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_source
        ON documents (source_type, source_id)
        WHERE source_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_source")
    op.execute("DROP TABLE IF EXISTS documents")
