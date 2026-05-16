"""add reimbursement tables

Revision ID: 004_add_reimbursement_tables
Revises: 003_add_agent_runtime_tables
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_add_reimbursement_tables"
down_revision = "003_add_agent_runtime_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employee_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("employee_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("manager_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_employee_profiles_name", "employee_profiles", ["name"])

    op.create_table(
        "travel_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_name", sa.String(length=80), nullable=False),
        sa.Column("receipt_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_valid", sa.String(length=10), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_travel_receipts_employee_name", "travel_receipts", ["employee_name"])

    op.create_table(
        "reimbursement_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_name", sa.String(length=80), nullable=False),
        sa.Column("trip_city", sa.String(length=80), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="submitted"),
        sa.Column("detail", sa.Text(), server_default=""),
        sa.Column("receipt_ids", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reimbursement_requests_employee_name", "reimbursement_requests", ["employee_name"])


def downgrade():
    op.drop_index("ix_reimbursement_requests_employee_name", table_name="reimbursement_requests")
    op.drop_table("reimbursement_requests")
    op.drop_index("ix_travel_receipts_employee_name", table_name="travel_receipts")
    op.drop_table("travel_receipts")
    op.drop_index("ix_employee_profiles_name", table_name="employee_profiles")
    op.drop_table("employee_profiles")
