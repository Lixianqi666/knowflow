import json
import logging
from typing import AsyncGenerator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm import llm_service
from app.core.prompts import NO_CONTEXT_SYSTEM, RAG_SYSTEM, build_messages, parse_rag_response
from app.models.agent import Agent
from app.models.agent_session import AgentMessage, AgentSession
from app.services.retrieval import RetrievalService, RetrievedChunk
from app.services.rewriter import rewrite as rewrite_query

logger = logging.getLogger(__name__)


class AgentService:
    MAX_HISTORY = 10

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval = RetrievalService(db)

    async def stream_chat(
        self,
        session_id: str,
        user_message: str,
        user_id: str,
        is_admin: bool = False,
    ) -> AsyncGenerator[str, None]:
        session = await self.db.get(AgentSession, session_id)
        if not session:
            raise ValueError("会话不存在")
        agent = await self.db.get(Agent, session.agent_id)
        if not agent or not agent.is_active:
            raise ValueError("Agent 不存在或已停用")

        top_k = agent.top_k or 5
        threshold = (agent.threshold or 30) / 100.0
        rerank_top_k = agent.rerank_top_k or 3
        agent_kb_ids = agent.knowledge_base_ids or []
        system_prompt = agent.system_prompt or ""

        # 1. 历史消息
        history_rows = await self._get_history(session_id)
        history_msgs: list[dict] = []
        for msg in history_rows[-self.MAX_HISTORY:]:
            history_msgs.append({"role": "user" if msg.role == "user" else "assistant", "content": msg.content})

        # 2. 查询改写 + 检索
        history_summary = " ".join(m["content"][:60] for m in history_msgs[-4:])
        search_query = await rewrite_query(user_message, history_summary)

        chunks: list[RetrievedChunk] = []
        if agent_kb_ids:
            for kb_id in agent_kb_ids:
                try:
                    kbs = await self.retrieval.search(
                        search_query, user_id, is_admin=is_admin,
                        top_k=top_k, threshold=threshold, rerank_top_k=rerank_top_k, kb_id=kb_id,
                    )
                    chunks.extend(kbs)
                except Exception as e:
                    logger.debug(f"Agent 知识库 {kb_id} 检索失败: {e}")
            seen_ids = set()
            unique_chunks = []
            for c in chunks:
                cid = str(c.id)
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    unique_chunks.append(c)
            chunks = unique_chunks[:top_k]
        else:
            chunks = await self.retrieval.search(
                search_query, user_id, is_admin=is_admin,
                top_k=top_k, threshold=threshold, rerank_top_k=rerank_top_k,
            )

        sources = [
            {"title": c.document_title, "content": c.content[:200], "score": round(c.score, 3),
             "chunk_id": str(c.id), "document_id": str(c.document_id)}
            for c in chunks
        ]
        yield json.dumps({"type": "sources", "data": sources}, ensure_ascii=False)

        # 3. 选择 prompt + 构造消息
        has_context = len(chunks) > 0 and any(c.score > 0 for c in chunks)
        context_text = (
            "\n\n---\n\n".join(f"[{c.document_title}]\n{c.content}" for c in chunks)
            if chunks else "未找到相关文档内容。"
        )

        if system_prompt:
            if has_context:
                messages = build_messages(system_prompt, context=context_text, history=history_msgs, question=search_query)
            else:
                messages = build_messages(NO_CONTEXT_SYSTEM, history=history_msgs, question=search_query)
        else:
            if has_context:
                messages = build_messages(RAG_SYSTEM, context=context_text, history=history_msgs, question=search_query)
            else:
                messages = build_messages(NO_CONTEXT_SYSTEM, history=history_msgs, question=search_query)

        # 4. 流式生成
        full_response = ""
        async for chunk in llm_service.stream_chat(messages):
            full_response += chunk
            yield json.dumps({"type": "token", "data": chunk}, ensure_ascii=False)

        # 5. 结构化解析
        if has_context:
            try:
                parsed = parse_rag_response(full_response)
                if parsed:
                    yield json.dumps({
                        "type": "structured",
                        "data": {"answer": parsed.answer, "sources": parsed.sources,
                                 "confidence": parsed.confidence, "has_sufficient_context": parsed.has_sufficient_context},
                    }, ensure_ascii=False)
            except Exception:
                pass

        # 6. 持久化
        self.db.add(AgentMessage(session_id=session_id, role="user", content=user_message))
        self.db.add(AgentMessage(session_id=session_id, role="assistant", content=full_response, sources=sources))
        await self.db.flush()
        yield json.dumps({"type": "done"}, ensure_ascii=False)

        # 7. 自动标题
        try:
            await self._auto_title(session_id, agent.name, user_message)
        except Exception:
            pass

    async def _auto_title(self, session_id: str, agent_name: str, user_message: str) -> None:
        session = await self.db.get(AgentSession, session_id)
        if not session or not _is_default_title(session.title):
            return
        count = await self.db.scalar(select(func.count()).where(AgentMessage.session_id == session_id))
        if count and count > 2:
            return
        try:
            from litellm import completion
            resp = completion(
                model=settings.LLM_MODEL,
                messages=[{"role": "system", "content": "根据用户的提问，生成 4-6 个字的简短标题，只输出标题本身，不要标点。"},
                          {"role": "user", "content": user_message}],
                temperature=0.1, max_tokens=20,
            )
            title = resp.choices[0].message.content.strip().strip("\"'").strip()
            if title and len(title) <= 20:
                session.title = title
        except Exception as e:
            logger.debug(f"自动标题失败: {e}")

    async def _get_history(self, session_id: str) -> list[AgentMessage]:
        result = await self.db.execute(
            select(AgentMessage).where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.desc()).limit(self.MAX_HISTORY)
        )
        return list(reversed(result.scalars().all()))


def _is_default_title(title: str | None) -> bool:
    return not title or title in ("新会话", "") or len(title) >= 30
