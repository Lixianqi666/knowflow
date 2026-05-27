"""P1: Rate limiting 行为测试"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, Request

from app.core.ratelimit import _check


def _make_request(ip: str = "127.0.0.1", auth: str = "") -> Request:
    """构造模拟 Request"""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", auth.encode())] if auth else [],
    }
    client = AsyncMock()
    client.host = ip
    req = Request(scope)
    req._client = client
    return req


@pytest.mark.asyncio
async def test_check_allows_within_limit(monkeypatch):
    """未超限时不应抛出异常"""
    mock_redis = AsyncMock()
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()

    monkeypatch.delenv("TESTING", raising=False)
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        await _check("test", 10, 60, "user:1")


@pytest.mark.asyncio
async def test_check_blocks_over_limit(monkeypatch):
    """超过限制时应抛出 429"""
    mock_redis = AsyncMock()
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=15)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()

    monkeypatch.delenv("TESTING", raising=False)
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await _check("chat", 15, 60, "user:1")
        assert exc_info.value.status_code == 429
        assert "频繁" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_skipped_in_testing_mode():
    """TESTING=1 时限流检查被跳过"""
    mock_redis = AsyncMock()
    with patch.dict(os.environ, {"TESTING": "1"}):
        with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
            await _check("chat", 1, 60, "user:1")
            mock_redis.zremrangebyscore.assert_not_called()
