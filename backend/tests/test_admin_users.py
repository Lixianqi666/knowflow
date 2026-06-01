"""企业账号治理测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.audit_log import AuditLog
from app.models.user import User


# ---------- 密码策略测试 ----------


@pytest.mark.asyncio
async def test_weak_password_register_fails(client: AsyncClient):
    """弱密码注册失败"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@test.com", "password": "12345678", "name": "弱密码"},
    )
    assert resp.status_code == 400
    assert "字母和数字" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_password_without_digit_fails(client: AsyncClient):
    """纯字母密码注册失败"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "nodigit@test.com", "password": "abcdefgh", "name": "纯字母"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_password_without_letter_fails(client: AsyncClient):
    """纯数字密码注册失败"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "nolett@test.com", "password": "12345678", "name": "纯数字"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_valid_password_register_succeeds(client: AsyncClient):
    """合规密码注册成功"""
    import uuid
    email = f"valid_{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234", "name": "合规"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_too_long_password_fails(client: AsyncClient):
    """过长密码注册失败"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "long@test.com", "password": "A1" + "a" * 200, "name": "过长"},
    )
    assert resp.status_code in (400, 422)


# ---------- 账号禁用/启用测试 ----------


@pytest.mark.asyncio
async def test_disabled_user_cannot_login(client: AsyncClient, admin_headers: dict, db_session_factory):
    """disabled 用户无法登录"""
    import uuid
    email = f"disabled_{uuid.uuid4().hex[:8]}@test.com"
    password = "Test1234"

    # 注册
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "禁用测试"},
    )
    assert reg.status_code == 200
    user_id = reg.json()["user"]["id"]

    # 禁用
    resp = await client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": False, "disabled_reason": "测试禁用"},
    )
    assert resp.status_code == 200

    # 尝试登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 401
    assert "账号或密码" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_disabled_login_audit_reason(client: AsyncClient, admin_headers: dict, db_session_factory):
    """disabled 登录审计 reason=disabled"""
    import uuid
    email = f"audit_dis_{uuid.uuid4().hex[:8]}@test.com"
    password = "Test1234"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "审计测试"},
    )
    user_id = reg.json()["user"]["id"]

    await client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )

    await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "auth.login.failed",
            )
        )
        logs = result.scalars().all()
        disabled_log = next((l for l in logs if (l.metadata_ or {}).get("reason") == "disabled"), None)
        assert disabled_log is not None


@pytest.mark.asyncio
async def test_login_failed_no_sensitive_data(client: AsyncClient, db_session_factory):
    """登录失败审计不包含 password/token"""
    await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexist@test.com", "password": "wrong"},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.login.failed")
        )
        log = result.scalars().first()
        if log and log.metadata_:
            assert "password" not in log.metadata_
            assert "token" not in log.metadata_
            assert "secret" not in log.metadata_


@pytest.mark.asyncio
async def test_admin_can_disable_user(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    """admin 可以禁用用户"""
    # 获取 auth 用户 ID
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    users = resp.json()
    auth_user = next((u for u in users if u["email"] == "pytest@test.com"), None)
    assert auth_user is not None

    resp = await client.patch(
        f"/api/v1/admin/users/{auth_user['id']}/status",
        headers=admin_headers,
        json={"is_active": False, "disabled_reason": "测试"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 恢复
    await client.patch(
        f"/api/v1/admin/users/{auth_user['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )


@pytest.mark.asyncio
async def test_admin_can_enable_user(client: AsyncClient, admin_headers: dict):
    """admin 可以启用用户"""
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    users = resp.json()
    # 禁用再启用
    target = users[0]
    await client.patch(
        f"/api/v1/admin/users/{target['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    resp = await client.patch(
        f"/api/v1/admin/users/{target['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_admin_cannot_disable_self(client: AsyncClient, admin_headers: dict):
    """admin 不能禁用自己"""
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    users = resp.json()
    admin_user = next((u for u in users if u["role"] == "admin"), None)
    assert admin_user is not None

    resp = await client.patch(
        f"/api/v1/admin/users/{admin_user['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400
    assert "不能禁用自己" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_non_admin_cannot_call_status_api(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """普通用户不能调用 status API"""
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    users = resp.json()
    target_id = users[0]["id"]

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_users_list_no_password_hash(client: AsyncClient, admin_headers: dict):
    """admin users 列表不返回 password_hash"""
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    for user in resp.json():
        assert "hashed_password" not in user
        assert "password_hash" not in user


# ---------- failed_login_count 测试 ----------


@pytest.mark.asyncio
async def test_failed_login_increments_count(client: AsyncClient, db_session_factory):
    """登录失败递增 failed_login_count"""
    import uuid
    email = f"failcnt_{uuid.uuid4().hex[:8]}@test.com"
    password = "Test1234"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "计数测试"},
    )

    # 登录失败
    await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})

    async with db_session_factory() as session:
        result = await session.execute(select(User.failed_login_count).where(User.email == email))
        count = result.scalar()
        assert count >= 2


@pytest.mark.asyncio
async def test_successful_login_resets_count(client: AsyncClient, db_session_factory):
    """登录成功清零 failed_login_count"""
    import uuid
    email = f"resetcnt_{uuid.uuid4().hex[:8]}@test.com"
    password = "Test1234"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "重置测试"},
    )

    # 失败几次
    await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})

    # 成功登录
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    async with db_session_factory() as session:
        result = await session.execute(select(User.failed_login_count).where(User.email == email))
        count = result.scalar()
        assert count == 0


# ---------- SSO/OIDC 预留测试 ----------


@pytest.mark.asyncio
async def test_sso_providers_returns_oidc_disabled(client: AsyncClient):
    """sso providers 默认返回 oidc enabled=false"""
    resp = await client.get("/api/v1/auth/sso/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["providers"]) == 1
    assert data["providers"][0]["id"] == "oidc"
    assert data["providers"][0]["enabled"] is False
    assert data["providers"][0]["login_url"] is None


@pytest.mark.asyncio
async def test_sso_oidc_login_returns_501(client: AsyncClient):
    """OIDC 未配置 login 返回 501"""
    resp = await client.get("/api/v1/auth/sso/oidc/login")
    assert resp.status_code == 501
    assert "未配置" in resp.json()["detail"]
