"""add stored_filename to documents

Revision ID: 008_add_stored_filename
Revises: 007_agent_kb_many_to_many
Create Date: 2026-05-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_add_stored_filename"
down_revision: Union[str, None] = "007_agent_kb_many_to_many"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("stored_filename", sa.String(500), nullable=True),
    )
    # 回填已有记录：用 title 作为 stored_filename
    op.execute(
        "UPDATE documents SET stored_filename = title WHERE stored_filename IS NULL"
    )


def downgrade() -> None:
    op.drop_column("documents", "stored_filename")
