import logging

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from FlagEmbedding import FlagReranker
        except ImportError:
            raise RuntimeError(
                "FlagEmbedding 未安装，请执行: pip install FlagEmbedding\n"
                "（依赖 PyTorch ~2GB，首次加载模型约 1-2 分钟）"
            )
        logger.info("加载 bge-reranker-base 模型...")
        _model = FlagReranker("BAAI/bge-reranker-base", use_fp16=True)
        logger.info("Reranker 模型加载完成")
    return _model


class RerankerService:
    """基于 FlagEmbedding 的 bge-reranker-base 精排服务"""

    async def rerank(self, query: str, chunks: list, top_k: int = 3) -> list:
        if not chunks:
            return []
        if not settings.RERANKER_ENABLED:
            # 未启用 reranker 时按 score 降序取 top_k，确保 LIKE 搜索（score=0.5）不被丢弃
            chunks.sort(key=lambda c: c.score, reverse=True)
            return chunks[:top_k]

        try:
            model = _get_model()
            pairs = [[query, c.content] for c in chunks]
            scores = model.compute_score(pairs, normalize=True)
            if not isinstance(scores, list):
                scores = [scores]
            for i, score in enumerate(scores):
                chunks[i].score = float(score)
            chunks.sort(key=lambda c: c.score, reverse=True)
        except Exception as e:
            logger.warning(f"Rerank 失败，降级为原始排序: {e}")

        return chunks[:top_k]


reranker_service = RerankerService()
