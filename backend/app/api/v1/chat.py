import json
import logging
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
    MessageFeedbackCreate,
    MessageFeedbackOut,
    MessageOut,
    MessageRatingCreate,
)
from app.services.audit import log as audit_log
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])


@router.get("/search")
async def global_search(
    q: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """全局搜索：按标题匹配对话和文档"""
    if not q.strip():
        return {"conversations": [], "documents": []}

    pattern = f"%{q.strip()}%"

    # 搜索对话
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.title.ilike(pattern))
        .order_by(Conversation.updated_at.desc())
        .limit(20)
    )
    conversations = [
        {"id": str(c.id), "title": c.title, "updated_at": str(c.updated_at)}
        for c in conv_result.scalars().all()
    ]

    # 搜索文档（非管理员只搜有权限的）
    from app.models.document import Document
    from app.models.permission import DocumentPermission, SourcePermission

    doc_query = select(Document).where(Document.title.ilike(pattern))
    if user.role != "admin":
        doc_query = doc_query.where(
            Document.id.in_(
                select(DocumentPermission.document_id).where(DocumentPermission.user_id == user.id)
            )
            | Document.source_id.in_(
                select(SourcePermission.source_id).where(SourcePermission.user_id == user.id)
            )
        )
    doc_result = await db.execute(doc_query.order_by(Document.created_at.desc()).limit(20))
    documents = [
        {"id": str(d.id), "title": d.title, "status": d.status, "created_at": str(d.created_at)}
        for d in doc_result.scalars().all()
    ]

    return {"conversations": conversations, "documents": documents}


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(user_id=user.id, title=data.title or "新对话", goal=data.goal)
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
    if data.title is not None:
        conv.title = data.title
    if data.goal is not None:
        conv.goal = data.goal
        if data.goal:
            conv.goal_status = "active"
            conv.goal_summary = None
            conv.missing_info = []
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
                    goal=data.goal,
                    knowledge_base_id=data.knowledge_base_id,
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


@router.post("/messages/{msg_id}/feedback", response_model=MessageFeedbackOut)
async def create_feedback(
    msg_id: UUID,
    data: MessageFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.message_feedback import MessageFeedback

    msg = await db.get(Message, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    if msg.role != "assistant":
        raise HTTPException(status_code=400, detail="只能对助手消息反馈")
    conv = await db.get(Conversation, msg.conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")
    if data.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating 必须是 up 或 down")
    if data.reason and len(data.reason) > 500:
        raise HTTPException(status_code=400, detail="reason 不能超过 500 字")

    result = await db.execute(
        select(MessageFeedback).where(
            MessageFeedback.message_id == msg_id,
            MessageFeedback.user_id == user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        old_rating = existing.rating
        existing.rating = data.rating
        existing.reason = data.reason
        await db.flush()

        if data.rating == "down":
            # 更新为 down 时创建质量问题
            from app.services.rag_quality import create_issue_from_feedback

            q_result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == msg.conversation_id,
                    Message.role == "user",
                    Message.created_at < msg.created_at,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg = q_result.scalar_one_or_none()
            try:
                await create_issue_from_feedback(
                    db,
                    message_id=str(msg_id),
                    question=user_msg.content if user_msg else None,
                    answer=msg.content,
                    citations=msg.citations or [],
                    reason=data.reason,
                    created_by=str(user.id),
                )
            except Exception:
                logger.exception(f"feedback quality issue 创建失败: msg={msg_id}")
        elif old_rating == "down" and data.rating == "up":
            # down→up 时关闭已有质量问题
            from app.models.rag_quality_issue import RagQualityIssue

            q_result = await db.execute(
                select(RagQualityIssue).where(
                    RagQualityIssue.source_type == "feedback",
                    RagQualityIssue.source_id == str(msg_id),
                    RagQualityIssue.status.in_(["open", "in_progress"]),
                )
            )
            for issue in q_result.scalars().all():
                issue.status = "ignored"
                issue.resolution_note = "用户将反馈改为正面"

        from app.services.audit import record_audit_event

        await record_audit_event(
            db,
            actor_user=user,
            action="chat.feedback",
            resource_type="message",
            resource_id=msg_id,
            metadata={"rating": data.rating, "updated": True},
        )
        return existing

    fb = MessageFeedback(
        message_id=msg_id,
        user_id=user.id,
        rating=data.rating,
        reason=data.reason,
    )
    db.add(fb)
    await db.flush()

    # down feedback 自动创建质量问题
    if data.rating == "down":
        from app.services.rag_quality import create_issue_from_feedback

        # 获取上一条 user 消息作为 question
        q_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == msg.conversation_id,
                Message.role == "user",
                Message.created_at < msg.created_at,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        user_msg = q_result.scalar_one_or_none()

        try:
            await create_issue_from_feedback(
                db,
                message_id=str(msg_id),
                question=user_msg.content if user_msg else None,
                answer=msg.content,
                citations=msg.citations or [],
                reason=data.reason,
                created_by=str(user.id),
            )
        except Exception:
            logger.exception(f"feedback quality issue 创建失败: msg={msg_id}")

    from app.services.audit import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="chat.feedback",
        resource_type="message",
        resource_id=msg_id,
        metadata={"rating": data.rating},
    )
    return fb


@router.get("/messages/{msg_id}/feedback")
async def get_feedback(
    msg_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.message_feedback import MessageFeedback

    msg = await db.get(Message, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    conv = await db.get(Conversation, msg.conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")

    result = await db.execute(
        select(MessageFeedback).where(
            MessageFeedback.message_id == msg_id,
            MessageFeedback.user_id == user.id,
        )
    )
    fb = result.scalar_one_or_none()
    if not fb:
        return None
    return {
        "id": str(fb.id),
        "message_id": str(fb.message_id),
        "user_id": str(fb.user_id),
        "rating": fb.rating,
        "reason": fb.reason,
        "created_at": str(fb.created_at),
        "updated_at": str(fb.updated_at),
    }
