"""Redis client for interview state management."""
import json
from typing import Optional, Any
import redis.asyncio as redis


class RedisClient:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

    # Queue operations
    async def push_question(self, question: dict) -> None:
        """Push pre-generated question to queue."""
        client = await self.get_client()
        await client.rpush(
            "pending_series_questions",
            json.dumps(question)
        )

    async def pop_question(self) -> Optional[dict]:
        """Pop next question from queue."""
        client = await self.get_client()
        data = await client.lpop("pending_series_questions")
        if data:
            return json.loads(data)
        return None

    # Hash operations
    async def hset_series_state(self, series: int, data: dict) -> None:
        """Set series state."""
        client = await self.get_client()
        await client.hset(f"series_{series}_state", mapping=data)

    async def hget_series_state(self, series: int) -> dict:
        """Get series state."""
        client = await self.get_client()
        data = await client.hgetall(f"series_{series}_state")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    async def hset_session_context(self, session_id: str, data: dict) -> None:
        """Set session context."""
        client = await self.get_client()
        await client.hset(f"session_{session_id}_context", mapping=data)

    async def hget_session_context(self, session_id: str) -> dict:
        """Get session context."""
        client = await self.get_client()
        data = await client.hgetall(f"session_{session_id}_context")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    # Review info storage
    async def save_review_info(self, session_id: str, agent: str, info: dict) -> None:
        """Save review information based on is_production config."""
        from src.config import config
        if not config.is_production or info.get("failed"):
            client = await self.get_client()
            await client.lpush(
                f"review_info:{session_id}",
                json.dumps({"agent": agent, **info})
            )


redis_client = RedisClient()