"""P2: 缓存层单元测试"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache import cache_delete, cache_get, cache_set, make_cache_key


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """写入后读取应返回相同数据"""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value='{"key": "value"}')
    mock_redis.setex = AsyncMock()

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_set("test:key", {"key": "value"}, ttl=60)
        result = await cache_get("test:key")

    assert result == {"key": "value"}
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_miss_returns_none():
    """缓存未命中时返回 None"""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        result = await cache_get("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_cache_set_with_tags():
    """带 tags 写入应注册到 tag 集合"""
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.sadd = AsyncMock()
    mock_redis.expire = AsyncMock()

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_set("k", "v", ttl=120, tags=["tag1", "tag2"])

    assert mock_redis.sadd.call_count == 2
    assert mock_redis.expire.call_count == 2


@pytest.mark.asyncio
async def test_cache_delete_by_tag():
    """通过 tag 删除应清理所有关联 key"""
    mock_redis = AsyncMock()
    mock_redis.smembers = AsyncMock(return_value={"k1", "k2"})
    mock_redis.delete = AsyncMock()

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_delete("tag1")

    mock_redis.delete.assert_called_once_with("k1", "k2", "cache:tag:tag1")


@pytest.mark.asyncio
async def test_cache_delete_exact_key_fallback():
    """tag 无匹配时应回退到精确 key 删除"""
    mock_redis = AsyncMock()
    mock_redis.smembers = AsyncMock(return_value=set())
    mock_redis.exists = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock()

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_delete("exact:key")

    mock_redis.exists.assert_called_once_with("exact:key")
    mock_redis.delete.assert_called_once_with("exact:key")


def test_make_cache_key_deterministic():
    """相同参数应生成相同的缓存键"""
    k1 = make_cache_key("a", "b", 1)
    k2 = make_cache_key("a", "b", 1)
    assert k1 == k2
    assert k1.startswith("cache:")


def test_make_cache_key_different_args():
    """不同参数应生成不同的缓存键"""
    k1 = make_cache_key("a", "b")
    k2 = make_cache_key("a", "c")
    assert k1 != k2
