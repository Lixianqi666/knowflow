"""RAG 检索调试 API"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.kb_permissions import can_view_kb


class RagDebugSearchRequest(PydanticBaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    knowledge_base_id: str | None = None
    top_k: int | None = Field(default=None, ge=1)


class RagDebugSearchResult(PydanticBaseModel):
    rank: int
    document_id: str
    document_title: str
    chunk_id: str
    snippet: str
    score: float
    page: int | None = None
    locator: dict | None = None


class RagDebugSearchResponse(PydanticBaseModel):
    query: str
    knowledge_base_id: str | None = None
    top_k: int
    results: list[RagDebugSearchResult]
    no_result_reason: str | None = None
    used_config: dict | None = None


router = APIRouter(prefix="/rag", tags=["RAG 调试"])


@router.post("/debug-search", response_model=RagDebugSearchResponse)
async def debug_search(
    data: RagDebugSearchRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检索调试：输入 query，返回检索到的 chunks 及定位信息，不调用 LLM"""
    query = data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")

    kb_id = data.knowledge_base_id
    no_result_reason: str | None = None

    # 读取 KB rag_config
    from app.services.rag_config import get_effective_rag_config

    rag_cfg: dict = {}
    if kb_id:
        kb = await db.get(KnowledgeBase, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if not await can_view_kb(db, user, kb):
            raise HTTPException(status_code=403, detail="无权限访问该知识库")
        rag_cfg = get_effective_rag_config(kb.rag_config)

    # top_k: 用户显式传入 > KB 配置 > 默认 5
    if data.top_k is not None:
        top_k = min(data.top_k, 20)
    elif rag_cfg.get("top_k"):
        top_k = rag_cfg["top_k"]
    else:
        top_k = 5

    score_threshold = rag_cfg.get("score_threshold", 0.0)

    # 权限处理
    allowed_kb_ids: set[str] | None = None
    if kb_id:
        allowed_kb_ids = {kb_id}
    elif user.role != "admin":
        from app.models.kb_member import KnowledgeBaseMember

        member_result = await db.execute(
            select(KnowledgeBaseMember.knowledge_base_id).where(
                KnowledgeBaseMember.user_id == user.id
            )
        )
        member_kb_ids = {str(row[0]) for row in member_result.fetchall()}

        created_result = await db.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.created_by == user.id)
        )
        created_kb_ids = {str(row[0]) for row in created_result.fetchall()}

        allowed_kb_ids = member_kb_ids | created_kb_ids
        if not allowed_kb_ids:
            return RagDebugSearchResponse(
                query=query, top_k=top_k, results=[],
                no_result_reason="没有可检索的知识库",
                used_config={"top_k": top_k, "score_threshold": score_threshold},
            )

    # 检索
    from app.services.retrieval import RetrievalService

    retrieval = RetrievalService(db)
    fetch_k = top_k * 3 if allowed_kb_ids else top_k
    chunks = await retrieval.search(
        query,
        str(user.id),
        is_admin=True,
        top_k=fetch_k,
        threshold=0.0,
        rerank_top_k=fetch_k,
    )

    # 按 KB 权限过滤
    if allowed_kb_ids is not None:
        doc_ids = {c.document_id for c in chunks}
        if doc_ids:
            doc_kb_result = await db.execute(
                select(Document.id, Document.kb_id).where(Document.id.in_(doc_ids))
            )
            doc_kb_map = {str(row[0]): str(row[1]) if row[1] else None for row in doc_kb_result.fetchall()}
            chunks = [c for c in chunks if doc_kb_map.get(str(c.document_id)) in allowed_kb_ids]

    # score_threshold 过滤
    chunks = [c for c in chunks if c.score >= score_threshold]
    chunks = chunks[:top_k]

    # chunk metadata
    chunk_ids = [c.id for c in chunks if c.score > 0]
    chunk_meta_map: dict[str, dict] = {}
    if chunk_ids:
        meta_result = await db.execute(
            select(DocumentChunk.id, DocumentChunk.metadata_).where(DocumentChunk.id.in_(chunk_ids))
        )
        chunk_meta_map = {str(row[0]): (row[1] or {}) for row in meta_result.fetchall()}

    results: list[RagDebugSearchResult] = []
    for i, c in enumerate(chunks):
        if c.score <= 0:
            continue
        cid = str(c.id)
        meta = chunk_meta_map.get(cid, {})
        page = meta.get("page") or meta.get("page_number")
        section = meta.get("section") or meta.get("heading")

        locator: dict = {}
        if page is not None:
            locator = {"type": "page", "value": str(page)}
        elif section:
            locator = {"type": "text", "value": str(section)}
        else:
            locator = {"type": "chunk", "value": cid}

        entry = RagDebugSearchResult(
            rank=i + 1,
            document_id=str(c.document_id),
            document_title=c.document_title,
            chunk_id=cid,
            snippet=c.content[:300],
            score=round(c.score, 4),
            locator=locator,
        )
        if page is not None:
            entry.page = int(page) if isinstance(page, (int, float, str)) and str(page).isdigit() else page
        results.append(entry)

    if not results:
        no_result_reason = "未检索到相关内容"

    # 审计
    from app.services.audit_v2 import record_audit_event

    await record_audit_event(
        db,
        actor_user=user,
        action="rag.debug_search",
        resource_type="rag",
        request=request,
        metadata={"query": query[:200], "kb_id": kb_id, "top_k": top_k, "result_count": len(results)},
    )

    return RagDebugSearchResponse(
        query=query,
        knowledge_base_id=kb_id,
        top_k=top_k,
        results=results,
        no_result_reason=no_result_reason,
        used_config={"top_k": top_k, "score_threshold": score_threshold},
    )
