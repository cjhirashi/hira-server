"""pgvector + document_chunks para RAG

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_EXTENSION_EXISTED = False


def upgrade() -> None:
    # Activar extensión pgvector (idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content     TEXT    NOT NULL,
            embedding   vector(1536)
        )
    """)

    # Índice HNSW para búsqueda coseno (solo en filas con embedding)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
        ON document_chunks USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
    """)

    # Índice único (document_id, chunk_index)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_document_chunks_doc_chunk
        ON document_chunks (document_id, chunk_index)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_doc_chunk")
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    # No eliminamos la extensión vector — puede estar en uso por otras tablas
