import json

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
    assert data["goal"] is None
    assert data["goal_status"] == "active"
    assert data["missing_info"] == []


@pytest.mark.asyncio
async def test_create_conversation_with_goal(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "目标对话", "goal": "制定Q3营销方案"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["goal"] == "制定Q3营销方案"
    assert data["goal_status"] == "active"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_update_conversation_goal(client: AsyncClient, auth_headers: dict):
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "更新目标"},
    )
    conv_id = conv.json()["id"]

    resp = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
        json={"goal": "新目标"},
    )
    assert resp.status_code == 200
    assert resp.json()["goal"] == "新目标"
    assert resp.json()["goal_status"] == "active"


@pytest.mark.asyncio
async def test_send_message_sse(client: AsyncClient, auth_headers: dict):
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "SSE测试"},
    )
    conv_id = conv.json()["id"]

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
                events.append(json.loads(line[6:]))

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


@pytest.mark.asyncio
async def test_send_message_sets_goal_on_first_message(client: AsyncClient, auth_headers: dict):
    """发送消息携带 goal 时写入 conversation.goal"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "目标测试"},
    )
    conv_id = conv.json()["id"]
    assert conv.json()["goal"] is None

    async with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "帮我制定计划", "goal": "制定年度计划"},
        timeout=30,
    ) as resp:
        async for line in resp.aiter_lines():
            pass

    # 验证 goal 已写入
    convs = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    updated = [c for c in convs.json() if c["id"] == conv_id]
    assert len(updated) == 1
    assert updated[0]["goal"] == "制定年度计划"


@pytest.mark.asyncio
async def test_goal_carries_over_without_explicit_goal(client: AsyncClient, auth_headers: dict):
    """后续消息不传 goal 时沿用已有 goal"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "沿用目标", "goal": "已有目标"},
    )
    conv_id = conv.json()["id"]

    # 第二条消息不传 goal
    async with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "继续讨论"},
        timeout=30,
    ) as resp:
        async for line in resp.aiter_lines():
            pass

    convs = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    updated = [c for c in convs.json() if c["id"] == conv_id]
    assert updated[0]["goal"] == "已有目标"


@pytest.mark.asyncio
async def test_conversation_out_includes_goal_fields(client: AsyncClient, auth_headers: dict):
    """ConversationOut 包含 goal 字段"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "字段测试", "goal": "测试目标"},
    )
    data = conv.json()
    assert "goal" in data
    assert "goal_summary" in data
    assert "goal_status" in data
    assert "missing_info" in data


# ---------- 跨用户目标权限测试 ----------


@pytest.mark.asyncio
async def test_user_cannot_read_others_messages(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 不能读取用户 B 的 conversation messages"""
    # admin 创建对话
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=admin_headers,
        json={"title": "admin的对话", "goal": "admin目标"},
    )
    conv_id = conv.json()["id"]

    # auth 用户尝试读取
    resp = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_patch_others_goal(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 不能 PATCH 用户 B 的 conversation goal"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=admin_headers,
        json={"title": "admin的对话"},
    )
    conv_id = conv.json()["id"]

    resp = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
        json={"goal": "被篡改"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_send_message_to_others_conversation(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 不能向用户 B 的 conversation 发送消息"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=admin_headers,
        json={"title": "admin的对话"},
    )
    conv_id = conv.json()["id"]

    resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "入侵", "goal": "恶意目标"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_list_excludes_others_conversations(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A list conversations 不会看到用户 B 的会话"""
    await client.post(
        "/api/v1/chat/conversations",
        headers=admin_headers,
        json={"title": "admin私有", "goal": "admin目标"},
    )
    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()]
    assert "admin私有" not in titles


@pytest.mark.asyncio
async def test_patch_goal_status_ignored(client: AsyncClient, auth_headers: dict):
    """PATCH 传 goal_status 不应生效（Pydantic 静默忽略未知字段）"""
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "状态测试", "goal": "原目标"},
    )
    conv_id = conv.json()["id"]

    # 尝试通过 PATCH 把 goal_status 改成 done
    resp = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
        json={"goal_status": "done"},
    )
    assert resp.status_code == 200
    assert resp.json()["goal_status"] == "active"
