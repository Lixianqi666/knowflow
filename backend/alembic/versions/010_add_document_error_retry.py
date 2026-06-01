"""add document error_message and retry_count

Revision ID: 010_add_document_error_retry
Revises: 009_add_conversation_goal
Create Date: 2026-05-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_add_document_error_retry"
down_revision: Union[str, None] = "009_add_conversation_goal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("documents", "retry_count")
    op.drop_column("documents", "error_message")
