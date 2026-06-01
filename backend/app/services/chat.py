import json
import logging
import re
import time
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.hooks import trigger as trigger_hooks
from app.core.llm import llm_service
from app.core.prompts import (
    NO_CONTEXT_SYSTEM,
    RAG_SYSTEM,
    RetrievedChunk,
    build_messages,
    format_goal_context,
    format_retrieved_context,
    parse_rag_response,
)
from app.models.conversation import Conversation, Message
from app.models.prompt_template import PromptTemplate
from app.services.retrieval import RetrievalService
from app.services.rewriter import rewrite as rewrite_query

logger = logging.getLogger(__name__)

GOAL_UPDATE_PROMPT = """分析以下对话，更新目标状态。返回 JSON：
{{"goal_summary": "进展摘要，一句话", "missing_info": ["缺失信息1"], "goal_status": "active|blocked|done"}}

规则：
- goal_status: active=进行中, blocked=缺少关键信息, done=已完成
- missing_info: 列出还需要用户提供的关键信息
- 只返回 JSON，不要其他内容

当前目标：{goal}
对话历史：
{history}
用户最新消息：{user_message}
助手回复：{assistant_reply}"""


class ChatService:
    MAX_HISTORY = 10

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval = RetrievalService(db)

    async def stream_chat(
        self,
        conversation_id: str,
        user_message: str,
        user_id: str,
        is_admin: bool = False,
        template_id: str | None = None,
        goal: str | None = None,
        knowledge_base_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        try:
            async for event in self._do_stream(
                conversation_id, user_message, user_id, is_admin, template_id, goal, knowledge_base_id
            ):
                yield event
        except Exception as e:
            logging.getLogger(__name__).exception(f"stream_chat异常: {e}")
            msg = str(e).lower()
            if "insufficient" in msg or "balance" in msg:
                friendly = "LLM 服务余额不足，请充值后再试"
            elif "rate" in msg or "limit" in msg or "429" in msg:
                friendly = "请求过于频繁，请稍后再试"
            elif "timeout" in msg or "timed out" in msg:
                friendly = "LLM 服务响应超时，请稍后再试"
            elif "connect" in msg or "refused" in msg:
                friendly = "LLM 服务连接失败，请稍后再试"
            elif "auth" in msg or "api_key" in msg or "unauthorized" in msg:
                friendly = "LLM API 密钥无效，请检查配置"
            else:
                friendly = "服务内部错误，请稍后重试"
            yield json.dumps({"type": "error", "data": friendly}, ensure_ascii=False)

    async def _do_stream(
        self,
        conversation_id: str,
        user_message: str,
        user_id: str,
        is_admin: bool = False,
        template_id: str | None = None,
        goal: str | None = None,
        knowledge_base_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        top_k = settings.RETRIEVAL_TOP_K
        threshold = settings.RETRIEVAL_THRESHOLD
        rerank_top_k = settings.RETRIEVAL_RERANK_TOP_K
        system_prompt = RAG_SYSTEM
        tmpl = None
        no_evidence_policy = "strict"

        # 获取对话并处理 goal
        conv = await self.db.get(Conversation, conversation_id)
        if not conv:
            raise ValueError("对话不存在")

        if goal and not conv.goal:
            conv.goal = goal
            await self.db.flush()

        # 优先使用 KB rag_config
        if knowledge_base_id:
            try:
                from app.models.knowledge_base import KnowledgeBase
                from app.services.rag_config import get_effective_rag_config

                kb = await self.db.get(KnowledgeBase, knowledge_base_id)
                if kb:
                    rc = get_effective_rag_config(kb.rag_config)
                    top_k = rc.get("top_k", top_k)
                    threshold = rc.get("score_threshold", threshold)
                    no_evidence_policy = rc.get("no_evidence_policy", "strict")
                    # chunk_size/chunk_overlap 用于索引阶段，聊天阶段不需要
            except Exception:
                pass

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    top_k = tmpl.top_k or top_k
                    threshold = (tmpl.threshold or 30) / 100.0 if tmpl.threshold else threshold
                    rerank_top_k = tmpl.rerank_top_k or settings.RETRIEVAL_RERANK_TOP_K
            except Exception:
                pass

        # 1. 历史消息
        history_rows = await self._get_history(conversation_id)
        history_msgs: list[dict] = []
        for msg in history_rows[-self.MAX_HISTORY :]:
            history_msgs.append(
                {"role": "user" if msg.role == "user" else "assistant", "content": msg.content}
            )

        # 2. 先持久化 user 消息，确保 LLM 失败时也有记录
        self.db.add(Message(conversation_id=conversation_id, role="user", content=user_message))
        await self.db.flush()

        # 3. 查询改写 + 检索
        history_summary = " ".join(m["content"][:60] for m in history_msgs[-4:])
        search_query = await rewrite_query(user_message, history_summary)
        _t0 = time.time()
        chunks = await self.retrieval.search(
            search_query,
            user_id,
            is_admin=is_admin,
            top_k=top_k,
            threshold=threshold,
            rerank_top_k=rerank_top_k,
        )
        sources = [
            {
                "title": c.document_title,
                "content": c.content[:200],
                "score": round(c.score, 3),
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
            }
            for c in chunks
        ]
        # 批量查询 chunk metadata（用于 page/section 定位）
        chunk_ids = [c.id for c in chunks if c.score > 0]
        chunk_meta_map: dict[str, dict] = {}
        if chunk_ids:
            from app.models.document import DocumentChunk as DC

            meta_result = await self.db.execute(
                select(DC.id, DC.metadata_).where(DC.id.in_(chunk_ids))
            )
            chunk_meta_map = {str(row[0]): (row[1] or {}) for row in meta_result.fetchall()}

        citations = []
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
            entry: dict = {
                "index": i + 1,
                "document_id": str(c.document_id),
                "document_title": c.document_title,
                "chunk_id": cid,
                "snippet": c.content[:300],
                "score": round(c.score, 3),
                "locator": locator,
            }
            if page is not None:
                entry["page"] = int(page) if isinstance(page, (int, float, str)) and str(page).isdigit() else page
            if section:
                entry["section"] = str(section)
            citations.append(entry)
        yield json.dumps({"type": "sources", "data": sources}, ensure_ascii=False)
        await trigger_hooks(
            "after_retrieval",
            query=user_message,
            chunk_count=len(chunks),
            elapsed=time.time() - _t0,
        )

        # 3. 选择 prompt + 构造消息
        has_context = len(chunks) > 0 and any(c.score > 0 for c in chunks)
        if not has_context:
            system_prompt = NO_CONTEXT_SYSTEM

        if tmpl and tmpl.is_active:
            if has_context:
                role = tmpl.system_prompt or "你是KnowFlow智能助手。"
                system_prompt = f"{role}\n\n{RAG_SYSTEM}"
            else:
                sp = tmpl.no_context_prompt
                if sp:
                    system_prompt = sp

        context_text = format_retrieved_context(
            [RetrievedChunk(title=c.document_title, content=c.content) for c in chunks]
        )

        # 构造 goal_context（独立于检索文档）
        goal_context = None
        if conv.goal:
            goal_context = format_goal_context(
                goal=conv.goal,
                goal_summary=conv.goal_summary or "",
                missing_info=conv.missing_info or [],
            )

        if not has_context:
            messages = build_messages(
                system_prompt, history=history_msgs, question=search_query, goal_context=goal_context
            )
        else:
            messages = build_messages(
                system_prompt,
                context=context_text,
                history=history_msgs,
                question=search_query,
                goal_context=goal_context,
            )

        # 4. 流式生成（检测 JSON 边界后截断）
        _t1 = time.time()
        full_response = ""
        streamed_text = ""
        json_started = False
        async for chunk in llm_service.stream_chat(messages):
            if json_started:
                full_response += chunk
                continue
            full_response += chunk
            if "```json" in full_response or re.search(r"\n\s*\{", full_response):
                json_started = True
                if "```json" in full_response:
                    text_part = full_response.split("```json")[0]
                else:
                    text_part = re.sub(r"\n\s*\{.*$", "", full_response, count=1)
                if text_part.strip():
                    streamed_text = text_part
                    yield json.dumps({"type": "token", "data": text_part}, ensure_ascii=False)
                continue
            streamed_text += chunk
            yield json.dumps({"type": "token", "data": chunk}, ensure_ascii=False)

        # 5. 结构化解析
        if has_context:
            try:
                parsed = parse_rag_response(full_response)
                if parsed:
                    yield json.dumps(
                        {
                            "type": "structured",
                            "data": {
                                "answer": parsed.answer,
                                "sources": parsed.sources,
                                "confidence": parsed.confidence,
                                "has_sufficient_context": parsed.has_sufficient_context,
                            },
                        },
                        ensure_ascii=False,
                    )
            except Exception:
                pass

        display_text = re.sub(r"\[来源:\s*[^\]]+\]", "", streamed_text)
        display_text = re.sub(r"\n{3,}", "\n\n", display_text).strip()

        await trigger_hooks(
            "after_llm",
            query=user_message,
            token_count=len(full_response) // 2,
            elapsed=time.time() - _t1,
        )

        # 6. 持久化 assistant 回复
        self.db.add(
            Message(
                conversation_id=conversation_id,
                role="assistant",
                content=display_text,
                sources=sources,
                citations=citations,
            )
        )
        await self.db.flush()
        yield json.dumps({"type": "done"}, ensure_ascii=False)

        # 7. 异步更新 goal 状态（不阻塞主流程）
        if conv.goal:
            try:
                await self._update_goal_state(conv, user_message, display_text, history_msgs)
            except Exception:
                pass

        # 8. 自动标题
        try:
            await self._auto_title(conversation_id, user_message)
        except Exception:
            pass

    async def _update_goal_state(
        self,
        conv: Conversation,
        user_message: str,
        assistant_reply: str,
        history: list[dict],
    ) -> None:
        """调用 LLM 更新 goal_summary / missing_info / goal_status"""
        history_text = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:100]}"
            for m in history[-6:]
        )
        prompt = GOAL_UPDATE_PROMPT.format(
            goal=conv.goal,
            history=history_text,
            user_message=user_message[:200],
            assistant_reply=assistant_reply[:200],
        )
        try:
            result = await llm_service.complete(
                [{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
                timeout=10,
            )
            data = json.loads(result)
            if isinstance(data, dict):
                conv.goal_summary = data.get("goal_summary", conv.goal_summary)
                missing = data.get("missing_info")
                if isinstance(missing, list):
                    conv.missing_info = missing
                status = data.get("goal_status")
                if status in ("active", "blocked", "done"):
                    conv.goal_status = status
        except (json.JSONDecodeError, Exception):
            pass

    async def _auto_title(self, conversation_id: str, user_message: str) -> None:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv:
            return
        from app.services.common import auto_generate_title

        await auto_generate_title(self.db, conv, user_message, Message, "conversation_id")

    async def _get_history(self, conversation_id: str) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(self.MAX_HISTORY)
        )
        return list(reversed(result.scalars().all()))
