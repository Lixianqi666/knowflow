"""add agent config fields

Revision ID: 014_add_agent_config
Revises: 013_extend_audit_log
Create Date: 2026-05-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "014_add_agent_config"
down_revision: Union[str, None] = "013_extend_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _column_exists(inspector, "agents", "draft_config"):
        op.add_column("agents", sa.Column("draft_config", JSONB(), nullable=True, server_default="{}"))
    if not _column_exists(inspector, "agents", "published_config"):
        op.add_column("agents", sa.Column("published_config", JSONB(), nullable=True, server_default="{}"))
    if not _column_exists(inspector, "agents", "status"):
        op.add_column("agents", sa.Column("status", sa.String(20), nullable=True, server_default="draft"))
    if not _column_exists(inspector, "agents", "published_version"):
        op.add_column("agents", sa.Column("published_version", sa.Integer(), nullable=True, server_default="0"))
    if not _column_exists(inspector, "agents", "last_published_at"):
        op.add_column("agents", sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "last_published_at")
    op.drop_column("agents", "published_version")
    op.drop_column("agents", "status")
    op.drop_column("agents", "published_config")
    op.drop_column("agents", "draft_config")
