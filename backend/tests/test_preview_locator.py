"""文档预览与 chunk 定位 API 测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.document import Document, DocumentChunk
from app.models.document import DataSource
from app.models.permission import DocumentPermission
from app.models.user import User
from app.models.audit_log import AuditLog


# ---------- 辅助函数 ----------

def _as_uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


async def _create_doc(db_factory, title: str, content: str = "test content", user_id=None, isolated_source: bool = False) -> str:
    """直接在数据库创建文档

    isolated_source=True 时创建独立 source，避免被其他测试的 SourcePermission 影响。
    """
    async with db_factory() as session:
        if isolated_source:
            source = DataSource(name=f"isolated_{title}", type="isolated", created_by=user_id)
            session.add(source)
            await session.flush()
        else:
            result = await session.execute(select(DataSource).where(DataSource.type == "local"))
            source = result.scalars().first()
            if not source:
                source = DataSource(name="本地文件", type="local", created_by=user_id)
                session.add(source)
                await session.flush()

        doc = Document(
            source_id=source.id,
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
        else:
            await session.commit()
        return doc_id


async def _create_chunk(db_factory, doc_id: str, content: str = "chunk content", metadata: dict | None = None) -> str:
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


async def _get_user_id(db_factory, email: str):
    async with db_factory() as session:
        result = await session.execute(select(User.id).where(User.email == email))
        return result.scalar()


# ---------- preview API 测试 ----------


@pytest.mark.asyncio
async def test_preview_txt_returns_text_content(client: AsyncClient, auth_headers: dict, db_session_factory):
    """txt 文档 preview 返回 text 模式和 content"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="readme.txt", content="This is a test document with some content.", user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "txt"
    assert data["preview_mode"] == "text"
    assert "content" in data
    assert "This is a test" in data["content"]
    assert data["download_url"] == f"/api/v1/documents/{doc_id}/file"


@pytest.mark.asyncio
async def test_preview_md_returns_text_content(client: AsyncClient, auth_headers: dict, db_session_factory):
    """md 文档 preview 返回 text 模式"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="doc.md", content="# Title\n\nSome markdown content.", user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "md"
    assert data["preview_mode"] == "text"
    assert "content" in data


@pytest.mark.asyncio
async def test_preview_pdf_returns_download_only(client: AsyncClient, auth_headers: dict, db_session_factory):
    """pdf 文档 preview 返回 download_only"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="test.pdf", user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "pdf"
    assert data["preview_mode"] == "download_only"
    assert "content" not in data


@pytest.mark.asyncio
async def test_preview_docx_returns_download_only(client: AsyncClient, auth_headers: dict, db_session_factory):
    """docx 文档 preview 返回 download_only"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="test.docx", user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "docx"
    assert data["preview_mode"] == "download_only"


@pytest.mark.asyncio
async def test_preview_xlsx_returns_download_only(client: AsyncClient, auth_headers: dict, db_session_factory):
    """xlsx 文档 preview 返回 download_only"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="test.xlsx", user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "xlsx"
    assert data["preview_mode"] == "download_only"


@pytest.mark.asyncio
async def test_preview_no_permission_returns_403(client: AsyncClient, auth_headers: dict, db_session_factory):
    """无权限用户 preview 返回 403"""
    doc_id = await _create_doc(db_session_factory, title="secret.txt", content="secret content", isolated_source=True)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_preview_not_found_returns_404(client: AsyncClient, auth_headers: dict):
    """不存在的文档 preview 返回 404"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/documents/{fake_id}/preview", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_content_length_limited(client: AsyncClient, auth_headers: dict, db_session_factory):
    """preview content 长度受限"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    long_content = "x" * 30000
    doc_id = await _create_doc(db_session_factory, title="long.txt", content=long_content, user_id=uid)
    resp = await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data.get("content", "")) <= 20000


@pytest.mark.asyncio
async def test_preview_audit_logged(client: AsyncClient, auth_headers: dict, db_session_factory):
    """preview 操作记录审计日志"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="audit_preview.txt", content="audit test", user_id=uid)
    await client.get(f"/api/v1/documents/{doc_id}/preview", headers=auth_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "document.preview").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None
    assert str(log.resource_id) == doc_id


# ---------- locator API 测试 ----------


@pytest.mark.asyncio
async def test_locator_returns_page_locator(client: AsyncClient, auth_headers: dict, db_session_factory):
    """chunk 有 page metadata 时返回 page locator"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="paged.txt", content="page content", user_id=uid)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="page 3 content", metadata={"page": 3})

    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}/locator", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 3
    assert data["locator"]["type"] == "page"
    assert data["locator"]["value"] == "3"
    assert data["snippet"] == "page 3 content"


@pytest.mark.asyncio
async def test_locator_fallback_to_chunk_locator(client: AsyncClient, auth_headers: dict, db_session_factory):
    """chunk 无 page metadata 时 fallback 到 chunk locator"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="nopage.txt", content="no page content", user_id=uid)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="some chunk content")

    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}/locator", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["locator"]["type"] == "chunk"
    assert data["locator"]["value"] == chunk_id
    assert "page" not in data


@pytest.mark.asyncio
async def test_locator_returns_section_locator(client: AsyncClient, auth_headers: dict, db_session_factory):
    """chunk 有 section metadata 时返回 text locator"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="section.txt", content="section content", user_id=uid)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="intro content", metadata={"section": "Introduction"})

    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}/locator", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["locator"]["type"] == "text"
    assert data["locator"]["value"] == "Introduction"
    assert data["section"] == "Introduction"


@pytest.mark.asyncio
async def test_locator_no_permission_returns_403(client: AsyncClient, auth_headers: dict, db_session_factory):
    """无权限用户 locator 返回 403"""
    doc_id = await _create_doc(db_session_factory, title="secret2.txt", content="secret", isolated_source=True)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="secret chunk")

    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}/locator", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_locator_wrong_chunk_returns_404(client: AsyncClient, auth_headers: dict, db_session_factory):
    """chunk 不属于该 document 时返回 404"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="doc_a.txt", content="doc a", user_id=uid)
    doc_id_2 = await _create_doc(db_session_factory, title="doc_b.txt", content="doc b", user_id=uid)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="chunk in doc a")

    resp = await client.get(f"/api/v1/documents/{doc_id_2}/chunks/{chunk_id}/locator", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_locator_not_found_returns_404(client: AsyncClient, auth_headers: dict, db_session_factory):
    """不存在的 chunk 返回 404"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="doc_c.txt", content="doc c", user_id=uid)
    fake_chunk = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks/{fake_chunk}/locator", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_locator_audit_logged(client: AsyncClient, auth_headers: dict, db_session_factory):
    """locator 操作记录审计日志"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    doc_id = await _create_doc(db_session_factory, title="audit_loc.txt", content="audit locator", user_id=uid)
    chunk_id = await _create_chunk(db_session_factory, doc_id, content="locator chunk")

    await client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}/locator", headers=auth_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "document.locator_view").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None
    assert str(log.resource_id) == doc_id


# ---------- citations locator 字段兼容测试 ----------


@pytest.mark.asyncio
async def test_citations_with_locator_field(client: AsyncClient, auth_headers: dict, db_session_factory):
    """citations 包含 locator 字段时 MessageOut 不报错"""
    from app.models.conversation import Conversation, Message

    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    async with db_session_factory() as session:
        conv = Conversation(title="locator test", user_id=uid)
        session.add(conv)
        await session.flush()
        conv_id = str(conv.id)

        msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="回答",
            citations=[{
                "index": 1,
                "document_id": "doc-001",
                "document_title": "文档A",
                "chunk_id": "chunk-001",
                "snippet": "片段",
                "score": 0.8,
                "page": 3,
                "locator": {"type": "page", "value": "3"},
            }],
        )
        session.add(msg)
        await session.commit()

    resp = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers)
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) > 0
    cit = msgs[-1]["citations"][0]
    assert cit["page"] == 3
    assert cit["locator"]["type"] == "page"


@pytest.mark.asyncio
async def test_citations_without_locator_still_works(client: AsyncClient, auth_headers: dict, db_session_factory):
    """旧 citations（无 locator）仍然正常返回"""
    from app.models.conversation import Conversation, Message

    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    async with db_session_factory() as session:
        conv = Conversation(title="old citation test", user_id=uid)
        session.add(conv)
        await session.flush()
        conv_id = str(conv.id)

        msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="回答",
            citations=[{
                "index": 1,
                "document_id": "doc-001",
                "document_title": "文档A",
                "chunk_id": "chunk-001",
                "snippet": "片段",
                "score": 0.8,
            }],
        )
        session.add(msg)
        await session.commit()

    resp = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers)
    assert resp.status_code == 200
    msgs = resp.json()
    cit = msgs[-1]["citations"][0]
    assert "locator" not in cit
    assert cit["snippet"] == "片段"
