"""extend audit_log fields

Revision ID: 013_extend_audit_log
Revises: 012_add_rag_eval
Create Date: 2026-05-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "013_extend_audit_log"
down_revision: Union[str, None] = "012_add_rag_eval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("actor_email", sa.String(255), nullable=True))
    op.add_column("audit_logs", sa.Column("status", sa.String(20), nullable=False, server_default="success"))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column("audit_logs", sa.Column("metadata", JSONB(), nullable=True, server_default="{}"))
    op.alter_column("audit_logs", "action", type_=sa.String(100))
    op.alter_column("audit_logs", "resource_type", nullable=True)


def downgrade() -> None:
    op.drop_column("audit_logs", "metadata")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "status")
    op.drop_column("audit_logs", "actor_email")
