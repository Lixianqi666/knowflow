"""P1: Webhook CRUD + SSRF 防护 + 权限测试"""

import socket
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.url_validator import URLError, validate_webhook_url
from app.services.webhook import _matches_event


# ---------- 辅助函数 ----------


def _fake_getaddrinfo(*ips):
    """构造一个返回固定 IP 的 getaddrinfo 替身"""

    def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        results = []
        for ip in ips:
            fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
            results.append((fam, socket.SOCK_STREAM, 6, "", (ip, 0)))
        return results

    return _getaddrinfo


def _dns_error(*args, **kwargs):
    raise socket.gaierror("DNS failure")


# ---------- Webhook CRUD 测试 ----------


@pytest.mark.asyncio
async def test_webhook_crud_admin(client: AsyncClient, admin_headers: dict):
    with patch("app.core.url_validator.socket.getaddrinfo", side_effect=_dns_error):
        pass  # CRUD 测试不涉及 URL 校验，直接用原始逻辑
    # 创建（monkeypatch 公网 IP）
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("93.184.216.34")):
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


# ---------- SSRF 防护单元测试（纯函数，无需 DB） ----------


def test_ssrf_allowed_public_ip():
    """公网 IP 应允许"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("93.184.216.34")):
        validate_webhook_url("https://example.com/hook")


def test_ssrf_reject_loopback():
    """127.0.0.1 应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("127.0.0.1")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/hook")


def test_ssrf_reject_private_10():
    """10.x.x.x 应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("10.0.0.1")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/hook")


def test_ssrf_reject_private_192():
    """192.168.x.x 应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("192.168.1.1")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/hook")


def test_ssrf_reject_link_local():
    """169.254.x.x 应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("169.254.169.254")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/metadata")


def test_ssrf_reject_shared_address_space():
    """100.64.0.1 (CGNAT) 应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("100.64.0.1")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/hook")


def test_ssrf_reject_zero_ip():
    """0.0.0.0 DNS 解析结果应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("0.0.0.0")):
        with pytest.raises(URLError):
            validate_webhook_url("http://example.com/hook")


def test_ssrf_reject_localhost_name():
    """localhost 主机名应拒绝（不走 DNS）"""
    with pytest.raises(URLError):
        validate_webhook_url("http://localhost/hook")


def test_ssrf_reject_loopback_name():
    """0.0.0.0 主机名应拒绝"""
    with pytest.raises(URLError):
        validate_webhook_url("http://0.0.0.0/hook")


def test_ssrf_reject_ftp():
    """ftp 协议应拒绝"""
    with pytest.raises(URLError):
        validate_webhook_url("ftp://example.com/file")


def test_ssrf_reject_dns_failure():
    """DNS 解析失败应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", side_effect=socket.gaierror("fail")):
        with pytest.raises(URLError, match="域名解析失败"):
            validate_webhook_url("https://nonexistent.invalid/hook")


def test_ssrf_reject_empty_result():
    """getaddrinfo 返回空列表应拒绝"""
    with patch("app.core.url_validator.socket.getaddrinfo", return_value=[]):
        with pytest.raises(URLError, match="域名解析失败"):
            validate_webhook_url("https://example.com/hook")


def test_ssrf_mixed_ips_one_bad():
    """DNS 返回多个 IP，只要有一个不安全就拒绝"""
    with patch(
        "app.core.url_validator.socket.getaddrinfo",
        _fake_getaddrinfo("93.184.216.34", "10.0.0.1"),
    ):
        with pytest.raises(URLError):
            validate_webhook_url("https://example.com/hook")


# ---------- SSRF API 集成测试（需 DB） ----------


@pytest.mark.asyncio
async def test_webhook_ssrf_allowed_public_url(client: AsyncClient, admin_headers: dict):
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("93.184.216.34")):
        resp = await client.post(
            "/api/v1/webhooks/",
            headers=admin_headers,
            json={"name": "公网Hook", "url": "https://example.com/hook"},
        )
        assert resp.status_code == 200
        hook_id = resp.json()["id"]
        await client.delete(f"/api/v1/webhooks/{hook_id}", headers=admin_headers)


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_loopback(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "坏Hook", "url": "http://127.0.0.1/hook"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_localhost(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "坏Hook", "url": "http://localhost/hook"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_private_ip(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "坏Hook", "url": "http://10.0.0.1/hook"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_metadata(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "坏Hook", "url": "http://169.254.169.254/hook"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_ftp(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/webhooks/",
        headers=admin_headers,
        json={"name": "坏Hook", "url": "ftp://example.com/hook"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ssrf_reject_on_update(client: AsyncClient, admin_headers: dict):
    """更新 URL 时也应校验 SSRF"""
    with patch("app.core.url_validator.socket.getaddrinfo", _fake_getaddrinfo("93.184.216.34")):
        resp = await client.post(
            "/api/v1/webhooks/",
            headers=admin_headers,
            json={"name": "临时Hook", "url": "https://example.com/hook"},
        )
        hook_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/webhooks/{hook_id}",
        headers=admin_headers,
        json={"url": "http://169.254.169.254/metadata"},
    )
    assert resp.status_code == 400

    await client.delete(f"/api/v1/webhooks/{hook_id}", headers=admin_headers)


# ---------- SQL 注入修复测试（事件精确匹配） ----------


def test_matches_event_exact():
    assert _matches_event("document.indexed,document.deleted", "document.indexed") is True


def test_matches_event_no_prefix():
    assert _matches_event("document.indexed", "document.indexed_x") is False


def test_matches_event_no_suffix():
    assert _matches_event("document.indexed", "xdocument.indexed") is False


def test_matches_event_empty():
    assert _matches_event("", "document.indexed") is False


def test_matches_event_whitespace():
    assert _matches_event(" document.indexed , document.deleted ", "document.indexed") is True
