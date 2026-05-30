"""P1: 知识库 CRUD + owner 校验 + 可见性测试"""

import uuid

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


# ---------- owner 校验测试 ----------


@pytest.mark.asyncio
async def test_user_cannot_update_others_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 不能修改用户 B（admin）的知识库"""
    # admin 创建知识库
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=admin_headers,
        json={"name": "admin的库"},
    )
    kb_id = resp.json()["id"]

    # auth 用户修改应 403
    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"name": "被篡改"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_delete_others_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 不能删除用户 B（admin）的知识库"""
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=admin_headers,
        json={"name": "admin待删库"},
    )
    kb_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_update_any_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """admin 可以修改任何知识库"""
    # auth 用户创建知识库
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "user库"},
    )
    kb_id = resp.json()["id"]

    # admin 修改
    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=admin_headers,
        json={"name": "admin已修改"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "admin已修改"


@pytest.mark.asyncio
async def test_admin_can_delete_any_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """admin 可以删除任何知识库"""
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "user待删库"},
    )
    kb_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=admin_headers)
    assert resp.status_code == 200


# ---------- 可见性测试 ----------


@pytest.mark.asyncio
async def test_user_cannot_see_admin_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """普通用户看不到 admin 创建的知识库"""
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=admin_headers,
        json={"name": "admin私有库"},
    )
    assert resp.status_code == 200
    admin_kb_id = resp.json()["id"]

    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    ids = [kb["id"] for kb in resp.json()]
    assert admin_kb_id not in ids


@pytest.mark.asyncio
async def test_user_can_see_own_kb(client: AsyncClient, auth_headers: dict):
    """普通用户能看到自己创建的知识库"""
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "我的知识库"},
    )
    assert resp.status_code == 200
    my_kb_id = resp.json()["id"]

    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    ids = [kb["id"] for kb in resp.json()]
    assert my_kb_id in ids


@pytest.mark.asyncio
async def test_admin_sees_all_kbs(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """admin 能看到所有知识库"""
    # auth 用户创建
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "user的库"},
    )
    user_kb_id = resp.json()["id"]

    # admin 创建
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=admin_headers,
        json={"name": "admin的库"},
    )
    admin_kb_id = resp.json()["id"]

    resp = await client.get("/api/v1/knowledge-bases/", headers=admin_headers)
    assert resp.status_code == 200
    ids = [kb["id"] for kb in resp.json()]
    assert user_kb_id in ids
    assert admin_kb_id in ids


@pytest.mark.asyncio
async def test_user_list_not_cached_cross_user(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """用户 A 创建知识库后，用户 B 的列表不受影响"""
    # auth 用户先查一次（缓存）
    resp1 = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    count_before = len(resp1.json())

    # admin 创建一个新库
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=admin_headers,
        json={"name": "隔离测试库"},
    )
    assert resp.status_code == 200

    # auth 用户再查，不应看到新增的
    resp2 = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    count_after = len(resp2.json())
    assert count_after == count_before


@pytest.mark.asyncio
async def test_admin_modify_kb_invalidates_owner_cache(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """admin 修改用户的知识库后，用户缓存应失效"""
    # auth 用户创建知识库
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=auth_headers,
        json={"name": "原始名"},
    )
    kb_id = resp.json()["id"]

    # auth 用户查询一次（建立缓存）
    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    assert any(kb["id"] == kb_id and kb["name"] == "原始名" for kb in resp.json())

    # admin 修改该知识库
    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=admin_headers,
        json={"name": "admin已改名"},
    )
    assert resp.status_code == 200

    # auth 用户再次查询，不应看到旧缓存
    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()
    matched = [kb for kb in kbs if kb["id"] == kb_id]
    assert len(matched) == 1
    assert matched[0]["name"] == "admin已改名"
