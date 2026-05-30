import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.config import settings


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def _make_token(overrides: dict) -> str:
    """构造自定义 claim 的 token（合法签名）"""
    claims = {"sub": "user1", "exp": 9999999999, "type": "access", "jti": "test_jti"}
    claims.update(overrides)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------- 基础测试 ----------


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    email = _unique_email("newuser")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "New"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    email = _unique_email("dup")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Dup"},
    )
    assert resp.status_code == 200
    resp2 = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Dup2"},
    )
    assert resp2.status_code == 400
    detail = resp2.json()["detail"]
    assert "邮箱已注册" not in detail
    assert email not in detail


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    email = _unique_email("login")
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Login"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    email = _unique_email("wrong")
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Wrong"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "badpassword"}
    )
    assert resp.status_code == 401


# ---------- Token 生命周期测试 ----------


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(client: AsyncClient):
    email = _unique_email("refresh")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Refresh"},
    )
    old_access = reg.json()["access_token"]
    cookies = reg.cookies
    resp = await client.post("/api/v1/auth/refresh", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json()["access_token"] != old_access


@pytest.mark.asyncio
async def test_refresh_rotation_old_refresh_invalid(client: AsyncClient):
    email = _unique_email("rot")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "Rot"},
    )
    old_cookies = reg.cookies
    resp1 = await client.post("/api/v1/auth/refresh", cookies=old_cookies)
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/auth/refresh", cookies=old_cookies)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh(client: AsyncClient):
    email = _unique_email("logout_ref")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "LogoutRef"},
    )
    access = reg.json()["access_token"]
    cookies = reg.cookies
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        cookies=cookies,
    )
    assert resp.status_code == 200
    resp2 = await client.post("/api/v1/auth/refresh", cookies=cookies)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_access(client: AsyncClient):
    email = _unique_email("logout_acc")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "LogoutAcc"},
    )
    access = reg.json()["access_token"]
    cookies = reg.cookies
    resp = await client.get(
        "/api/v1/knowledge-bases/",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
    await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        cookies=cookies,
    )
    resp2 = await client.get(
        "/api/v1/knowledge-bases/",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access(client: AsyncClient):
    email = _unique_email("ref_as_acc")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "RefAsAcc"},
    )
    refresh_token = reg.cookies.get("refresh_token")
    resp = await client.get(
        "/api/v1/knowledge-bases/",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_token_cannot_be_used_as_refresh(client: AsyncClient):
    email = _unique_email("acc_as_ref")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "AccAsRef"},
    )
    access = reg.json()["access_token"]
    resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": access},
    )
    assert resp.status_code == 401


# ---------- Claim 校验测试 ----------


@pytest.mark.asyncio
async def test_access_token_missing_sub_returns_401(client: AsyncClient):
    """合法签名但缺 sub 的 access token 返回 401"""
    token = _make_token({"sub": ""})
    resp = await client.get(
        "/api/v1/knowledge-bases/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_token_missing_jti_returns_401(client: AsyncClient):
    """合法签名但缺 jti 的 access token 返回 401"""
    token = _make_token({"jti": ""})
    resp = await client.get(
        "/api/v1/knowledge-bases/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_missing_jti_returns_401(client: AsyncClient):
    """合法签名但缺 jti 的 refresh token 调 /auth/refresh 返回 401"""
    token = _make_token({"type": "refresh", "jti": ""})
    resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": token},
    )
    assert resp.status_code == 401


# ---------- Redis 黑名单写入失败测试 ----------


@pytest.mark.asyncio
async def test_refresh_blacklist_write_failure_returns_503(client: AsyncClient):
    """refresh 过程中 blacklist 写入失败返回 503，不签发新 token"""
    email = _unique_email("ref_bl_fail")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "RefBLFail"},
    )
    cookies = reg.cookies

    with patch("app.api.v1.auth.blacklist_token") as mock_bl:
        from fastapi import HTTPException, status

        async def fail_blacklist(*args, **kwargs):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")

        mock_bl.side_effect = fail_blacklist
        resp = await client.post("/api/v1/auth/refresh", cookies=cookies)

    assert resp.status_code == 503
    assert "access_token" not in resp.json()
    assert "refresh_token" not in resp.cookies


@pytest.mark.asyncio
async def test_logout_access_blacklist_write_failure_returns_503(client: AsyncClient):
    """logout 过程中 access token 黑名单写入失败返回 503"""
    email = _unique_email("logout_acc_bl")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "LogoutAccBL"},
    )
    access = reg.json()["access_token"]
    cookies = reg.cookies

    call_count = 0

    with patch("app.api.v1.auth.blacklist_token") as mock_bl:
        from fastapi import HTTPException, status

        async def selective_fail(jti, prefix, ttl, user_id=""):
            nonlocal call_count
            call_count += 1
            if "access" in prefix:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")

        mock_bl.side_effect = selective_fail
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
            cookies=cookies,
        )

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_logout_refresh_blacklist_write_failure_returns_503(client: AsyncClient):
    """logout 过程中 refresh token 黑名单写入失败返回 503"""
    email = _unique_email("logout_ref_bl")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "name": "LogoutRefBL"},
    )
    access = reg.json()["access_token"]
    cookies = reg.cookies

    with patch("app.api.v1.auth.blacklist_token") as mock_bl:
        from fastapi import HTTPException, status

        async def selective_fail(jti, prefix, ttl, user_id=""):
            if "refresh" in prefix:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")

        mock_bl.side_effect = selective_fail
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
            cookies=cookies,
        )

    assert resp.status_code == 503
