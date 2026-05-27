"""P0: RAG 端到端测试 — 上传文档 → 写入 chunk → 对话检索 → 验证来源"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _inject_chunks(
    session_factory: async_sessionmaker,
    doc_id: str,
    content: str = "请假流程：员工需提前3天提交申请",
):
    """手动注入 document_chunks，跳过 Celery 索引任务"""
    async with session_factory() as session:
        chunk_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO document_chunks
                    (id, document_id, content, chunk_index, embedding, tsvector)
                VALUES (
                    :cid, :did, :content, 0,
                    CAST(:embedding AS vector),
                    to_tsvector('simple', :tsv)
                )
                """),
            {
                "cid": chunk_id,
                "did": doc_id,
                "content": content,
                "embedding": "[" + ",".join(["0.1"] * 1024) + "]",
                "tsv": content,
            },
        )
        await session.commit()
        return chunk_id


@pytest.mark.asyncio
async def test_rag_chat_returns_sources(
    client: AsyncClient, auth_headers: dict, db_session_factory
):
    """上传文档 → 注入 chunk → 发送消息 → 验证 sources 事件"""
    # 1. 上传文档
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("请假制度.txt", "请假流程：员工需提前3天提交申请".encode(), "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    # 2. 手动注入 chunk（跳过 Celery）
    await _inject_chunks(db_session_factory, doc_id)

    # 3. 创建对话并发送消息
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "RAG测试"},
    )
    conv_id = conv.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "请假流程是什么"},
        timeout=30,
    ) as resp:
        assert resp.status_code == 200
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                import json

                events.append(json.loads(line[6:]))

    # 4. 验证事件结构
    assert len(events) >= 2
    assert events[0]["type"] == "sources"
    assert len(events[0]["data"]) >= 1
    assert "title" in events[0]["data"][0]
    assert "score" in events[0]["data"][0]

    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) > 0
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_rag_chat_no_docs_returns_error_or_empty(client: AsyncClient, auth_headers: dict):
    """无文档时发送消息，应返回 sources 为空或 error"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "空知识库测试"},
    )
    conv_id = conv.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "测试问题"},
        timeout=30,
    ) as resp:
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                import json

                events.append(json.loads(line[6:]))

    # 无文档时第一个事件可能是 sources（空列表）或 error
    assert events[0]["type"] in ("sources", "error")
    if events[0]["type"] == "sources":
        assert isinstance(events[0]["data"], list)
