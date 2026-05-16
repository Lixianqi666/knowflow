"""add agent runtime tables

Revision ID: 003_add_agent_runtime_tables
Revises: 002_add_tsvector_and_feedback
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_add_agent_runtime_tables"
down_revision = "002_add_tsvector_and_feedback"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="running"),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("total_steps", sa.Integer(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])

    op.create_table(
        "agent_step_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=30), nullable=False),
        sa.Column("thought", sa.Text(), server_default=""),
        sa.Column("action", postgresql.JSONB(), server_default="{}"),
        sa.Column("observation", postgresql.JSONB(), server_default="{}"),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("tokens", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_step_traces_run_id", "agent_step_traces", ["run_id"])
    op.create_index("idx_agent_step_run_step", "agent_step_traces", ["run_id", "step_index"])


def downgrade():
    op.drop_index("idx_agent_step_run_step", table_name="agent_step_traces")
    op.drop_index("ix_agent_step_traces_run_id", table_name="agent_step_traces")
    op.drop_table("agent_step_traces")
    op.drop_index("ix_agent_runs_user_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_table("agent_runs")
