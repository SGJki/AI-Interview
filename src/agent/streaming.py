"""Streaming output handler for AI Interview Agent."""

from typing import AsyncGenerator, Optional
import json
import logging
from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)


class StreamingHandler:
    """
    流式响应处理器
    """

    def __init__(self) -> None:
        self.buffers: dict[str, list[str]] = {}

    async def handle_stream(
        self,
        session_id: str,
        generator: AsyncGenerator[str, None]
    ) -> str:
        """
        处理流式输出

        Args:
            session_id: 会话 ID
            generator: token 生成器

        Returns:
            完整的文本内容
        """
        self.buffers[session_id] = []
        try:
            async for token in generator:
                self.buffers[session_id].append(token)
            full_text = "".join(self.buffers[session_id])
            return full_text
        finally:
            del self.buffers[session_id]


class RedisStreamingHandler(StreamingHandler):
    """
    基于 Redis 的流式处理器
    """

    async def publish_token(self, session_id: str, token: str):
        """发布 token 到 Redis"""
        try:
            channel = f"stream:{session_id}"
            await redis_client.publish(
                channel,
                json.dumps({"type": "token", "content": token})
            )
        except Exception as e:
            logger.error(f"Failed to publish token for session {session_id}: {e}")

    async def publish_complete(self, session_id: str, full_content: str):
        """发布完成信号"""
        try:
            channel = f"stream:{session_id}"
            await redis_client.publish(
                channel,
                json.dumps({"type": "complete", "content": full_content})
            )
        except Exception as e:
            logger.error(f"Failed to publish complete for session {session_id}: {e}")

    async def subscribe(self, session_id: str) -> AsyncGenerator[dict, None]:
        """订阅流式输出"""
        try:
            pubsub = redis_client.subscribe(f"stream:{session_id}")
            async for message in pubsub:
                yield json.loads(message)
        except Exception as e:
            logger.error(f"Failed to subscribe for session {session_id}: {e}")