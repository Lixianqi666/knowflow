"""add vector and conversation indexes

Revision ID: REVISION_PLACEHOLDER
Revises: 005_add_performance_indexes
Create Date: 2026-05-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "abbd9aca2f92"
down_revision: Union[str, None] = "005_add_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IVFFlat index for vector search on embedding column
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
    # Composite index for conversation listing
    op.create_index(
        "idx_conversations_user_updated",
        "conversations",
        ["user_id", sa.text("updated_at DESC")],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_embedding", if_exists=True)
    op.drop_index("idx_conversations_user_updated", if_exists=True)
