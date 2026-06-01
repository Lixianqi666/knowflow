"""RAG 评测测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from app.models.rag_eval import RagEvalCase, RagEvalRun
from app.services.rag_eval import evaluate_rag_answer


# ---------- evaluate_rag_answer 单元测试 ----------


def test_evaluate_answer_hit():
    """expected_answer 命中时 passed=true"""
    passed, score, reason = evaluate_rag_answer(
        answer="试用期为3个月，特殊岗位可延长至6个月",
        citations=[],
        expected_answer="试用期 3个月",
    )
    assert passed is True
    assert score == 1.0
    assert reason is None


def test_evaluate_citation_hit():
    """expected citation 命中时 passed=true"""
    passed, score, reason = evaluate_rag_answer(
        answer="根据员工手册...",
        citations=[{"document_id": "doc-001", "document_title": "员工手册"}],
        expected_citation_doc_ids=["doc-001"],
    )
    assert passed is True
    assert score == 1.0


def test_evaluate_both_required():
    """answer 和 citation 都要求时必须同时满足"""
    passed, score, reason = evaluate_rag_answer(
        answer="试用期3个月",
        citations=[{"document_id": "doc-001"}],
        expected_answer="试用期",
        expected_citation_doc_ids=["doc-001"],
    )
    assert passed is True

    # 只满足一个
    passed, score, reason = evaluate_rag_answer(
        answer="试用期3个月",
        citations=[{"document_id": "doc-999"}],
        expected_answer="试用期",
        expected_citation_doc_ids=["doc-001"],
    )
    assert passed is False
    assert "未引用预期文档" in reason


def test_evaluate_empty_expected():
    """case 缺少 expected 时 passed=false"""
    passed, score, reason = evaluate_rag_answer(
        answer="回答内容",
        citations=[],
    )
    assert passed is False
    assert score == 0.0
    assert "缺少" in reason


def test_evaluate_answer_miss():
    """answer 未命中时 passed=false"""
    passed, score, reason = evaluate_rag_answer(
        answer="公司有10个部门",
        citations=[],
        expected_answer="试用期 3个月",
    )
    assert passed is False
    assert "未包含预期" in reason


# ---------- 辅助函数 ----------


async def _create_conv(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/chat/conversations", headers=headers, json={"title": "评测测试"}
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_assistant_msg(db_factory, conv_id: str) -> str:
    from app.models.conversation import Message

    async with db_factory() as session:
        user_msg = Message(
            conversation_id=UUID(conv_id),
            role="user",
            content="公司的考勤制度是什么？",
        )
        session.add(user_msg)

        assistant_msg = Message(
            conversation_id=UUID(conv_id),
            role="assistant",
            content="根据员工手册，工作时间为周一至周五9:00-18:00",
            citations=[
                {"document_id": "doc-001", "document_title": "员工手册", "snippet": "工作时间..."}
            ],
        )
        session.add(assistant_msg)
        await session.commit()
        return str(assistant_msg.id)


# ---------- Eval Case CRUD 测试 ----------


@pytest.mark.asyncio
async def test_create_eval_case(client: AsyncClient, auth_headers: dict):
    """创建 eval case"""
    resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={
            "question": "公司的考勤制度是什么？",
            "expected_answer": "工作时间",
            "expected_citation_doc_ids": ["doc-001"],
            "tags": ["hr"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "公司的考勤制度是什么？"
    assert data["expected_answer"] == "工作时间"
    assert data["tags"] == ["hr"]


@pytest.mark.asyncio
async def test_list_eval_cases_own(client: AsyncClient, auth_headers: dict):
    """普通用户只能看到自己的 eval cases"""
    await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "我的问题"},
    )
    resp = await client.get("/api/v1/rag-evals/cases", headers=auth_headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) >= 1
    assert any(c["question"] == "我的问题" for c in cases)


@pytest.mark.asyncio
async def test_list_eval_cases_admin_sees_all(
    client: AsyncClient, auth_headers: dict, admin_headers: dict
):
    """admin 可以看到全部 eval cases"""
    await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "用户问题"},
    )
    resp = await client.get("/api/v1/rag-evals/cases", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_eval_case(client: AsyncClient, auth_headers: dict):
    """更新 eval case"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "原始问题"},
    )
    case_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rag-evals/cases/{case_id}",
        headers=auth_headers,
        json={"question": "更新后问题", "tags": ["updated"]},
    )
    assert resp.status_code == 200
    assert resp.json()["question"] == "更新后问题"
    assert resp.json()["tags"] == ["updated"]


@pytest.mark.asyncio
async def test_delete_eval_case(client: AsyncClient, auth_headers: dict):
    """删除 eval case"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "待删除"},
    )
    case_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/rag-evals/cases/{case_id}", headers=auth_headers)
    assert resp.status_code == 200

    # 列表不返回
    resp = await client.get("/api/v1/rag-evals/cases", headers=auth_headers)
    assert not any(c["id"] == case_id for c in resp.json())


@pytest.mark.asyncio
async def test_permission_denied_other_user(
    client: AsyncClient, auth_headers: dict, admin_headers: dict
):
    """其他用户不能操作无权限 eval case"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=admin_headers,
        json={"question": "admin的问题"},
    )
    case_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/rag-evals/cases/{case_id}", headers=auth_headers)
    assert resp.status_code == 404


# ---------- Run Eval Case 测试 ----------


@pytest.mark.asyncio
async def test_run_eval_case(client: AsyncClient, auth_headers: dict, db_session_factory):
    """运行 eval case 会保存 rag_eval_run"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={
            "question": "考勤制度",
            "expected_answer": "工作时间",
        },
    )
    case_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/rag-evals/cases/{case_id}/run", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["question"] == "考勤制度"
    assert "passed" in data
    assert "score" in data


@pytest.mark.asyncio
async def test_run_eval_case_saves_to_db(
    client: AsyncClient, auth_headers: dict, db_session_factory
):
    """运行 eval case 后数据库有记录"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "测试问题", "expected_answer": "测试"},
    )
    case_id = create_resp.json()["id"]

    await client.post(f"/api/v1/rag-evals/cases/{case_id}/run", headers=auth_headers)

    async with db_session_factory() as session:
        result = await session.execute(
            select(RagEvalRun).where(RagEvalRun.case_id == UUID(case_id))
        )
        runs = result.scalars().all()
        assert len(runs) >= 1


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient, auth_headers: dict):
    """查询 eval case 运行历史"""
    create_resp = await client.post(
        "/api/v1/rag-evals/cases",
        headers=auth_headers,
        json={"question": "历史测试"},
    )
    case_id = create_resp.json()["id"]

    await client.post(f"/api/v1/rag-evals/cases/{case_id}/run", headers=auth_headers)

    resp = await client.get(
        f"/api/v1/rag-evals/cases/{case_id}/runs", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------- Feedback to Eval Case 测试 ----------


@pytest.mark.asyncio
async def test_feedback_to_eval_case(
    client: AsyncClient, auth_headers: dict, db_session_factory
):
    """feedback 转 eval case"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/rag-evals/messages/{msg_id}/to-eval-case",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "公司的考勤制度是什么？"
    assert "feedback" in data["tags"]
    assert "doc-001" in data["expected_citation_doc_ids"]


@pytest.mark.asyncio
async def test_feedback_to_eval_case_with_negative(
    client: AsyncClient, auth_headers: dict, db_session_factory
):
    """down feedback 转 eval case 带 negative tag"""
    conv_id = await _create_conv(client, auth_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    # 先创建 down feedback
    await client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        headers=auth_headers,
        json={"rating": "down", "reason": "不准确"},
    )

    resp = await client.post(
        f"/api/v1/rag-evals/messages/{msg_id}/to-eval-case",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "negative" in resp.json()["tags"]


@pytest.mark.asyncio
async def test_feedback_to_eval_case_rejects_user_message(
    client: AsyncClient, auth_headers: dict, db_session_factory
):
    """user 消息不能转 eval case"""
    conv_id = await _create_conv(client, auth_headers)
    from app.models.conversation import Message

    async with db_session_factory() as session:
        msg = Message(
            conversation_id=UUID(conv_id),
            role="user",
            content="用户消息",
        )
        session.add(msg)
        await session.commit()
        msg_id = str(msg.id)

    resp = await client.post(
        f"/api/v1/rag-evals/messages/{msg_id}/to-eval-case",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_feedback_to_eval_case_permission_denied(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, db_session_factory
):
    """其他用户不能转无权限 message"""
    conv_id = await _create_conv(client, admin_headers)
    msg_id = await _create_assistant_msg(db_session_factory, conv_id)

    resp = await client.post(
        f"/api/v1/rag-evals/messages/{msg_id}/to-eval-case",
        headers=auth_headers,
    )
    assert resp.status_code == 404
