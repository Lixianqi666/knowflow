from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get, cache_set
from app.core.security import get_current_user
from app.database import get_db
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


@router.get("/")
async def list_kbs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache_key = _kb_cache_key(user)

    cached = await cache_get(cache_key)
    if cached:
        return cached

    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    if user.role != "admin":
        query = query.where(KnowledgeBase.created_by == user.id)

    result = await db.execute(query)
    data = [
        {
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description,
            "created_at": str(kb.created_at),
        }
        for kb in result.scalars().all()
    ]
    await cache_set(cache_key, data, ttl=120)
    return data


async def _invalidate_kb_cache(user: User, owner_id=None):
    """失效操作者缓存 + admin 缓存 + owner 缓存"""
    await cache_delete(_kb_cache_key(user))
    await cache_delete("cache:kb:list:admin")
    if owner_id and owner_id != user.id:
        await cache_delete(f"cache:kb:list:{owner_id}")


@router.post("/")
async def create_kb(
    data: KBCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(name=data.name, description=data.description, created_by=user.id)
    db.add(kb)
    await db.flush()
    await _invalidate_kb_cache(user)
    return {"id": str(kb.id), "name": kb.name, "description": kb.description}


@router.patch("/{kb_id}")
async def update_kb(
    kb_id: UUID,
    data: KBUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if user.role != "admin" and kb.created_by != user.id:
        raise HTTPException(status_code=403, detail="无权修改该知识库")
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    await db.flush()
    await _invalidate_kb_cache(user, owner_id=kb.created_by)
    return {"id": str(kb.id), "name": kb.name, "description": kb.description}


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if user.role != "admin" and kb.created_by != user.id:
        raise HTTPException(status_code=403, detail="无权删除该知识库")
    await db.delete(kb)
    await _invalidate_kb_cache(user, owner_id=kb.created_by)
    return {"detail": "已删除"}
