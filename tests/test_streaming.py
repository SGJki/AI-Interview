"""Tests for streaming module."""

import pytest
from src.agent.streaming import StreamingHandler, RedisStreamingHandler


@pytest.mark.asyncio
async def test_streaming_handler_buffer():
    """测试流式处理器 buffer 累积"""
    handler = StreamingHandler()
    session_id = "test_session"

    async def mock_generator():
        yield "hello"
        yield " "
        yield "world"

    result = await handler.handle_stream(session_id, mock_generator())
    assert result == "hello world"
    assert session_id not in handler.buffers
