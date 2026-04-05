"""
Memory Tools for AI Interview Agent

短期记忆：LangGraph State（内存）
短中期记忆：Redis（会话级）
"""

import json
import redis
from typing import Optional
from datetime import timedelta

from src.agent.state import (
    InterviewState,
    InterviewContext,
    InterviewMode,
    FeedbackMode,
)


# =============================================================================
# Redis Configuration
# =============================================================================

def get_redis_client() -> redis.Redis:
    """
    获取 Redis 客户端

    配置来自 pyproject.toml [tool.ai-interview.redis]
    """
    from src.config import get_redis_config

    cfg = get_redis_config()
    kwargs = cfg.to_redis_kwargs()
    return redis.Redis(**kwargs)


# =============================================================================
# Session Memory Keys
# =============================================================================

def _session_key(session_id: str, key: str) -> str:
    """生成会话内存 key"""
    return f"interview:{session_id}:{key}"


# =============================================================================
# Session Memory Operations
# =============================================================================

async def save_to_session_memory(
    session_id: str,
    state: InterviewContext,
    ttl: int = 86400  # 24 hours
) -> None:
    """
    保存会话到短中期记忆 (Redis)

    Args:
        session_id: 会话ID
        state: 面试上下文
        ttl: 过期时间（秒）
    """
    client = get_redis_client()

    # 序列化状态
    state_data = {
        "session_id": state.session_id,
        "resume_id": state.resume_id,
        "knowledge_base_id": state.knowledge_base_id,
        "interview_mode": state.interview_mode.value,
        "feedback_mode": state.feedback_mode.value,
        "error_threshold": state.error_threshold,
        "current_series": state.current_series,
        "current_question_id": state.current_question_id,
        "answers": state.answers,
        "feedbacks": state.feedbacks,
        "followup_depth": state.followup_depth,
        "followup_chain": state.followup_chain,
        "pending_feedbacks": state.pending_feedbacks,
        "error_count": state.error_count,
        # 上下文内容（用于跨 API 调用保持上下文）
        "resume_context": state.resume_context,
        "knowledge_context": state.knowledge_context,
        "current_knowledge": state.current_knowledge,
        "question_contents": state.question_contents,
    }

    key = _session_key(session_id, "state")
    client.setex(key, timedelta(seconds=ttl), json.dumps(state_data))


async def get_session_memory(session_id: str) -> Optional[InterviewContext]:
    """
    获取会话记忆

    Args:
        session_id: 会话ID

    Returns:
        InterviewContext 或 None
    """
    client = get_redis_client()
    key = _session_key(session_id, "state")

    data = client.get(key)
    if not data:
        return None

    state_data = json.loads(data)

    return InterviewContext(
        session_id=state_data["session_id"],
        resume_id=state_data["resume_id"],
        knowledge_base_id=state_data["knowledge_base_id"],
        interview_mode=InterviewMode(state_data["interview_mode"]),
        feedback_mode=FeedbackMode(state_data["feedback_mode"]),
        error_threshold=state_data["error_threshold"],
        current_series=state_data["current_series"],
        current_question_id=state_data.get("current_question_id"),
        answers=state_data.get("answers", []),
        feedbacks=state_data.get("feedbacks", []),
        followup_depth=state_data.get("followup_depth", 0),
        followup_chain=state_data.get("followup_chain", []),
        pending_feedbacks=state_data.get("pending_feedbacks", []),
        error_count=state_data.get("error_count", 0),
        # 恢复上下文内容
        resume_context=state_data.get("resume_context", ""),
        knowledge_context=state_data.get("knowledge_context", ""),
        current_knowledge=state_data.get("current_knowledge", ""),
        question_contents=state_data.get("question_contents", {}),
    )


async def clear_session_memory(session_id: str) -> None:
    """
    清理会话记忆

    Args:
        session_id: 会话ID
    """
    client = get_redis_client()

    # 删除所有相关 key
    pattern = f"interview:{session_id}:*"
    keys = client.keys(pattern)
    if keys:
        client.delete(*keys)


async def update_session_series(
    session_id: str,
    series: int
) -> None:
    """
    更新会话当前系列号

    Args:
        session_id: 会话ID
        series: 新系列号
    """
    client = get_redis_client()
    key = _session_key(session_id, "state")

    data = client.get(key)
    if data:
        state_data = json.loads(data)
        state_data["current_series"] = series
        client.set(key, json.dumps(state_data))


# =============================================================================
# Series Question Cache (系列间预生成)
# =============================================================================

async def cache_next_series_question(
    session_id: str,
    series: int,
    question_content: str,
    ttl: int = 3600  # 1 hour
) -> None:
    """
    缓存下一系列的第一个问题

    用于系列间预生成

    Args:
        session_id: 会话ID
        series: 系列号
        question_content: 问题内容
        ttl: 过期时间
    """
    client = get_redis_client()
    key = f"interview:{session_id}:series:{series}:q1"
    client.setex(key, timedelta(seconds=ttl), question_content)


async def get_cached_next_question(
    session_id: str,
    series: int
) -> Optional[str]:
    """
    获取缓存的下一问题

    Args:
        session_id: 会话ID
        series: 系列号

    Returns:
        问题内容或 None
    """
    client = get_redis_client()
    key = f"interview:{session_id}:series:{series}:q1"
    return client.get(key)


# =============================================================================
# User Session Tracking
# =============================================================================

async def set_user_current_interview(
    user_id: str,
    session_id: str,
    ttl: int = 86400
) -> None:
    """
    设置用户当前活跃面试

    Args:
        user_id: 用户ID
        session_id: 会话ID
        ttl: 过期时间
    """
    client = get_redis_client()
    key = f"user:{user_id}:current_interview"
    client.setex(key, timedelta(seconds=ttl), session_id)


async def get_user_current_interview(user_id: str) -> Optional[str]:
    """
    获取用户当前活跃面试

    Args:
        user_id: 用户ID

    Returns:
        session_id 或 None
    """
    client = get_redis_client()
    key = f"user:{user_id}:current_interview"
    return client.get(key)


# =============================================================================
# Session State Manager - Redis Session Management
# =============================================================================

class SessionStateManager:
    """
    会话状态管理器

    负责 Redis 会话的持久化、加载、删除和恢复

    Attributes:
        _lock_prefix: 会话锁 key 前缀
        _expiring_threshold: 过期提醒阈值（秒）
    """

    _lock_prefix = "interview:lock:"
    _expiring_threshold = 600  # 10 minutes

    def __init__(self):
        """初始化会话状态管理器"""
        self._redis = None

    @property
    def redis(self):
        """Lazy Redis client initialization"""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    def _state_key(self, session_id: str) -> str:
        """生成会话状态 key"""
        return f"interview:{session_id}:state"

    def _lock_key(self, session_id: str) -> str:
        """生成会话锁 key"""
        return f"{self._lock_prefix}{session_id}"

    async def save_interview_state(
        self,
        session_id: str,
        state: InterviewContext,
        ttl: int = 86400
    ) -> None:
        """
        保存面试状态到 Redis

        Args:
            session_id: 会话ID
            state: 面试上下文
            ttl: 过期时间（秒），默认 24 小时
        """
        state_data = {
            "session_id": state.session_id,
            "resume_id": state.resume_id,
            "knowledge_base_id": state.knowledge_base_id,
            "interview_mode": state.interview_mode.value,
            "feedback_mode": state.feedback_mode.value,
            "error_threshold": state.error_threshold,
            "current_series": state.current_series,
            "current_question_id": state.current_question_id,
            "answers": state.answers,
            "feedbacks": state.feedbacks,
            "followup_depth": state.followup_depth,
            "followup_chain": state.followup_chain,
            "pending_feedbacks": state.pending_feedbacks,
            "error_count": state.error_count,
            "resume_context": state.resume_context,
            "knowledge_context": state.knowledge_context,
            "current_knowledge": state.current_knowledge,
            "question_contents": state.question_contents,
        }

        key = self._state_key(session_id)
        self.redis.setex(key, timedelta(seconds=ttl), json.dumps(state_data))

    async def load_interview_state(
        self,
        session_id: str
    ) -> Optional[InterviewContext]:
        """
        从 Redis 加载面试状态

        Args:
            session_id: 会话ID

        Returns:
            InterviewContext 或 None（会话不存在或数据损坏）
        """
        key = self._state_key(session_id)
        data = self.redis.get(key)

        if not data:
            return None

        try:
            state_data = json.loads(data)

            # Validate required fields
            required_fields = [
                "session_id", "resume_id", "knowledge_base_id",
                "interview_mode", "feedback_mode"
            ]
            for field in required_fields:
                if field not in state_data:
                    return None

            return InterviewContext(
                session_id=state_data["session_id"],
                resume_id=state_data["resume_id"],
                knowledge_base_id=state_data["knowledge_base_id"],
                interview_mode=InterviewMode(state_data["interview_mode"]),
                feedback_mode=FeedbackMode(state_data["feedback_mode"]),
                error_threshold=state_data.get("error_threshold", 2),
                current_series=state_data.get("current_series", 1),
                current_question_id=state_data.get("current_question_id"),
                answers=state_data.get("answers", []),
                feedbacks=state_data.get("feedbacks", []),
                followup_depth=state_data.get("followup_depth", 0),
                followup_chain=state_data.get("followup_chain", []),
                pending_feedbacks=state_data.get("pending_feedbacks", []),
                error_count=state_data.get("error_count", 0),
                resume_context=state_data.get("resume_context", ""),
                knowledge_context=state_data.get("knowledge_context", ""),
                current_knowledge=state_data.get("current_knowledge", ""),
                question_contents=state_data.get("question_contents", {}),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Data corruption or missing required fields
            return None

    async def delete_interview_state(self, session_id: str) -> None:
        """
        删除会话状态及所有相关 key

        Args:
            session_id: 会话ID
        """
        pattern = f"interview:{session_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

    async def get_active_sessions(self, user_id: str) -> list[str]:
        """
        获取用户的所有活跃会话

        Args:
            user_id: 用户ID

        Returns:
            活跃会话 ID 列表
        """
        active_sessions = []

        # Scan for user's sessions
        pattern = f"interview:*:state"
        for key in self.redis.scan_iter(match=pattern):
            # Extract session_id from key
            parts = key.split(":")
            if len(parts) >= 2:
                session_id = parts[1]
                # Check if session belongs to user by checking user mapping
                user_key = f"user:{user_id}:current_interview"
                if self.redis.exists(user_key):
                    current = self.redis.get(user_key)
                    if current == session_id:
                        active_sessions.append(session_id)

        return active_sessions

    async def acquire_session_lock(
        self,
        session_id: str,
        worker_id: str,
        ttl: int = 30
    ) -> bool:
        """
        尝试获取会话锁（用于分布式会话控制）

        Args:
            session_id: 会话ID
            worker_id: 工作器ID
            ttl: 锁过期时间（秒）

        Returns:
            是否成功获取锁
        """
        key = self._lock_key(session_id)
        # Use SET NX (set if not exists) with expiration
        result = self.redis.set(
            key,
            worker_id,
            nx=True,
            ex=ttl
        )
        return result is True

    async def release_session_lock(
        self,
        session_id: str,
        worker_id: str
    ) -> None:
        """
        释放会话锁

        Args:
            session_id: 会话ID
            worker_id: 工作器ID（用于验证）
        """
        key = self._lock_key(session_id)
        # Only delete if we own the lock
        current_owner = self.redis.get(key)
        if current_owner == worker_id:
            self.redis.delete(key)

    async def extend_session_ttl(
        self,
        session_id: str,
        additional_ttl: int = 86400
    ) -> bool:
        """
        延长会话 TTL

        Args:
            session_id: 会话ID
            additional_ttl: 延长的秒数

        Returns:
            是否成功延长
        """
        key = self._state_key(session_id)
        return self.redis.expire(key, additional_ttl)


class SessionHealthMonitor:
    """
    会话健康监控器

    负责会话健康检查、活跃会话统计和过期提醒
    """

    def __init__(self):
        """初始化会话健康监控器"""
        self._redis = None

    @property
    def redis(self):
        """Lazy Redis client initialization"""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    async def get_active_session_count(self) -> int:
        """
        获取活跃会话总数

        Returns:
            活跃会话数量
        """
        count = 0
        pattern = "interview:*:state"
        for _ in self.redis.scan_iter(match=pattern):
            count += 1
        return count

    async def get_session_ttl(self, session_id: str) -> int:
        """
        获取会话剩余 TTL

        Args:
            session_id: 会话ID

        Returns:
            剩余秒数（-2 表示不存在，-1 表示无过期时间）
        """
        key = f"interview:{session_id}:state"
        return self.redis.ttl(key)

    async def check_session_health(self, session_id: str) -> dict:
        """
        检查会话健康状态

        Args:
            session_id: 会话ID

        Returns:
            健康状态字典
        """
        key = f"interview:{session_id}:state"
        exists = self.redis.exists(key) > 0
        ttl = self.redis.ttl(key) if exists else -2

        is_healthy = False
        expiring_soon = False

        if exists:
            is_healthy = ttl > SessionStateManager._expiring_threshold
            expiring_soon = 0 < ttl <= SessionStateManager._expiring_threshold

        return {
            "session_id": session_id,
            "exists": exists,
            "ttl": ttl,
            "is_healthy": is_healthy,
            "expiring_soon": expiring_soon,
        }

    async def get_sessions_expiring_soon(
        self,
        threshold_seconds: int = 600
    ) -> list[dict]:
        """
        获取即将过期的会话列表

        Args:
            threshold_seconds: 过期阈值（秒），默认 10 分钟

        Returns:
            即将过期会话的信息列表
        """
        expiring_sessions = []
        pattern = "interview:*:state"

        for key in self.redis.scan_iter(match=pattern):
            ttl = self.redis.ttl(key)
            if 0 < ttl <= threshold_seconds:
                # Extract session_id
                parts = key.split(":")
                if len(parts) >= 2:
                    session_id = parts[1]
                    expiring_sessions.append({
                        "session_id": session_id,
                        "ttl": ttl,
                        "key": key,
                    })

        return expiring_sessions

