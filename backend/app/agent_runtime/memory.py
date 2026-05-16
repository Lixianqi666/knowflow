from typing import Any


class ShortTermMemory:
    """短期记忆：限制进入上下文的最近消息。"""

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages

    def select(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return messages[-self.max_messages :]


class LongTermKnowledge:
    """长期知识：复用现有知识库检索服务。"""

    def __init__(self, retrieval_service):
        self.retrieval_service = retrieval_service

    async def search(
        self,
        query: str,
        user_id: str,
        is_admin: bool = False,
        top_k: int = 5,
        kb_id: str | None = None,
    ):
        return await self.retrieval_service.search(
            query,
            user_id,
            is_admin=is_admin,
            top_k=top_k,
            kb_id=kb_id,
        )
