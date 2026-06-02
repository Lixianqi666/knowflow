"""文档索引 Redis 幂等锁测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.indexing import (
    _FALLBACK_TOKEN,
    _RELEASE_LUA,
    _acquire_lock,
    _index_with_lock,
    _release_lock,
    clear_index_lock,
)


@pytest.mark.asyncio
async def test_acquire_lock_success():
    """获取锁成功时返回 token（非 '1'）"""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        token = await _acquire_lock("doc-123")
    assert token is not None
    assert token != "1"
    assert len(token) == 32  # uuid4 hex
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "lock:index_document:doc-123"
    assert call_args[0][1] == token
    assert call_args[1]["nx"] is True
    assert call_args[1]["ex"] == 600


@pytest.mark.asyncio
async def test_acquire_lock_already_held():
    """锁已被持有时返回 None"""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        result = await _acquire_lock("doc-123")
    assert result is None


@pytest.mark.asyncio
async def test_acquire_lock_redis_error_fallback():
    """Redis 异常时返回 fallback token"""
    mock_redis = AsyncMock()
    mock_redis.set.side_effect = ConnectionError("Redis down")
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        result = await _acquire_lock("doc-123")
    assert result == _FALLBACK_TOKEN


@pytest.mark.asyncio
async def test_release_fallback_token_no_redis():
    """释放 fallback token 时不调用 Redis"""
    mock_redis = AsyncMock()
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        await _release_lock("doc-123", _FALLBACK_TOKEN)
    mock_redis.eval.assert_not_called()
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_release_normal_token_uses_lua():
    """释放正常 token 时用 Lua 脚本原子比较后删除"""
    mock_redis = AsyncMock()
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        await _release_lock("doc-123", "abc123")
    mock_redis.eval.assert_called_once_with(_RELEASE_LUA, 1, "lock:index_document:doc-123", "abc123")


@pytest.mark.asyncio
async def test_release_does_not_call_delete_directly():
    """release 不直接调用 delete，只通过 eval"""
    mock_redis = AsyncMock()
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        await _release_lock("doc-123", "abc123")
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_index_with_lock_calls_index_with_token():
    """获取锁成功时调用 _index，并用同一个 token 释放"""
    fake_token = "tok_abc"
    with (
        patch("app.tasks.indexing._acquire_lock", return_value=fake_token) as mock_acquire,
        patch("app.tasks.indexing._index", new_callable=AsyncMock) as mock_index,
        patch("app.tasks.indexing._release_lock", new_callable=AsyncMock) as mock_release,
    ):
        await _index_with_lock("doc-123")
    mock_acquire.assert_called_once_with("doc-123")
    mock_index.assert_called_once_with("doc-123")
    mock_release.assert_called_once_with("doc-123", fake_token)


@pytest.mark.asyncio
async def test_index_with_lock_skips_when_none():
    """获取锁返回 None 时不调用 _index 和 release"""
    with (
        patch("app.tasks.indexing._acquire_lock", return_value=None) as mock_acquire,
        patch("app.tasks.indexing._index", new_callable=AsyncMock) as mock_index,
        patch("app.tasks.indexing._release_lock", new_callable=AsyncMock) as mock_release,
    ):
        await _index_with_lock("doc-123")
    mock_acquire.assert_called_once_with("doc-123")
    mock_index.assert_not_called()
    mock_release.assert_not_called()


@pytest.mark.asyncio
async def test_index_with_lock_releases_on_error():
    """_index 抛异常时仍用同一个 token 释放锁"""
    fake_token = "tok_err"
    with (
        patch("app.tasks.indexing._acquire_lock", return_value=fake_token),
        patch("app.tasks.indexing._index", new_callable=AsyncMock, side_effect=ValueError("fail")),
        patch("app.tasks.indexing._release_lock", new_callable=AsyncMock) as mock_release,
    ):
        with pytest.raises(ValueError, match="fail"):
            await _index_with_lock("doc-123")
    mock_release.assert_called_once_with("doc-123", fake_token)


@pytest.mark.asyncio
async def test_index_with_lock_fallback_still_indexes():
    """Redis 异常 fallback 时仍调用 _index"""
    with (
        patch("app.tasks.indexing._acquire_lock", return_value=_FALLBACK_TOKEN),
        patch("app.tasks.indexing._index", new_callable=AsyncMock) as mock_index,
        patch("app.tasks.indexing._release_lock", new_callable=AsyncMock) as mock_release,
    ):
        await _index_with_lock("doc-123")
    mock_index.assert_called_once_with("doc-123")
    mock_release.assert_called_once_with("doc-123", _FALLBACK_TOKEN)


# ========== clear_index_lock 测试 ==========


@pytest.mark.asyncio
async def test_clear_index_lock_success():
    """get_redis 正常时删除锁并返回 True"""
    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 1
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        result = await clear_index_lock("doc-abc")
    assert result is True
    mock_redis.delete.assert_called_once_with("lock:index_document:doc-abc")


@pytest.mark.asyncio
async def test_clear_index_lock_key_not_exist():
    """锁 key 不存在时 delete 返回 0，仍返回 True（不影响重试）"""
    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 0
    with patch("app.core.ratelimit.get_redis", return_value=mock_redis):
        result = await clear_index_lock("doc-abc")
    assert result is True


@pytest.mark.asyncio
async def test_clear_index_lock_fallback_connection():
    """get_redis 异常时创建独立连接兜底删除"""
    mock_fresh_redis = AsyncMock()
    mock_fresh_redis.delete.return_value = 1
    with (
        patch("app.core.ratelimit.get_redis", side_effect=ConnectionError("stale")),
        patch("redis.asyncio.from_url", return_value=mock_fresh_redis),
    ):
        result = await clear_index_lock("doc-abc")
    assert result is True
    mock_fresh_redis.delete.assert_called_once_with("lock:index_document:doc-abc")
    mock_fresh_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_clear_index_lock_all_connections_fail():
    """所有 Redis 连接都失败时返回 False"""
    with (
        patch("app.core.ratelimit.get_redis", side_effect=ConnectionError("stale")),
        patch("redis.asyncio.from_url", side_effect=ConnectionError("no redis")),
    ):
        result = await clear_index_lock("doc-abc")
    assert result is False
