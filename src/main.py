"""
FastAPI Application Entry Point

AI Interview Agent - FastAPI Server

启动方式:
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys
from contextlib import asynccontextmanager

# 配置 logging - 输出到 stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import interview_router, training_router, knowledge_router
from src.core.lifespan_manager import server_lifespan


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="AI Interview Agent",
    description="AI 面试助手 - 支持实时点评和流式输出",
    version="0.1.0",
    lifespan=server_lifespan,
)

# =============================================================================
# CORS Configuration
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(interview_router)
app.include_router(training_router)
app.include_router(knowledge_router)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """存活检查 (Liveness) - 判断进程是否存活"""
    return {
        "status": "healthy",
        "service": "ai-interview",
        "version": "0.1.0",
    }


@app.get("/health/ready")
async def readiness_check():
    """
    就绪检查 (Readiness) - 判断依赖服务是否可用

    检查:
    - PostgreSQL 数据库连接
    - Redis 连接
    - 活跃 SSE 连接数
    """
    from src.core.lifespan_manager import get_connection_tracker

    status = {
        "status": "ready",
        "service": "ai-interview",
        "checks": {}
    }

    # Check database
    try:
        from src.db.database import get_database_manager
        db = get_database_manager()
        async with db.engine.connect() as conn:
            await conn.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Redis
    try:
        from src.db.redis_client import redis_client
        client = await redis_client.get_client()
        await client.ping()
        status["checks"]["redis"] = "ok"
    except Exception as e:
        status["checks"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check active connections
    tracker = get_connection_tracker()
    status["checks"]["active_connections"] = tracker.active_count

    return status


@app.get("/health/startup")
async def startup_check():
    """
    启动检查 (Startup) - 用于 Kubernetes startup probe

    在启动完成前返回 error，启动完成后返回 ok
    """
    # 如果 lifespan 已完成 startup 阶段，说明启动成功
    from src.core.lifespan_manager import lifespan_state
    if lifespan_state.get("_startup_complete"):
        return {"status": "ok", "message": "Startup complete"}
    return {"status": "error", "message": "Still starting up"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "AI Interview Agent",
        "version": "0.1.0",
        "docs": "/docs",
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    from src.config import get_server_config

    cfg = get_server_config()
    uvicorn.run(
        "src.main:app",
        host=cfg.host,
        port=cfg.port,
        reload=cfg.reload,
        workers=cfg.workers,
    )
