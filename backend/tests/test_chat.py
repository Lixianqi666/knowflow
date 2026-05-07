import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "测试对话"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "测试对话"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_send_message_sse(client: AsyncClient, auth_headers: dict):
    # 创建对话
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "SSE测试"},
    )
    conv_id = conv.json()["id"]

    # 发送消息（SSE流）
    async with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "你好"},
        timeout=30,
    ) as resp:
        assert resp.status_code == 200
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                import json

                events.append(json.loads(line[6:]))

    # 验证事件顺序
    assert events[0]["type"] == "sources"
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) > 0
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_send_message_unauthorized(client: AsyncClient):
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers={"Authorization": "Bearer fake"},
        json={"title": "test"},
    )
    assert conv.status_code == 401
