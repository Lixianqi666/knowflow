import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


def init_langfuse() -> bool:
    """初始化 Langfuse 环境变量，通过 litellm 原生回调集成"""
    if not settings.LANGFUSE_PUBLIC_KEY:
        return False
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
    os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST
    os.environ["LANGFUSE_FLUSH_INTERVAL"] = "5"
    logger.info(f"Langfuse 已启用: {settings.LANGFUSE_HOST}")
    return True
