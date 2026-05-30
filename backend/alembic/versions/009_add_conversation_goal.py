"""add conversation goal fields

Revision ID: 009_add_conversation_goal
Revises: 008_add_stored_filename
Create Date: 2026-05-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009_add_conversation_goal"
down_revision: Union[str, None] = "008_add_stored_filename"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("goal", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("goal_summary", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("goal_status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "conversations",
        sa.Column("missing_info", JSONB(), nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("conversations", "missing_info")
    op.drop_column("conversations", "goal_status")
    op.drop_column("conversations", "goal_summary")
    op.drop_column("conversations", "goal")
