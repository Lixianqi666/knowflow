from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.models.user import User

router = APIRouter(prefix="/prompt-templates", tags=["Prompt 模板"])


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    context_prompt: str = ""
    no_context_prompt: str = ""
    top_k: int = 5
    threshold: int = 30
    rerank_top_k: int = 3


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    context_prompt: str | None = None
    no_context_prompt: str | None = None
    is_active: bool | None = None
    top_k: int | None = None
    threshold: int | None = None
    rerank_top_k: int | None = None


@router.get("/")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.is_active.is_(True))
        .order_by(PromptTemplate.created_at.desc())
    )
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


@router.get("/{tmpl_id}")
async def get_template(tmpl_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await db.get(PromptTemplate, tmpl_id)
    if not t or not t.is_active:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "system_prompt": t.system_prompt,
        "context_prompt": t.context_prompt,
        "no_context_prompt": t.no_context_prompt,
        "is_active": t.is_active,
        "top_k": t.top_k,
        "threshold": t.threshold,
        "rerank_top_k": t.rerank_top_k,
    }


@router.post("/")
async def create_template(
    data: TemplateCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    t = PromptTemplate(
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        context_prompt=data.context_prompt,
        no_context_prompt=data.no_context_prompt,
        created_by=admin.id,
        top_k=data.top_k,
        threshold=data.threshold,
        rerank_top_k=data.rerank_top_k,
    )
    db.add(t)
    await db.flush()
    return {"id": str(t.id), "name": t.name}


@router.patch("/{tmpl_id}")
async def update_template(
    tmpl_id: UUID,
    data: TemplateUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(PromptTemplate, tmpl_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if data.name is not None:
        t.name = data.name
    if data.description is not None:
        t.description = data.description
    if data.system_prompt is not None:
        t.system_prompt = data.system_prompt
    if data.context_prompt is not None:
        t.context_prompt = data.context_prompt
    if data.no_context_prompt is not None:
        t.no_context_prompt = data.no_context_prompt
    if data.is_active is not None:
        t.is_active = data.is_active
    if data.top_k is not None:
        t.top_k = data.top_k
    if data.threshold is not None:
        t.threshold = data.threshold
    if data.rerank_top_k is not None:
        t.rerank_top_k = data.rerank_top_k
    await db.flush()
    return {"id": str(t.id), "name": t.name}


@router.delete("/{tmpl_id}")
async def delete_template(
    tmpl_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(PromptTemplate, tmpl_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.is_active = False  # 软删除
    await db.flush()
    return {"detail": "已停用"}
