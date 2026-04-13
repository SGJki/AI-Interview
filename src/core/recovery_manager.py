"""
Recovery Manager Module

协调 Context Catch 和 Prompt Cache，按序执行恢复流程：
1. 加载快照 (context_catch)
2. 验证缓存 (prompt_cache)
3. 根据缓存状态决定恢复路径
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DegradedReason(Enum):
    """降级原因"""
    CACHE_NOT_FOUND = "cache_not_found"
    CACHE_INVALIDATED = "cache_invalidated"
    CACHE_TTL_EXPIRED = "cache_ttl_expired"
    GLM_API_ERROR = "glm_api_error"


@dataclass
class RecoveryResult:
    """恢复结果"""
    session_id: str
    snapshot: any  # ConversationSnapshot
    cache_state: any  # PromptCacheState
    degraded: bool
    degraded_reason: Optional[DegradedReason] = None
    cache_hit_rate: float = 0.0


class RecoveryManager:
    """
    会话恢复管理器

    协调 Context Catch 和 Prompt Cache，按序执行恢复流程：
    1. 加载快照 (context_catch)
    2. 验证缓存 (prompt_cache)
    3. 根据缓存状态决定恢复路径
    """

    def __init__(self):
        """初始化 RecoveryManager"""
        from src.core.context_catch import ContextCatchEngine
        from src.core.prompt_cache import PromptCache

        self.context_catch = ContextCatchEngine()
        self.prompt_cache = PromptCache()

    async def recover_session(
        self,
        session_id: str,
    ) -> RecoveryResult:
        """
        恢复会话

        Args:
            session_id: 会话 ID

        Returns:
            RecoveryResult 实例
        """
        logger.info(f"Starting session recovery for {session_id}")

        # 1. 加载快照
        snapshot = await self.context_catch.restore(session_id)
        if snapshot is None:
            logger.warning(f"No snapshot found for session {session_id}")
            raise ValueError(f"Session {session_id} not found")

        # 2. 获取缓存状态
        cache_state = await self.prompt_cache.get_cache_state(session_id)

        # 3. 根据缓存状态决定路径
        if cache_state is None:
            logger.info(f"No cache state for session {session_id}, degrading")
            return RecoveryResult(
                session_id=session_id,
                snapshot=snapshot,
                cache_state=None,
                degraded=True,
                degraded_reason=DegradedReason.CACHE_NOT_FOUND,
            )

        if not cache_state.is_valid:
            logger.info(f"Cache invalidated for session {session_id}, degrading")
            return RecoveryResult(
                session_id=session_id,
                snapshot=snapshot,
                cache_state=cache_state,
                degraded=True,
                degraded_reason=DegradedReason.CACHE_INVALIDATED,
                cache_hit_rate=cache_state.hit_rate,
            )

        # 4. 缓存有效，正常恢复
        return RecoveryResult(
            session_id=session_id,
            snapshot=snapshot,
            cache_state=cache_state,
            degraded=False,
            cache_hit_rate=cache_state.hit_rate,
        )

    async def save_checkpoint(
        self,
        session_id: str,
        snapshot: any,
    ) -> None:
        """
        保存检查点（协调 context_catch 和 prompt_cache）

        Args:
            session_id: 会话 ID
            snapshot: 快照数据
        """
        # 1. 保存快照
        await self.context_catch.save_checkpoint(session_id, snapshot)

        # 2. 初始化/更新缓存状态
        cache_state = await self.prompt_cache.get_cache_state(session_id)
        if cache_state is None:
            from src.core.prompt_cache import PromptCacheState, CacheKey

            cache_key = CacheKey.generate(
                resume_id=snapshot.resume_id,
                responsibilities=snapshot.responsibilities,
            )

            cache_state = PromptCacheState(
                cache_key=cache_key.cache_key,
                responsibilities_hash=cache_key.responsibilities_hash,
                is_valid=True,
                last_cached_tokens=0,
                created_at=snapshot.created_at,
            )

        await self.prompt_cache.record_cache(session_id, cache_state)
