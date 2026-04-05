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
        # 注意：knowledge_base_id 当前未使用，因为使用的是全局向量存储
        results = await retrieve_knowledge(
            query=request.query,
            top_k=request.top_k,
        )

        # 转换 Document 对象为字典
        results_dict = []
        for doc in results if results else []:
            results_dict.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            })

        return RagQueryResult(
            query=request.query,
            results=results_dict,
            total=len(results_dict),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query RAG: {str(e)}")


@knowledge_router.post("/build")
async def build_knowledge(request: BuildKnowledgeRequest) -> BuildKnowledgeResult:
    """
    构建知识库

    支持多种数据源：
    - resume: 从简历文本构建
    - preset: 构建预设面试题库
    - standard: 构建标准回答知识库
    - skill_point: 从技能点列表构建

    Args:
        request: 构建知识库请求

    Returns:
        BuildKnowledgeResult: 构建结果
    """
    try:
        from src.services.knowledge_base_service import KnowledgeBaseService

        kb_service = KnowledgeBaseService()

        if request.source_type == "resume":
            # 从简历构建
            if not request.content:
                raise HTTPException(status_code=400, detail="简历内容不能为空")

            result = await kb_service.build_from_resume(
                resume_content=request.content,
                resume_id=request.knowledge_base_id or "default",
            )

        elif request.source_type == "preset":
            # 构建预设题库
            result = await kb_service.build_preset_question_bank()

        elif request.source_type == "standard":
            # 构建标准回答库
            result = await kb_service.build_standard_answer_kb()

        elif request.source_type == "skill_point":
            # 从技能点构建
            skill_points = request.skill_points or []
            result = await kb_service.build_skill_point_kb(skill_points)

        elif request.source_type == "full":
            # 构建完整知识库
            result = await kb_service.build_all()

        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的 source_type: {request.source_type}"
            )

        # 提取文档数量
        documents_count = 0
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, dict) and "documents_added" in value:
                    documents_count += value["documents_added"]
            if "documents_added" in result:
                documents_count = result["documents_added"]
            if "questions_added" in result:
                documents_count = result["questions_added"]

        return BuildKnowledgeResult(
            knowledge_base_id=request.knowledge_base_id,
            status=result.get("status", "completed"),
            documents_count=documents_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build knowledge: {str(e)}")
