"""
Knowledge API Endpoints - FastAPI Route Handlers

知识库相关 API 端点：
- POST /rag/query - 查询 RAG 知识库
- POST /knowledge/build - 构建知识库
"""

from fastapi import APIRouter, HTTPException

from src.api.routers import knowledge_router
from src.api.models import (
    RagQueryRequest,
    BuildKnowledgeRequest,
    RagQueryResult,
    BuildKnowledgeResult,
)


@knowledge_router.post("/query")
async def query_rag(request: RagQueryRequest) -> RagQueryResult:
    """
    查询 RAG 知识库

    Args:
        request: RAG 查询请求

    Returns:
        RagQueryResult: 查询结果
    """
    try:
        from src.tools.rag_tools import retrieve_knowledge

        # 执行 RAG 查询
        results = await retrieve_knowledge(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            top_k=request.top_k,
        )

        return RagQueryResult(
            query=request.query,
            results=results if isinstance(results, list) else [],
            total=len(results) if isinstance(results, list) else 0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query RAG: {str(e)}")


@knowledge_router.post("/build")
async def build_knowledge(request: BuildKnowledgeRequest) -> BuildKnowledgeResult:
    """
    构建知识库

    Args:
        request: 构建知识库请求

    Returns:
        BuildKnowledgeResult: 构建结果
    """
    try:
        # TODO: 实现知识库构建逻辑
        # 1. 根据 source_type 处理不同数据源
        # 2. 调用 vector store 构建索引
        # 3. 返回构建状态

        return BuildKnowledgeResult(
            knowledge_base_id=request.knowledge_base_id,
            status="building",
            documents_count=0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build knowledge: {str(e)}")
