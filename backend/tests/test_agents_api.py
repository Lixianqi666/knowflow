"""Agent session 归属校验测试"""

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_message_stream_emits_trace(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={
            "name": "报销助手",
            "description": "测试",
            "system_prompt": "",
            "knowledge_base_ids": [],
        },
    )
    assert agent_resp.status_code == 200
    agent_id = agent_resp.json()["id"]

    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=auth_headers,
        json={"title": "报销测试"},
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/agents/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "帮张三报销上海出差费用"},
        timeout=30,
    ) as resp:
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert any(event["type"] == "trace" for event in events)
    assert events[-1]["type"] in ("done", "error")


# ---------- Session 归属校验测试 ----------


@pytest.mark.asyncio
async def test_user_cannot_access_others_session(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    """用户 A 不能查看用户 B 的会话"""
    # admin 创建 agent + session
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "归属测试Agent", "knowledge_base_ids": []},
    )
    agent_id = agent_resp.json()["id"]
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=admin_headers,
        json={"title": "admin的会话"},
    )
    session_id = session_resp.json()["id"]

    # auth 用户查看应 404
    resp = await client.get(f"/api/v1/agents/sessions/{session_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_update_others_session(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    """用户 A 不能修改用户 B 的会话标题"""
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "归属测试Agent2", "knowledge_base_ids": []},
    )
    agent_id = agent_resp.json()["id"]
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=admin_headers,
        json={"title": "admin的会话2"},
    )
    session_id = session_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/agents/sessions/{session_id}",
        headers=auth_headers,
        json={"title": "被篡改"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_delete_others_session(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    """用户 A 不能删除用户 B 的会话"""
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "归属测试Agent3", "knowledge_base_ids": []},
    )
    agent_id = agent_resp.json()["id"]
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=admin_headers,
        json={"title": "admin待删会话"},
    )
    session_id = session_resp.json()["id"]

    resp = await client.delete(f"/api/v1/agents/sessions/{session_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_read_others_messages(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    """用户 A 不能查看用户 B 会话的消息"""
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "归属测试Agent4", "knowledge_base_ids": []},
    )
    agent_id = agent_resp.json()["id"]
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=admin_headers,
        json={"title": "admin的消息会话"},
    )
    session_id = session_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/agents/sessions/{session_id}/messages", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_rate_others_message(
    client: AsyncClient, admin_headers: dict, auth_headers: dict
):
    """用户 A 不能给用户 B 的消息评分"""
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "归属测试Agent5", "knowledge_base_ids": []},
    )
    agent_id = agent_resp.json()["id"]
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=admin_headers,
        json={"title": "评分测试"},
    )
    session_id = session_resp.json()["id"]

    # 先发一条消息
    async with client.stream(
        "POST",
        f"/api/v1/agents/sessions/{session_id}/messages",
        headers=admin_headers,
        json={"content": "测试评分"},
        timeout=30,
    ) as resp:
        async for line in resp.aiter_lines():
            pass

    # 获取消息列表拿到 msg_id
    msgs = await client.get(
        f"/api/v1/agents/sessions/{session_id}/messages", headers=admin_headers
    )
    assert msgs.status_code == 200
    msg_list = msgs.json()
    if not msg_list:
        pytest.skip("无消息可评分")
    msg_id = msg_list[0]["id"]

    # auth 用户评分应 404
    resp = await client.patch(
        f"/api/v1/agents/messages/{msg_id}/rating",
        headers=auth_headers,
        json={"rating": 1},
    )
    assert resp.status_code == 404
