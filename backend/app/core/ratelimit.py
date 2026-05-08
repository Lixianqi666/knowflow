import os
import time

import redis.asyncio as aioredis
from fastapi import HTTPException, Request

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        from app.config import settings

        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def _key_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _key_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.core.security import decode_token

            return f"user:{decode_token(auth[7:])}"
        except Exception:
            pass
    return _key_ip(request)


async def chat_rate_limit(request: Request):
    """对话接口限流: 每分钟最多 15 次"""
    await _check("chat", 15, 60, _key_user(request))


async def auth_rate_limit(request: Request):
    """认证接口限流: 每分钟最多 5 次"""
    await _check("auth", 5, 60, _key_ip(request))


async def upload_rate_limit(request: Request):
    """上传接口限流: 每小时最多 30 次"""
    await _check("upload", 30, 3600, _key_user(request))


async def _check(name: str, limit: int, window: int, key: str):
    if os.getenv("TESTING"):
        return
    r = await get_redis()
    now = time.time()
    redis_key = f"ratelimit:{name}:{key}"
    await r.zremrangebyscore(redis_key, 0, now - window)
    count = await r.zcard(redis_key)
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(window)},
        )
    await r.zadd(redis_key, {str(now): now})
    await r.expire(redis_key, window)
