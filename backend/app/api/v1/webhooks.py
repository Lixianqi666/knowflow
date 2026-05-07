from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.database import get_db
from app.models.user import User
from app.models.webhook import Webhook

router = APIRouter(prefix="/webhooks", tags=["Webhook"])


class WebhookCreate(BaseModel):
    name: str
    url: str
    secret: str = ""
    events: str = "document.indexed,document.deleted,feedback.created"


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: str | None = None
    is_active: bool | None = None


@router.get("/")
async def list_webhooks(
    admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    return [
        {
            "id": str(h.id),
            "name": h.name,
            "url": h.url,
            "events": h.events,
            "is_active": h.is_active,
        }
        for h in result.scalars().all()
    ]


@router.post("/")
async def create_webhook(
    data: WebhookCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    h = Webhook(
        name=data.name, url=data.url, secret=data.secret, events=data.events, created_by=admin.id
    )
    db.add(h)
    await db.flush()
    return {"id": str(h.id), "name": h.name}


@router.patch("/{hook_id}")
async def update_webhook(
    hook_id: UUID,
    data: WebhookUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    h = await db.get(Webhook, hook_id)
    if not h:
        raise HTTPException(404, "Webhook 不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(h, k, v)
    await db.flush()
    return {"detail": "已更新"}


@router.delete("/{hook_id}")
async def delete_webhook(
    hook_id: UUID, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    h = await db.get(Webhook, hook_id)
    if not h:
        raise HTTPException(404, "Webhook 不存在")
    await db.delete(h)
    return {"detail": "已删除"}
