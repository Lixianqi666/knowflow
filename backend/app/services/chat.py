import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.hooks import trigger as trigger_hooks
from app.core.llm import llm_service
from app.core.prompts import NO_CONTEXT_PROMPT, RAG_PROMPT, rag_parser
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
        # 0. 加载 Pipeline 参数
        top_k = settings.RETRIEVAL_TOP_K
        threshold = settings.RETRIEVAL_THRESHOLD
        rerank_top_k = settings.RETRIEVAL_RERANK_TOP_K
        cur_prompt = RAG_PROMPT

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    top_k = tmpl.top_k or settings.RETRIEVAL_TOP_K
                    threshold = (tmpl.threshold or 30) / 100.0
                    rerank_top_k = tmpl.rerank_top_k or settings.RETRIEVAL_RERANK_TOP_K
            except Exception:
                pass

        # 1. 获取历史消息
        history_rows = await self._get_history(conversation_id)
        history_msgs = []
        for msg in history_rows[-self.MAX_HISTORY :]:
            if msg.role == "user":
                history_msgs.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history_msgs.append(AIMessage(content=msg.content))

        # 2. 查询改写 + 检索（一次检索，结果同时用于 sources 和 LLM 上下文）
        import time

        history_summary = " ".join(m.content[:60] for m in history_msgs[-4:])
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

        # 3. 选择 Prompt
        has_context = len(chunks) > 0 and any(c.score > 0 for c in chunks)
        if not has_context:
            cur_prompt = NO_CONTEXT_PROMPT

        if template_id:
            try:
                tmpl = await self.db.get(PromptTemplate, template_id)
                if tmpl and tmpl.is_active:
                    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

                    system = tmpl.context_prompt if has_context else tmpl.no_context_prompt
                    if system:
                        cur_prompt = ChatPromptTemplate.from_messages(
                            [
                                ("system", system),
                                MessagesPlaceholder("history"),
                                ("human", "{question}"),
                            ]
                        )
            except Exception:
                pass

        # 4. 流式生成（直接用已检索结果，绕开 ChatLiteLLM 兼容问题）
        _t1 = time.time()
        context_text = (
            "\n\n---\n\n".join(f"[{c.document_title}]\n{c.content}" for c in chunks)
            if chunks
            else "未找到相关文档内容。"
        )
        formatted = await cur_prompt.aformat_messages(
            context=context_text,
            history=history_msgs,
            question=search_query,
        )
        _role_map = {"human": "user", "ai": "assistant"}
        messages = [
            {"role": _role_map.get(m.type, m.type), "content": m.content} for m in formatted
        ]
        full_response = ""
        async for chunk in llm_service.stream_chat(messages):
            full_response += chunk
            yield json.dumps({"type": "token", "data": chunk}, ensure_ascii=False)

        # 5. 结构化解析
        if has_context:
            try:
                parsed = rag_parser.parse(full_response)
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

        await trigger_hooks(
            "after_llm",
            query=user_message,
            token_count=len(full_response) // 2,
            elapsed=time.time() - _t1,
        )

        # 6. 持久化
        self.db.add(Message(conversation_id=conversation_id, role="user", content=user_message))
        self.db.add(
            Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
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
        if not conv or not _is_default_title(conv.title):
            return
        count = await self.db.scalar(
            select(func.count()).where(Message.conversation_id == conversation_id)
        )
        if count and count > 2:
            return
        try:
            from litellm import completion

            resp = completion(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "根据用户的提问，生成 4-6 个字的简短标题，只输出标题本身，不要标点。",
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=20,
            )
            title = resp.choices[0].message.content.strip().strip("\"'").strip()
            if title and len(title) <= 20:
                conv.title = title
        except Exception as e:
            logger.debug(f"自动标题失败: {e}")

    async def _get_history(self, conversation_id: str) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(self.MAX_HISTORY)
        )
        return list(reversed(result.scalars().all()))


def _is_default_title(title: str | None) -> bool:
    return not title or title in ("新对话", "") or len(title) >= 30
