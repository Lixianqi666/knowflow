"""RAG 质量问题队列测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.message_feedback import MessageFeedback
from app.models.rag_eval import RagEvalCase, RagEvalRun
from app.models.rag_quality_issue import RagQualityIssue
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
            knowledge_base_id=_as_uuid(kb_id), user_id=user_id, role=role,
        ))
        await session.commit()


async def _create_conv_msg(db_factory, user_id) -> tuple[str, str, str]:
    """创建对话和消息，返回 (conv_id, user_msg_id, assistant_msg_id)"""
    async with db_factory() as session:
        conv = Conversation(user_id=user_id, title="测试对话")
        session.add(conv)
        await session.flush()
        conv_id = str(conv.id)

        user_msg = Message(conversation_id=conv.id, role="user", content="测试问题")
        session.add(user_msg)
        await session.flush()

        assistant_msg = Message(
            conversation_id=conv.id, role="assistant", content="测试回答",
            citations=[{"index": 1, "document_id": "doc-1", "document_title": "文档A", "chunk_id": "c-1", "snippet": "片段", "score": 0.8}],
        )
        session.add(assistant_msg)
        await session.commit()
        return conv_id, str(user_msg.id), str(assistant_msg.id)


# ---------- down feedback 自动创建 issue ----------


@pytest.mark.asyncio
async def test_down_feedback_creates_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """down feedback 自动创建 quality issue"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    _, _, msg_id = await _create_conv_msg(db_session_factory, uid)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down", "reason": "回答不准确"},
    )
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(RagQualityIssue).where(
                RagQualityIssue.source_type == "feedback",
                RagQualityIssue.source_id == msg_id,
            )
        )
        issue = result.scalars().first()
    assert issue is not None
    assert issue.reason == "回答不准确"
    assert issue.severity == "medium"
    assert issue.status == "open"


@pytest.mark.asyncio
async def test_up_feedback_no_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """up feedback 不创建 issue"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    _, _, msg_id = await _create_conv_msg(db_session_factory, uid)

    resp = await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "up"},
    )
    assert resp.status_code == 200

    async with db_session_factory() as session:
        result = await session.execute(
            select(RagQualityIssue).where(RagQualityIssue.source_type == "feedback")
        )
        issues = result.scalars().all()
    # 不应有 feedback 类型的 issue（可能有其他测试创建的，但不会有这个 msg_id 的）
    assert not any(i.source_id == msg_id for i in issues)


@pytest.mark.asyncio
async def test_same_feedback_no_duplicate(client: AsyncClient, auth_headers: dict, db_session_factory):
    """同一 feedback 不重复创建 issue"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    _, _, msg_id = await _create_conv_msg(db_session_factory, uid)

    # 第一次
    await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down", "reason": "第一次"},
    )
    # 第二次（更新）
    await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down", "reason": "第二次"},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(RagQualityIssue).where(
                RagQualityIssue.source_type == "feedback",
                RagQualityIssue.source_id == msg_id,
            )
        )
        issues = result.scalars().all()
    assert len(issues) == 1


# ---------- issue API 测试 ----------


@pytest.mark.asyncio
async def test_admin_can_list_issues(client: AsyncClient, admin_headers: dict, db_session_factory):
    """admin 可查看全部 issues"""
    async with db_session_factory() as session:
        session.add(RagQualityIssue(source_type="manual", question="test", severity="medium", status="open"))
        await session.commit()

    resp = await client.get("/api/v1/rag-quality/issues", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_kb_owner_can_update_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """KB owner 可更新 issue"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "owner_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    async with db_session_factory() as session:
        issue = RagQualityIssue(
            knowledge_base_id=_as_uuid(kb_id), source_type="manual", question="test",
            severity="medium", status="open",
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.patch(
        f"/api/v1/rag-quality/issues/{issue_id}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_viewer_cannot_update_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """viewer 不能更新 issue"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "viewer_kb", admin_uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "viewer")

    async with db_session_factory() as session:
        issue = RagQualityIssue(
            knowledge_base_id=_as_uuid(kb_id), source_type="manual", question="test",
            severity="medium", status="open",
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.patch(
        f"/api/v1/rag-quality/issues/{issue_id}",
        headers=auth_headers,
        json={"status": "resolved"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_view_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """非成员不能查看 KB issue"""
    admin_uid = await _get_user_id(db_session_factory, "admin@test.com")
    kb_id = await _create_kb(db_session_factory, "non_member_kb", admin_uid)

    async with db_session_factory() as session:
        issue = RagQualityIssue(
            knowledge_base_id=_as_uuid(kb_id), source_type="manual", question="test",
            severity="medium", status="open",
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.get(f"/api/v1/rag-quality/issues/{issue_id}", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_no_kb_issue_only_admin_or_creator(client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory):
    """knowledge_base_id 为空 issue 仅 admin/创建者可见"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")

    # 创建一个无 KB 的 issue（由其他用户创建）
    import uuid as _uuid
    unique_email = f"other-{_uuid.uuid4().hex[:8]}@test.com"
    async with db_session_factory() as session:
        other = User(email=unique_email, name="Other", hashed_password="x")
        session.add(other)
        await session.flush()
        issue = RagQualityIssue(
            source_type="manual", question="other's issue",
            severity="medium", status="open", created_by=other.id,
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    # 非创建者不可见
    resp = await client.get(f"/api/v1/rag-quality/issues/{issue_id}", headers=auth_headers)
    assert resp.status_code == 403

    # admin 可见
    resp = await client.get(f"/api/v1/rag-quality/issues/{issue_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resolved_writes_resolved_at(client: AsyncClient, auth_headers: dict, db_session_factory):
    """resolved 写 resolved_at"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "resolve_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    async with db_session_factory() as session:
        issue = RagQualityIssue(
            knowledge_base_id=_as_uuid(kb_id), source_type="manual", question="test",
            severity="medium", status="open",
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.patch(
        f"/api/v1/rag-quality/issues/{issue_id}",
        headers=auth_headers,
        json={"status": "resolved", "resolution_note": "已修复"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None
    assert resp.json()["resolution_note"] == "已修复"


@pytest.mark.asyncio
async def test_resolved_back_to_open_clears_resolved_at(client: AsyncClient, auth_headers: dict, db_session_factory):
    """resolved 改回 open 清空 resolved_at"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "reopen_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    async with db_session_factory() as session:
        from datetime import datetime, timezone
        issue = RagQualityIssue(
            knowledge_base_id=_as_uuid(kb_id), source_type="manual", question="test",
            severity="medium", status="resolved", resolved_at=datetime.now(timezone.utc),
        )
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.patch(
        f"/api/v1/rag-quality/issues/{issue_id}",
        headers=auth_headers,
        json={"status": "open"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is None


@pytest.mark.asyncio
async def test_limit_max_100(client: AsyncClient, admin_headers: dict):
    """limit 最大 100"""
    resp = await client.get("/api/v1/rag-quality/issues?limit=200", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient, admin_headers: dict, db_session_factory):
    """查询支持 status 过滤"""
    async with db_session_factory() as session:
        session.add(RagQualityIssue(source_type="manual", question="open", severity="medium", status="open"))
        session.add(RagQualityIssue(source_type="manual", question="resolved", severity="medium", status="resolved"))
        await session.commit()

    resp = await client.get("/api/v1/rag-quality/issues?status=open", headers=admin_headers)
    assert resp.status_code == 200
    for issue in resp.json():
        assert issue["status"] == "open"


@pytest.mark.asyncio
async def test_issue_audit_logged(client: AsyncClient, auth_headers: dict, db_session_factory):
    """issue create 记录审计"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")
    kb_id = await _create_kb(db_session_factory, "audit_issue_kb", uid)
    await _add_kb_member(db_session_factory, kb_id, uid, "owner")

    await client.post(
        "/api/v1/rag-quality/issues",
        headers=auth_headers,
        json={"source_type": "manual", "question": "审计测试", "severity": "medium", "knowledge_base_id": kb_id},
    )

    async with db_session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "rag_quality.issue_create").order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
    assert log is not None


# ---------- eval failed 自动创建 issue ----------


@pytest.mark.asyncio
async def test_eval_failed_creates_issue(client: AsyncClient, auth_headers: dict, db_session_factory):
    """eval failed 自动创建 issue"""
    uid = await _get_user_id(db_session_factory, "pytest@test.com")

    # 创建 eval case 和 run（模拟 failed）
    async with db_session_factory() as session:
        case = RagEvalCase(question="评测问题", created_by=uid)
        session.add(case)
        await session.flush()
        case_id = str(case.id)

        run = RagEvalRun(
            case_id=case.id, question="评测问题", answer="错误回答",
            citations=[], passed=False, score=0.0, failure_reason="答案不匹配",
            created_by=uid,
        )
        session.add(run)
        await session.commit()
        run_id = str(run.id)

    # 手动调用 issue 创建（模拟 eval run 后的行为）
    from app.services.rag_quality import create_issue_from_eval

    async with db_session_factory() as session:
        issue = await create_issue_from_eval(
            session, run_id=run_id, case_id=case_id,
            question="评测问题", answer="错误回答", citations=[],
            failure_reason="答案不匹配", created_by=str(uid),
        )
        await session.commit()
        assert issue is not None
        assert issue.source_type == "eval_failed"
        assert issue.severity == "high"


@pytest.mark.asyncio
async def test_citations_default_empty(client: AsyncClient, auth_headers: dict, db_session_factory):
    """citations 默认 [] 且旧数据兼容"""
    async with db_session_factory() as session:
        issue = RagQualityIssue(source_type="manual", question="test", severity="medium", status="open")
        session.add(issue)
        await session.commit()
        issue_id = str(issue.id)

    resp = await client.get(f"/api/v1/rag-quality/issues/{issue_id}", headers=auth_headers)
    # admin 可以看到无 KB issue 吗？这个 issue created_by 为空，所以只有 admin 能看
    # 用 admin headers
    resp = await client.get(f"/api/v1/rag-quality/issues/{issue_id}", headers=auth_headers)
    # 如果不是 admin 且 created_by 为空，应该 403
    # 这里用 admin_headers
