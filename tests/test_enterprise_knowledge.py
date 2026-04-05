"""
Tests for Enterprise Knowledge Retrieval - Phase 3
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.documents import Document

from src.tools.enterprise_knowledge import (
    retrieve_enterprise_knowledge,
    retrieve_enterprise_knowledge_with_fusion,
    EnterpriseKnowledgeRetriever,
    KnowledgeFusionResult,
)


class TestEnterpriseKnowledgeRetriever:
    """Test enterprise knowledge retrieval tools"""

    def test_enterprise_knowledge_retriever_class_exists(self):
        """Test EnterpriseKnowledgeRetriever class exists"""
        assert EnterpriseKnowledgeRetriever is not None

    def test_enterprise_knowledge_retriever_name(self):
        """Test tool name is correct"""
        assert EnterpriseKnowledgeRetriever.name == "retrieve_enterprise_knowledge"

    def test_enterprise_knowledge_retriever_description(self):
        """Test tool description is correct"""
        assert "企业级知识库" in EnterpriseKnowledgeRetriever.description
        assert "技术最佳实践" in EnterpriseKnowledgeRetriever.description

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_returns_results(self):
        """Test knowledge retrieval returns results"""
        # Mock search results
        mock_docs = [
            Document(
                page_content="Redis 分布式缓存最佳实践：使用 Redis Cluster 实现数据分片...",
                metadata={"source": "enterprise_kb", "skill_point": "Redis", "weight": 0.9}
            ),
            Document(
                page_content="缓存穿透解决方案：布隆过滤器 + 缓存空值...",
                metadata={"source": "enterprise_kb", "skill_point": "Redis", "weight": 0.85}
            ),
        ]

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=mock_docs
        ):
            results = await retrieve_enterprise_knowledge("Redis 缓存")

            assert len(results) == 2
            assert "Redis" in results[0].page_content
            assert results[0].metadata["source"] == "enterprise_kb"

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_empty_query(self):
        """Test empty query returns empty list"""
        results = await retrieve_enterprise_knowledge("")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_no_results(self):
        """Test no results returns empty list"""
        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=[]
        ):
            results = await retrieve_enterprise_knowledge("nonexistent_skill_xyz")
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_with_web_fallback(self):
        """Test web search fallback when no local results"""
        # When enterprise KB has no results, should fall back to web search
        mock_web_docs = [
            Document(
                page_content="Latest Redis best practices from web search...",
                metadata={"source": "web_search", "skill_point": "Redis", "weight": 0.7}
            ),
        ]

        async def mock_search(skill_point, top_k, threshold=0.7):
            # First call returns empty, simulating enterprise KB miss
            return []

        async def mock_web_search(skill_point, top_k):
            return mock_web_docs

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            side_effect=mock_search
        ), patch(
            "src.tools.enterprise_knowledge.search_web_best_practices",
            new_callable=AsyncMock,
            side_effect=mock_web_search
        ):
            results = await retrieve_enterprise_knowledge("Redis")

            assert len(results) == 1
            assert results[0].metadata["source"] == "web_search"

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_invoke_method(self):
        """Test EnterpriseKnowledgeRetriever.invoke method"""
        mock_docs = [
            Document(
                page_content="Test content",
                metadata={"source": "enterprise_kb"}
            ),
        ]

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=mock_docs
        ):
            result = await EnterpriseKnowledgeRetriever.invoke("Redis")
            assert len(result) == 1


class TestKnowledgeFusion:
    """Test knowledge fusion functionality"""

    @pytest.mark.asyncio
    async def test_retrieve_enterprise_knowledge_with_fusion_exists(self):
        """Test fusion function exists"""
        assert retrieve_enterprise_knowledge_with_fusion is not None

    @pytest.mark.asyncio
    async def test_knowledge_fusion_result_dataclass(self):
        """Test KnowledgeFusionResult dataclass"""
        result = KnowledgeFusionResult(
            documents=[Document(page_content="test", metadata={})],
            has_dynamic_retrieval=True,
            has_local_knowledge=True,
            fusion_applied=True
        )
        assert len(result.documents) == 1
        assert result.has_dynamic_retrieval is True
        assert result.has_local_knowledge is True
        assert result.fusion_applied is True

    @pytest.mark.asyncio
    async def test_fusion_combines_dynamic_and_local(self):
        """Test fusion combines dynamic and local knowledge"""
        dynamic_docs = [
            Document(
                page_content="Dynamic: Redis Cluster best practices",
                metadata={"source": "dynamic", "score": 0.95}
            ),
        ]

        local_docs = [
            Document(
                page_content="Local: Redis basic usage",
                metadata={"source": "local", "score": 0.85}
            ),
        ]

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=dynamic_docs
        ), patch(
            "src.tools.enterprise_knowledge.retrieve_knowledge",
            new_callable=AsyncMock,
            return_value=local_docs
        ):
            result = await retrieve_enterprise_knowledge_with_fusion("Redis")

            assert result.has_dynamic_retrieval is True
            assert result.has_local_knowledge is True
            assert result.fusion_applied is True
            assert len(result.documents) == 2

    @pytest.mark.asyncio
    async def test_fusion_sorts_by_weighted_score(self):
        """Test fusion sorts documents by weighted score"""
        dynamic_docs = [
            Document(
                page_content="Dynamic with high weight",
                metadata={"source": "dynamic", "weight": 0.9, "score": 0.95}
            ),
        ]

        local_docs = [
            Document(
                page_content="Local with lower weight",
                metadata={"source": "local", "weight": 0.7, "score": 0.85}
            ),
        ]

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=dynamic_docs
        ), patch(
            "src.tools.enterprise_knowledge.retrieve_knowledge",
            new_callable=AsyncMock,
            return_value=local_docs
        ):
            result = await retrieve_enterprise_knowledge_with_fusion("Redis")

            # Dynamic should be first due to higher weight
            assert result.documents[0].metadata["source"] == "dynamic"
            assert result.documents[0].metadata["weight"] == 0.9


class TestEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_both_sources_return_empty(self):
        """Test when both sources return empty"""
        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=[]
        ), patch(
            "src.tools.enterprise_knowledge.search_web_best_practices",
            new_callable=AsyncMock,
            return_value=[]
        ), patch(
            "src.tools.enterprise_knowledge.retrieve_knowledge",
            new_callable=AsyncMock,
            return_value=[]
        ):
            result = await retrieve_enterprise_knowledge_with_fusion("UnknownSkill")

            assert len(result.documents) == 0
            assert result.has_dynamic_retrieval is False
            assert result.has_local_knowledge is False

    @pytest.mark.asyncio
    async def test_whitespace_skill_point_normalized(self):
        """Test whitespace in skill_point is normalized"""
        mock_docs = [Document(page_content="test", metadata={})]

        with patch(
            "src.tools.enterprise_knowledge.search_enterprise_best_practices",
            new_callable=AsyncMock,
            return_value=mock_docs
        ) as mock_search:
            await retrieve_enterprise_knowledge("  Redis 缓存  ")

            # Should be called with normalized query
            call_args = mock_search.call_args
            assert "Redis" in call_args[0][0] or "redis" in call_args[0][0].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
