import asyncio
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.deps import get_current_admin
from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.permission import DocumentPermission
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.services.audit import log as audit_log

router = APIRouter(prefix="/admin", tags=["管理后台"])


class UpdateUserBody(BaseModel):
    role: Literal["admin", "member"] | None = None
    is_active: bool | None = None


class GrantPermissionBody(BaseModel):
    user_id: UUID
    permission: str = Field(default="read", pattern=r"^(read|write)$")


@router.get("/prompt-templates")
async def list_all_templates(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptTemplate).order_by(PromptTemplate.created_at.desc()))
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "top_k": t.top_k,
            "threshold": t.threshold,
        }
        for t in result.scalars().all()
    ]


@router.get("/users")
async def list_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    limit = min(limit, 100)
    query = select(User)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.where(User.name.ilike(pattern) | User.email.ilike(pattern))
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(limit))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "is_admin": u.role == "admin",
            "disabled_reason": u.disabled_reason,
            "disabled_at": str(u.disabled_at) if u.disabled_at else None,
            "failed_login_count": u.failed_login_count or 0,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


class UserStatusUpdate(BaseModel):
    is_active: bool
    disabled_reason: str | None = None


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    body: UserStatusUpdate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == admin.id and not body.is_active:
        raise HTTPException(status_code=400, detail="不能禁用自己")

    from datetime import datetime, timezone

    if not body.is_active:
        user.is_active = False
        user.disabled_reason = body.disabled_reason
        user.disabled_at = datetime.now(timezone.utc)
        action = "user.disable"
    else:
        user.is_active = True
        user.disabled_reason = None
        user.disabled_at = None
        user.failed_login_count = 0
        action = "user.enable"

    await db.flush()

    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=admin,
        action=action,
        resource_type="user",
        resource_id=user_id,
        request=request,
        metadata={"target_email": user.email, "reason": body.disabled_reason},
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "disabled_reason": user.disabled_reason,
        "disabled_at": str(user.disabled_at) if user.disabled_at else None,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UpdateUserBody,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    detail_changes = []
    if body.role is not None:
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="不能修改自己的角色")
        detail_changes.append(f"角色: {user.role}→{body.role}")
        user.role = body.role
    if body.is_active is not None:
        if user.id == admin.id and not body.is_active:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        detail_changes.append(f"状态: {'启用' if body.is_active else '禁用'}")
        user.is_active = body.is_active
    await db.flush()

    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=admin,
        action="admin.update_user",
        resource_type="user",
        resource_id=user_id,
        request=request,
        metadata={"detail": "; ".join(detail_changes), "target_email": user.email},
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.get("/stats")
async def get_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache_get("cache:admin:stats")
    if cached:
        return cached

    from app.models.message_feedback import MessageFeedback

    # 并行执行所有 COUNT 查询
    results = await asyncio.gather(
        db.scalar(select(func.count(User.id))),
        db.scalar(select(func.count(Document.id))),
        db.scalar(select(func.count(Conversation.id))),
        db.scalar(select(func.count(DocumentChunk.id))),
        db.scalar(select(func.count(KnowledgeBase.id))),
        db.scalar(select(func.count(Message.id))),
        db.scalar(select(func.count(Message.id)).where(Message.role == "assistant")),
        db.scalar(
            select(func.count(Message.id)).where(
                Message.role == "assistant",
                Message.sources.isnot(None),
                func.jsonb_array_length(Message.sources) > 0,
            )
        ),
        db.scalar(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "up")),
        db.scalar(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "down")),
        db.scalar(
            select(func.count(Conversation.id)).where(
                func.date(Conversation.created_at) == func.current_date()
            )
        ),
    )
    user_count, doc_count, conv_count, chunk_count, kb_count, msg_count = results[:6]
    total_assistant, hit_assistant, praise, critic, today = results[6:]
    hit_rate = round(hit_assistant / total_assistant * 100, 1) if total_assistant else 0
    data = {
        "users": user_count,
        "documents": doc_count,
        "conversations": conv_count,
        "chunks": chunk_count,
        "knowledge_bases": kb_count,
        "messages": msg_count,
        "hit_rate": hit_rate,
        "praise": praise or 0,
        "criticism": critic or 0,
        "today_conversations": today or 0,
    }
    await cache_set("cache:admin:stats", data, ttl=60)
    return data


@router.get("/documents")
async def list_all_documents(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        {"id": str(d.id), "title": d.title, "status": d.status, "created_at": str(d.created_at)}
        for d in docs
    ]


@router.get("/documents/{doc_id}/permissions")
async def list_permissions(
    doc_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    result = await db.execute(
        select(DocumentPermission, User)
        .join(User, DocumentPermission.user_id == User.id)
        .where(DocumentPermission.document_id == doc_id)
    )
    rows = result.all()
    return [
        {"user_id": str(u.id), "name": u.name, "email": u.email, "permission": p.permission}
        for p, u in rows
    ]


@router.post("/documents/{doc_id}/permissions")
async def grant_permission(
    doc_id: UUID,
    body: GrantPermissionBody,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, body.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 检查是否已有权限记录，避免 UniqueConstraint → 500
    existing = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该用户已有此文档权限")

    perm = DocumentPermission(document_id=doc_id, user_id=body.user_id, permission=body.permission)
    db.add(perm)
    await db.flush()
    await audit_log(
        db,
        str(admin.id),
        "admin_grant_permission",
        "document",
        str(doc_id),
        f"管理员 {admin.name} 授予 {target.name} 对文档「{doc_id}」的权限",
        ip=request.client.host if request.client else None,
    )
    return {"detail": "已授权"}


@router.delete("/documents/{doc_id}/permissions/{user_id}")
async def revoke_permission(
    doc_id: UUID,
    user_id: UUID,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.user_id == user_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    await db.delete(perm)
    target_user = await db.get(User, user_id)
    target_name = target_user.name if target_user else str(user_id)
    doc = await db.get(Document, doc_id)
    doc_title = doc.title if doc else str(doc_id)
    await audit_log(
        db,
        str(admin.id),
        "admin_revoke_permission",
        "document",
        str(doc_id),
        f"管理员 {admin.name} 撤销 {target_name} 对文档「{doc_title}」的权限",
        ip=request.client.host if request.client else None,
    )
    return {"detail": "已撤销"}


# ---------- 健康状态 API ----------


@router.get("/health/overview")
async def health_overview(
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统健康概览"""
    import time

    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=admin,
        action="admin.health.view",
        request=request,
    )

    result = {
        "status": "ok",
        "database": {"status": "ok", "latency_ms": 0},
        "redis": {"status": "ok", "latency_ms": 0},
        "documents": {"total": 0, "indexed": 0, "processing": 0, "failed": 0, "recent_failed": []},
        "rag_evals": {"total_runs": 0, "latest_score": None, "latest_passed": 0, "latest_failed": 0},
        "feedback": {"up": 0, "down": 0},
    }

    # Database check
    try:
        t0 = time.time()
        await db.execute(select(func.count(Document.id)))
        result["database"]["latency_ms"] = round((time.time() - t0) * 1000)
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        result["database"]["status"] = "down"
        result["status"] = "degraded"

    # Redis check
    try:
        from app.core.ratelimit import get_redis

        t0 = time.time()
        r = await get_redis()
        await r.ping()
        result["redis"]["latency_ms"] = round((time.time() - t0) * 1000)
    except Exception as e:
        logger.warning(f"Redis 健康检查失败: {e}")
        result["redis"]["status"] = "down"
        result["status"] = "degraded"

    # Document stats
    try:
        from sqlalchemy import case

        doc_stats = await db.execute(
            select(
                func.count(Document.id).label("total"),
                func.sum(case((Document.status == "indexed", 1), else_=0)).label("indexed"),
                func.sum(case((Document.status == "processing", 1), else_=0)).label("processing"),
                func.sum(case((Document.status == "failed", 1), else_=0)).label("failed"),
            )
        )
        row = doc_stats.one()
        result["documents"]["total"] = row.total or 0
        result["documents"]["indexed"] = row.indexed or 0
        result["documents"]["processing"] = row.processing or 0
        result["documents"]["failed"] = row.failed or 0

        # Recent failed
        failed_result = await db.execute(
            select(Document)
            .where(Document.status == "failed")
            .order_by(Document.updated_at.desc())
            .limit(5)
        )
        result["documents"]["recent_failed"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "status": d.status,
                "error_message": (d.error_message or "")[:200],
                "updated_at": str(d.updated_at) if d.updated_at else None,
            }
            for d in failed_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"文档统计查询失败: {e}")
        result["status"] = "degraded"

    # RAG eval stats
    try:
        from app.models.rag_eval import RagEvalRun

        eval_stats = await db.execute(
            select(
                func.count(RagEvalRun.id).label("total"),
                func.count(RagEvalRun.id).filter(RagEvalRun.passed.is_(True)).label("passed"),
                func.count(RagEvalRun.id).filter(RagEvalRun.passed.is_(False)).label("failed"),
            )
        )
        eval_row = eval_stats.one()
        result["rag_evals"]["total_runs"] = eval_row.total or 0
        result["rag_evals"]["latest_passed"] = eval_row.passed or 0
        result["rag_evals"]["latest_failed"] = eval_row.failed or 0

        # Latest score
        latest_run = await db.execute(
            select(RagEvalRun.score).where(RagEvalRun.score.isnot(None)).order_by(RagEvalRun.created_at.desc()).limit(1)
        )
        score = latest_run.scalar_one_or_none()
        result["rag_evals"]["latest_score"] = round(score, 2) if score is not None else None
    except Exception as e:
        logger.warning(f"RAG eval 统计查询失败: {e}")

    # Feedback stats
    try:
        from app.models.message_feedback import MessageFeedback

        fb_stats = await db.execute(
            select(
                func.count(MessageFeedback.id).filter(MessageFeedback.rating == "up").label("up"),
                func.count(MessageFeedback.id).filter(MessageFeedback.rating == "down").label("down"),
            )
        )
        fb_row = fb_stats.one()
        result["feedback"]["up"] = fb_row.up or 0
        result["feedback"]["down"] = fb_row.down or 0
    except Exception as e:
        logger.warning(f"反馈统计查询失败: {e}")

    return result


@router.get("/health/indexing")
async def health_indexing(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """索引状态概览"""
    result = {
        "pending": 0, "processing": 0, "indexed": 0, "failed": 0,
        "stuck_processing": [], "top_retry": [], "recent_failed": [], "recent_indexed": [],
    }

    # Status counts
    try:
        stats = await db.execute(
            select(
                func.count(Document.id).filter(Document.status == "pending").label("pending"),
                func.count(Document.id).filter(Document.status == "processing").label("processing"),
                func.count(Document.id).filter(Document.status == "indexed").label("indexed"),
                func.count(Document.id).filter(Document.status == "failed").label("failed"),
            )
        )
        row = stats.one()
        result["pending"] = row.pending or 0
        result["processing"] = row.processing or 0
        result["indexed"] = row.indexed or 0
        result["failed"] = row.failed or 0
    except Exception as e:
        logger.warning(f"索引状态统计查询失败: {e}")

    # Top retry count
    try:
        retry_result = await db.execute(
            select(Document)
            .where(Document.retry_count > 0)
            .order_by(Document.retry_count.desc())
            .limit(5)
        )
        result["top_retry"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "retry_count": d.retry_count,
                "status": d.status,
            }
            for d in retry_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"重试统计查询失败: {e}")

    # Recent failed
    try:
        failed_result = await db.execute(
            select(Document)
            .where(Document.status == "failed")
            .order_by(Document.updated_at.desc())
            .limit(5)
        )
        result["recent_failed"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "error_message": (d.error_message or "")[:200],
                "updated_at": str(d.updated_at) if d.updated_at else None,
            }
            for d in failed_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"最近失败文档查询失败: {e}")

    # Recent indexed
    try:
        indexed_result = await db.execute(
            select(Document)
            .where(Document.status == "indexed")
            .order_by(Document.indexed_at.desc())
            .limit(5)
        )
        result["recent_indexed"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "indexed_at": str(d.indexed_at) if d.indexed_at else None,
            }
            for d in indexed_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"最近索引文档查询失败: {e}")

    # Stuck processing (>10 minutes)
    try:
        from datetime import datetime, timedelta, timezone

        stuck_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        stuck_result = await db.execute(
            select(Document)
            .where(Document.status == "processing", Document.updated_at < stuck_threshold)
            .order_by(Document.updated_at.asc())
            .limit(10)
        )
        result["stuck_processing"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "updated_at": str(d.updated_at) if d.updated_at else None,
            }
            for d in stuck_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"卡住文档查询失败: {e}")

    return result


@router.get("/health/chat")
async def health_chat(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """聊天/RAG 健康概览"""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # Recent 24h assistant messages
    msg_count = await db.scalar(
        select(func.count(Message.id)).where(
            Message.role == "assistant",
            Message.created_at >= day_ago,
        )
    )

    # Recent 24h feedback
    from app.models.message_feedback import MessageFeedback

    fb_stats = await db.execute(
        select(
            func.count(MessageFeedback.id).filter(MessageFeedback.rating == "up").label("up"),
            func.count(MessageFeedback.id).filter(MessageFeedback.rating == "down").label("down"),
        ).where(MessageFeedback.created_at >= day_ago)
    )
    fb_row = fb_stats.one()

    # RAG eval stats
    from app.models.rag_eval import RagEvalRun

    eval_stats = await db.execute(
        select(
            func.count(RagEvalRun.id).label("total"),
            func.avg(RagEvalRun.score).label("avg_score"),
            func.count(RagEvalRun.id).filter(RagEvalRun.passed.is_(False)).label("failed"),
        ).where(RagEvalRun.created_at >= day_ago)
    )
    eval_row = eval_stats.one()

    # Top failure reasons
    failure_result = await db.execute(
        select(RagEvalRun.failure_reason, func.count(RagEvalRun.id).label("count"))
        .where(RagEvalRun.passed.is_(False), RagEvalRun.failure_reason.isnot(None))
        .group_by(RagEvalRun.failure_reason)
        .order_by(func.count(RagEvalRun.id).desc())
        .limit(5)
    )
    top_failures = [
        {"reason": row.failure_reason, "count": row.count}
        for row in failure_result.all()
    ]

    return {
        "messages_24h": msg_count or 0,
        "feedback_up_24h": fb_row.up or 0,
        "feedback_down_24h": fb_row.down or 0,
        "rag_eval_avg_score": round(eval_row.avg_score, 2) if eval_row.avg_score else None,
        "rag_eval_failed_24h": eval_row.failed or 0,
        "rag_eval_top_failures": top_failures,
    }


@router.get("/audit-logs")
async def list_audit_logs(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """查询审计日志"""
    from app.models.audit_log import AuditLog

    limit = min(limit, 100)

    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if actor_user_id:
        query = query.where(AuditLog.user_id == actor_user_id)
        count_query = count_query.where(AuditLog.user_id == actor_user_id)
    if status:
        query = query.where(AuditLog.status == status)
        count_query = count_query.where(AuditLog.status == status)

    total = await db.scalar(count_query)
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(log.id),
                "actor_email": log.actor_email,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "status": log.status,
                "ip": log.ip,
                "metadata": log.metadata_ or {},
                "created_at": str(log.created_at),
            }
            for log in logs
        ],
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }
