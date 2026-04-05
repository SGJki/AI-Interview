"""
Enterprise Knowledge Retrieval - Phase 3

Dynamic retrieval of enterprise-level technical best practices
using SearchAPI or LLM Function Calling for real-time knowledge acquisition
"""

from dataclasses import dataclass, field
from typing import Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.tools.rag_tools import retrieve_knowledge


# =============================================================================
# Knowledge Fusion Result
# =============================================================================

@dataclass(frozen=True)
class KnowledgeFusionResult:
    """
    Knowledge fusion result combining dynamic and local retrieval

    Attributes:
        documents: Combined and sorted document list
        has_dynamic_retrieval: Whether dynamic retrieval contributed results
        has_local_knowledge: Whether local RAG contributed results
        fusion_applied: Whether fusion logic was applied
    """
    documents: tuple[Document, ...] = field(default_factory=tuple)
    has_dynamic_retrieval: bool = False
    has_local_knowledge: bool = False
    fusion_applied: bool = False


# =============================================================================
# Dynamic Retrieval Functions
# =============================================================================

async def search_enterprise_best_practices(
    skill_point: str,
    top_k: int = 5,
    threshold: float = 0.7
) -> list[Document]:
    """
    Search enterprise knowledge base for best practices

    This function would connect to an enterprise SearchAPI or internal
    knowledge management system. Currently returns empty list as placeholder.

    Args:
        skill_point: Technical skill point name
        top_k: Maximum number of results
        threshold: Relevance threshold (0-1)

    Returns:
        List of relevant documents from enterprise knowledge base
    """
    # TODO: Integrate with enterprise SearchAPI
    # Expected: Connect to internal knowledge management system
    # Format: API call to enterprise knowledge base with skill_point query

    if not skill_point or not skill_point.strip():
        return []

    # Placeholder implementation - returns empty list
    # In production, this would call:
    # - Enterprise SearchAPI
    # - Internal knowledge management system
    # - Confluence/Notion/Slack search APIs
    return []


async def search_web_best_practices(
    skill_point: str,
    top_k: int = 5
) -> list[Document]:
    """
    Search web for latest technical best practices

    Uses web search to supplement enterprise knowledge when
    local KB doesn't have sufficient coverage.

    Args:
        skill_point: Technical skill point name
        top_k: Maximum number of results

    Returns:
        List of relevant documents from web search
    """
    if not skill_point or not skill_point.strip():
        return []

    # TODO: Integrate with Exa/ Tavily / SerpAPI for web search
    # Expected: Real-time web search for latest best practices
    #
    # Example integration:
    # from langchain_community.retrievers import TavilySearchAPIRetriever
    #
    # retriever = TavilySearchAPIRetriever(api_key=os.environ.get("TAVILY_API_KEY"))
    # results = await retriever.ainvoke(skill_point)
    #
    # For now, return empty list - web search is optional fallback

    return []


async def retrieve_enterprise_knowledge(
    skill_point: str,
    top_k: int = 5
) -> list[Document]:
    """
    Dynamically retrieve enterprise-level technical best practices

    This function implements the main enterprise knowledge retrieval interface:
    1. First attempts to retrieve from enterprise knowledge base
    2. Falls back to web search if enterprise KB returns no results
    3. Returns combined and ranked results

    Args:
        skill_point: Technical skill point name (e.g., "Redis", "分布式缓存", "微服务")

    Returns:
        List of relevant Document objects sorted by relevance
    """
    if not skill_point or not skill_point.strip():
        return []

    # Normalize skill point (strip whitespace)
    normalized_skill = skill_point.strip()

    # Step 1: Try enterprise knowledge base
    enterprise_docs = await search_enterprise_best_practices(
        normalized_skill,
        top_k=top_k
    )

    # Step 2: If no enterprise results, fall back to web search
    if not enterprise_docs:
        web_docs = await search_web_best_practices(
            normalized_skill,
            top_k=top_k
        )
        if web_docs:
            return web_docs

    return enterprise_docs


async def retrieve_enterprise_knowledge_with_fusion(
    skill_point: str,
    top_k: int = 5,
    dynamic_weight: float = 0.6,
    local_weight: float = 0.4
) -> KnowledgeFusionResult:
    """
    Retrieve and fuse enterprise knowledge with local RAG knowledge

    Fusion strategy:
    - Dynamic retrieval (enterprise KB + web): weighted by configurable weight
    - Local RAG knowledge: weighted by configurable weight
    - Final ranking: weighted_score = (dynamic_score * dynamic_weight) +
                                     (local_score * local_weight)

    Args:
        skill_point: Technical skill point name
        top_k: Maximum number of results per source
        dynamic_weight: Weight for dynamic retrieval (default 0.6)
        local_weight: Weight for local RAG (default 0.4)

    Returns:
        KnowledgeFusionResult with combined documents
    """
    if not skill_point or not skill_point.strip():
        return KnowledgeFusionResult()

    normalized_skill = skill_point.strip()

    # Parallel retrieval from all sources
    enterprise_docs = await search_enterprise_best_practices(normalized_skill, top_k)

    # If enterprise KB is empty, try web search as fallback
    if not enterprise_docs:
        web_docs = await search_web_best_practices(normalized_skill, top_k)
        if web_docs:
            # Mark web search results with appropriate source
            for doc in web_docs:
                doc.metadata["source"] = doc.metadata.get("source", "web_search")
            enterprise_docs = web_docs

    local_docs = await retrieve_knowledge(normalized_skill, top_k=top_k)

    # Check if fusion is needed
    has_dynamic = len(enterprise_docs) > 0
    has_local = len(local_docs) > 0

    if not has_dynamic and not has_local:
        return KnowledgeFusionResult(
            documents=(),
            has_dynamic_retrieval=False,
            has_local_knowledge=False,
            fusion_applied=False
        )

    # Apply weights to documents
    weighted_docs: list[tuple[Document, float]] = []

    for doc in enterprise_docs:
        base_score = doc.metadata.get("score", 0.9)
        weight = doc.metadata.get("weight", dynamic_weight)
        weighted_score = base_score * dynamic_weight
        doc.metadata["weighted_score"] = weighted_score
        doc.metadata["retrieval_source"] = "dynamic"
        weighted_docs.append((doc, weighted_score))

    for doc in local_docs:
        base_score = doc.metadata.get("score", 0.8)
        weight = local_weight
        weighted_score = base_score * local_weight
        doc.metadata["weighted_score"] = weighted_score
        doc.metadata["retrieval_source"] = "local"
        weighted_docs.append((doc, weighted_score))

    # Sort by weighted score descending
    weighted_docs.sort(key=lambda x: x[1], reverse=True)

    # Take top_k results
    sorted_docs = [doc for doc, _ in weighted_docs[:top_k]]

    return KnowledgeFusionResult(
        documents=tuple(sorted_docs),
        has_dynamic_retrieval=has_dynamic,
        has_local_knowledge=has_local,
        fusion_applied=has_dynamic and has_local
    )


# =============================================================================
# LangChain Tool Class (for Function Calling)
# =============================================================================

class EnterpriseKnowledgeRetriever:
    """
    Enterprise Knowledge Retriever for LangChain Agent

    This tool class enables LangChain agents to dynamically retrieve
    enterprise-level technical best practices using function calling.

    Tool Definition:
        name: "retrieve_enterprise_knowledge"
        description: "从企业级知识库检索技术最佳实践，适用于查询特定技术主题的最佳解决方案"

    Usage in LangChain Agent:
        tools = [EnterpriseKnowledgeRetriever.as_tool()]
        agent = create_react_agent(model, tools)
    """

    name = "retrieve_enterprise_knowledge"
    description = """
    从企业级知识库检索技术最佳实践。

    适用于查询以下内容：
    - 特定技术的最佳解决方案（如 Redis、Kafka、Docker）
    - 架构设计模式与实践
    - 企业内部技术标准与规范
    - 行业最佳实践与案例分析

    Args:
        skill_point: 技能点名称（如 "Redis 缓存"、"微服务架构"、"Docker 容器化"）

    Returns:
        相关知识文档列表，包含技术最佳实践和解决方案
    """

    @staticmethod
    async def invoke(skill_point: str, top_k: int = 5) -> list[Document]:
        """
        Invoke the enterprise knowledge retrieval

        Args:
            skill_point: Technical skill point name
            top_k: Maximum number of results

        Returns:
            List of relevant documents
        """
        return await retrieve_enterprise_knowledge(skill_point, top_k)

    @classmethod
    def as_tool(cls) -> "EnterpriseKnowledgeRetrieverTool":
        """
        Get as a LangChain tool instance

        Returns:
            EnterpriseKnowledgeRetrieverTool instance
        """
        return EnterpriseKnowledgeRetrieverTool(cls.name, cls.description, cls.invoke)


class EnterpriseKnowledgeRetrieverTool:
    """
    LangChain Tool wrapper for EnterpriseKnowledgeRetriever

    This class adapts the EnterpriseKnowledgeRetriever for use
    with LangChain's tool calling mechanism.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: callable
    ):
        self.name = name
        self.description = description
        self.func = func

    def __call__(self, skill_point: str, top_k: int = 5) -> list[Document]:
        """
        Synchronous call interface for LangChain

        Note: For async usage, prefer calling the function directly
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.func(skill_point, top_k)
                    )
                    return future.result()
            else:
                return asyncio.run(self.func(skill_point, top_k))
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(self.func(skill_point, top_k))
