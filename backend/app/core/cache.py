"""Redis 缓存层"""

import hashlib
import json
import logging
from typing import Any

from app.core.ratelimit import get_redis

logger = logging.getLogger(__name__)


async def cache_get(key: str) -> Any | None:
    """从缓存获取数据"""
    try:
        r = await get_redis()
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"缓存读取失败: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 300, tags: list[str] | None = None) -> None:
    """写入缓存，默认 TTL 5 分钟。tags 用于分组失效。"""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        # 注册到 tag 集合，便于批量失效
        if tags:
            for tag in tags:
                await r.sadd(f"cache:tag:{tag}", key)
                await r.expire(f"cache:tag:{tag}", ttl)
    except Exception as e:
        logger.debug(f"缓存写入失败: {e}")


async def cache_delete(pattern: str) -> None:
    """删除匹配模式的缓存（精确 key 或 tag 集合）"""
    try:
        r = await get_redis()
        # 优先从 tag 集合中获取 key
        tag_key = f"cache:tag:{pattern}"
        keys = await r.smembers(tag_key)
        if keys:
            await r.delete(*keys, tag_key)
        else:
            # 兜底：精确匹配删除
            exists = await r.exists(pattern)
            if exists:
                await r.delete(pattern)
    except Exception as e:
        logger.debug(f"缓存删除失败: {e}")


def make_cache_key(*args) -> str:
    """生成缓存键"""
    raw = ":".join(str(a) for a in args)
    return f"cache:{hashlib.md5(raw.encode()).hexdigest()}"
