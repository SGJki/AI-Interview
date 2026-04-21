"""
优雅关闭管理器 - 连接追踪与排空机制

功能:
- 追踪活跃的 SSE 连接
- 支持连接排空（drain）实现优雅关闭
- 提供 readiness 健康检查
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTracker:
    """
    连接追踪器 - 追踪活跃的 SSE/长连接

    用于优雅关闭时等待所有活跃请求完成
    """
    _active_connections: dict[str, dict] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _shutdown_event: asyncio.Event = field(default_factory=asyncio.Event)
    _is_shutting_down: bool = False

    def register(self, connection_id: str, metadata: dict | None = None) -> None:
        """注册一个新连接"""
        if self._is_shutting_down:
            raise RuntimeError("Server is shutting down, new connections not allowed")

        self._active_connections[connection_id] = {
            "metadata": metadata or {},
            "connected_at": datetime.now(),
        }
        logger.debug(f"Connection registered: {connection_id}, active: {len(self._active_connections)}")

    def unregister(self, connection_id: str) -> None:
        """注销一个连接"""
        if connection_id in self._active_connections:
            del self._active_connections[connection_id]
            logger.debug(f"Connection unregistered: {connection_id}, active: {len(self._active_connections)}")

            # 如果正在关闭且没有活跃连接了，触发 shutdown event
            if self._is_shutting_down and len(self._active_connections) == 0:
                self._shutdown_event.set()

    async def wait_for_drain(self, timeout: float = 30.0) -> bool:
        """
        等待所有活跃连接完成（排空）

        Args:
            timeout: 最大等待时间（秒）

        Returns:
            True if all connections drained, False if timeout
        """
        if len(self._active_connections) == 0:
            logger.info("No active connections to drain")
            return True

        logger.info(f"Waiting for {len(self._active_connections)} active connections to drain...")

        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=timeout
            )
            logger.info("All connections drained successfully")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Drain timeout after {timeout}s, {len(self._active_connections)} still active")
            return False

    @property
    def active_count(self) -> int:
        """获取活跃连接数"""
        return len(self._active_connections)

    @property
    def is_shutting_down(self) -> bool:
        """是否正在关闭"""
        return self._is_shutting_down

    def begin_shutdown(self) -> None:
        """开始关闭流程 - 禁止新连接注册"""
        self._is_shutting_down = True
        logger.info("Shutdown initiated, no new connections will be accepted")

        # 如果没有活跃连接，立即触发
        if len(self._active_connections) == 0:
            self._shutdown_event.set()


# 全局连接追踪器实例
_connection_tracker: ConnectionTracker | None = None


def get_connection_tracker() -> ConnectionTracker:
    """获取全局连接追踪器实例"""
    global _connection_tracker
    if _connection_tracker is None:
        _connection_tracker = ConnectionTracker()
    return _connection_tracker


class SSEConnection:
    """
    SSE 连接上下文管理器

    用法:
        async with SSEConnection(connection_id, metadata) as conn:
            async for event in event_generator():
                yield event
    """

    def __init__(self, connection_id: str, metadata: dict | None = None):
        self.connection_id = connection_id
        self.metadata = metadata or {}
        self._tracker = get_connection_tracker()

    async def __aenter__(self) -> "SSEConnection":
        self._tracker.register(self.connection_id, self.metadata)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._tracker.unregister(self.connection_id)


# =============================================================================
# FastAPI Dependencies
# =============================================================================

from fastapi import Request
from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def sse_connection(request: Request) -> AsyncGenerator[str, None]:
    """
    SSE 连接追踪依赖

    用法:
        @app.get("/stream")
        async def stream(request: Request, conn_id: str = Depends(sse_connection)):
            ...

    Returns:
        connection_id: 生成的唯一连接 ID
    """
    import uuid
    tracker = get_connection_tracker()

    # 如果服务器正在关闭，拒绝新连接
    if tracker.is_shutting_down:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Server is shutting down")

    # 生成唯一连接 ID
    connection_id = str(uuid.uuid4())

    # 注册连接
    tracker.register(connection_id, {
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown",
    })

    try:
        yield connection_id
    finally:
        # 注销连接
        tracker.unregister(connection_id)


@asynccontextmanager
async def server_lifespan(app) -> AsyncGenerator[None, None]:
    """
    服务器生命周期管理器

    实现:
    1. 启动时: 初始化数据库、Redis 等资源
    2. 运行中: 追踪活跃连接
    3. 关闭时: 排空活跃连接、关闭资源
    """
    import logging
    logger = logging.getLogger(__name__)

    # ========== Startup ==========
    logger.info("=" * 50)
    logger.info("Starting AI Interview Agent...")

    # Initialize database
    try:
        from src.db.database import get_database_manager, close_database_manager
        from src.db.models import Base

        db = get_database_manager()
        logger.info("Initializing database...")
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

        # Store cleanup function for shutdown
        lifespan_state["close_database"] = close_database_manager
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application will continue but database features may not work")

    # Initialize Redis connection pool
    try:
        from src.db.redis_client import redis_client
        logger.info("Initializing Redis connection...")
        await redis_client.get_client()
        logger.info("Redis initialized")

        # Store cleanup function for shutdown
        lifespan_state["close_redis"] = redis_client.close
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        logger.warning("Application will continue without Redis caching")

    # Initialize LLM client (warmup)
    try:
        from src.llm.client import get_chat_model
        logger.info("Warming up LLM client...")
        # Don't actually call LLM, just ensure the client is initialized
        # get_chat_model()  # Uncomment if needed
        logger.info("LLM client ready")
    except Exception as e:
        logger.warning(f"LLM warmup failed: {e}")

    logger.info("AI Interview Agent started successfully")
    logger.info("=" * 50)

    # Mark startup as complete
    lifespan_state["_startup_complete"] = True

    # ========== Runtime -> Shutdown Signal ==========
    yield

    # ========== Shutdown ==========
    logger.info("=" * 50)
    logger.info("Shutting down AI Interview Agent...")

    tracker = get_connection_tracker()

    # Phase 1: 停止接受新连接
    logger.info("Phase 1: Stop accepting new connections...")
    tracker.begin_shutdown()

    # Phase 2: 等待活跃连接排空
    logger.info("Phase 2: Draining active connections...")
    drained = await tracker.wait_for_drain(timeout=30.0)
    if not drained:
        logger.warning(f"Shutdown timeout: {tracker.active_count} connections still active")
        for conn_id, conn_info in tracker._active_connections.items():
            logger.warning(f"  - {conn_id}: {conn_info['metadata']}")

    # Phase 3: 关闭数据库连接
    if "close_database" in lifespan_state:
        logger.info("Phase 3: Closing database connections...")
        try:
            await lifespan_state["close_database"]()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

    # Phase 4: 关闭 Redis 连接
    if "close_redis" in lifespan_state:
        logger.info("Phase 4: Closing Redis connections...")
        try:
            await lifespan_state["close_redis"]()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

    logger.info("AI Interview Agent shutdown complete")
    logger.info("=" * 50)


# 用于存储 lifecycle 状态的字典
lifespan_state: dict = {
    "_startup_complete": False,
}
