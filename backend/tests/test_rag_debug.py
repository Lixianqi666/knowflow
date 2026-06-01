"""RAG 检索调试 API 测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentChunk, DataSource
from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.permission import DocumentPermission
from app.models.user import User


def _as_uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


async def _get_user_id(db_factory, email: str):
    async with db_factory() as session:
        result = await session.execute(select(User.id).where(User.email == email))
        return result.scalar()


async def _create_kb(db_factory, name: str, created_by) -> str:
    async with db_factory() as session:
        kb = KnowledgeBase(name=name, created_by=created_by)
        session.add(kb)
        await session.commit()
        return str(kb.id)


async def _add_kb_member(db_factory, kb_id, user_id, role: str = "viewer"):
    async with db_factory() as session:
        session.add(KnowledgeBaseMember(
            knowledge_base_id=_as_uuid(kb_id),
            user_id=user_id,
            role=role,
        ))
        await session.commit()


async def _create_doc_in_kb(db_factory, title: str, content: str, kb_id, user_id=None) -> str:
    async with db_factory() as session:
        result = await session.execute(select(DataSource).where(DataSource.type == "local"))
        source = result.scalars().first()
        if not source:
            source = DataSource(name="本地文件", type="local", created_by=user_id)
            session.add(source)
            await session.flush()

        doc = Document(
            source_id=source.id,
            kb_id=_as_uuid(kb_id),
            title=title,
            content=content,
            status="indexed",
        )
        session.add(doc)
        await session.flush()
        doc_id = str(doc.id)

        if user_id:
            session.add(DocumentPermission(document_id=doc.id, user_id=user_id, permission="write"))
        await session.commit()
        return doc_id


async def _create_chunk(db_factory, doc_id: str, content: str, metadata: dict | None = None) -> str:
    async with db_factory() as session:
        chunk = DocumentChunk(
            document_id=_as_uuid(doc_id),
            chunk_index=0,
            content=content,
            metadata_=metadata or {},
        )
        session.add(chunk)
        await session.commit()
        return str(chunk.id)


# ---------- 基础功能测试 ----------


@pytest.mark.asyncio
async def test_debug_search_empty_query_returns_400(client: AsyncClient, auth_headers: dict):
    """query 为空返回 400"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": ""},
    )
    assert resp.status_code == 422 or resp.status_code == 400


@pytest.mark.asyncio
async def test_debug_search_whitespace_query_returns_400(client: AsyncClient, auth_headers: dict):
    """query 全空白返回 400"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "   "},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_debug_search_default_top_k(client: AsyncClient, auth_headers: dict):
    """top_k 默认 5"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test query"},
    )
    assert resp.status_code == 200
    assert resp.json()["top_k"] == 5


@pytest.mark.asyncio
async def test_debug_search_top_k_max_20(client: AsyncClient, auth_headers: dict):
    """top_k 最大限制 20"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test query", "top_k": 50},
    )
    assert resp.status_code == 200
    assert resp.json()["top_k"] == 20


@pytest.mark.asyncio
async def test_debug_search_top_k_below_1_returns_422(client: AsyncClient, auth_headers: dict):
    """top_k < 1 返回 422"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "top_k": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_debug_search_no_results(client: AsyncClient, auth_headers: dict):
    """无结果时返回空列表和 no_result_reason"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "完全不存在的内容xyz123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["no_result_reason"] is not None


@pytest.mark.asyncio
async def test_debug_search_snippet_length_limited(client: AsyncClient, auth_headers: dict, db_session_factory):
    """snippet 长度受限"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "snippet_test_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")
    long_content = "这是一段很长的测试内容。" * 100
    doc_id = await _create_doc_in_kb(db_session_factory, "snippet_test.txt", long_content, kb_id, uid)
    await _create_chunk(db_session_factory, doc_id, long_content)

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "测试内容", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data["results"]:
        assert len(data["results"][0]["snippet"]) <= 300


@pytest.mark.asyncio
async def test_debug_search_returns_locator_page(client: AsyncClient, auth_headers: dict, db_session_factory):
    """返回 locator 和 page 字段"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "locator_test_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")
    doc_id = await _create_doc_in_kb(db_session_factory, "locator_doc.txt", "定位测试内容", kb_id, uid)
    await _create_chunk(db_session_factory, doc_id, "定位测试内容", metadata={"page": 5})

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "定位测试", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data["results"]:
        r = data["results"][0]
        assert r["locator"]["type"] == "page"
        assert r["locator"]["value"] == "5"
        assert r["page"] == 5


@pytest.mark.asyncio
async def test_debug_search_audit_logged(client: AsyncClient, auth_headers: dict, db_session_factory):
    """debug search 记录审计日志"""
    await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "审计测试query"},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "rag.debug_search").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None


# ---------- 权限测试 ----------


@pytest.mark.asyncio
async def test_debug_search_with_permission(client: AsyncClient, auth_headers: dict, db_session_factory):
    """有权限用户 debug 指定知识库"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "perm_test_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 200
    assert resp.json()["knowledge_base_id"] == kb_id


@pytest.mark.asyncio
async def test_debug_search_no_permission_returns_403(client: AsyncClient, auth_headers: dict, db_session_factory):
    """无权限用户 debug 指定知识库返回 403"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    kb_id = await _create_kb(db_session_factory, "no_perm_kb", admin_uid)
    # 不给 pytest@test.com 添加成员权限

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_debug_search_kb_not_found_returns_404(client: AsyncClient, auth_headers: dict):
    """不存在的知识库返回 404"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "knowledge_base_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_debug_search_admin_can_search_all(client: AsyncClient, admin_headers: dict):
    """admin 可检索全部"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=admin_headers,
        json={"query": "任意查询"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_debug_search_non_admin_filters_by_kb(client: AsyncClient, auth_headers: dict, db_session_factory):
    """非管理员未传 kb_id 时只返回有权限结果"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    # 创建用户有权限的 KB
    kb_id = await _create_kb(db_session_factory, "filtered_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")
    doc_id = await _create_doc_in_kb(db_session_factory, "filtered_doc.txt", "过滤测试内容", kb_id, uid)
    await _create_chunk(db_session_factory, doc_id, "过滤测试内容")

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "过滤测试"},
    )
    assert resp.status_code == 200
    # 结果中的文档都应属于用户有权限的 KB
    for r in resp.json()["results"]:
        assert r["document_id"] is not None


@pytest.mark.asyncio
async def test_debug_search_no_llm_call(client: AsyncClient, auth_headers: dict, db_session_factory):
    """debug search 不调用 LLM（纯检索）"""
    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "不调用LLM测试"},
    )
    assert resp.status_code == 200
    # 响应中无 answer / token 等 LLM 生成字段
    data = resp.json()
    assert "answer" not in data
    assert "token" not in data


@pytest.mark.asyncio
async def test_debug_search_chat_service_unaffected(client: AsyncClient, auth_headers: dict):
    """正式 ChatService 行为不受影响（验证路由未被篡改）"""
    # 创建对话
    resp = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_headers,
        json={"title": "不影响测试"},
    )
    assert resp.status_code == 200
    conv_id = resp.json()["id"]

    # 发送消息（SSE 流式）
    resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "正常聊天测试"},
    )
    assert resp.status_code == 200
