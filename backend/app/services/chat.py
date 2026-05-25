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
        try:
            async for event in self._do_stream(
                conversation_id, user_message, user_id, is_admin, template_id
            ):
                yield event
        except Exception as e:
            import logging

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

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    if has_context:
                        # 模板的 system_prompt 作为角色设定，RAG_SYSTEM 的规则作为强制约束
                        role = tmpl.system_prompt or "你是KnowFlow智能助手。"
                        system_prompt = f"{role}\n\n{RAG_SYSTEM}"
                    else:
                        sp = tmpl.no_context_prompt
                        if sp:
                            system_prompt = sp
            except Exception:
                pass

        context_text = (
            "\n\n---\n\n".join(f"[{c.document_title}]\n{c.content}" for c in chunks)
            if chunks
            else "未找到相关文档内容。"
        )

        if not has_context:
            messages = build_messages(system_prompt, history=history_msgs, question=search_query)
        else:
            messages = build_messages(
                system_prompt, context=context_text, history=history_msgs, question=search_query
            )

        # 4. 流式生成（检测 JSON 边界后截断）
        _t1 = time.time()
        full_response = ""
        streamed_text = ""  # 实际发送给前端的完整文本
        json_started = False
        async for chunk in llm_service.stream_chat(messages):
            if json_started:
                full_response += chunk
                continue
            full_response += chunk
            # 检测 JSON 块开始（```json 或 单独一行的 {）
            if "```json" in full_response or re.search(r"\n\s*\{", full_response):
                json_started = True
                # 只输出 JSON 之前的文本
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

        # 5. 结构化解析（仅用于发送 structured 事件，不影响持久化文本）
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

        # 持久化文本 = 实际发送给前端的文本（清理多余空行即可）
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
            )
        )
        await self.db.flush()
        yield json.dumps({"type": "done"}, ensure_ascii=False)

        # 7. 自动标题
        try:
            await self._auto_title(conversation_id, user_message)
        except Exception:
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
