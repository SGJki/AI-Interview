"""
Prompt Cache Module

职责：
- 缓存状态记录
- 缓存有效性验证
- 降级策略处理
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptCacheState:
    """Prompt Cache 状态"""
    cache_key: str                    # resume_id + responsibilities_hash
    responsibilities_hash: str        # 用于验证
    is_valid: bool                   # 缓存是否有效
    last_cached_tokens: int          # 最近一次缓存命中 token 数
    created_at: str                  # 创建时间（用于 TTL 判断）
    hit_count: int = 0              # 命中次数
    miss_count: int = 0             # 未命中次数

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total


@dataclass
class CacheKey:
    """缓存 Key 生成器"""
    resume_id: str
    responsibilities_hash: str
    cache_key: str

    @staticmethod
    def generate(resume_id: str, responsibilities: list[str]) -> "CacheKey":
        """
        生成缓存 Key

        Args:
            resume_id: 简历 ID
            responsibilities: 职责列表

        Returns:
            CacheKey 实例
        """
        # 组合 responsibilities 为稳定字符串
        resp_str = json.dumps(responsibilities, sort_keys=True)
        responsibilities_hash = hashlib.sha256(resp_str.encode()).hexdigest()[:16]

        # 组合 cache_key
        key_content = f"{resume_id}:{responsibilities_hash}"
        cache_key = hashlib.sha256(key_content.encode()).hexdigest()

        return CacheKey(
            resume_id=resume_id,
            responsibilities_hash=responsibilities_hash,
            cache_key=cache_key,
        )


class PromptCache:
    """
    Prompt Cache 管理器

    职责：
    - 缓存状态记录
    - 缓存有效性验证
    - 降级策略处理
    """

    def __init__(self):
        """初始化 PromptCache"""
        self._cache_store: dict[str, PromptCacheState] = {}
        self._redis = None  # 可选的 Redis 后端

    async def record_cache(
        self,
        session_id: str,
        state: PromptCacheState,
    ) -> None:
        """
        记录缓存状态

        Args:
            session_id: 会话 ID
            state: 缓存状态
        """
        self._cache_store[session_id] = state
        logger.debug(f"Recorded cache state for session {session_id}: valid={state.is_valid}")

    async def get_cache_state(
        self,
        session_id: str,
    ) -> Optional[PromptCacheState]:
        """
        获取缓存状态

        Args:
            session_id: 会话 ID

        Returns:
            缓存状态，如果不存在返回 None
        """
        return self._cache_store.get(session_id)

    async def invalidate(
        self,
        session_id: str,
    ) -> None:
        """
        使缓存失效

        Args:
            session_id: 会话 ID
        """
        if session_id in self._cache_store:
            state = self._cache_store[session_id]
            state.is_valid = False
            logger.info(f"Invalidated cache for session {session_id}")

    async def validate_cache(
        self,
        session_id: str,
        resume_id: str,
        responsibilities: list[str],
        mock_response=None,  # 用于测试的 mock
    ) -> PromptCacheState:
        """
        验证缓存有效性

        通过检查 LLM 响应中的 cached_tokens 判断缓存是否命中。

        Args:
            session_id: 会话 ID
            resume_id: 简历 ID
            responsibilities: 职责列表
            mock_response: 测试用的 mock 响应（可选）

        Returns:
            PromptCacheState 实例
        """
        # 生成 cache_key
        cache_key_obj = CacheKey.generate(resume_id, responsibilities)
        cached_tokens = 0

        if mock_response is not None:
            # 从 mock 响应提取 cached_tokens
            usage = getattr(mock_response, "usage", None)
            if usage:
                prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
                if prompt_tokens_details:
                    cached_tokens = getattr(prompt_tokens_details, "cached_tokens", 0) or 0
        else:
            # TODO: 调用真实的 LLM 验证
            # 这部分在 Task 5 实现
            pass

        is_valid = cached_tokens > 0

        state = PromptCacheState(
            cache_key=cache_key_obj.cache_key,
            responsibilities_hash=cache_key_obj.responsibilities_hash,
            is_valid=is_valid,
            last_cached_tokens=cached_tokens,
            created_at=datetime.now().isoformat(),
            hit_count=1 if is_valid else 0,
            miss_count=0 if is_valid else 1,
        )

        # 记录到缓存存储
        await self.record_cache(session_id, state)

        return state

    async def validate_cache_with_llm(
        self,
        session_id: str,
        resume_id: str,
        responsibilities: list[str],
        system_prompt: str,
        test_prompt: str = "缓存验证测试",
    ) -> PromptCacheState:
        """
        使用真实 LLM 调用验证缓存

        注意：此方法需要 invoke_llm 返回包含 usage 信息的完整响应。
        目前 invoke_llm 仅返回文本内容，需要扩展以支持 cached_tokens 提取。

        Args:
            session_id: 会话 ID
            resume_id: 简历 ID
            responsibilities: 职责列表
            system_prompt: 系统提示词
            test_prompt: 测试用提示词

        Returns:
            PromptCacheState 实例
        """
        from src.llm.client import invoke_llm

        cache_key_obj = CacheKey.generate(resume_id, responsibilities)

        try:
            # 调用 LLM
            _ = await invoke_llm(
                system_prompt=system_prompt,
                user_prompt=test_prompt,
                temperature=0.0,  # 使用确定输出
            )

            # TODO: 从响应中提取 usage 信息（需要修改 invoke_llm 返回完整响应）
            # 目前 invoke_llm 不返回 usage，故暂时假设缓存有效
            # 后续修改 invoke_llm 后再提取 cached_tokens

            state = PromptCacheState(
                cache_key=cache_key_obj.cache_key,
                responsibilities_hash=cache_key_obj.responsibilities_hash,
                is_valid=True,  # 暂时假设有效
                last_cached_tokens=0,  # TODO: 从响应获取
                created_at=datetime.now().isoformat(),
            )

            await self.record_cache(session_id, state)
            return state

        except Exception as e:
            logger.error(f"LLM validation failed for session {session_id}: {e}")
            raise
