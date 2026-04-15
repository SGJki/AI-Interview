"""
Tests for lifespan_manager - graceful shutdown and connection tracking
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from src.core.lifespan_manager import (
    ConnectionTracker,
    get_connection_tracker,
    SSEConnection,
)


class TestConnectionTracker:
    """Tests for ConnectionTracker"""

    def test_register_connection(self):
        """Test registering a new connection"""
        tracker = ConnectionTracker()
        assert tracker.active_count == 0

        tracker.register("conn-1", {"path": "/test"})
        assert tracker.active_count == 1

    def test_unregister_connection(self):
        """Test unregistering a connection"""
        tracker = ConnectionTracker()
        tracker.register("conn-1", {"path": "/test"})
        assert tracker.active_count == 1

        tracker.unregister("conn-1")
        assert tracker.active_count == 0

    def test_register_multiple_connections(self):
        """Test registering multiple connections"""
        tracker = ConnectionTracker()
        tracker.register("conn-1", {"path": "/test1"})
        tracker.register("conn-2", {"path": "/test2"})
        tracker.register("conn-3", {"path": "/test3"})

        assert tracker.active_count == 3

    def test_unregister_triggers_drain_event_when_shutting_down(self):
        """Test that unregistering last connection triggers drain event when shutting down"""
        tracker = ConnectionTracker()
        tracker.register("conn-1", {"path": "/test"})
        tracker.begin_shutdown()

        assert tracker.is_shutting_down is True

        # Unregister should trigger shutdown event since it's the last connection
        tracker.unregister("conn-1")

        # The shutdown event should be set
        assert tracker._shutdown_event.is_set()

    def test_prevents_new_connections_during_shutdown(self):
        """Test that new connections are prevented during shutdown"""
        tracker = ConnectionTracker()
        tracker.begin_shutdown()

        with pytest.raises(RuntimeError, match="Server is shutting down"):
            tracker.register("conn-1", {"path": "/test"})

    @pytest.mark.asyncio
    async def test_wait_for_drain_returns_immediately_when_no_connections(self):
        """Test wait_for_drain returns immediately when no active connections"""
        tracker = ConnectionTracker()
        result = await tracker.wait_for_drain(timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_drain_timeout(self):
        """Test wait_for_drain times out when connections are still active"""
        tracker = ConnectionTracker()
        tracker.register("conn-1", {"path": "/test"})
        result = await tracker.wait_for_drain(timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_drain_succeeds_after_unregister(self):
        """Test wait_for_drain succeeds after all connections are unregistered"""
        tracker = ConnectionTracker()
        tracker.register("conn-1", {"path": "/test"})
        tracker.begin_shutdown()

        # Start waiting in background
        task = asyncio.create_task(tracker.wait_for_drain(timeout=2.0))
        await asyncio.sleep(0.1)  # Give it time to start waiting

        # Unregister connection
        tracker.unregister("conn-1")

        # Wait for result
        result = await task
        assert result is True


class TestSSEConnection:
    """Tests for SSEConnection context manager"""

    @pytest.mark.asyncio
    async def test_sse_connection_context_manager(self):
        """Test SSEConnection as async context manager"""
        tracker = get_connection_tracker()
        tracker._active_connections = {}  # Reset
        tracker._is_shutting_down = False

        conn_id = "test-conn-123"
        async with SSEConnection(conn_id, {"path": "/test"}) as conn:
            assert tracker.active_count == 1
            assert conn.connection_id == conn_id

        # After exiting context, connection should be unregistered
        assert tracker.active_count == 0

    @pytest.mark.asyncio
    async def test_sse_connection_unregister_on_exception(self):
        """Test SSEConnection unregisters even on exception"""
        tracker = get_connection_tracker()
        tracker._active_connections = {}  # Reset
        tracker._is_shutting_down = False

        conn_id = "test-conn-456"

        with pytest.raises(ValueError):
            async with SSEConnection(conn_id, {"path": "/test"}) as conn:
                assert tracker.active_count == 1
                raise ValueError("Test error")

        # Should be unregistered after exception
        assert tracker.active_count == 0


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_lifespan_state_initialization(self):
        """Test lifespan_state is properly initialized"""
        from src.core.lifespan_manager import lifespan_state

        # Should have _startup_complete key
        assert "_startup_complete" in lifespan_state
        assert lifespan_state["_startup_complete"] is False
