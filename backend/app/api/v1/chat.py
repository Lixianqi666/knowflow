import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import chat_rate_limit
from app.core.security import get_current_user
from app.database import async_session, get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
    MessageRatingCreate,
)
from app.services.audit import log as audit_log
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(user_id=user.id, title=data.title or "新对话")
    db.add(conv)
    await db.flush()
    return conv


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: UUID,
    data: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="对话不存在")
    conv.title = data.title
    await db.flush()
    return conv


@router.patch("/conversations/{conv_id}/pin", response_model=ConversationOut)
async def toggle_pin(
    conv_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """切换对话置顶状态"""
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="对话不存在")
    from datetime import datetime, timezone

    conv.is_pinned = not conv.is_pinned
    conv.pinned_at = datetime.now(timezone.utc) if conv.is_pinned else None
    await db.flush()
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(
            Conversation.is_pinned.desc(),
            case((Conversation.is_pinned.is_(True), Conversation.pinned_at), else_=None).desc(),
            Conversation.updated_at.desc(),
        )
    )
    return result.scalars().all()


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conv_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="对话不存在")

    result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    return result.scalars().all()


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="对话不存在")
    await db.delete(conv)
    return {"detail": "已删除"}


@router.get("/conversations/{conv_id}/export")
async def export_conversation(
    conv_id: UUID,
    format: str = "json",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="对话不存在")

    result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    messages = result.scalars().all()

    if format == "markdown":
        lines = [f"# {conv.title or '对话'}\n"]
        for msg in messages:
            role = "用户" if msg.role == "user" else "助手"
            lines.append(f"## {role}\n\n{msg.content}\n")
        content = "\n".join(lines)
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{conv_id}.md"'},
        )
    else:
        data = {
            "title": conv.title,
            "created_at": str(conv.created_at),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "sources": m.sources,
                    "created_at": str(m.created_at),
                }
                for m in messages
            ],
        }
        return StreamingResponse(
            iter([json.dumps(data, ensure_ascii=False, indent=2)]),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{conv_id}.json"'},
        )


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: UUID,
    data: MessageCreate,
    _: None = Depends(chat_rate_limit),
    user: User = Depends(get_current_user),
):
    # 手动管理DB会话，确保SSE流结束后再commit
    async with async_session() as db:
        conv = await db.get(Conversation, conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="对话不存在")

        chat_service = ChatService(db)

        await audit_log(
            db, str(user.id), "send_message", "conversation", str(conv_id), data.content[:200]
        )

        async def event_stream():
            try:
                async for event in chat_service.stream_chat(
                    str(conv_id),
                    data.content,
                    str(user.id),
                    user.role == "admin",
                    template_id=data.template_id,
                ):
                    yield f"data: {event}\n\n"
                await db.commit()
            except Exception as e:
                import logging

                logging.getLogger(__name__).exception(f"SSE流异常: {e}")
                await db.rollback()
                error_event = json.dumps(
                    {"type": "error", "data": "服务内部错误，请稍后重试"},
                    ensure_ascii=False,
                )
                yield f"data: {error_event}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )


@router.patch("/messages/{msg_id}/rating")
async def rate_message(
    msg_id: UUID,
    data: MessageRatingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(Message, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    # 查看所属对话是否属于当前用户
    conv = await db.get(Conversation, msg.conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")
    if data.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="评分必须是 1(赞) 或 -1(踩)")
    msg.rating = data.rating
    await db.flush()
    return {"detail": "已评分", "rating": data.rating}
