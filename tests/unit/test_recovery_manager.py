"""
Unit tests for RecoveryManager
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.recovery_manager import RecoveryResult, DegradedReason, RecoveryManager


class TestRecoveryResult:
    """测试 RecoveryResult 数据类"""

    def test_recovery_result_creation(self):
        result = RecoveryResult(
            session_id="session-123",
            snapshot=None,  # 简化测试
            cache_state=None,  # 简化测试
            degraded=False,
        )
        assert result.session_id == "session-123"
        assert result.degraded is False
        assert result.cache_hit_rate == 0.0

    def test_recovery_result_degraded(self):
        result = RecoveryResult(
            session_id="session-123",
            snapshot=None,
            cache_state=None,
            degraded=True,
            degraded_reason=DegradedReason.CACHE_INVALIDATED,
        )
        assert result.degraded is True
        assert result.degraded_reason == DegradedReason.CACHE_INVALIDATED


class TestRecoveryManager:
    """测试 RecoveryManager 类"""

    @pytest.fixture
    def manager(self):
        return RecoveryManager()

    @pytest.mark.asyncio
    async def test_recovery_with_valid_cache(self, manager):
        """缓存有效时，直接恢复"""
        mock_snapshot = MagicMock()
        mock_snapshot.session_id = "session-123"
        mock_cache_state = MagicMock()
        mock_cache_state.is_valid = True
        mock_cache_state.hit_rate = 1.0

        with patch.object(manager.context_catch, "restore", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_snapshot

            with patch.object(manager.prompt_cache, "get_cache_state", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_cache_state

                result = await manager.recover_session("session-123")

                assert result.degraded is False
                assert result.snapshot == mock_snapshot

    @pytest.mark.asyncio
    async def test_recovery_with_invalid_cache_triggers_degrade(self, manager):
        """缓存无效时，降级恢复"""
        mock_snapshot = MagicMock()
        mock_snapshot.session_id = "session-123"
        mock_cache_state = MagicMock()
        mock_cache_state.is_valid = False

        with patch.object(manager.context_catch, "restore", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_snapshot

            with patch.object(manager.prompt_cache, "get_cache_state", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_cache_state

                result = await manager.recover_session("session-123")

                assert result.degraded is True
                assert result.degraded_reason == DegradedReason.CACHE_INVALIDATED

    @pytest.mark.asyncio
    async def test_recovery_no_cache_state_triggers_degrade(self, manager):
        """无缓存状态时，降级恢复"""
        mock_snapshot = MagicMock()
        mock_snapshot.session_id = "session-123"

        with patch.object(manager.context_catch, "restore", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_snapshot

            with patch.object(manager.prompt_cache, "get_cache_state", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = None  # 无缓存状态

                result = await manager.recover_session("session-123")

                assert result.degraded is True
                assert result.degraded_reason == DegradedReason.CACHE_NOT_FOUND
