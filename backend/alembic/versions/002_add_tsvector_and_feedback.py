"""add tsvector and feedback

Revision ID: a1b2c3d4e5f6
Revises: 5c2ebacfbc3e
Create Date: 2026-05-03 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5c2ebacfbc3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tsvector_content TSVECTOR")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON document_chunks USING gin (tsvector_content)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id),
            conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
            query TEXT NOT NULL,
            feedback_type VARCHAR(20) NOT NULL,
            message TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedbacks")
    op.execute("DROP INDEX IF EXISTS idx_chunks_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS tsvector_content")
