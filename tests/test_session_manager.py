"""
Tests for Redis Session State Manager

Phase 5: Redis Session Management - TDD Tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.agent.state import InterviewState
from src.session.context import InterviewContext
from src.domain.enums import InterviewMode, FeedbackMode, QuestionType
from src.domain.models import Question, Answer
from src.infrastructure.session_store import (
    SessionStateManager,
    SessionHealthMonitor,
)


async def async_iter(items):
    """Helper to create async iterator from list"""
    for item in items:
        yield item


class AsyncIteratorMock:
    """Mock for async Redis scan_iter - returns async iterator"""
    def __init__(self, items):
        self.items = items

    def __call__(self, match=None):
        return async_iter(self.items)

    def __aiter__(self):
        return async_iter(self.items).__aiter__()


class TestSessionStateManager:
    """Test SessionStateManager for Redis session persistence"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client with async methods"""
        with patch('src.infrastructure.session_store.get_redis_client') as mock:
            client = MagicMock()
            # Set async methods to AsyncMock
            client.setex = AsyncMock(return_value=True)
            client.get = AsyncMock(return_value=None)
            client.delete = AsyncMock(return_value=True)
            client.keys = AsyncMock(return_value=[])
            client.scan_iter = AsyncIteratorMock([])
            client.exists = AsyncMock(return_value=0)
            client.set = AsyncMock(return_value=True)
            client.ttl = AsyncMock(return_value=-2)
            client.expire = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create SessionStateManager instance with mocked Redis"""
        return SessionStateManager()

    @pytest.fixture
    def sample_interview_context(self):
        """Create a sample InterviewContext for testing"""
        return InterviewContext(
            session_id="test-session-123",
            resume_id="resume-456",
            knowledge_base_id="kb-789",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
            current_series=1,
        )

    @pytest.mark.asyncio
    async def test_save_interview_state(self, session_manager, mock_redis, sample_interview_context):
        """Test saving interview state to Redis"""
        mock_redis.setex.return_value = True

        await session_manager.save_interview_state(
            session_id="test-session-123",
            state=sample_interview_context,
            ttl=86400
        )

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "interview:test-session-123:state" in str(call_args)

    @pytest.mark.asyncio
    async def test_load_interview_state_found(self, session_manager, mock_redis):
        """Test loading existing interview state from Redis"""
        import json

        stored_data = {
            "session_id": "test-session-123",
            "resume_id": "resume-456",
            "knowledge_base_id": "kb-789",
            "interview_mode": "free",
            "feedback_mode": "recorded",
            "error_threshold": 2,
            "current_series": 1,
            "current_question_id": None,
            "answers": [],
            "feedbacks": [],
            "followup_depth": 0,
            "followup_chain": [],
            "pending_feedbacks": [],
            "error_count": 0,
        }
        mock_redis.get.return_value = json.dumps(stored_data)

        result = await session_manager.load_interview_state("test-session-123")

        assert result is not None
        assert result.session_id == "test-session-123"
        assert result.resume_id == "resume-456"
        mock_redis.get.assert_called_once_with("interview:test-session-123:state")

    @pytest.mark.asyncio
    async def test_load_interview_state_not_found(self, session_manager, mock_redis):
        """Test loading non-existent interview state returns None"""
        mock_redis.get.return_value = None

        result = await session_manager.load_interview_state("non-existent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_interview_state(self, session_manager, mock_redis):
        """Test deleting interview state from Redis"""
        mock_redis.keys.return_value = [
            "interview:test-session-123:state",
            "interview:test-session-123:series:1",
        ]
        mock_redis.delete.return_value = 2

        await session_manager.delete_interview_state("test-session-123")

        mock_redis.keys.assert_called_once_with("interview:test-session-123:*")
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager, mock_redis):
        """Test getting active sessions for a user"""
        import json

        # Mock user session lookup
        mock_redis.get.return_value = "user-session-1"

        # Mock scanning for user's sessions
        mock_redis.scan_iter.return_value = iter([
            "interview:user-session-1:state",
            "interview:user-session-2:state",
        ])

        # Mock getting state data for each session
        def get_side_effect(key):
            if "user-session-1" in key:
                return json.dumps({
                    "session_id": "user-session-1",
                    "resume_id": "resume-1",
                    "knowledge_base_id": "kb-1",
                    "interview_mode": "free",
                    "feedback_mode": "recorded",
                    "error_threshold": 2,
                    "current_series": 1,
                    "current_question_id": None,
                    "answers": [],
                    "feedbacks": [],
                    "followup_depth": 0,
                    "followup_chain": [],
                    "pending_feedbacks": [],
                    "error_count": 0,
                })
            return None

        mock_redis.get.side_effect = get_side_effect
        mock_redis.exists.return_value = True

        result = await session_manager.get_active_sessions("user-123")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_save_interview_state_with_ttl(self, session_manager, mock_redis, sample_interview_context):
        """Test that save_interview_state respects TTL parameter"""
        from datetime import timedelta

        mock_redis.setex.return_value = True

        custom_ttl = 3600  # 1 hour
        await session_manager.save_interview_state(
            session_id="test-session-123",
            state=sample_interview_context,
            ttl=custom_ttl
        )

        call_args = mock_redis.setex.call_args
        # Check that setex was called with correct TTL (timedelta object)
        args, kwargs = call_args
        assert args[1] == timedelta(seconds=custom_ttl)

    @pytest.mark.asyncio
    async def test_state_integrity_check(self, session_manager, mock_redis):
        """Test state integrity check when loading corrupted data"""
        import json

        # Corrupted data - missing required fields
        corrupted_data = {
            "session_id": "test-session-123",
            # missing other required fields
        }
        mock_redis.get.return_value = json.dumps(corrupted_data)

        # Should handle gracefully, not raise exception
        result = await session_manager.load_interview_state("test-session-123")

        # Returns None for corrupted/incomplete data
        assert result is None


class TestSessionHealthMonitor:
    """Test SessionHealthMonitor for session health checks"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client with async methods"""
        with patch('src.infrastructure.session_store.get_redis_client') as mock:
            client = MagicMock()
            # Set async methods to AsyncMock
            client.setex = AsyncMock(return_value=True)
            client.get = AsyncMock(return_value=None)
            client.delete = AsyncMock(return_value=True)
            client.keys = AsyncMock(return_value=[])
            client.scan_iter = AsyncIteratorMock([])
            client.exists = AsyncMock(return_value=0)
            client.set = AsyncMock(return_value=True)
            client.ttl = AsyncMock(return_value=-2)
            client.expire = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    @pytest.fixture
    def health_monitor(self, mock_redis):
        """Create SessionHealthMonitor instance with mocked Redis"""
        return SessionHealthMonitor()

    @pytest.mark.asyncio
    async def test_get_active_session_count(self, health_monitor, mock_redis):
        """Test getting count of active sessions"""
        # Mock scan_iter returning some sessions (async iterator)
        mock_redis.scan_iter = AsyncIteratorMock([
            "interview:session-1:state",
            "interview:session-2:state",
            "interview:session-3:state",
        ])

        count = await health_monitor.get_active_session_count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_session_ttl(self, health_monitor, mock_redis):
        """Test getting TTL for a session"""
        mock_redis.ttl.return_value = 3600  # 1 hour

        ttl = await health_monitor.get_session_ttl("test-session-123")

        assert ttl == 3600
        mock_redis.ttl.assert_called_once_with("interview:test-session-123:state")

    @pytest.mark.asyncio
    async def test_check_session_health_healthy(self, health_monitor, mock_redis):
        """Test session health check for healthy session"""
        import json

        mock_redis.ttl.return_value = 3600
        mock_redis.exists.return_value = True

        stored_data = {
            "session_id": "test-session-123",
            "resume_id": "resume-456",
            "knowledge_base_id": "kb-789",
            "interview_mode": "free",
            "feedback_mode": "recorded",
            "error_threshold": 2,
            "current_series": 1,
            "current_question_id": None,
            "answers": [],
            "feedbacks": [],
            "followup_depth": 0,
            "followup_chain": [],
            "pending_feedbacks": [],
            "error_count": 0,
        }
        mock_redis.get.return_value = json.dumps(stored_data)

        health = await health_monitor.check_session_health("test-session-123")

        assert health is not None
        assert health["exists"] is True
        assert health["ttl"] == 3600
        assert health["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_check_session_health_not_found(self, health_monitor, mock_redis):
        """Test session health check for non-existent session"""
        mock_redis.ttl.return_value = -2  # Key does not exist
        mock_redis.exists.return_value = False

        health = await health_monitor.check_session_health("non-existent")

        assert health["exists"] is False
        assert health["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_check_session_health_expiring_soon(self, health_monitor, mock_redis):
        """Test session health check for session expiring soon"""
        import json

        mock_redis.ttl.return_value = 60  # Only 60 seconds left
        mock_redis.exists.return_value = True

        stored_data = {
            "session_id": "test-session-123",
            "resume_id": "resume-456",
            "knowledge_base_id": "kb-789",
            "interview_mode": "free",
            "feedback_mode": "recorded",
            "error_threshold": 2,
            "current_series": 1,
            "current_question_id": None,
            "answers": [],
            "feedbacks": [],
            "followup_depth": 0,
            "followup_chain": [],
            "pending_feedbacks": [],
            "error_count": 0,
        }
        mock_redis.get.return_value = json.dumps(stored_data)

        health = await health_monitor.check_session_health("test-session-123")

        assert health["exists"] is True
        assert health["is_healthy"] is False  # Expiring soon
        assert health["expiring_soon"] is True


class TestSessionRecovery:
    """Test session recovery mechanism"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client with async methods"""
        with patch('src.infrastructure.session_store.get_redis_client') as mock:
            client = MagicMock()
            # Set async methods to AsyncMock
            client.setex = AsyncMock(return_value=True)
            client.get = AsyncMock(return_value=None)
            client.delete = AsyncMock(return_value=True)
            client.keys = AsyncMock(return_value=[])
            client.scan_iter = AsyncIteratorMock([])
            client.exists = AsyncMock(return_value=0)
            client.set = AsyncMock(return_value=True)
            client.ttl = AsyncMock(return_value=-2)
            client.expire = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create SessionStateManager instance with mocked Redis"""
        return SessionStateManager()

    @pytest.mark.asyncio
    async def test_recover_from_partial_state(self, session_manager, mock_redis):
        """Test recovery from partial/corrupted state"""
        import json

        # Partial state with some data
        partial_data = {
            "session_id": "test-session-123",
            "resume_id": "resume-456",
            "knowledge_base_id": "kb-789",
            "interview_mode": "free",
            "feedback_mode": "recorded",
            "error_threshold": 2,
            "current_series": 2,  # Partially through interview
            "current_question_id": "q-5",
            "answers": [{"question_id": "q-1", "answer": "test"}],
            "feedbacks": [],
            "followup_depth": 1,
            "followup_chain": ["q-1", "q-2"],
            "pending_feedbacks": [],
            "error_count": 0,
        }
        mock_redis.get.return_value = json.dumps(partial_data)

        result = await session_manager.load_interview_state("test-session-123")

        # Should recover partial state
        assert result is not None
        assert result.current_series == 2
        assert len(result.answers) == 1

    @pytest.mark.asyncio
    async def test_session_lock_acquire(self, session_manager, mock_redis):
        """Test acquiring session lock"""
        mock_redis.set.return_value = True

        lock_acquired = await session_manager.acquire_session_lock(
            "test-session-123",
            "worker-1",
            ttl=30
        )

        assert lock_acquired is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_lock_acquire_failed(self, session_manager, mock_redis):
        """Test failing to acquire session lock when already held"""
        mock_redis.set.return_value = False  # Lock already held

        lock_acquired = await session_manager.acquire_session_lock(
            "test-session-123",
            "worker-2",
            ttl=30
        )

        assert lock_acquired is False

    @pytest.mark.asyncio
    async def test_session_lock_release(self, session_manager, mock_redis):
        """Test releasing session lock"""
        mock_redis.delete.return_value = 1
        # Mock get to return the worker_id so the lock ownership check passes
        mock_redis.get.return_value = "worker-1"

        await session_manager.release_session_lock("test-session-123", "worker-1")

        mock_redis.delete.assert_called_once_with("interview:lock:test-session-123")


class TestSessionExpiration:
    """Test session expiration handling"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client with async methods"""
        with patch('src.infrastructure.session_store.get_redis_client') as mock:
            client = MagicMock()
            # Set async methods to AsyncMock
            client.setex = AsyncMock(return_value=True)
            client.get = AsyncMock(return_value=None)
            client.delete = AsyncMock(return_value=True)
            client.keys = AsyncMock(return_value=[])
            client.scan_iter = AsyncIteratorMock([])
            client.exists = AsyncMock(return_value=0)
            client.set = AsyncMock(return_value=True)
            client.ttl = AsyncMock(return_value=-2)
            client.expire = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create SessionStateManager instance with mocked Redis"""
        return SessionStateManager()

    @pytest.fixture
    def health_monitor(self, mock_redis):
        """Create SessionHealthMonitor instance with mocked Redis"""
        return SessionHealthMonitor()

    @pytest.mark.asyncio
    async def test_get_sessions_expiring_soon(self, health_monitor, mock_redis):
        """Test getting sessions that are expiring soon"""
        import json

        # Mock scan returning some sessions
        mock_redis.scan_iter.return_value = iter([
            "interview:session-1:state",
            "interview:session-2:state",
        ])

        def ttl_side_effect(key):
            if "session-1" in key:
                return 300  # 5 minutes - expiring soon
            return 3600  # 1 hour - healthy

        def get_side_effect(key):
            return json.dumps({
                "session_id": key.split(":")[1],
                "resume_id": "resume-1",
                "knowledge_base_id": "kb-1",
                "interview_mode": "free",
                "feedback_mode": "recorded",
                "error_threshold": 2,
                "current_series": 1,
                "current_question_id": None,
                "answers": [],
                "feedbacks": [],
                "followup_depth": 0,
                "followup_chain": [],
                "pending_feedbacks": [],
                "error_count": 0,
            })

        mock_redis.ttl.side_effect = ttl_side_effect
        mock_redis.get.side_effect = get_side_effect

        expiring = await health_monitor.get_sessions_expiring_soon(threshold_seconds=600)

        assert isinstance(expiring, list)

    @pytest.mark.asyncio
    async def test_extend_session_ttl(self, session_manager, mock_redis):
        """Test extending session TTL"""
        mock_redis.expire.return_value = True

        extended = await session_manager.extend_session_ttl(
            "test-session-123",
            additional_ttl=86400
        )

        assert extended is True
        mock_redis.expire.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
