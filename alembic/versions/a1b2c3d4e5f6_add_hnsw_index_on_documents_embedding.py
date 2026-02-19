"""add HNSW index on documents.embedding

Revision ID: a1b2c3d4e5f6
Revises: e573ef0afc85
Create Date: 2026-02-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e573ef0afc85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index for cosine distance similarity search on document embeddings.
    # m=16 and ef_construction=64 are pgvector defaults; suitable for ~thousands of rows.
    op.execute("""
        CREATE INDEX ix_documents_embedding_hnsw
        ON documents
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding_hnsw")
