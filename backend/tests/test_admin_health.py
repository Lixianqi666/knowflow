"""Admin 健康状态 API 测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_overview_admin(client: AsyncClient, admin_headers: dict):
    """admin 可以访问 health overview"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "down")
    assert "database" in data
    assert "redis" in data
    assert "documents" in data
    assert "rag_evals" in data
    assert "feedback" in data


@pytest.mark.asyncio
async def test_health_overview_non_admin_forbidden(client: AsyncClient, auth_headers: dict):
    """普通用户访问 health overview 返回 403"""
    resp = await client.get("/api/v1/admin/health/overview", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_health_overview_database_ok(client: AsyncClient, admin_headers: dict):
    """database ok 时返回 database.status=ok"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"]["status"] == "ok"
    assert isinstance(data["database"]["latency_ms"], (int, float))


@pytest.mark.asyncio
async def test_health_overview_redis_ok(client: AsyncClient, admin_headers: dict):
    """redis ok 时返回 redis.status=ok"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["redis"]["status"] == "ok"
    assert isinstance(data["redis"]["latency_ms"], (int, float))


@pytest.mark.asyncio
async def test_health_overview_document_stats(client: AsyncClient, admin_headers: dict):
    """overview 返回文档 indexed / processing / failed 统计"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert "total" in docs
    assert "indexed" in docs
    assert "processing" in docs
    assert "failed" in docs
    assert isinstance(docs["total"], int)


@pytest.mark.asyncio
async def test_health_overview_recent_failed_limit(client: AsyncClient, admin_headers: dict):
    """overview recent_failed 最多返回 5 条"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    recent = resp.json()["documents"]["recent_failed"]
    assert isinstance(recent, list)
    assert len(recent) <= 5


@pytest.mark.asyncio
async def test_health_indexing_admin(client: AsyncClient, admin_headers: dict):
    """admin 可以访问 indexing health"""
    resp = await client.get("/api/v1/admin/health/indexing", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pending" in data
    assert "processing" in data
    assert "indexed" in data
    assert "failed" in data
    assert "top_retry" in data
    assert "recent_failed" in data
    assert "recent_indexed" in data


@pytest.mark.asyncio
async def test_health_indexing_top_retry_limit(client: AsyncClient, admin_headers: dict):
    """indexing API 返回 retry_count 排名前 5"""
    resp = await client.get("/api/v1/admin/health/indexing", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()["top_retry"]) <= 5


@pytest.mark.asyncio
async def test_health_chat_admin(client: AsyncClient, admin_headers: dict):
    """admin 可以访问 chat health"""
    resp = await client.get("/api/v1/admin/health/chat", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "messages_24h" in data
    assert "feedback_up_24h" in data
    assert "feedback_down_24h" in data
    assert "rag_eval_avg_score" in data
    assert "rag_eval_failed_24h" in data
    assert "rag_eval_top_failures" in data


@pytest.mark.asyncio
async def test_health_chat_feedback_stats(client: AsyncClient, admin_headers: dict):
    """chat health 返回 feedback up/down 统计"""
    resp = await client.get("/api/v1/admin/health/chat", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["feedback_up_24h"], int)
    assert isinstance(data["feedback_down_24h"], int)


@pytest.mark.asyncio
async def test_health_no_stack_trace(client: AsyncClient, admin_headers: dict):
    """health 接口不暴露完整异常堆栈"""
    resp = await client.get("/api/v1/admin/health/overview", headers=admin_headers)
    assert resp.status_code == 200
    text = resp.text
    assert "Traceback" not in text
    assert "File " not in text


@pytest.mark.asyncio
async def test_health_original_health_unaffected(client: AsyncClient):
    """原有 /health 不受影响"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
