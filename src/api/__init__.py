"""
FastAPI API Module

面试 API 路由：
- /interview/* - 面试相关接口
- /train/* - 专项训练接口
- /knowledge/* - 知识库接口
"""

# Import submodules to register routes
from src.api import interview, training, knowledge

# Import routers after submodules have registered their routes
from src.api.routers import interview_router, training_router, knowledge_router

__all__ = ["interview_router", "training_router", "knowledge_router"]
