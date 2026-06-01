"""citations 与 feedback 测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.conversation import Conversation, Message
from app.models.message_feedback import MessageFeedback


# ---------- 辅助函数 ----------


async def _create_conv(client: AsyncClient, headers: dict, title: str = "测试对话") -> str:
    resp = await client.post(
        "/api/v1/chat/conversations", headers=headers, json={"title": title}
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_assistant_msg(db_factory, conv_id: str, content: str = "回答内容") -> str:
    async with db_factory() as session:
        msg = Message(
            conversation_id=UUID(conv_id),
            role="assistant",
            content=content,
            sources=[{"title": "文档A", "content": "片段", "score": 0.8}],
            citations=[
                {
                    "index": 1,
                    "document_id": "doc-001",
                    "document_title": "文档A",
                    "chunk_id": "chunk-001",
                    "snippet": "相关片段内容",
                    "score": 0.8,
                }
            ],
        )
        session.add(msg)
        await session.commit()
        msg_id = str(msg.id)
        return msg_id


async def _create_user_msg(db_factory, conv_id: str, content: str = "用户问题") -> str:
    async with db_factory() as session:
        msg = Message(
            conversation_id=UUID(conv_id),
            role="user",
            content=content,
        )
        session.add(msg)
        await session.commit()
        return str(msg.id)


# ---------- citations 测试 ----------


@pytest.mark.asyncio
async def test_assistant_message_has_citations(client: AsyncClient, auth_headers: dict, db_session_factory):
    """assistant 消息返回 citations"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers
    )
    assert resp.status_code == 200
    msgs = resp.json()
    assistant_msg = next(m for m in msgs if m["id"] == msg_id)
    assert len(assistant_msg["citations"]) == 1
    assert assistant_msg["citations"][0]["document_title"] == "文档A"
    assert assistant_msg["citations"][0]["snippet"] == "相关片段内容"


@pytest.mark.asyncio
async def test_user_message_citations_empty(client: AsyncClient, auth_headers: dict, db_session_factory):
    """user 消息 citations 为 []"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_user_msg(db_session_factory, conv_id)

    resp = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers
    )
    assert resp.status_code == 200
    msgs = resp.json()
    user_msg = next(m for m in msgs if m["id"] == msg_id)
    assert user_msg["citations"] == []


@pytest.mark.asyncio
async def test_old_message_no_citations_field(client: AsyncClient, auth_headers: dict, db_session_factory):
    """旧消息没有 citations 时返回 []"""
    conv_id = await _create_conv(client, auth_headers)
    # 手动插入没有 citations 的消息
    async with db_session_factory() as session:
        msg = Message(
            conversation_id=UUID(conv_id),
            role="assistant",
            content="旧回答",
            sources=[],
            # citations 字段默认为 []
        )
        session.add(msg)
        await session.commit()

    resp = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers
    )
    assert resp.status_code == 200
    msgs = resp.json()
    old_msg = next(m for m in msgs if m["content"] == "旧回答")
    assert old_msg["citations"] == []


# ---------- feedback 测试 ----------


@pytest.mark.asyncio
async def test_create_feedback_up(client: AsyncClient, auth_headers: dict, db_session_factory):
    """用户可以对 assistant 消息反馈 up"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up", "reason": "回答准确"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating"] == "up"
    assert data["reason"] == "回答准确"


@pytest.mark.asyncio
async def test_create_feedback_down(client: AsyncClient, auth_headers: dict, db_session_factory):
    """用户可以对 assistant 消息反馈 down"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down"},
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == "down"
    assert resp.json()["reason"] is None


@pytest.mark.asyncio
async def test_feedback_rejects_user_message(client: AsyncClient, auth_headers: dict, db_session_factory):
    """不能对 user 消息反馈"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_user_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up"},
    )
    assert resp.status_code == 400
    assert "助手消息" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_feedback_rejects_invalid_rating(client: AsyncClient, auth_headers: dict, db_session_factory):
    """非法 rating 被拒绝"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "maybe"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_feedback_upsert_updates(client: AsyncClient, auth_headers: dict, db_session_factory):
    """重复反馈会更新，不重复插入"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp1 = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up"},
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down", "reason": "改主意了"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["rating"] == "down"
    assert resp2.json()["reason"] == "改主意了"

    # 验证只有一条记录
    async with db_session_factory() as session:
        result = await session.execute(
            select(MessageFeedback).where(MessageFeedback.message_id == UUID(msg_id))
        )
        records = result.scalars().all()
        assert len(records) == 1


@pytest.mark.asyncio
async def test_feedback_permission_denied(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """其他用户不能反馈无权限消息"""
    conv_id = await _create_conv(client, admin_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_feedback(client: AsyncClient, auth_headers: dict, db_session_factory):
    """获取已有反馈"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up", "reason": "好"},
    )

    resp = await client.get(
        f"/api/v1/chat/messages/{msg_id}/feedback", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == "up"


@pytest.mark.asyncio
async def test_get_feedback_none(client: AsyncClient, auth_headers: dict, db_session_factory):
    """无反馈时返回 null"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.get(
        f"/api/v1/chat/messages/{msg_id}/feedback", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() is None


# ---------- prompt 测试 ----------


def test_rag_system_has_refusal_rule():
    """RAG_SYSTEM 包含无依据拒答规则"""
    from app.core.prompts import RAG_SYSTEM

    assert "没有找到足够依据" in RAG_SYSTEM
    assert "不要编造" in RAG_SYSTEM or "不要编造任何" in RAG_SYSTEM


def test_no_context_system_is_strict():
    """NO_CONTEXT_SYSTEM 严格限制无上下文回答"""
    from app.core.prompts import NO_CONTEXT_SYSTEM

    assert "不要编造" in NO_CONTEXT_SYSTEM
    assert "不要提供任何信息" in NO_CONTEXT_SYSTEM
