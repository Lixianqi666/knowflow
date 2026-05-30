"""文档上传 + 权限 read/write 区分测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.document import Document
from app.models.permission import DocumentPermission, SourcePermission
from app.models.user import User


# ---------- 基础上传测试 ----------


@pytest.mark.asyncio
async def test_upload_txt(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "test.txt"
    assert data["status"] in ("pending", "indexed", "processing", "failed")


@pytest.mark.asyncio
async def test_upload_rejected_extension(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("bad.exe", b"bad", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/documents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code in (401, 403)


# ---------- 辅助函数 ----------


def _as_uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


async def _get_user_id(session, email: str) -> UUID:
    result = await session.execute(select(User.id).where(User.email == email))
    return result.scalar()


async def _grant_doc_perm(session, doc_id, user_id, perm: str):
    session.add(DocumentPermission(document_id=_as_uuid(doc_id), user_id=user_id, permission=perm))
    await session.flush()


async def _grant_source_perm(session, source_id, user_id, perm: str):
    result = await session.execute(
        select(SourcePermission).where(
            SourcePermission.source_id == _as_uuid(source_id),
            SourcePermission.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.permission = perm
    else:
        session.add(SourcePermission(source_id=_as_uuid(source_id), user_id=user_id, permission=perm))
    await session.flush()


async def _get_doc(session, doc_id):
    return await session.get(Document, _as_uuid(doc_id))


# ---------- DocumentPermission read/write 测试 ----------


@pytest.mark.asyncio
async def test_upload_gives_write_permission(client: AsyncClient, auth_headers: dict, db_session_factory):
    """上传者应获得 write 权限"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("perm_test.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        result = await session.execute(
            select(DocumentPermission.permission).where(
                DocumentPermission.document_id == _as_uuid(doc_id)
            )
        )
        perm = result.scalar()
    assert perm == "write"


@pytest.mark.asyncio
async def test_read_user_cannot_delete(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """read 权限用户不能删除文档"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("del_test.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        await _grant_doc_perm(session, doc_id, uid, "read")
        await session.commit()

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_write_user_can_delete(client: AsyncClient, auth_headers: dict):
    """write 权限用户可以删除文档"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("write_del.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_delete(client: AsyncClient, admin_headers: dict):
    """admin 可以删除任何文档"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("admin_del.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    assert resp.status_code == 200


# ---------- SourcePermission 权限合并测试 ----------


@pytest.mark.asyncio
async def test_doc_read_takes_precedence_over_source_write(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """DocumentPermission=read 优先于 SourcePermission=write，不能删除"""
    # admin 创建文档
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("src_write.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        doc = await _get_doc(session, doc_id)
        # 给 read doc perm
        await _grant_doc_perm(session, doc_id, uid, "read")
        # 给 write source perm（但 doc perm 优先）
        await _grant_source_perm(session, doc.source_id, uid, "write")
        await session.commit()

    # doc perm=read 优先，不能删除
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_source_read_only_cannot_delete(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """只有 SourcePermission=read → 不能删除"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("src_read.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        doc = await _get_doc(session, doc_id)
        # 只给 source read，不给 doc perm
        await _grant_source_perm(session, doc.source_id, uid, "read")
        await session.commit()

    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 403


# ---------- Batch 操作权限测试 ----------


@pytest.mark.asyncio
async def test_batch_delete_only_write_docs(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """batch-delete 只删除有 write 权限的文档，read 权限的不动"""
    ids = []
    for name in ("batch_a.txt", "batch_b.txt"):
        resp = await client.post(
            "/api/v1/documents/upload",
            headers=admin_headers,
            files={"file": (name, b"batch test", "text/plain")},
        )
        ids.append(resp.json()["id"])

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        await _grant_doc_perm(session, ids[0], uid, "write")
        await _grant_doc_perm(session, ids[1], uid, "read")
        await session.commit()

    resp = await client.post(
        "/api/v1/documents/batch-delete",
        headers=auth_headers,
        json={"ids": ids},
    )
    assert resp.status_code == 200
    assert "已删除 1 个文档" in resp.json()["detail"]

    # 验证第二个仍然存在
    resp = await client.get(f"/api/v1/documents/{ids[1]}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batch_delete_source_write(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """只有 SourcePermission=write 的文档，batch-delete 应该能删除"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("batch_src_write.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        doc = await _get_doc(session, doc_id)
        await _grant_source_perm(session, doc.source_id, uid, "write")
        await session.commit()

    resp = await client.post(
        "/api/v1/documents/batch-delete",
        headers=auth_headers,
        json={"ids": [doc_id]},
    )
    assert resp.status_code == 200
    assert "已删除 1 个文档" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_batch_delete_source_read_only(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """只有 SourcePermission=read 的文档，batch-delete 不应删除"""
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        files={"file": ("batch_src_read.txt", b"test", "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    async with db_session_factory() as session:
        uid = await _get_user_id(session, "pytest@test.com")
        doc = await _get_doc(session, doc_id)
        await _grant_source_perm(session, doc.source_id, uid, "read")
        await session.commit()

    resp = await client.post(
        "/api/v1/documents/batch-delete",
        headers=auth_headers,
        json={"ids": [doc_id]},
    )
    assert resp.status_code == 200
    assert "已删除 0 个文档" in resp.json()["detail"]
