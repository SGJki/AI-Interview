# tests/test_retry.py

import pytest
from src.agent.retry import async_retryable

@pytest.mark.asyncio
async def test_async_retryable_success():
    """测试重试装饰器在成功时直接返回"""
    call_count = 0

    @async_retryable(max_attempts=3)
    async def successful_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await successful_func()
    assert result == "success"
    assert call_count == 1

@pytest.mark.asyncio
async def test_async_retryable_retries_on_failure():
    """测试重试装饰器在失败时重试"""
    call_count = 0

    @async_retryable(max_attempts=3)
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("fail")
        return "success"

    result = await failing_func()
    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_async_retryable_exhausts_retries():
    """测试重试装饰器在所有重试都失败后抛出异常"""
    call_count = 0

    @async_retryable(max_attempts=3, base_wait=0.01)
    async def always_failing_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("always fail")

    with pytest.raises(ValueError):
        await always_failing_func()

    assert call_count == 3
