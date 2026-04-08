"""
Tests for Redis Client - Interview State Management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRedisClient:
    """Test RedisClient class"""

    def test_redis_client_initialization(self):
        """Test RedisClient initialization with default URL"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        assert client.url == "redis://localhost:6379"
        assert client._client is None

    def test_redis_client_custom_url(self):
        """Test RedisClient initialization with custom URL"""
        from src.db.redis_client import RedisClient

        custom_url = "redis://custom:6379"
        client = RedisClient(url=custom_url)
        assert client.url == custom_url
        assert client._client is None

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Test get_client creates Redis client"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        with patch("src.db.redis_client.redis.from_url", return_value=mock_redis):
            result = await client.get_client()
            assert result == mock_redis
            assert client._client == mock_redis

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """Test get_client reuses existing client"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        result = await client.get_client()
        assert result == mock_redis

    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """Test close closes the client"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        await client.close()
        mock_redis.close.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """Test close does nothing when no client exists"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        await client.close()  # Should not raise
        assert client._client is None


class TestRedisClientQueueOperations:
    """Test RedisClient queue operations"""

    @pytest.mark.asyncio
    async def test_push_question(self):
        """Test push_question adds question to queue"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        question = {"question": "What is Python?", "series": 1}
        await client.push_question(question)

        mock_redis.rpush.assert_called_once_with(
            "pending_series_questions",
            '{"question": "What is Python?", "series": 1}'
        )

    @pytest.mark.asyncio
    async def test_pop_question_returns_data(self):
        """Test pop_question returns parsed question"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        mock_redis.lpop.return_value = b'{"question": "What is Python?", "series": 1}'

        result = await client.pop_question()

        assert result == {"question": "What is Python?", "series": 1}
        mock_redis.lpop.assert_called_once_with("pending_series_questions")

    @pytest.mark.asyncio
    async def test_pop_question_returns_none_when_empty(self):
        """Test pop_question returns None when queue is empty"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        mock_redis.lpop.return_value = None

        result = await client.pop_question()

        assert result is None


class TestRedisClientHashOperations:
    """Test RedisClient hash operations"""

    @pytest.mark.asyncio
    async def test_hset_series_state(self):
        """Test hset_series_state sets hash"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        data = {"status": "in_progress", "count": "5"}
        await client.hset_series_state(1, data)

        mock_redis.hset.assert_called_once_with(
            "series_1_state",
            mapping=data
        )

    @pytest.mark.asyncio
    async def test_hget_series_state_returns_dict(self):
        """Test hget_series_state returns decoded dict"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        mock_redis.hgetall.return_value = {
            b"status": b"in_progress",
            b"count": b"5"
        }

        result = await client.hget_series_state(1)

        assert result == {"status": "in_progress", "count": "5"}
        mock_redis.hgetall.assert_called_once_with("series_1_state")

    @pytest.mark.asyncio
    async def test_hget_series_state_returns_empty_when_no_data(self):
        """Test hget_series_state returns empty dict when no data"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        mock_redis.hgetall.return_value = None

        result = await client.hget_series_state(1)

        assert result == {}

    @pytest.mark.asyncio
    async def test_hset_session_context(self):
        """Test hset_session_context sets hash"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        data = {"current_question": "Q1", "stage": "interview"}
        await client.hset_session_context("session-123", data)

        mock_redis.hset.assert_called_once_with(
            "session_session-123_context",
            mapping=data
        )

    @pytest.mark.asyncio
    async def test_hget_session_context_returns_dict(self):
        """Test hget_session_context returns decoded dict"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        mock_redis.hgetall.return_value = {
            b"current_question": b"Q1",
            b"stage": b"interview"
        }

        result = await client.hget_session_context("session-123")

        assert result == {"current_question": "Q1", "stage": "interview"}
        mock_redis.hgetall.assert_called_once_with("session_session-123_context")


class TestRedisClientReviewInfo:
    """Test RedisClient review info storage"""

    @pytest.mark.asyncio
    async def test_save_review_info_saves_when_not_production(self):
        """Test save_review_info saves info when is_production is False"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        with patch("src.config.config") as mock_config:
            mock_config.is_production = False

            info = {"feedback": "good", "score": 5}
            await client.save_review_info("session-123", "evaluate_agent", info)

            mock_redis.lpush.assert_called_once()
            call_args = mock_redis.lpush.call_args
            assert call_args[0][0] == "review_info:session-123"

    @pytest.mark.asyncio
    async def test_save_review_info_saves_when_failed(self):
        """Test save_review_info saves info when failed is True even in production"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        with patch("src.config.config") as mock_config:
            mock_config.is_production = True

            info = {"feedback": "bad", "failed": True}
            await client.save_review_info("session-123", "evaluate_agent", info)

            mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_review_info_skips_in_production(self):
        """Test save_review_info skips when is_production is True and not failed"""
        from src.db.redis_client import RedisClient

        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis

        with patch("src.config.config") as mock_config:
            mock_config.is_production = True

            info = {"feedback": "good", "failed": False}
            await client.save_review_info("session-123", "evaluate_agent", info)

            mock_redis.lpush.assert_not_called()
