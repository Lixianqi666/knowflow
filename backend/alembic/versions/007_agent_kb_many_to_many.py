"""agent knowledge_base many-to-many

Revision ID: 007_agent_kb_many_to_many
Revises: 006_add_conversation_pin
Create Date: 2026-05-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "007_agent_kb_many_to_many"
down_revision: Union[str, None] = "006_add_conversation_pin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建关联表
    op.create_table(
        "agent_knowledge_bases",
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
    )

    # 2. 迁移现有数据：从 JSONB knowledge_base_ids 插入关联表
    op.execute("""
        INSERT INTO agent_knowledge_bases (agent_id, kb_id)
        SELECT a.id, kb_id_val::uuid
        FROM agents a,
        LATERAL unnest(
            CASE
                WHEN jsonb_typeof(a.knowledge_base_ids) = 'array'
                THEN ARRAY(SELECT jsonb_array_elements_text(a.knowledge_base_ids))
                ELSE '{}'::text[]
            END
        ) AS kb_id_val
        WHERE a.knowledge_base_ids IS NOT NULL
          AND jsonb_typeof(a.knowledge_base_ids) = 'array'
          AND jsonb_array_length(a.knowledge_base_ids) > 0
    """)

    # 3. 删除旧的 JSONB 列
    op.drop_column("agents", "knowledge_base_ids")


def downgrade() -> None:
    # 1. 恢复 JSONB 列
    op.add_column("agents", sa.Column("knowledge_base_ids", JSONB, server_default="[]"))

    # 2. 从关联表回填 JSONB
    op.execute("""
        UPDATE agents a
        SET knowledge_base_ids = COALESCE(
            (SELECT jsonb_agg(akb.kb_id::text)
             FROM agent_knowledge_bases akb
             WHERE akb.agent_id = a.id),
            '[]'::jsonb
        )
    """)

    # 3. 删除关联表
    op.drop_table("agent_knowledge_bases")
