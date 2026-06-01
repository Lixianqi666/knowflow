"""fix production schema compatibility

Revision ID: 019_fix_production_schema_compat
Revises: 018_add_rag_quality_issues
Create Date: 2026-06-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "019_fix_production_schema_compat"
down_revision: Union[str, None] = "018_add_rag_quality_issues"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    return name in inspect(bind).get_table_names()


def _has_column(bind, table: str, col: str) -> bool:
    try:
        return any(c["name"] == col for c in inspect(bind).get_columns(table))
    except Exception:
        return False


def _has_index(bind, table: str, idx_name: str) -> bool:
    try:
        return any(i["name"] == idx_name for i in inspect(bind).get_indexes(table))
    except Exception:
        return False


def _add_col(bind, table: str, column: sa.Column):
    if not _has_column(bind, table, column.name):
        op.add_column(table, column)


def _ensure_nullable(table: str, column: str):
    """Use raw SQL to drop NOT NULL — survives transaction issues from prior ops."""
    op.execute(
        text(
            f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()

    # ── audit_logs ──────────────────────────────────────────────
    if _has_table(bind, "audit_logs"):
        _add_col(bind, "audit_logs", sa.Column("actor_email", sa.String(255), nullable=True))
        _add_col(bind, "audit_logs", sa.Column("status", sa.String(20), nullable=True, server_default="success"))
        _add_col(bind, "audit_logs", sa.Column("user_agent", sa.String(500), nullable=True))
        _add_col(bind, "audit_logs", sa.Column("metadata", JSONB(), nullable=True, server_default="{}"))

        # resource_type must be nullable — raw SQL is immune to prior txn state
        _ensure_nullable("audit_logs", "resource_type")

        # resource_id also nullable (some audit events don't have a resource)
        _ensure_nullable("audit_logs", "resource_id")

    # ── users ───────────────────────────────────────────────────
    if _has_table(bind, "users"):
        _add_col(bind, "users", sa.Column("disabled_reason", sa.Text(), nullable=True))
        _add_col(bind, "users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
        _add_col(bind, "users", sa.Column("failed_login_count", sa.Integer(), nullable=True, server_default="0"))

    # ── documents ───────────────────────────────────────────────
    if _has_table(bind, "documents"):
        _add_col(bind, "documents", sa.Column("error_message", sa.Text(), nullable=True))
        _add_col(bind, "documents", sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"))

    # ── messages ────────────────────────────────────────────────
    if _has_table(bind, "messages"):
        _add_col(bind, "messages", sa.Column("citations", JSONB(), nullable=True, server_default="[]"))

    # ── knowledge_bases ─────────────────────────────────────────
    if _has_table(bind, "knowledge_bases"):
        _add_col(bind, "knowledge_bases", sa.Column("rag_config", JSONB(), nullable=True))

    # ── agents ──────────────────────────────────────────────────
    if _has_table(bind, "agents"):
        _add_col(bind, "agents", sa.Column("draft_config", JSONB(), nullable=True))
        _add_col(bind, "agents", sa.Column("published_config", JSONB(), nullable=True))
        _add_col(bind, "agents", sa.Column("status", sa.String(20), nullable=True, server_default="draft"))
        _add_col(bind, "agents", sa.Column("published_version", sa.Integer(), nullable=True))
        _add_col(bind, "agents", sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True))

    # ── message_feedbacks ───────────────────────────────────────
    if not _has_table(bind, "message_feedbacks"):
        op.create_table(
            "message_feedbacks",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rating", sa.String(10), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedback_user"),
        )
        if not _has_index(bind, "message_feedbacks", "ix_message_feedbacks_message_id"):
            op.create_index("ix_message_feedbacks_message_id", "message_feedbacks", ["message_id"])
        if not _has_index(bind, "message_feedbacks", "ix_message_feedbacks_user_id"):
            op.create_index("ix_message_feedbacks_user_id", "message_feedbacks", ["user_id"])

    # ── rag_eval_cases ──────────────────────────────────────────
    if not _has_table(bind, "rag_eval_cases"):
        op.create_table(
            "rag_eval_cases",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("expected_answer", sa.Text(), nullable=True),
            sa.Column("expected_citation_doc_ids", JSONB(), nullable=True, server_default="[]"),
            sa.Column("tags", JSONB(), nullable=True, server_default="[]"),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )

    # ── rag_eval_runs ───────────────────────────────────────────
    if not _has_table(bind, "rag_eval_runs"):
        op.create_table(
            "rag_eval_runs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("rag_eval_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer", sa.Text(), nullable=True),
            sa.Column("citations", JSONB(), nullable=True, server_default="[]"),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )

    # ── knowledge_base_members ──────────────────────────────────
    if not _has_table(bind, "knowledge_base_members"):
        op.create_table(
            "knowledge_base_members",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("knowledge_base_id", "user_id", name="uq_kb_member_user"),
        )

    # ── rag_quality_issues ──────────────────────────────────────
    if not _has_table(bind, "rag_quality_issues"):
        op.create_table(
            "rag_quality_issues",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True),
            sa.Column("source_type", sa.String(20), nullable=False),
            sa.Column("source_id", sa.String(255), nullable=True),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("answer", sa.Text(), nullable=True),
            sa.Column("citations", JSONB(), nullable=True, server_default="[]"),
            sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column("assignee_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_rag_quality_issues_source_type", "rag_quality_issues", ["source_type"])
        op.create_index("ix_rag_quality_issues_status", "rag_quality_issues", ["status"])
        op.create_index("ix_rag_quality_issues_knowledge_base_id", "rag_quality_issues", ["knowledge_base_id"])


def downgrade() -> None:
    pass
