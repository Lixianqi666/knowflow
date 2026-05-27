"""add conversation pin columns

Revision ID: 006_add_conversation_pin
Revises: abbd9aca2f92
Create Date: 2026-05-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_add_conversation_pin"
down_revision: Union[str, None] = "abbd9aca2f92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "conversations",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_conversations_pinned",
        "conversations",
        ["user_id", "is_pinned", sa.text("pinned_at DESC NULLS LAST")],
    )


def downgrade() -> None:
    op.drop_index("idx_conversations_pinned", if_exists=True)
    op.drop_column("conversations", "pinned_at")
    op.drop_column("conversations", "is_pinned")
