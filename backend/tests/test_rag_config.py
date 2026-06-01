"""知识库 RAG 配置与重建索引测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentChunk, DataSource
from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase, DEFAULT_RAG_CONFIG
from app.models.permission import DocumentPermission
from app.models.user import User
from app.services.rag_config import normalize_rag_config, get_effective_rag_config


def _as_uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


async def _get_user_id(db_factory, email: str):
    async with db_factory() as session:
        result = await session.execute(select(User.id).where(User.email == email))
        return result.scalar()


async def _create_kb(db_factory, name: str, created_by, rag_config=None) -> str:
    async with db_factory() as session:
        kb = KnowledgeBase(name=name, created_by=created_by, rag_config=rag_config)
        session.add(kb)
        await session.commit()
        return str(kb.id)


async def _add_kb_member(db_factory, kb_id, user_id, role: str = "viewer"):
    async with db_factory() as session:
        session.add(KnowledgeBaseMember(
            knowledge_base_id=_as_uuid(kb_id), user_id=user_id, role=role,
        ))
        await session.commit()


async def _create_doc_in_kb(db_factory, title: str, content: str, kb_id, status="indexed") -> str:
    async with db_factory() as session:
        result = await session.execute(select(DataSource).where(DataSource.type == "local"))
        source = result.scalars().first()
        if not source:
            source = DataSource(name="本地文件", type="local")
            session.add(source)
            await session.flush()
        doc = Document(source_id=source.id, kb_id=_as_uuid(kb_id), title=title, content=content, status=status)
        session.add(doc)
        await session.commit()
        return str(doc.id)


# ---------- normalize_rag_config 单元测试 ----------


def test_normalize_default():
    cfg = normalize_rag_config(None)
    assert cfg == DEFAULT_RAG_CONFIG


def test_normalize_empty():
    cfg = normalize_rag_config({})
    assert cfg == DEFAULT_RAG_CONFIG


def test_normalize_valid():
    cfg = normalize_rag_config({"top_k": 10, "score_threshold": 0.5, "chunk_size": 500, "chunk_overlap": 50})
    assert cfg["top_k"] == 10
    assert cfg["score_threshold"] == 0.5
    assert cfg["chunk_size"] == 500
    assert cfg["chunk_overlap"] == 50


def test_normalize_top_k_invalid():
    with pytest.raises(ValueError, match="top_k"):
        normalize_rag_config({"top_k": 0})
    with pytest.raises(ValueError, match="top_k"):
        normalize_rag_config({"top_k": 25})


def test_normalize_score_threshold_invalid():
    with pytest.raises(ValueError, match="score_threshold"):
        normalize_rag_config({"score_threshold": -0.1})
    with pytest.raises(ValueError, match="score_threshold"):
        normalize_rag_config({"score_threshold": 1.5})


def test_normalize_chunk_size_invalid():
    with pytest.raises(ValueError, match="chunk_size"):
        normalize_rag_config({"chunk_size": 100})
    with pytest.raises(ValueError, match="chunk_size"):
        normalize_rag_config({"chunk_size": 5000})


def test_normalize_chunk_overlap_gte_size():
    with pytest.raises(ValueError, match="chunk_overlap"):
        normalize_rag_config({"chunk_size": 500, "chunk_overlap": 500})
    with pytest.raises(ValueError, match="chunk_overlap"):
        normalize_rag_config({"chunk_size": 500, "chunk_overlap": 600})


def test_normalize_no_evidence_policy_invalid():
    with pytest.raises(ValueError, match="no_evidence_policy"):
        normalize_rag_config({"no_evidence_policy": "invalid"})


def test_get_effective_rag_config_fallback():
    cfg = get_effective_rag_config(None)
    assert cfg == DEFAULT_RAG_CONFIG


def test_get_effective_rag_config_invalid_fallback():
    cfg = get_effective_rag_config({"top_k": -1})
    assert cfg == DEFAULT_RAG_CONFIG


# ---------- rag-config API 测试 ----------


@pytest.mark.asyncio
async def test_get_rag_config_default(client: AsyncClient, auth_headers: dict, db_session_factory):
    """旧知识库无 rag_config 时返回默认配置"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "default_cfg_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/rag-config", headers=auth_headers)
    assert resp.status_code == 200
    cfg = resp.json()["rag_config"]
    assert cfg["top_k"] == 5
    assert cfg["score_threshold"] == 0.0
    assert cfg["chunk_size"] == 1000


@pytest.mark.asyncio
async def test_patch_rag_config_success(client: AsyncClient, auth_headers: dict, db_session_factory):
    """PATCH rag_config 成功"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "patch_cfg_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"top_k": 10, "score_threshold": 0.3}},
    )
    assert resp.status_code == 200
    cfg = resp.json()["rag_config"]
    assert cfg["top_k"] == 10
    assert cfg["score_threshold"] == 0.3


@pytest.mark.asyncio
async def test_viewer_cannot_patch_rag_config(client: AsyncClient, auth_headers: dict, db_session_factory):
    """viewer 不能 PATCH rag_config"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "viewer_cfg_kb", admin_uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"top_k": 10}},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_get_rag_config(client: AsyncClient, auth_headers: dict, db_session_factory):
    """非成员不能 GET rag_config"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    kb_id = await _create_kb(db_factory=db_session_factory, name="non_member_cfg_kb", created_by=admin_uid)

    resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/rag-config", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_top_k_invalid(client: AsyncClient, auth_headers: dict, db_session_factory):
    """top_k 非法返回 422"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "invalid_cfg_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"top_k": 25}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_score_threshold_invalid(client: AsyncClient, auth_headers: dict, db_session_factory):
    """score_threshold 非法返回 422"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "invalid_st_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"score_threshold": 2.0}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_chunk_overlap_gte_size(client: AsyncClient, auth_headers: dict, db_session_factory):
    """chunk_overlap >= chunk_size 返回 422"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "invalid_overlap_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"chunk_size": 500, "chunk_overlap": 500}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rag_config_update_audit(client: AsyncClient, auth_headers: dict, db_session_factory):
    """rag_config_update 记录审计"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "audit_cfg_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/rag-config",
        headers=auth_headers,
        json={"rag_config": {"top_k": 8}},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "knowledge_base.rag_config_update").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None


# ---------- reindex API 测试 ----------


@pytest.mark.asyncio
async def test_owner_can_reindex(client: AsyncClient, auth_headers: dict, db_session_factory):
    """owner 可触发 reindex"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "reindex_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")
    await _create_doc_in_kb(db_session_factory, "reindex_doc.txt", "reindex content", kb_id)

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] >= 1
    assert data["knowledge_base_id"] == kb_id


@pytest.mark.asyncio
async def test_editor_can_reindex(client: AsyncClient, auth_headers: dict, db_session_factory):
    """editor 可触发 reindex"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "editor_reindex_kb", admin_uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "editor")

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_reindex(client: AsyncClient, auth_headers: dict, db_session_factory):
    """viewer 不能触发 reindex"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "viewer_reindex_kb", admin_uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reindex_resets_doc_status(client: AsyncClient, auth_headers: dict, db_session_factory):
    """reindex 会重置文档状态和 error_message"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "reset_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")
    doc_id = await _create_doc_in_kb(db_session_factory, "reset_doc.txt", "reset", kb_id, status="failed")

    # 设置 error_message
    async with db_session_factory() as session:
        doc = await session.get(Document, _as_uuid(doc_id))
        doc.error_message = "some error"
        await session.commit()

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200

    async with db_session_factory() as session:
        doc = await session.get(Document, _as_uuid(doc_id))
        assert doc.status == "pending"
        assert doc.error_message is None


@pytest.mark.asyncio
async def test_reindex_calls_indexing_task(client: AsyncClient, auth_headers: dict, db_session_factory):
    """reindex 会调用现有 indexing task"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "task_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")
    await _create_doc_in_kb(db_session_factory, "task_doc.txt", "task", kb_id)

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["queued"] >= 1


@pytest.mark.asyncio
async def test_reindex_empty_kb(client: AsyncClient, auth_headers: dict, db_session_factory):
    """空知识库返回 queued=0"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "empty_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["queued"] == 0


@pytest.mark.asyncio
async def test_reindex_audit(client: AsyncClient, auth_headers: dict, db_session_factory):
    """reindex 记录审计"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "reindex_audit_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    await client.post(f"/api/v1/knowledge-bases/{kb_id}/reindex", headers=auth_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "knowledge_base.reindex").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None


# ---------- debug-search used_config 测试 ----------


@pytest.mark.asyncio
async def test_debug_search_returns_used_config(client: AsyncClient, auth_headers: dict, db_session_factory):
    """debug-search 返回 used_config"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "debug_cfg_kb", uid, rag_config={"top_k": 8, "score_threshold": 0.1})
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_config"] is not None
    assert data["used_config"]["top_k"] == 8
    assert data["used_config"]["score_threshold"] == 0.1


@pytest.mark.asyncio
async def test_debug_search_uses_kb_default_top_k(client: AsyncClient, auth_headers: dict, db_session_factory):
    """debug-search 使用 KB 默认 top_k"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "debug_default_kb", uid, rag_config={"top_k": 12})
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    resp = await client.post(
        "/api/v1/rag/debug-search",
        headers=auth_headers,
        json={"query": "test", "knowledge_base_id": kb_id},
    )
    assert resp.status_code == 200
    assert resp.json()["top_k"] == 12
