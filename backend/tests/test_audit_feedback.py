"""P1: 审计日志 + 反馈 API 测试"""

import pytest
from httpx import AsyncClient

# ============ 审计日志 ============


@pytest.mark.asyncio
async def test_audit_logs_admin(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/audit/logs", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_logs_non_admin_forbidden(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_pagination(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/audit/logs?limit=1&offset=0", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 1


# ============ 反馈 ============


@pytest.mark.asyncio
async def test_create_feedback(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/feedback/",
        headers=auth_headers,
        json={"query": "测试问题", "feedback_type": "transfer_human", "message": "需要人工"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["detail"] == "反馈已记录"


@pytest.mark.asyncio
async def test_create_feedback_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/v1/feedback/",
        json={"query": "test", "feedback_type": "record_issue"},
    )
    assert resp.status_code in (401, 403)
