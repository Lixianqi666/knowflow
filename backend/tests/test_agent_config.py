"""Agent 配置/调试/发布/回滚测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.agent import Agent


# ---------- 辅助函数 ----------


async def _create_agent(client: AsyncClient, headers: dict, name: str = "测试Agent") -> str:
    resp = await client.post(
        "/api/v1/agents/",
        headers=headers,
        json={
            "name": name,
            "description": "测试",
            "system_prompt": "你是测试助手",
            "knowledge_base_ids": [],
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ---------- Config API 测试 ----------


@pytest.mark.asyncio
async def test_get_config_returns_draft_and_published(client: AsyncClient, admin_headers: dict):
    """GET config 返回 draft_config / published_config / status / published_version"""
    agent_id = await _create_agent(client, admin_headers)
    resp = await client.get(f"/api/v1/agents/{agent_id}/config", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "draft_config" in data
    assert "published_config" in data
    assert "status" in data
    assert data["status"] == "draft"
    assert "published_version" in data
    assert data["published_version"] == 0
    assert "has_unpublished_changes" in data


@pytest.mark.asyncio
async def test_patch_config_only_updates_draft(client: AsyncClient, admin_headers: dict):
    """PATCH config 只更新 draft_config，不更新 published_config"""
    agent_id = await _create_agent(client, admin_headers)

    # 先设置 draft 内容
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "原始版本", "temperature": 0.3},
    )

    # 发布
    await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)

    # 修改 draft
    resp = await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "新的提示词", "temperature": 0.5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft_config"]["system_prompt"] == "新的提示词"
    assert data["draft_config"]["temperature"] == 0.5
    # published_config 不变
    assert data["published_config"].get("system_prompt") == "原始版本"
    assert data["has_unpublished_changes"] is True


@pytest.mark.asyncio
async def test_patch_config_validates_temperature(client: AsyncClient, admin_headers: dict):
    """PATCH config 校验 temperature 范围"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"temperature": 3.0},
    )
    assert resp.status_code == 400
    assert "temperature" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_config_validates_max_tokens(client: AsyncClient, admin_headers: dict):
    """PATCH config 校验 max_tokens 范围"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"max_tokens": 10000},
    )
    assert resp.status_code == 400
    assert "max_tokens" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_config_validates_system_prompt_length(client: AsyncClient, admin_headers: dict):
    """PATCH config 校验 system_prompt 长度"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "a" * 5000},
    )
    assert resp.status_code == 400
    assert "system_prompt" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_config_permission_denied(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """普通用户不能修改别人的 Agent config"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=auth_headers,
        json={"system_prompt": "尝试修改"},
    )
    assert resp.status_code == 403


# ---------- Debug API 测试 ----------


@pytest.mark.asyncio
async def test_debug_uses_draft_config(client: AsyncClient, admin_headers: dict):
    """owner 可以 debug Agent"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.post(
        f"/api/v1/agents/{agent_id}/debug",
        headers=admin_headers,
        json={"content": "你好"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert "used_config" in data


@pytest.mark.asyncio
async def test_debug_permission_denied(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """普通用户不能 debug 别人的 Agent"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.post(
        f"/api/v1/agents/{agent_id}/debug",
        headers=auth_headers,
        json={"content": "你好"},
    )
    assert resp.status_code == 403


# ---------- Publish API 测试 ----------


@pytest.mark.asyncio
async def test_publish_copies_draft_to_published(client: AsyncClient, admin_headers: dict):
    """publish 会复制 draft_config 到 published_config"""
    agent_id = await _create_agent(client, admin_headers)

    # 先设置 draft
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "发布测试", "temperature": 0.3},
    )

    # 发布
    resp = await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "published"
    assert data["published_version"] == 1
    assert data["published_config"].get("system_prompt") == "发布测试"
    assert data["last_published_at"] is not None


@pytest.mark.asyncio
async def test_publish_increments_version(client: AsyncClient, admin_headers: dict):
    """publish 会 published_version + 1"""
    agent_id = await _create_agent(client, admin_headers)

    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "v1"},
    )
    resp1 = await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)
    assert resp1.json()["published_version"] == 1

    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "v2"},
    )
    resp2 = await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)
    assert resp2.json()["published_version"] == 2


@pytest.mark.asyncio
async def test_publish_empty_draft_rejected(client: AsyncClient, admin_headers: dict):
    """空 draft_config 无法发布"""
    agent_id = await _create_agent(client, admin_headers)

    # 不设置 draft 直接发布
    resp = await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)
    assert resp.status_code == 400


# ---------- Rollback API 测试 ----------


@pytest.mark.asyncio
async def test_rollback_resets_draft_to_published(client: AsyncClient, admin_headers: dict):
    """rollback 会把 draft_config 重置为 published_config"""
    agent_id = await _create_agent(client, admin_headers)

    # 发布
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "原始版本"},
    )
    await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)

    # 修改 draft
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "修改后"},
    )

    # 回滚
    resp = await client.post(f"/api/v1/agents/{agent_id}/rollback", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft_config"].get("system_prompt") == "原始版本"
    assert data["has_unpublished_changes"] is False


@pytest.mark.asyncio
async def test_rollback_without_published_rejected(client: AsyncClient, admin_headers: dict):
    """没有已发布版本无法回滚"""
    agent_id = await _create_agent(client, admin_headers)

    resp = await client.post(f"/api/v1/agents/{agent_id}/rollback", headers=admin_headers)
    assert resp.status_code == 400


# ---------- Agent 对话使用 published_config ----------


@pytest.mark.asyncio
async def test_unpublished_agent_rejects_normal_user(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """未发布 Agent 正式调用时被拒绝"""
    agent_id = await _create_agent(client, admin_headers)

    # 创建 session
    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=auth_headers,
        json={"title": "测试"},
    )
    session_id = session_resp.json()["id"]

    # 尝试发送消息
    resp = await client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "你好"},
    )
    assert resp.status_code == 400
    assert "未发布" in resp.json()["detail"]


# ---------- 审计测试 ----------


@pytest.mark.asyncio
async def test_publish_records_audit(client: AsyncClient, admin_headers: dict, db_session_factory):
    """agent.publish 会记录 audit"""
    from app.models.audit_log import AuditLog

    agent_id = await _create_agent(client, admin_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "审计测试"},
    )
    await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "agent.publish")
        )
        log = result.scalars().first()
        assert log is not None


@pytest.mark.asyncio
async def test_rollback_records_audit(client: AsyncClient, admin_headers: dict, db_session_factory):
    """agent.rollback 会记录 audit"""
    from app.models.audit_log import AuditLog

    agent_id = await _create_agent(client, admin_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "回滚测试"},
    )
    await client.post(f"/api/v1/agents/{agent_id}/publish", headers=admin_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}/config",
        headers=admin_headers,
        json={"system_prompt": "修改"},
    )
    await client.post(f"/api/v1/agents/{agent_id}/rollback", headers=admin_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "agent.rollback")
        )
        log = result.scalars().first()
        assert log is not None
