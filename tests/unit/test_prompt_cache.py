"""
Unit tests for PromptCache
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.prompt_cache import PromptCacheState, CacheKey, PromptCache


class TestPromptCacheState:
    """测试 PromptCacheState 数据类"""

    def test_prompt_cache_state_creation(self):
        state = PromptCacheState(
            cache_key="abc123",
            responsibilities_hash="hash456",
            is_valid=True,
            last_cached_tokens=800,
            created_at="2026-04-13T10:00:00",
        )
        assert state.cache_key == "abc123"
        assert state.is_valid is True
        assert state.last_cached_tokens == 800

    def test_prompt_cache_state_defaults(self):
        state = PromptCacheState(
            cache_key="abc123",
            responsibilities_hash="hash456",
            is_valid=False,
            last_cached_tokens=0,
            created_at="2026-04-13T10:00:00",
        )
        assert state.hit_count == 0
        assert state.miss_count == 0


class TestCacheKey:
    """测试 CacheKey 生成"""

    def test_generate_cache_key(self):
        key = CacheKey.generate(
            resume_id="resume-123",
            responsibilities=["后端开发", "微服务"]
        )
        assert key.resume_id == "resume-123"
        assert key.responsibilities_hash is not None
        assert len(key.cache_key) > 0

    def test_same_input_same_hash(self):
        key1 = CacheKey.generate(resume_id="r1", responsibilities=["a", "b"])
        key2 = CacheKey.generate(resume_id="r1", responsibilities=["a", "b"])
        assert key1.cache_key == key2.cache_key

    def test_different_input_different_hash(self):
        key1 = CacheKey.generate(resume_id="r1", responsibilities=["a"])
        key2 = CacheKey.generate(resume_id="r2", responsibilities=["b"])
        assert key1.cache_key != key2.cache_key


class TestPromptCache:
    """测试 PromptCache 类"""

    @pytest.fixture
    def cache(self):
        return PromptCache()

    def test_cache_initialization(self, cache):
        assert cache._cache_store == {}
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_record_cache_hit(self, cache):
        state = PromptCacheState(
            cache_key="test-key",
            responsibilities_hash="hash123",
            is_valid=True,
            last_cached_tokens=500,
            created_at=datetime.now().isoformat(),
        )
        await cache.record_cache("session-1", state)
        assert "session-1" in cache._cache_store

    @pytest.mark.asyncio
    async def test_get_cache_state(self, cache):
        state = PromptCacheState(
            cache_key="test-key",
            responsibilities_hash="hash123",
            is_valid=True,
            last_cached_tokens=500,
            created_at=datetime.now().isoformat(),
        )
        await cache.record_cache("session-1", state)
        retrieved = await cache.get_cache_state("session-1")
        assert retrieved is not None
        assert retrieved.cache_key == "test-key"
        assert retrieved.last_cached_tokens == 500

    @pytest.mark.asyncio
    async def test_get_cache_state_not_found(self, cache):
        retrieved = await cache.get_cache_state("non-existent")
        assert retrieved is None


class TestValidateCache:
    """测试 validate_cache 方法"""

    @pytest.fixture
    def cache(self):
        return PromptCache()

    @pytest.mark.asyncio
    async def test_validate_cache_cached_tokens_present(self, cache):
        """当响应包含 cached_tokens 时，缓存有效"""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens_details = MagicMock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 800
        mock_response.usage.prompt_tokens = 1200

        state = await cache.validate_cache(
            session_id="session-1",
            resume_id="resume-123",
            responsibilities=["后端开发"],
            mock_response=mock_response,
        )

        assert state.is_valid is True
        assert state.last_cached_tokens == 800
        assert state.hit_count == 1

    @pytest.mark.asyncio
    async def test_validate_cache_no_cached_tokens(self, cache):
        """当响应不包含 cached_tokens 时，缓存无效"""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens_details = None
        mock_response.usage.prompt_tokens = 1200

        state = await cache.validate_cache(
            session_id="session-1",
            resume_id="resume-123",
            responsibilities=["后端开发"],
            mock_response=mock_response,
        )

        assert state.is_valid is False
        assert state.last_cached_tokens == 0
        assert state.miss_count == 1

    @pytest.mark.asyncio
    async def test_validate_cache_cached_tokens_zero(self, cache):
        """当 cached_tokens 为 0 时，缓存无效"""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens_details = MagicMock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 0
        mock_response.usage.prompt_tokens = 1200

        state = await cache.validate_cache(
            session_id="session-1",
            resume_id="resume-123",
            responsibilities=["后端开发"],
            mock_response=mock_response,
        )

        assert state.is_valid is False
        assert state.miss_count == 1


class TestValidateCacheWithLLM:
    """Tests for validate_cache_with_llm method."""

    @pytest.fixture
    def cache(self):
        return PromptCache()

    @pytest.fixture
    def mock_llm_response_cached(self):
        """Mock LLM response with cached_tokens > 0."""
        from src.llm.usage import LLMResponse, PromptTokensDetails, LLMUsage

        return LLMResponse(
            content="缓存验证响应",
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                prompt_tokens_details=PromptTokensDetails(cached_tokens=80)
            )
        )

    @pytest.fixture
    def mock_llm_response_not_cached(self):
        """Mock LLM response with cached_tokens = 0."""
        from src.llm.usage import LLMResponse, PromptTokensDetails, LLMUsage

        return LLMResponse(
            content="非缓存响应",
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                prompt_tokens_details=PromptTokensDetails(cached_tokens=0)
            )
        )

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_cached(self, cache, mock_llm_response_cached):
        """Test validate_cache_with_llm when cache hits."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_cached

            state = await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1", "职责2"],
                system_prompt="测试系统提示词",
                test_prompt="测试提示词",
            )

            assert state.is_valid is True
            assert state.last_cached_tokens == 80
            assert state.hit_count >= 0

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_not_cached(self, cache, mock_llm_response_not_cached):
        """Test validate_cache_with_llm when cache misses."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_not_cached

            state = await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1", "职责2"],
                system_prompt="测试系统提示词",
                test_prompt="测试提示词",
            )

            assert state.is_valid is False
            assert state.last_cached_tokens == 0

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_exception(self, cache):
        """Test validate_cache_with_llm handles exceptions."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("LLM 调用失败")

            with pytest.raises(Exception, match="LLM 调用失败"):
                await cache.validate_cache_with_llm(
                    session_id="session-123",
                    resume_id="resume-456",
                    responsibilities=["职责1"],
                    system_prompt="测试系统提示词",
                )

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_records_state(self, cache, mock_llm_response_cached):
        """Test validate_cache_with_llm records state to cache store."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_cached

            await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1"],
                system_prompt="测试",
            )

            # Verify state was recorded
            recorded_state = await cache.get_cache_state("session-123")
            assert recorded_state is not None
            assert recorded_state.cache_key is not None
