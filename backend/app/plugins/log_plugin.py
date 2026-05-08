"""内置日志插件——记录每次检索和对话的统计信息"""

import logging

from app.core.hooks import register
from app.core.metrics import documents_indexed_total, llm_requests_total
from app.core.plugins import BasePlugin, register_plugin

logger = logging.getLogger("app")


@register_plugin
class LogPlugin(BasePlugin):
    name = "log_stats"
    description = "记录检索和对话耗时统计"

    async def on_load(self):
        register("after_retrieval", self.name, self._after_retrieval)
        register("after_llm", self.name, self._after_llm)
        logger.warning("插件加载成功: log_stats")

    async def _after_retrieval(self, query: str, chunk_count: int, elapsed: float, **kwargs):
        logger.info(f"[PLUGIN] 检索: query={query[:30]} chunks={chunk_count} time={elapsed:.2f}s")

    async def _after_llm(self, query: str, token_count: int, elapsed: float, **kwargs):
        llm_requests_total.labels(operation="chat").inc()
        logger.info(f"[PLUGIN] LLM: query={query[:30]} tokens={token_count} time={elapsed:.2f}s")
