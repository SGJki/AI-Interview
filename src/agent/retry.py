# src/agent/retry.py

from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)

def async_retryable(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,),
):
    """
    异步重试装饰器工厂（类似 Spring @Retryable）

    Args:
        max_attempts: 最大尝试次数
        base_wait: 基础等待时间（秒）
        max_wait: 最大等待时间（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempt + 1, max_attempts, func.__name__, str(e)
                    )
                    if attempt < max_attempts - 1:
                        wait_time = min(base_wait * (2 ** attempt), max_wait)
                        logger.debug("Retrying %s in %s seconds", func.__name__, wait_time)
                        await asyncio.sleep(wait_time)
            logger.error("All %d attempts failed for %s", max_attempts, func.__name__)
            raise last_error
        return wrapper
    return decorator
