import asyncio
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import EN_STOP, ZH_STOP, settings
from app.core.llm import embedding_service
from app.services.reranker import reranker_service


def _get_kb_filter(kb_id: str | None = None, kb_ids: list[str] | None = None) -> tuple[str, dict]:
    if kb_ids:
        return " AND d.kb_id = ANY(:kb_ids::uuid[])", {"kb_ids": kb_ids}
    if kb_id:
        return " AND d.kb_id = :kb_id::uuid", {"kb_id": kb_id}
    return "", {}


logger = logging.getLogger(__name__)

# 非管理员的权限过滤子句
PERM_FILTER = """
    AND (
        EXISTS (
            SELECT 1 FROM document_permissions dp
            WHERE dp.document_id = d.id AND dp.user_id = :uid
        )
        OR EXISTS (
            SELECT 1 FROM source_permissions sp
            WHERE sp.source_id = d.source_id AND sp.user_id = :uid
        )
    )
"""


@dataclass
class RetrievedChunk:
    id: UUID
    content: str
    document_title: str
    document_id: UUID
    score: float


def _tokenize(query: str) -> list[str]:
    """jieba 分词 + 停用词过滤（保留中文单字以支持人名检索）"""
    import jieba

    cleaned = re.sub(r"[？！。，、；：“”‘’（）\[\]【】\s]+", " ", query).strip()
    words = jieba.cut_for_search(cleaned)
    tokens = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        # 短于2的非中文字符过滤，中文单字保留（人名如"赵六"分词后可能为单字）
        if len(w) < 2 and not re.search(r"[一-鿿]", w):
            continue
        if w.lower() in EN_STOP or w in ZH_STOP:
            continue
        tokens.append(w)
    # 去重保序
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        user_id: str,
        is_admin: bool = False,
        top_k: int | None = None,
        threshold: float | None = None,
        rerank_top_k: int | None = None,
        kb_id: str | None = None,
        kb_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.RETRIEVAL_TOP_K
        threshold = threshold or settings.RETRIEVAL_THRESHOLD
        rerank_top_k = rerank_top_k or settings.RETRIEVAL_RERANK_TOP_K
        perm = "" if is_admin else PERM_FILTER

        # 阶段1: 双路召回（向量+BM25）
        vector_results = await self._vector_search_safe(
            query, user_id, perm, kb_id, kb_ids, top_k * 2, threshold
        )
        bm25_results = await self._bm25_search(query, user_id, perm, kb_id, kb_ids, top_k * 2)

        # 阶段2: RRF 融合
        merged = self._rrf_fusion(vector_results, bm25_results, k=settings.RRF_K)
        if not merged:
            merged = []

        # 阶段3: 去重（同一文档最多 2 个 chunk）
        deduped = []
        seen_docs: set[str] = set()
        for c in merged:
            did = str(c.document_id)
            if did not in seen_docs:
                seen_docs.add(did)
                deduped.append(c)
            elif sum(1 for d in deduped if str(d.document_id) == did) < 2:
                deduped.append(c)

        # 阶段4: LIKE 子串补充——中文人名等不被向量/BM25 很好匹配的场景
        like_results = await self._like_search(query, user_id, perm, kb_id, kb_ids, top_k * 2)
        if like_results:
            existing_ids = {str(c.id) for c in deduped}
            for c in like_results:
                if str(c.id) not in existing_ids:
                    deduped.append(c)
                    existing_ids.add(str(c.id))

        # 阶段5: Rerank 精排
        return await reranker_service.rerank(query, deduped, top_k=rerank_top_k)

    async def _vector_search_safe(
        self,
        query: str,
        user_id: str,
        perm: str,
        kb_id: str | None,
        kb_ids: list[str] | None,
        top_k: int,
        threshold: float,
    ) -> list[RetrievedChunk]:
        try:
            query_emb = await asyncio.wait_for(
                embedding_service.embed_single(query), timeout=settings.EMBEDDING_TIMEOUT
            )
            if query_emb:
                return await self._vector_search(
                    query_emb, user_id, perm, kb_id, kb_ids, top_k, threshold
                )
        except Exception as e:
            logger.debug(f"向量搜索失败: {e}")
        return []

    async def _vector_search(
        self,
        embedding: list[float],
        user_id: str,
        perm: str,
        kb_id: str | None,
        kb_ids: list[str] | None,
        top_k: int,
        threshold: float,
    ) -> list[RetrievedChunk]:
        kb_cond, kb_params = _get_kb_filter(kb_id, kb_ids)
        emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
        sql = text(f"""
            SELECT dc.id, dc.content, d.title, d.id AS document_id,
                   1 - (dc.embedding <=> :embedding) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'indexed' AND dc.embedding IS NOT NULL
            {perm} {kb_cond}
            ORDER BY dc.embedding <=> :embedding
            LIMIT :limit
        """)
        params = {"embedding": emb_str, "limit": top_k, "uid": user_id, **kb_params}
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        return [
            RetrievedChunk(
                id=row[0],
                content=row[1],
                document_title=row[2],
                document_id=row[3],
                score=float(row[4]),
            )
            for row in rows
            if row[4] >= threshold
        ]

    async def _bm25_search(
        self,
        query: str,
        user_id: str,
        perm: str,
        kb_id: str | None,
        kb_ids: list[str] | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        kb_cond, kb_params = _get_kb_filter(kb_id, kb_ids)
        tokens = await asyncio.to_thread(_tokenize, query)
        if not tokens:
            cleaned = re.sub(r"[？！。，、；：“”‘’（）\[\]【】\s]+", "", query).strip()
            tokens = [cleaned] if cleaned else [query]

        tsquery_str = " | ".join(tokens)
        sql = text(f"""
            SELECT dc.id, dc.content, d.title, d.id AS document_id,
                   ts_rank(dc.tsvector_content, to_tsquery('simple', :tsquery)) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'indexed'
              AND dc.tsvector_content @@ to_tsquery('simple', :tsquery)
              {perm} {kb_cond}
            ORDER BY score DESC
            LIMIT :limit
        """)
        params = {"tsquery": tsquery_str, "limit": top_k, "uid": user_id, **kb_params}
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        return [
            RetrievedChunk(
                id=row[0],
                content=row[1],
                document_title=row[2],
                document_id=row[3],
                score=float(row[4]),
            )
            for row in rows
        ]

    async def _like_search(
        self,
        query: str,
        user_id: str,
        perm: str,
        kb_id: str | None,
        kb_ids: list[str] | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """CJK 子串直接匹配（不依赖分词器，中文名搜索兜底）"""
        cjk_terms = re.findall(r"[一-鿿]{2,}", query)
        if not cjk_terms:
            return []
        kb_cond, kb_params = _get_kb_filter(kb_id, kb_ids)
        like_conds = " OR ".join("dc.content ILIKE :t{}".format(i) for i in range(len(cjk_terms)))
        params = {"uid": user_id, **kb_params}
        for i, term in enumerate(cjk_terms):
            params[f"t{i}"] = f"%{term}%"
        sql = text(f"""
            SELECT dc.id, dc.content, d.title, d.id AS document_id, 0.5 AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'indexed' AND ({like_conds})
              {perm} {kb_cond}
            LIMIT :limit
        """)
        params["limit"] = top_k
        try:
            result = await self.db.execute(sql, params)
            return [
                RetrievedChunk(
                    id=row[0],
                    content=row[1],
                    document_title=row[2],
                    document_id=row[3],
                    score=float(row[4]),
                )
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.debug(f"LIKE搜索失败: {e}")
            return []

    def _rrf_fusion(
        self,
        vector_results: list[RetrievedChunk],
        bm25_results: list[RetrievedChunk],
        k: int = 60,
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion"""
        score_map: dict[str, float] = {}
        chunk_map: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(vector_results):
            cid = str(chunk.id)
            score_map[cid] = score_map.get(cid, 0) + 1.0 / (k + rank + 1)
            chunk_map[cid] = chunk

        for rank, chunk in enumerate(bm25_results):
            cid = str(chunk.id)
            score_map[cid] = score_map.get(cid, 0) + 1.0 / (k + rank + 1)
            chunk_map[cid] = chunk

        sorted_ids = sorted(score_map, key=score_map.get, reverse=True)
        results = []
        for cid in sorted_ids:
            chunk = chunk_map[cid]
            chunk.score = score_map[cid]
            results.append(chunk)
        return results
