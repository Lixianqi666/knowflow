from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get, cache_set
from app.core.security import get_current_user
from app.database import get_db
from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


def _kb_cache_key(user) -> str:
    """user 可以是 User 对象或 UUID/str"""
    role = getattr(user, "role", None)
    if role == "admin":
        return "cache:kb:list:admin"
    uid = user.id if hasattr(user, "id") else user
    return f"cache:kb:list:{uid}"


class KBCreate(BaseModel):
    name: str
    description: str = ""


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class KBMemberAdd(BaseModel):
    user_id: str
    role: str = "viewer"


class KBMemberUpdate(BaseModel):
    role: str


@router.get("/")
async def list_kbs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache_key = _kb_cache_key(user)

    cached = await cache_get(cache_key)
    if cached:
        return cached

    if user.role == "admin":
        query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    else:
        # 用户可以看到自己创建的 + 自己是成员的知识库
        member_kb_ids = select(KnowledgeBaseMember.knowledge_base_id).where(
            KnowledgeBaseMember.user_id == user.id
        )
        query = (
            select(KnowledgeBase)
            .where(
                (KnowledgeBase.created_by == user.id)
                | (KnowledgeBase.id.in_(member_kb_ids))
            )
            .order_by(KnowledgeBase.created_at.desc())
        )

    result = await db.execute(query)
    kbs = result.scalars().all()

    # 获取用户角色信息
    if user.role != "admin":
        member_result = await db.execute(
            select(KnowledgeBaseMember.knowledge_base_id, KnowledgeBaseMember.role).where(
                KnowledgeBaseMember.user_id == user.id,
                KnowledgeBaseMember.knowledge_base_id.in_([kb.id for kb in kbs]),
            )
        )
        member_map = {row.knowledge_base_id: row.role for row in member_result}
    else:
        member_map = {}

    data = [
        {
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description,
            "created_at": str(kb.created_at),
            "user_role": "admin" if user.role == "admin" else member_map.get(kb.id, "owner" if kb.created_by == user.id else None),
        }
        for kb in kbs
    ]
    await cache_set(cache_key, data, ttl=120)
    return data


async def _invalidate_kb_cache(user: User, owner_id=None):
    """失效操作者缓存 + admin 缓存 + owner 缓存"""
    await cache_delete(_kb_cache_key(user))
    await cache_delete("cache:kb:list:admin")
    if owner_id and owner_id != user.id:
        await cache_delete(f"cache:kb:list:{owner_id}")


async def _clean_agent_configs_after_kb_delete(db: AsyncSession, kb_id: str):
    """KB 删除后清理 agent draft_config/published_config 中的无效 knowledge_base_ids"""
    from app.models.agent import Agent

    any_changed = False
    result = await db.execute(select(Agent))
    for agent in result.scalars().all():
        changed = False
        for config_field in ("draft_config", "published_config"):
            config = getattr(agent, config_field)
            if not config or not isinstance(config, dict):
                continue
            kb_ids = config.get("knowledge_base_ids")
            if isinstance(kb_ids, list) and kb_id in kb_ids:
                new_config = dict(config)
                new_config["knowledge_base_ids"] = [kid for kid in kb_ids if kid != kb_id]
                setattr(agent, config_field, new_config)
                changed = True
        if changed:
            any_changed = True
    if any_changed:
        await db.flush()


@router.post("/")
async def create_kb(
    request: Request,
    data: KBCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(name=data.name, description=data.description, created_by=user.id)
    db.add(kb)
    await db.flush()

    # 自动给创建者 owner 成员关系
    member = KnowledgeBaseMember(
        knowledge_base_id=kb.id,
        user_id=user.id,
        role="owner",
        created_by=user.id,
    )
    db.add(member)
    await db.flush()

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.create",
        resource_type="knowledge_base",
        resource_id=kb.id,
        request=request,
        metadata={"name": data.name},
    )

    await _invalidate_kb_cache(user)
    return {"id": str(kb.id), "name": kb.name, "description": kb.description}


@router.patch("/{kb_id}")
async def update_kb(
    kb_id: UUID,
    request: Request,
    data: KBUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_manage_kb

    if not await can_manage_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权修改该知识库")

    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    await db.flush()

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.update",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
    )

    await _invalidate_kb_cache(user, owner_id=kb.created_by)
    return {"id": str(kb.id), "name": kb.name, "description": kb.description}


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_manage_kb

    if not await can_manage_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权删除该知识库")

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.delete",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
    )

    await db.delete(kb)
    await _invalidate_kb_cache(user, owner_id=kb.created_by)
    # KB 删除后 agent config 中的 knowledge_base_ids 变为无效，需清理并失效缓存
    await _clean_agent_configs_after_kb_delete(db, str(kb_id))
    await cache_delete("cache:agents:active")
    return {"detail": "已删除"}


# ---------- 成员管理 API ----------


# ---------- RAG 配置 API ----------


@router.get("/{kb_id}/rag-config")
async def get_rag_config(
    kb_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_view_kb

    if not await can_view_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权查看该知识库")

    from app.services.rag_config import get_effective_rag_config

    return {"knowledge_base_id": str(kb.id), "rag_config": get_effective_rag_config(kb.rag_config)}


@router.patch("/{kb_id}/rag-config")
async def update_rag_config(
    kb_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_edit_kb

    if not await can_edit_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权修改该知识库配置")

    body = await request.json()
    raw_config = body.get("rag_config")
    if not isinstance(raw_config, dict):
        raise HTTPException(status_code=400, detail="rag_config 必须是对象")

    from app.services.rag_config import get_effective_rag_config, normalize_rag_config

    old_config = get_effective_rag_config(kb.rag_config)
    try:
        new_config = normalize_rag_config(raw_config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    kb.rag_config = new_config
    await db.flush()

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.rag_config_update",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
        metadata={
            "old_top_k": old_config.get("top_k"),
            "new_top_k": new_config.get("top_k"),
            "old_threshold": old_config.get("score_threshold"),
            "new_threshold": new_config.get("score_threshold"),
        },
    )

    return {"knowledge_base_id": str(kb.id), "rag_config": new_config}


# ---------- 重建索引 API ----------


@router.post("/{kb_id}/reindex")
async def reindex_kb(
    kb_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_edit_kb

    if not await can_edit_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权重建该知识库索引")

    from app.models.document import Document

    result = await db.execute(
        select(Document.id).where(
            Document.kb_id == kb_id,
            Document.status.in_(["indexed", "failed", "pending", "processing"]),
        )
    )
    doc_ids = [str(row[0]) for row in result.fetchall()]

    queued = 0
    for doc_id in doc_ids:
        doc = await db.get(Document, doc_id)
        if doc:
            doc.status = "pending"
            doc.error_message = None
            doc.retry_count = (doc.retry_count or 0) + 1
            await db.flush()
            from app.tasks.indexing import index_document_task

            index_document_task.delay(doc_id)
            queued += 1

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.reindex",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
        metadata={"queued": queued},
    )

    return {"knowledge_base_id": str(kb.id), "queued": queued, "skipped": 0}


@router.get("/{kb_id}/members")
async def list_members(
    kb_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_view_kb

    if not await can_view_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权查看该知识库成员")

    result = await db.execute(
        select(KnowledgeBaseMember, User)
        .join(User, KnowledgeBaseMember.user_id == User.id)
        .where(KnowledgeBaseMember.knowledge_base_id == kb_id)
        .order_by(KnowledgeBaseMember.created_at)
    )
    return [
        {
            "user_id": str(member.user_id),
            "email": u.email,
            "name": u.name,
            "role": member.role,
            "created_at": str(member.created_at),
        }
        for member, u in result.all()
    ]


@router.post("/{kb_id}/members")
async def add_member(
    kb_id: UUID,
    data: KBMemberAdd,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_manage_kb

    if not await can_manage_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权管理该知识库成员")

    if data.role not in ("owner", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="role 必须是 owner/editor/viewer")

    target_user = await db.get(User, data.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已存在
    existing = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户已是知识库成员")

    member = KnowledgeBaseMember(
        knowledge_base_id=kb_id,
        user_id=data.user_id,
        role=data.role,
        created_by=user.id,
    )
    db.add(member)
    await db.flush()

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.member_add",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
        metadata={"target_user_id": data.user_id, "role": data.role},
    )

    # 失效目标用户的缓存
    await cache_delete(f"cache:kb:list:{data.user_id}")
    await _invalidate_kb_cache(user, owner_id=kb.created_by)

    return {"detail": "已添加", "user_id": data.user_id, "role": data.role}


@router.patch("/{kb_id}/members/{member_user_id}")
async def update_member(
    kb_id: UUID,
    member_user_id: UUID,
    data: KBMemberUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_manage_kb

    if not await can_manage_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权管理该知识库成员")

    if data.role not in ("owner", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="role 必须是 owner/editor/viewer")

    result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    old_role = member.role

    # 不能把最后一个 owner 降级
    if old_role == "owner" and data.role != "owner":
        owner_count = await db.scalar(
            select(func.count(KnowledgeBaseMember.id)).where(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.role == "owner",
            )
        )
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="不能降级最后一个 owner")

    member.role = data.role
    await db.flush()

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.member_update",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
        metadata={"target_user_id": str(member_user_id), "old_role": old_role, "new_role": data.role},
    )

    await cache_delete(f"cache:kb:list:{member_user_id}")
    await _invalidate_kb_cache(user, owner_id=kb.created_by)

    return {"detail": "已更新", "user_id": str(member_user_id), "role": data.role}


@router.delete("/{kb_id}/members/{member_user_id}")
async def remove_member(
    kb_id: UUID,
    member_user_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    from app.services.kb_permissions import can_manage_kb

    if not await can_manage_kb(db, user, kb):
        raise HTTPException(status_code=403, detail="无权管理该知识库成员")

    result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    # 不能删除最后一个 owner
    if member.role == "owner":
        owner_count = await db.scalar(
            select(func.count(KnowledgeBaseMember.id)).where(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.role == "owner",
            )
        )
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="不能删除最后一个 owner")

    await db.delete(member)

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="knowledge_base.member_remove",
        resource_type="knowledge_base",
        resource_id=kb_id,
        request=request,
        metadata={"target_user_id": str(member_user_id), "role": member.role},
    )

    await cache_delete(f"cache:kb:list:{member_user_id}")
    await _invalidate_kb_cache(user, owner_id=kb.created_by)

    return {"detail": "已移除"}
