"""回归测试：覆盖核心路径，作为 Java 重构的行为基线"""

import json

import pytest
from httpx import AsyncClient

# ============ 认证回归 ============


@pytest.mark.asyncio
async def test_register_response_structure(client: AsyncClient):
    import uuid

    email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "pass1234", "name": "Test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    user = data["user"]
    assert "id" in user
    assert user["email"] == email
    assert user["role"] == "member"
    assert user["is_active"] is True


@pytest.mark.asyncio
async def test_login_response_structure(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login_struct@test.com", "password": "pass1234", "name": "Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "login_struct@test.com", "password": "pass1234"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_struct@test.com"


# ============ 文档上传回归 ============


@pytest.mark.asyncio
async def test_upload_txt_status(client: AsyncClient, auth_headers: dict):
    content = "回归测试文档内容"
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("回归.txt", content.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "回归.txt"
    assert data["status"] in ("pending", "indexed", "processing", "failed")
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_md(client: AsyncClient, auth_headers: dict):
    content = "# 标题\n\n这是 markdown 内容"
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.md", content.encode(), "text/markdown")},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "test.md"


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


# ============ SSE 事件流回归 ============


@pytest.mark.asyncio
async def test_sse_event_order_and_types(client: AsyncClient, auth_headers: dict):
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "SSE回归测试"},
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
        assert "text/event-stream" in resp.headers.get("content-type", "")
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    # 验证事件结构（无 indexed 文档时可能是 error）
    assert len(events) >= 1
    # 第一个事件是 sources 或 error
    assert events[0]["type"] in ("sources", "error")
    if events[0]["type"] == "sources":
        assert isinstance(events[0]["data"], list)
        # 最后一个事件是 done
        assert events[-1]["type"] == "done"
        # 中间有 token 事件
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) > 0
        for te in token_events:
            assert isinstance(te["data"], str)
    else:
        # error 事件
        assert "data" in events[0]


@pytest.mark.asyncio
async def test_sse_sources_structure(client: AsyncClient, auth_headers: dict):
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "sources结构测试"},
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
                events.append(json.loads(line[6:]))

    sources_event = events[0]
    # 无 indexed 文档时可能是 error
    if sources_event["type"] == "sources":
        for src in sources_event["data"]:
            assert "title" in src
            assert "content" in src
            assert "score" in src
            assert isinstance(src["score"], (int, float))


# ============ 管理员接口回归 ============


@pytest.mark.asyncio
async def test_admin_stats_structure(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = [
        "users",
        "documents",
        "conversations",
        "chunks",
        "knowledge_bases",
        "messages",
        "hit_rate",
        "praise",
        "criticism",
        "today_conversations",
    ]
    for key in expected_keys:
        assert key in data, f"缺少字段: {key}"


@pytest.mark.asyncio
async def test_admin_user_list_structure(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    if users:
        user = users[0]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "is_active" in user


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(client: AsyncClient, admin_headers: dict):
    # 获取当前用户 ID
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    admin_user = [u for u in resp.json() if u["email"] == "admin@test.com"][0]
    user_id = admin_user["id"]

    resp = await client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"role": "member"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 403


# ============ 错误响应格式回归 ============


@pytest.mark.asyncio
async def test_error_response_has_detail(client: AsyncClient):
    import uuid

    email = f"nonexist_{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    # 可能是 401（密码错误）或 429（限流）
    assert resp.status_code in (401, 429)
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_not_found_returns_detail(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages",
        headers=auth_headers,
    )
    assert resp.status_code in (403, 404)
    assert "detail" in resp.json()


# ============ 健康检查 ============


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
