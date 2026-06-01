"""RAG 质量问题队列 API"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.rag_quality_issue import RagQualityIssue
from app.models.user import User
from app.services.kb_permissions import can_edit_kb, can_view_kb
from app.schemas.rag_quality import (
    RagQualityIssueCreate,
    RagQualityIssueOut,
    RagQualityIssueUpdate,
)

router = APIRouter(prefix="/rag-quality", tags=["RAG 质量"])


async def _can_view_issue(db: AsyncSession, user: User, issue: RagQualityIssue) -> bool:
    """检查用户是否可以查看该 issue"""
    if user.role == "admin":
        return True
    if issue.knowledge_base_id:
        kb = await db.get(KnowledgeBase, issue.knowledge_base_id)
        if kb and await can_view_kb(db, user, kb):
            return True
        return False
    # knowledge_base_id 为空：仅 admin 或创建者
    return issue.created_by == user.id


async def _can_update_issue(db: AsyncSession, user: User, issue: RagQualityIssue) -> bool:
    """检查用户是否可以更新该 issue"""
    if user.role == "admin":
        return True
    if issue.knowledge_base_id:
        kb = await db.get(KnowledgeBase, issue.knowledge_base_id)
        if kb and await can_edit_kb(db, user, kb):
            return True
    return False


@router.get("/issues", response_model=list[RagQualityIssueOut])
async def list_issues(
    status: str | None = None,
    severity: str | None = None,
    source_type: str | None = None,
    knowledge_base_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, 100)
    query = select(RagQualityIssue).order_by(RagQualityIssue.created_at.desc())

    if status:
        query = query.where(RagQualityIssue.status == status)
    if severity:
        query = query.where(RagQualityIssue.severity == severity)
    if source_type:
        query = query.where(RagQualityIssue.source_type == source_type)
    if knowledge_base_id:
        # 校验用户对指定 KB 的访问权限
        kb = await db.get(KnowledgeBase, knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if not await can_view_kb(db, user, kb):
            raise HTTPException(status_code=403, detail="无权限访问该知识库")
        query = query.where(RagQualityIssue.knowledge_base_id == knowledge_base_id)

    # 权限过滤
    if user.role != "admin":
        # 获取用户有权限的 KB IDs
        member_result = await db.execute(
            select(KnowledgeBaseMember.knowledge_base_id).where(
                KnowledgeBaseMember.user_id == user.id
            )
        )
        member_kb_ids = {str(row[0]) for row in member_result.fetchall()}
        created_result = await db.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.created_by == user.id)
        )
        created_kb_ids = {str(row[0]) for row in created_result.fetchall()}
        allowed_kb_ids = member_kb_ids | created_kb_ids

        # 可见：用户有权限的 KB 的 issue + 自己创建的无 KB issue
        query = query.where(
            RagQualityIssue.knowledge_base_id.in_([UUID(kid) for kid in allowed_kb_ids])
            | (
                (RagQualityIssue.knowledge_base_id.is_(None))
                & (RagQualityIssue.created_by == user.id)
            )
        )

    result = await db.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


@router.post("/issues", response_model=RagQualityIssueOut)
async def create_issue(
    data: RagQualityIssueCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.source_type not in ("feedback", "eval_failed", "no_evidence", "manual"):
        raise HTTPException(status_code=400, detail="source_type 无效")
    if data.severity not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="severity 无效")

    if data.knowledge_base_id:
        kb = await db.get(KnowledgeBase, data.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")

    issue = RagQualityIssue(
        knowledge_base_id=data.knowledge_base_id,
        source_type=data.source_type,
        source_id=data.source_id,
        question=data.question,
        answer=data.answer[:2000] if data.answer else None,
        citations=data.citations or [],
        severity=data.severity,
        status="open",
        reason=data.reason,
        created_by=str(user.id),
    )
    db.add(issue)
    await db.flush()

    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="rag_quality.issue_create",
        resource_type="rag_quality_issue",
        resource_id=issue.id,
        request=request,
        metadata={"source_type": data.source_type, "severity": data.severity, "kb_id": data.knowledge_base_id},
    )

    return issue


@router.get("/issues/{issue_id}", response_model=RagQualityIssueOut)
async def get_issue(
    issue_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issue = await db.get(RagQualityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="质量问题不存在")
    if not await _can_view_issue(db, user, issue):
        raise HTTPException(status_code=403, detail="无权查看该质量问题")
    return issue


@router.patch("/issues/{issue_id}", response_model=RagQualityIssueOut)
async def update_issue(
    issue_id: UUID,
    data: RagQualityIssueUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issue = await db.get(RagQualityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="质量问题不存在")
    if not await _can_update_issue(db, user, issue):
        raise HTTPException(status_code=403, detail="无权更新该质量问题")

    old_status = issue.status

    if data.status is not None:
        if data.status not in ("open", "in_progress", "resolved", "ignored"):
            raise HTTPException(status_code=400, detail="status 无效")
        issue.status = data.status
        if data.status == "resolved":
            issue.resolved_at = datetime.now(timezone.utc)
        elif old_status == "resolved" and data.status == "open":
            issue.resolved_at = None

    if data.severity is not None:
        if data.severity not in ("low", "medium", "high"):
            raise HTTPException(status_code=400, detail="severity 无效")
        issue.severity = data.severity

    if data.resolution_note is not None:
        issue.resolution_note = data.resolution_note

    if data.assignee_user_id is not None:
        issue.assignee_user_id = data.assignee_user_id

    await db.flush()

    from app.services.audit_v2 import record_audit_event

    action = "rag_quality.issue_update"
    if data.status == "resolved":
        action = "rag_quality.issue_resolve"
    elif data.status == "ignored":
        action = "rag_quality.issue_ignore"

    await record_audit_event(
        db,
        actor_user=user,
        action=action,
        resource_type="rag_quality_issue",
        resource_id=issue_id,
        request=request,
        metadata={
            "old_status": old_status,
            "new_status": issue.status,
            "severity": issue.severity,
            "kb_id": str(issue.knowledge_base_id) if issue.knowledge_base_id else None,
        },
    )

    return issue
