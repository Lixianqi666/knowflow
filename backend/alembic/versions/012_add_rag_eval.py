"""add rag eval cases and runs

Revision ID: 012_add_rag_eval
Revises: 011_add_citations_feedback
Create Date: 2026-05-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "012_add_rag_eval"
down_revision: Union[str, None] = "011_add_citations_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "rag_eval_cases"):
        op.create_table(
            "rag_eval_cases",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "knowledge_base_id",
                UUID(as_uuid=True),
                sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("expected_answer", sa.Text(), nullable=True),
            sa.Column("expected_citation_doc_ids", JSONB(), nullable=True, server_default="[]"),
            sa.Column("tags", JSONB(), nullable=True, server_default="[]"),
            sa.Column(
                "created_by",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )

    if not _table_exists(inspector, "rag_eval_runs"):
        op.create_table(
            "rag_eval_runs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "case_id",
                UUID(as_uuid=True),
                sa.ForeignKey("rag_eval_cases.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer", sa.Text(), nullable=True),
            sa.Column("citations", JSONB(), nullable=True, server_default="[]"),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column(
                "created_by",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )


def downgrade() -> None:
    op.drop_table("rag_eval_runs")
    op.drop_table("rag_eval_cases")
