"""add citations and message_feedbacks

Revision ID: 011_add_citations_feedback
Revises: 010_add_document_error_retry
Create Date: 2026-05-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "011_add_citations_feedback"
down_revision: Union[str, None] = "010_add_document_error_retry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Message citations
    if not _column_exists(inspector, "messages", "citations"):
        op.add_column("messages", sa.Column("citations", JSONB(), nullable=True, server_default="[]"))

    # MessageFeedback table
    if "message_feedbacks" not in inspector.get_table_names():
        op.create_table(
            "message_feedbacks",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "message_id",
                UUID(as_uuid=True),
                sa.ForeignKey("messages.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("rating", sa.String(10), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedback_user"),
        )


def downgrade() -> None:
    op.drop_table("message_feedbacks")
    op.drop_column("messages", "citations")
