"""
FastAPI Application Entry Point

AI Interview Agent - FastAPI Server

启动方式:
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys

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


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="AI Interview Agent",
    description="AI 面试助手 - 支持实时点评和流式输出",
    version="0.1.0",
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
# Health Check Endpoint
# =============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "ai-interview"}


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
