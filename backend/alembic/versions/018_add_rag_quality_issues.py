"""add rag quality issues

Revision ID: 018_add_rag_quality_issues
Revises: 017_add_kb_rag_config
Create Date: 2026-06-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018_add_rag_quality_issues"
down_revision: Union[str, None] = "017_add_kb_rag_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("assignee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rag_quality_issues_source_type", "rag_quality_issues", ["source_type"])
    op.create_index("ix_rag_quality_issues_status", "rag_quality_issues", ["status"])
    op.create_index("ix_rag_quality_issues_knowledge_base_id", "rag_quality_issues", ["knowledge_base_id"])


def downgrade() -> None:
    op.drop_table("rag_quality_issues")
