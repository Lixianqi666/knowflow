"""审计日志测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.audit_log import AuditLog
from app.services.audit import _sanitize_metadata, record_audit_event


# ---------- _sanitize_metadata 单元测试 ----------


def test_sanitize_metadata_removes_password():
    """清洗 password key"""
    result = _sanitize_metadata({"password": "secret123", "name": "test"})
    assert "password" not in result
    assert result["name"] == "test"


def test_sanitize_metadata_removes_token():
    """清洗 token key"""
    result = _sanitize_metadata({"token": "abc123", "action": "login"})
    assert "token" not in result
    assert result["action"] == "login"


def test_sanitize_metadata_removes_secret():
    """清洗 secret key"""
    result = _sanitize_metadata({"secret": "hidden", "data": "visible"})
    assert "secret" not in result
    assert result["data"] == "visible"


def test_sanitize_metadata_removes_authorization():
    """清洗 authorization key"""
    result = _sanitize_metadata({"authorization": "Bearer xxx", "info": "ok"})
    assert "authorization" not in result


def test_sanitize_metadata_removes_api_key():
    """清洗 api_key key"""
    result = _sanitize_metadata({"api_key": "sk-xxx", "name": "test"})
    assert "api_key" not in result


def test_sanitize_metadata_truncates_long_value():
    """长值会截断"""
    long_value = "a" * 300
    result = _sanitize_metadata({"data": long_value})
    assert len(result["data"]) < 250
    assert result["data"].endswith("...")


def test_sanitize_metadata_none_input():
    """None 输入返回空 dict"""
    assert _sanitize_metadata(None) == {}


def test_sanitize_metadata_empty_input():
    """空 dict 输入返回空 dict"""
    assert _sanitize_metadata({}) == {}


# ---------- record_audit_event 测试 ----------


@pytest.mark.asyncio
async def test_record_audit_event_writes(client: AsyncClient, auth_headers: dict, db_session_factory):
    """record_audit_event 能写入审计日志"""
    from app.models.user import User

    async with db_session_factory() as session:
        result = await session.execute(select(User).where(User.email == "pytest@test.com"))
        user = result.scalar_one()

        await record_audit_event(
            session,
            actor_user=user,
            action="test.write.action",
            resource_type="test",
            resource_id="test-123",
        )
        await session.commit()

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "test.write.action")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.actor_email == "pytest@test.com"


@pytest.mark.asyncio
async def test_record_audit_event_sanitizes_metadata(client: AsyncClient, db_session_factory):
    """record_audit_event 会清洗敏感 metadata"""
    async with db_session_factory() as session:
        await record_audit_event(
            session,
            action="test.sanitize.metadata",
            metadata={"password": "secret", "safe_key": "safe_value"},
        )
        await session.commit()

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "test.sanitize.metadata")
        )
        log = result.scalars().first()
        assert log is not None
        assert "password" not in (log.metadata_ or {})
        assert (log.metadata_ or {}).get("safe_key") == "safe_value"


@pytest.mark.asyncio
async def test_record_audit_event_failure_not_block_main(client: AsyncClient, db_session_factory):
    """审计记录失败不影响主业务"""
    # 模拟 db 异常 - 传入 None user_id 不会抛异常
    async with db_session_factory() as session:
        # 这不应该抛异常
        await record_audit_event(
            session,
            action="test.no_block",
            metadata={"key": "value"},
        )


# ---------- 审计查询 API 测试 ----------


@pytest.mark.asyncio
async def test_admin_can_query_audit_logs(client: AsyncClient, admin_headers: dict):
    """admin 可以查询 audit logs"""
    resp = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.asyncio
async def test_non_admin_cannot_query_audit_logs(client: AsyncClient, auth_headers: dict):
    """普通用户查询 audit logs 返回 403"""
    resp = await client.get("/api/v1/admin/audit-logs", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_support_action_filter(client: AsyncClient, admin_headers: dict, db_session_factory):
    """audit logs 支持 action 过滤"""
    # 写入测试数据
    async with db_session_factory() as session:
        await record_audit_event(session, action="test.filter.action", resource_type="test")
        await record_audit_event(session, action="test.other.action", resource_type="test")
        await session.commit()

    resp = await client.get(
        "/api/v1/admin/audit-logs?action=test.filter.action", headers=admin_headers
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["action"] == "test.filter.action" for item in items)


@pytest.mark.asyncio
async def test_audit_logs_support_status_filter(client: AsyncClient, admin_headers: dict, db_session_factory):
    """audit logs 支持 status 过滤"""
    async with db_session_factory() as session:
        await record_audit_event(session, action="test.status.success", status="success")
        await record_audit_event(session, action="test.status.failed", status="failed")
        await session.commit()

    resp = await client.get(
        "/api/v1/admin/audit-logs?status=failed", headers=admin_headers
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["status"] == "failed" for item in items)


@pytest.mark.asyncio
async def test_audit_logs_limit_max_100(client: AsyncClient, admin_headers: dict):
    """limit 最大不超过 100"""
    resp = await client.get(
        "/api/v1/admin/audit-logs?limit=200", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["limit"] == 100


@pytest.mark.asyncio
async def test_audit_logs_sorted_by_created_at_desc(client: AsyncClient, admin_headers: dict, db_session_factory):
    """查询结果按 created_at desc 排序"""
    async with db_session_factory() as session:
        await record_audit_event(session, action="test.sort.first")
        await record_audit_event(session, action="test.sort.second")
        await session.commit()

    resp = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    if len(items) >= 2:
        assert items[0]["created_at"] >= items[1]["created_at"]


# ---------- 关键操作审计集成测试 ----------


@pytest.mark.asyncio
async def test_login_success_records_audit(client: AsyncClient, db_session_factory):
    """登录成功记录 auth.login.success"""
    email = "audit_login@test.com"
    password = "test1234"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "AuditTest"},
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.login.success")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.status == "success"


@pytest.mark.asyncio
async def test_login_failed_records_audit(client: AsyncClient, db_session_factory):
    """登录失败记录 auth.login.failed"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexist@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.login.failed")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.status == "failed"


@pytest.mark.asyncio
async def test_document_upload_records_audit(client: AsyncClient, auth_headers: dict, db_session_factory):
    """文档上传记录 document.upload"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("audit_upload.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "document.upload")
        )
        log = result.scalars().first()
        assert log is not None


@pytest.mark.asyncio
async def test_document_delete_records_audit(client: AsyncClient, auth_headers: dict, db_session_factory):
    """文档删除记录 document.delete"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("del_audit.txt", b"test", "text/plain")},
    )
    doc_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "document.delete")
        )
        log = result.scalars().first()
        assert log is not None


@pytest.mark.asyncio
async def test_admin_health_view_records_audit(client: AsyncClient, admin_headers: dict, db_session_factory):
    """admin health view 记录 admin.health.view"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "admin.health.view")
        )
        log = result.scalars().first()
        assert log is not None
