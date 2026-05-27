"""P1: 知识库 CRUD API 测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_kb_create_and_list(client: AsyncClient, auth_headers: dict):
    # 创建
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "测试知识库", "description": "自动化测试"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "测试知识库"
    kb_id = data["id"]

    # 列表
    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()
    assert any(kb["id"] == kb_id for kb in kbs)


@pytest.mark.asyncio
async def test_kb_update(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "待更新"},
    )
    kb_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"name": "已更新", "description": "新描述"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "已更新"


@pytest.mark.asyncio
async def test_kb_delete(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "待删除"},
    )
    kb_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 200

    # 删除后更新应 404
    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"name": "不存在"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kb_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        "/api/v1/knowledge-bases/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
        json={"name": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kb_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/knowledge-bases/")
    assert resp.status_code in (401, 403)
