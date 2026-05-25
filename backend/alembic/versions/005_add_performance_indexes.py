"""add performance indexes

Revision ID: 005_add_performance_indexes
Revises: 004_add_reimbursement_tables
Create Date: 2026-05-21
"""

from alembic import op

revision = "005_add_performance_indexes"
down_revision = "004_add_reimbursement_tables"
branch_labels = None
depends_on = None


def upgrade():
    # documents.status 索引（检索时过滤 status='indexed'）
    op.create_index("ix_documents_status", "documents", ["status"])

    # audit_logs 复合索引（按用户+时间查询）
    op.create_index(
        "ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"]
    )


def downgrade():
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_index("ix_documents_status", table_name="documents")
