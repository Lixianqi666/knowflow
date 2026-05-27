"""P1: Webhook CRUD + 权限测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_crud_admin(client: AsyncClient, admin_headers: dict):
    # 创建
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "测试Hook", "url": "https://example.com/hook", "events": "document.indexed"},
    )
    assert resp.status_code == 200
    hook_id = resp.json()["id"]

    # 列表
    resp = await client.get("/api/v1/webhooks/", headers=admin_headers)
    assert resp.status_code == 200
    assert any(h["id"] == hook_id for h in resp.json())

    # 更新
    resp = await client.patch(
        f"/api/v1/webhooks/{hook_id}",
        headers=admin_headers,
        json={"name": "已更新"},
    )
    assert resp.status_code == 200

    # 删除
    resp = await client.delete(f"/api/v1/webhooks/{hook_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_non_admin_forbidden(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/webhooks/", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_not_found(client: AsyncClient, admin_headers: dict):
    resp = await client.patch(
        "/api/v1/webhooks/00000000-0000-0000-0000-000000000000",
        headers=admin_headers,
        json={"name": "x"},
    )
    assert resp.status_code == 404

    resp = await client.delete(
        "/api/v1/webhooks/00000000-0000-0000-0000-000000000000",
        headers=admin_headers,
    )
    assert resp.status_code == 404
