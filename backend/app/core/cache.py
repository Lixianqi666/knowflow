"""Redis 缓存层"""

import json
import hashlib
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


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """写入缓存，默认 TTL 5 分钟"""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception as e:
        logger.debug(f"缓存写入失败: {e}")


async def cache_delete(pattern: str) -> None:
    """删除匹配模式的缓存"""
    try:
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception as e:
        logger.debug(f"缓存删除失败: {e}")


def make_cache_key(*args) -> str:
    """生成缓存键"""
    raw = ":".join(str(a) for a in args)
    return f"cache:{hashlib.md5(raw.encode()).hexdigest()}"
