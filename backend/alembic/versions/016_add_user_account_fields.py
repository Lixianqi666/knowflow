"""add user account fields

Revision ID: 016_add_user_account_fields
Revises: 015_add_kb_members
Create Date: 2026-05-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "016_add_user_account_fields"
down_revision: Union[str, None] = "015_add_kb_members"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _column_exists(inspector, "users", "disabled_reason"):
        op.add_column("users", sa.Column("disabled_reason", sa.Text(), nullable=True))
    if not _column_exists(inspector, "users", "disabled_at"):
        op.add_column("users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(inspector, "users", "failed_login_count"):
        op.add_column("users", sa.Column("failed_login_count", sa.Integer(), nullable=True, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "disabled_at")
    op.drop_column("users", "disabled_reason")
