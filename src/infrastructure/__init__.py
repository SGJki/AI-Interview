"""
Infrastructure Layer - 基础设施层

包含Redis会话存储等基础设施组件。
"""

from src.infrastructure.session_store import (
    # Session memory operations
    save_to_session_memory,
    get_session_memory,
    clear_session_memory,
    update_session_series,
    # Series question cache
    cache_next_series_question,
    get_cached_next_question,
    # User session tracking
    set_user_current_interview,
    get_user_current_interview,
    # Session state manager
    SessionStateManager,
    SessionHealthMonitor,
    # Redis client
    get_redis_client,
)

__all__ = [
    # Session memory operations
    "save_to_session_memory",
    "get_session_memory",
    "clear_session_memory",
    "update_session_series",
    # Series question cache
    "cache_next_series_question",
    "get_cached_next_question",
    # User session tracking
    "set_user_current_interview",
    "get_user_current_interview",
    # Session state manager
    "SessionStateManager",
    "SessionHealthMonitor",
    # Redis client
    "get_redis_client",
]
