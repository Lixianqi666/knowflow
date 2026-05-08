import json
import logging
import re
from typing import AsyncGenerator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.hooks import trigger as trigger_hooks
from app.core.llm import llm_service
from app.core.prompts import NO_CONTEXT_SYSTEM, RAG_SYSTEM, build_messages, parse_rag_response
from app.models.conversation import Conversation, Message
from app.models.prompt_template import PromptTemplate
from app.services.retrieval import RetrievalService
from app.services.rewriter import rewrite as rewrite_query

logger = logging.getLogger(__name__)


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
    ) -> AsyncGenerator[str, None]:
        top_k = settings.RETRIEVAL_TOP_K
        threshold = settings.RETRIEVAL_THRESHOLD
        rerank_top_k = settings.RETRIEVAL_RERANK_TOP_K
        system_prompt = RAG_SYSTEM

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    top_k = tmpl.top_k or settings.RETRIEVAL_TOP_K
                    threshold = (tmpl.threshold or 30) / 100.0
                    rerank_top_k = tmpl.rerank_top_k or settings.RETRIEVAL_RERANK_TOP_K
            except Exception:
                pass

        # 1. 历史消息
        history_rows = await self._get_history(conversation_id)
        history_msgs: list[dict] = []
        for msg in history_rows[-self.MAX_HISTORY:]:
            history_msgs.append({"role": "user" if msg.role == "user" else "assistant", "content": msg.content})

        # 2. 查询改写 + 检索
        import time

        history_summary = " ".join(m["content"][:60] for m in history_msgs[-4:])
        search_query = await rewrite_query(user_message, history_summary)
        _t0 = time.time()
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
        await trigger_hooks("after_retrieval", query=user_message, chunk_count=len(chunks), elapsed=time.time() - _t0)

        # 3. 选择 prompt + 构造消息
        has_context = len(chunks) > 0 and any(c.score > 0 for c in chunks)
        if not has_context:
            system_prompt = NO_CONTEXT_SYSTEM

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    sp = tmpl.context_prompt if has_context else tmpl.no_context_prompt
                    if sp:
                        system_prompt = sp
            except Exception:
                pass

        context_text = (
            "\n\n---\n\n".join(f"[{c.document_title}]\n{c.content}" for c in chunks)
            if chunks else "未找到相关文档内容。"
        )

        if system_prompt is NO_CONTEXT_SYSTEM:
            messages = build_messages(system_prompt, history=history_msgs, question=search_query)
        else:
            messages = build_messages(system_prompt, context=context_text, history=history_msgs, question=search_query)

        # 4. 流式生成（检测 JSON 边界后截断）
        _t1 = time.time()
        full_response = ""
        json_started = False
        async for chunk in llm_service.stream_chat(messages):
            if json_started:
                full_response += chunk
                continue
            full_response += chunk
            # 检测 JSON 块开始（```json 或 单独一行的 {）
            if '```json' in full_response or re.search(r'\n\s*\{', full_response):
                json_started = True
                # 只输出 JSON 之前的文本
                if '```json' in full_response:
                    text_part = full_response.split('```json')[0]
                else:
                    text_part = re.sub(r'\n\s*\{.*$', '', full_response, count=1)
                # 重发截断后的最终文本
                if text_part.strip():
                    yield json.dumps({"type": "token", "data": text_part}, ensure_ascii=False)
                continue
            yield json.dumps({"type": "token", "data": chunk}, ensure_ascii=False)

        # 5. 结构化解析
        display_text = full_response
        if has_context:
            try:
                parsed = parse_rag_response(full_response)
                if parsed:
                    yield json.dumps({
                        "type": "structured",
                        "data": {"answer": parsed.answer, "sources": parsed.sources,
                                 "confidence": parsed.confidence, "has_sufficient_context": parsed.has_sufficient_context},
                    }, ensure_ascii=False)
                    display_text = parsed.answer
            except Exception:
                pass

        # 清理显示文本
        display_text = re.sub(r'```json[\s\S]*?```', '', display_text)
        display_text = re.sub(r'\s*\{[\s\S]*"answer"[\s\S]*"sources"[\s\S]*\}\s*$', '', display_text)
        display_text = re.sub(r'\[来源:\s*[^\]]+\]', '', display_text)
        display_text = re.sub(r'\n{3,}', '\n\n', display_text).strip()

        await trigger_hooks("after_llm", query=user_message, token_count=len(full_response) // 2, elapsed=time.time() - _t1)

        # 6. 持久化
        self.db.add(Message(conversation_id=conversation_id, role="user", content=user_message))
        self.db.add(Message(conversation_id=conversation_id, role="assistant", content=display_text, sources=sources))
        await self.db.flush()
        yield json.dumps({"type": "done"}, ensure_ascii=False)

        # 7. 自动标题
        try:
            await self._auto_title(conversation_id, user_message)
        except Exception:
            pass

    async def _auto_title(self, conversation_id: str, user_message: str) -> None:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv or not _is_default_title(conv.title):
            return
        count = await self.db.scalar(select(func.count()).where(Message.conversation_id == conversation_id))
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
                conv.title = title
        except Exception as e:
            logger.debug(f"自动标题失败: {e}")

    async def _get_history(self, conversation_id: str) -> list[Message]:
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc()).limit(self.MAX_HISTORY)
        )
        return list(reversed(result.scalars().all()))


def _is_default_title(title: str | None) -> bool:
    return not title or title in ("新对话", "") or len(title) >= 30
