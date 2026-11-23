"""Add pgvector-compatible embedding storage for document chunks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '202503010000'
down_revision = '202501010000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw '
        'ON document_chunks USING hnsw (embedding vector_cosine_ops)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw')
    op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE JSON USING embedding::json')
