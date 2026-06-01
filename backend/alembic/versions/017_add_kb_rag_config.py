"""add kb rag_config

Revision ID: 017_add_kb_rag_config
Revises: 016_add_user_account_fields
Create Date: 2026-06-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017_add_kb_rag_config"
down_revision: Union[str, None] = "016_add_user_account_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("rag_config", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_bases", "rag_config")
