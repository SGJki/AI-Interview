"""
API Routers Configuration

定义所有 API 路由路由器
"""

from fastapi import APIRouter

# Interview Router
interview_router = APIRouter(prefix="/interview", tags=["interview"])

# Training Router
training_router = APIRouter(prefix="/train", tags=["training"])

# Knowledge Router
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
