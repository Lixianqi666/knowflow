"""知识库成员管理测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User


# ---------- 辅助函数 ----------


async def _create_kb(client: AsyncClient, headers: dict, name: str = "测试知识库") -> str:
    resp = await client.post(
        "/api/v1/knowledge-bases/",
        headers=headers,
        json={"name": name, "description": "测试"},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _get_user_id(db_factory, email: str) -> str:
    async with db_factory() as session:
        result = await session.execute(select(User.id).where(User.email == email))
        return str(result.scalar())


# ---------- 创建知识库自动成为 owner ----------


@pytest.mark.asyncio
async def test_create_kb_auto_owner(client: AsyncClient, auth_headers: dict, db_session_factory):
    """创建知识库时创建者自动成为 owner"""
    kb_id = await _create_kb(client, auth_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(KnowledgeBaseMember).where(
                KnowledgeBaseMember.knowledge_base_id == UUID(kb_id)
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "owner"


@pytest.mark.asyncio
async def test_created_by_treated_as_owner(client: AsyncClient, auth_headers: dict, db_session_factory):
    """旧数据没有成员记录时 created_by 仍视为 owner"""
    # 手动创建一个没有成员记录的知识库
    async with db_session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == "pytest@test.com"))
        user = user_result.scalar_one()

        kb = KnowledgeBase(name="旧知识库", description="无成员记录", created_by=user.id)
        session.add(kb)
        await session.commit()
        kb_id = str(kb.id)

    # 验证 list 中该知识库的 user_role 是 owner
    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()
    old_kb = next((kb for kb in kbs if kb["id"] == kb_id), None)
    assert old_kb is not None
    assert old_kb["user_role"] == "owner"


# ---------- 成员管理权限 ----------


@pytest.mark.asyncio
async def test_owner_can_add_member(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """owner 可以添加成员"""
    kb_id = await _create_kb(client, admin_headers)
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")

    # admin 添加 auth 用户
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role": "viewer"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_editor_cannot_add_member(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """editor 不能添加成员"""
    kb_id = await _create_kb(client, admin_headers)

    # 添加 auth 用户为 editor
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")
    await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role": "editor"},
    )

    # editor 尝试添加成员
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=auth_headers,
        json={"user_id": "some-id", "role": "viewer"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_manage_members(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """admin 可以管理成员"""
    kb_id = await _create_kb(client, auth_headers)

    # 获取另一个用户 ID（admin 自己）
    async with db_session_factory() as session:
        result = await session.execute(select(User).where(User.email == "admin@test.com"))
        admin_user = result.scalar_one()
        admin_user_id = str(admin_user.id)

    # admin 添加成员到 auth 用户创建的知识库
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=admin_headers,
        json={"user_id": admin_user_id, "role": "editor"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_add_member_invalid_role(client: AsyncClient, admin_headers: dict):
    """添加成员时 role 非法返回 400"""
    kb_id = await _create_kb(client, admin_headers)

    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=admin_headers,
        json={"user_id": "some-id", "role": "superadmin"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cannot_remove_last_owner(client: AsyncClient, auth_headers: dict, db_session_factory):
    """不能删除最后一个 owner"""
    kb_id = await _create_kb(client, auth_headers)
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")

    resp = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/members/{user_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "最后一个 owner" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_downgrade_last_owner(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """不能把最后一个 owner 降级"""
    kb_id = await _create_kb(client, auth_headers)
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")

    resp = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}/members/{user_id}",
        headers=auth_headers,
        json={"role": "viewer"},
    )
    assert resp.status_code == 400
    assert "最后一个 owner" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_member_list_permission(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """成员列表只允许有权限用户查看"""
    kb_id = await _create_kb(client, admin_headers)

    # 非成员不能查看
    resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/members", headers=auth_headers)
    assert resp.status_code == 403


# ---------- 知识库列表按成员权限过滤 ----------


@pytest.mark.asyncio
async def test_user_can_see_member_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """普通用户能看到自己是 member 的知识库"""
    kb_id = await _create_kb(client, admin_headers, "共享知识库")
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")

    # 添加为成员
    await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role": "viewer"},
    )

    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()
    assert any(kb["id"] == kb_id for kb in kbs)


@pytest.mark.asyncio
async def test_user_cannot_see_unrelated_kb(client: AsyncClient, auth_headers: dict, admin_headers: dict):
    """普通用户不能看到无关知识库"""
    kb_id = await _create_kb(client, admin_headers, "私有知识库")

    resp = await client.get("/api/v1/knowledge-bases/", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()
    assert not any(kb["id"] == kb_id for kb in kbs)


# ---------- 审计测试 ----------


@pytest.mark.asyncio
async def test_member_add_records_audit(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """member add 记录 audit"""
    from app.models.audit_log import AuditLog

    kb_id = await _create_kb(client, auth_headers)
    user_id = await _get_user_id(db_session_factory, "pytest@test.com")

    # 先添加第二个 owner（以便可以添加成员）
    await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/members",
        headers=auth_headers,
        json={"user_id": user_id, "role": "editor"},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "knowledge_base.member_add")
        )
        log = result.scalars().first()
        assert log is not None
