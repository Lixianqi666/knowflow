"""P2: Prompt 模板 CRUD + 权限测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_template_crud_admin(client: AsyncClient, admin_headers: dict):
    # 创建
    resp = await client.post(
        "/api/v1/prompt-templates/",
        headers=admin_headers,
        json={
            "name": "测试模板",
            "system_prompt": "你是测试助手",
            "context_prompt": "上下文：{context}",
            "no_context_prompt": "无上下文回答",
        },
    )
    assert resp.status_code == 200
    tmpl_id = resp.json()["id"]

    # 列表
    resp = await client.get("/api/v1/prompt-templates/", headers=admin_headers)
    assert resp.status_code == 200
    assert any(t["id"] == tmpl_id for t in resp.json())

    # 获取详情
    resp = await client.get(f"/api/v1/prompt-templates/{tmpl_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "测试模板"
    assert resp.json()["system_prompt"] == "你是测试助手"

    # 更新
    resp = await client.patch(
        f"/api/v1/prompt-templates/{tmpl_id}",
        headers=admin_headers,
        json={"name": "已更新"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "已更新"

    # 软删除
    resp = await client.delete(f"/api/v1/prompt-templates/{tmpl_id}", headers=admin_headers)
    assert resp.status_code == 200

    # 删除后获取应 404
    resp = await client.get(f"/api/v1/prompt-templates/{tmpl_id}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_template_non_admin_cannot_create(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/prompt-templates/",
        headers=auth_headers,
        json={"name": "越权创建"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_template_list_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/prompt-templates/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_template_not_found(client: AsyncClient, admin_headers: dict):
    resp = await client.get(
        "/api/v1/prompt-templates/00000000-0000-0000-0000-000000000000",
        headers=admin_headers,
    )
    assert resp.status_code == 404
