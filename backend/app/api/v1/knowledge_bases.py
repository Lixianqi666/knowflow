from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


class KBCreate(BaseModel):
    name: str
    description: str = ""


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("/")
async def list_kbs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    return [
        {
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description,
            "created_at": str(kb.created_at),
        }
        for kb in result.scalars().all()
    ]


@router.post("/")
async def create_kb(
    data: KBCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(name=data.name, description=data.description, created_by=user.id)
    db.add(kb)
    await db.flush()
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
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    await db.flush()
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
    await db.delete(kb)
    return {"detail": "已删除"}
