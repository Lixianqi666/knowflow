import asyncio
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
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
            "created_at": str(u.created_at),
        }
        for u in users
    ]


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
    await audit_log(
        db,
        str(admin.id),
        "admin_update_user",
        "user",
        str(user_id),
        f"管理员 {admin.name} 修改用户 {user.name}: {'; '.join(detail_changes)}",
        ip=request.client.host if request.client else None,
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
        db.scalar(select(func.count(Message.id)).where(Message.rating == 1)),
        db.scalar(select(func.count(Message.id)).where(Message.rating == -1)),
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
