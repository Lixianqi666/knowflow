"""RAG 质量问题自动创建服务"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_quality_issue import RagQualityIssue

logger = logging.getLogger(__name__)


async def create_issue_from_feedback(
    db: AsyncSession,
    *,
    message_id: str,
    question: str | None = None,
    answer: str | None = None,
    citations: list | None = None,
    reason: str | None = None,
    knowledge_base_id: str | None = None,
    created_by: str | None = None,
) -> RagQualityIssue | None:
    """从 down feedback 自动创建质量问题，避免重复"""
    # 检查是否已有同一 source 的 open/in_progress issue
    existing = await db.execute(
        select(RagQualityIssue).where(
            RagQualityIssue.source_type == "feedback",
            RagQualityIssue.source_id == message_id,
            RagQualityIssue.status.in_(["open", "in_progress"]),
        )
    )
    if existing.scalar_one_or_none():
        return None

    issue = RagQualityIssue(
        knowledge_base_id=knowledge_base_id,
        source_type="feedback",
        source_id=message_id,
        question=question,
        answer=answer[:2000] if answer else None,
        citations=citations or [],
        severity="medium",
        status="open",
        reason=reason,
        created_by=created_by,
    )
    db.add(issue)
    await db.flush()
    return issue


async def create_issue_from_eval(
    db: AsyncSession,
    *,
    run_id: str,
    case_id: str,
    question: str,
    answer: str | None = None,
    citations: list | None = None,
    failure_reason: str | None = None,
    knowledge_base_id: str | None = None,
    created_by: str | None = None,
) -> RagQualityIssue | None:
    """从 eval failed 自动创建质量问题，避免重复"""
    existing = await db.execute(
        select(RagQualityIssue).where(
            RagQualityIssue.source_type == "eval_failed",
            RagQualityIssue.source_id == run_id,
            RagQualityIssue.status.in_(["open", "in_progress"]),
        )
    )
    if existing.scalar_one_or_none():
        return None

    issue = RagQualityIssue(
        knowledge_base_id=knowledge_base_id,
        source_type="eval_failed",
        source_id=run_id,
        question=question,
        answer=answer[:2000] if answer else None,
        citations=citations or [],
        severity="high",
        status="open",
        reason=failure_reason,
        created_by=created_by,
    )
    db.add(issue)
    await db.flush()
    return issue
