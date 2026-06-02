from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase
from app.models.rag_eval import RagEvalCase, RagEvalRun
from app.models.user import User
from app.schemas.rag_eval import (
    RagEvalCaseCreate,
    RagEvalCaseOut,
    RagEvalCaseUpdate,
    RagEvalRunOut,
)
from app.services.rag_eval import evaluate_rag_answer

router = APIRouter(prefix="/rag-evals", tags=["RAG 评测"])


async def _can_access_case(db: AsyncSession, user: User, case: RagEvalCase) -> bool:
    """检查用户是否可以访问该评测用例"""
    if user.role == "admin":
        return True
    if case.created_by == user.id:
        return True
    if case.knowledge_base_id:
        from app.services.kb_permissions import can_view_kb

        kb = await db.get(KnowledgeBase, case.knowledge_base_id)
        if kb and await can_view_kb(db, user, kb):
            return True
    return False


async def _can_edit_case(db: AsyncSession, user: User, case: RagEvalCase) -> bool:
    """检查用户是否可以编辑该评测用例"""
    if user.role == "admin":
        return True
    if case.created_by == user.id:
        return True
    if case.knowledge_base_id:
        from app.services.kb_permissions import can_edit_kb

        kb = await db.get(KnowledgeBase, case.knowledge_base_id)
        if kb and await can_edit_kb(db, user, kb):
            return True
    return False


@router.get("/cases", response_model=list[RagEvalCaseOut])
async def list_cases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(RagEvalCase).order_by(RagEvalCase.created_at.desc())
    if user.role != "admin":
        # 用户可见：自己创建的 + 自己有权限的 KB 的用例
        from app.models.kb_member import KnowledgeBaseMember

        member_kb_ids = select(KnowledgeBaseMember.knowledge_base_id).where(
            KnowledgeBaseMember.user_id == user.id
        )
        created_kb_ids = select(KnowledgeBase.id).where(KnowledgeBase.created_by == user.id)
        query = query.where(
            (RagEvalCase.created_by == user.id)
            | RagEvalCase.knowledge_base_id.in_(member_kb_ids)
            | RagEvalCase.knowledge_base_id.in_(created_kb_ids)
        )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/cases", response_model=RagEvalCaseOut)
async def create_case(
    data: RagEvalCaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 校验知识库权限
    if data.knowledge_base_id:
        kb = await db.get(KnowledgeBase, data.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        from app.services.kb_permissions import can_edit_kb

        if not await can_edit_kb(db, user, kb):
            raise HTTPException(status_code=403, detail="无权使用该知识库")

    case = RagEvalCase(
        knowledge_base_id=data.knowledge_base_id,
        question=data.question,
        expected_answer=data.expected_answer,
        expected_citation_doc_ids=data.expected_citation_doc_ids,
        tags=data.tags,
        created_by=user.id,
    )
    db.add(case)
    await db.flush()
    return case


@router.get("/cases/{case_id}", response_model=RagEvalCaseOut)
async def get_case(
    case_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(RagEvalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="评测用例不存在")
    if not await _can_access_case(db, user, case):
        raise HTTPException(status_code=404, detail="评测用例不存在")
    return case


@router.patch("/cases/{case_id}", response_model=RagEvalCaseOut)
async def update_case(
    case_id: UUID,
    data: RagEvalCaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(RagEvalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="评测用例不存在")
    if not await _can_edit_case(db, user, case):
        raise HTTPException(status_code=403, detail="无权编辑该评测用例")

    if data.question is not None:
        case.question = data.question
    if data.expected_answer is not None:
        case.expected_answer = data.expected_answer
    if data.expected_citation_doc_ids is not None:
        case.expected_citation_doc_ids = data.expected_citation_doc_ids
    if data.tags is not None:
        case.tags = data.tags
    await db.flush()
    return case


@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(RagEvalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="评测用例不存在")
    if not await _can_edit_case(db, user, case):
        raise HTTPException(status_code=403, detail="无权删除该评测用例")
    await db.delete(case)
    return {"detail": "已删除"}


@router.post("/cases/{case_id}/run", response_model=RagEvalRunOut)
async def run_case(
    case_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(RagEvalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="评测用例不存在")
    if not await _can_access_case(db, user, case):
        raise HTTPException(status_code=404, detail="评测用例不存在")

    # 创建临时对话用于检索
    from app.services.retrieval import RetrievalService
    from app.core.prompts import RAG_SYSTEM, RetrievedChunk, build_messages, format_retrieved_context
    from app.core.llm import llm_service
    from app.config import settings

    retrieval = RetrievalService(db)
    chunks = await retrieval.search(
        case.question,
        str(user.id),
        is_admin=user.role == "admin",
        top_k=settings.RETRIEVAL_TOP_K,
        threshold=settings.RETRIEVAL_THRESHOLD,
        rerank_top_k=settings.RETRIEVAL_RERANK_TOP_K,
    )

    citations = [
        {
            "index": i + 1,
            "document_id": str(c.document_id),
            "document_title": c.document_title,
            "chunk_id": str(c.id),
            "snippet": c.content[:300],
            "score": round(c.score, 3),
        }
        for i, c in enumerate(chunks)
        if c.score > 0
    ]

    has_context = len(chunks) > 0 and any(c.score > 0 for c in chunks)
    system_prompt = RAG_SYSTEM if has_context else None

    answer = ""
    if has_context:
        context_text = format_retrieved_context(
            [RetrievedChunk(title=c.document_title, content=c.content) for c in chunks]
        )
        messages = build_messages(system_prompt, context=context_text, question=case.question)
        try:
            answer = await llm_service.complete(messages, temperature=0.0)
        except Exception as e:
            answer = f"LLM 调用失败: {e}"
    else:
        answer = "没有找到足够依据，无法回答此问题。"

    passed, score, failure_reason = evaluate_rag_answer(
        answer=answer,
        citations=citations,
        expected_answer=case.expected_answer,
        expected_citation_doc_ids=case.expected_citation_doc_ids,
    )

    run = RagEvalRun(
        case_id=case.id,
        question=case.question,
        answer=answer,
        citations=citations,
        passed=passed,
        score=score,
        failure_reason=failure_reason,
        created_by=user.id,
    )
    db.add(run)
    await db.flush()

    # eval failed 自动创建质量问题（失败不阻塞 eval run 保存）
    if not passed:
        from app.services.rag_quality import create_issue_from_eval

        try:
            await create_issue_from_eval(
                db,
                run_id=str(run.id),
                case_id=str(case.id),
                question=case.question,
                answer=answer,
                citations=citations,
                failure_reason=failure_reason,
                knowledge_base_id=str(case.knowledge_base_id) if case.knowledge_base_id else None,
                created_by=str(user.id),
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception(f"eval quality issue 创建失败: run={run.id}")

    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="rag_eval.run",
        resource_type="rag_eval_case",
        resource_id=case.id,
        metadata={"passed": passed, "score": score},
    )

    return run


@router.get("/cases/{case_id}/runs", response_model=list[RagEvalRunOut])
async def list_runs(
    case_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(RagEvalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="评测用例不存在")
    if not await _can_access_case(db, user, case):
        raise HTTPException(status_code=404, detail="评测用例不存在")

    result = await db.execute(
        select(RagEvalRun)
        .where(RagEvalRun.case_id == case_id)
        .order_by(RagEvalRun.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/messages/{msg_id}/to-eval-case", response_model=RagEvalCaseOut)
async def feedback_to_eval_case(
    msg_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """将 feedback 转为 eval case"""
    msg = await db.get(Message, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    if msg.role != "assistant":
        raise HTTPException(status_code=400, detail="只能对助手消息操作")

    conv = await db.get(Conversation, msg.conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")

    # 找上一条 user 消息作为 question
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == msg.conversation_id,
            Message.role == "user",
            Message.created_at < msg.created_at,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    user_msg = result.scalar_one_or_none()
    if not user_msg:
        raise HTTPException(status_code=400, detail="找不到对应的用户问题")

    # 提取 citations 中的 document_id
    cited_doc_ids = []
    if msg.citations:
        cited_doc_ids = list({c.get("document_id") for c in msg.citations if c.get("document_id")})

    # 构造 tags
    tags = ["feedback"]
    from app.models.message_feedback import MessageFeedback

    fb_result = await db.execute(
        select(MessageFeedback).where(
            MessageFeedback.message_id == msg_id,
            MessageFeedback.user_id == user.id,
        )
    )
    fb = fb_result.scalar_one_or_none()
    if fb and fb.rating == "down":
        tags.append("negative")

    case = RagEvalCase(
        question=user_msg.content,
        expected_citation_doc_ids=cited_doc_ids,
        tags=tags,
        created_by=user.id,
    )
    db.add(case)
    await db.flush()
    return case
