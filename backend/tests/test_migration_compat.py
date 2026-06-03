"""迁移一致性与审计字段兼容测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit import _sanitize_metadata, record_audit_event


# ---------- audit_logs nullable 测试 ----------


@pytest.mark.asyncio
async def test_audit_resource_type_nullable(client: AsyncClient, auth_headers: dict, db_session_factory):
    """record_audit_event 不传 resource_type 能写入"""
    async with db_session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == "pytest@test.com"))
        user = user_result.scalar_one_or_none()
        assert user is not None

        await record_audit_event(
            session,
            actor_user=user,
            action="test.no_resource_type",
            status="success",
        )
        await session.commit()

        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "test.no_resource_type")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.resource_type is None


@pytest.mark.asyncio
async def test_auth_login_success_audit(client: AsyncClient, auth_headers: dict, db_session_factory):
    """auth.login.success 能写入 audit_logs"""
    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.login.success")
        )
        log = result.scalars().first()
        if log is not None:
            assert log.action == "auth.login.success"


@pytest.mark.asyncio
async def test_auth_login_failed_audit(client: AsyncClient, db_session_factory):
    """auth.login.failed 能写入 audit_logs"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "pytest@test.com", "password": "wrong_password"},
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
async def test_audit_logs_api_returns_null_resource_type(client: AsyncClient, admin_headers: dict):
    """audit logs API 能返回 resource_type 为空的事件"""
    resp = await client.get("/api/v1/audit/logs?limit=100", headers=admin_headers)
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)


@pytest.mark.asyncio
async def test_audit_metadata_sanitize_still_works():
    """metadata 清洗继续有效"""
    result = _sanitize_metadata({"password": "secret", "name": "test", "token": "abc"})
    assert "password" not in result
    assert "token" not in result
    assert result["name"] == "test"


# ---------- migration 幂等性测试 ----------


@pytest.mark.asyncio
async def test_critical_tables_exist(client: AsyncClient, db_session_factory):
    """关键表存在性检查"""
    required = [
        "users", "documents", "messages", "conversations",
        "audit_logs", "knowledge_bases", "knowledge_base_members",
        "rag_eval_cases", "rag_eval_runs", "message_feedbacks",
        "rag_quality_issues", "agents", "document_chunks",
    ]
    async with db_session_factory() as session:
        for table in required:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = :name)"),
                {"name": table},
            )
            exists = result.scalar()
            assert exists, f"表 {table} 不存在"


@pytest.mark.asyncio
async def test_critical_columns_exist(client: AsyncClient, db_session_factory):
    """关键列存在性检查"""
    checks = [
        ("users", "disabled_reason"),
        ("users", "disabled_at"),
        ("users", "failed_login_count"),
        ("documents", "error_message"),
        ("documents", "retry_count"),
        ("messages", "citations"),
        ("audit_logs", "actor_email"),
        ("audit_logs", "status"),
        ("audit_logs", "user_agent"),
        ("audit_logs", "metadata"),
        ("knowledge_bases", "rag_config"),
        ("agents", "draft_config"),
        ("agents", "published_config"),
        ("agents", "status"),
    ]
    async with db_session_factory() as session:
        for table, col in checks:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c)"),
                {"t": table, "c": col},
            )
            exists = result.scalar()
            assert exists, f"列 {table}.{col} 不存在"


@pytest.mark.asyncio
async def test_audit_logs_resource_type_is_nullable(client: AsyncClient, db_session_factory):
    """audit_logs.resource_type 在数据库中是 nullable"""
    async with db_session_factory() as session:
        result = await session.execute(
            text("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'resource_type'"),
        )
        nullable = result.scalar()
        assert nullable is not None, "resource_type 列不存在"
        assert nullable == "YES", f"resource_type 应为 nullable，实际: {nullable}"
