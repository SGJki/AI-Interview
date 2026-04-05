"""
Tests for RAG Enhancement Features

Tests for MultiVectorRetriever, HybridRetriever, Reranker, and fusion methods.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

from src.tools.rag_enhancements import (
    FusionType,
    MultiVectorRetriever,
    HybridRetriever,
    Reranker,
    fusion_results,
    retrieve_with_fusion,
)


class TestFusionType:
    """Test FusionType enum"""

    def test_fusion_type_rrf(self):
        """Test RRF fusion type"""
        assert FusionType.RRF.value == "rrf"
        assert FusionType.RRF.name == "RRF"

    def test_fusion_type_drr(self):
        """Test DRR fusion type"""
        assert FusionType.DRR.value == "drr"
        assert FusionType.DRR.name == "DRR"

    def test_fusion_type_sbert(self):
        """Test SBERT fusion type"""
        assert FusionType.SBERT.value == "sbert"
        assert FusionType.SBERT.name == "SBERT"


class TestMultiVectorRetriever:
    """Test MultiVectorRetriever class"""

    def test_multi_vector_retriever_initialization(self):
        """Test MultiVectorRetriever can be initialized"""
        retriever = MultiVectorRetriever(
            vectorstores=["chroma", "pgvector"],
            weights=[0.6, 0.4]
        )
        assert retriever.vectorstores == ["chroma", "pgvector"]
        assert retriever.weights == [0.6, 0.4]

    def test_multi_vector_retriever_default_weights(self):
        """Test default weights are equal"""
        retriever = MultiVectorRetriever(
            vectorstores=["chroma", "pgvector", "milvus"]
        )
        # Default weights should be equal
        assert len(retriever.weights) == 3
        assert all(w == 1.0 / 3.0 for w in retriever.weights)

    @pytest.mark.asyncio
    async def test_multi_vector_retriever_invoke(self):
        """Test MultiVectorRetriever invoke method"""
        mock_doc = MagicMock()
        mock_doc.page_content = "Test document"
        mock_doc.metadata = {"source": "chroma", "score": 0.9}

        # Create mock retriever
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[mock_doc])

        mock_vs1 = MagicMock()
        mock_vs1.as_retriever.return_value = mock_retriever

        mock_vs2 = MagicMock()
        mock_vs2.as_retriever.return_value = mock_retriever

        retriever = MultiVectorRetriever(
            vectorstores=[mock_vs1, mock_vs2],
            weights=[0.5, 0.5]
        )

        results = await retriever.invoke("test query", top_k=5)

        assert isinstance(results, list)
        # Should return combined results from both vectorstores
        assert len(results) >= 1

    def test_multi_vector_retriever_with_empty_vectorstores(self):
        """Test MultiVectorRetriever with no vectorstores"""
        retriever = MultiVectorRetriever(vectorstores=[])
        assert retriever.vectorstores == []

    @pytest.mark.asyncio
    async def test_multi_vector_retriever_different_results_per_store(self):
        """Test results are combined from multiple vectorstores"""
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Document from chroma"
        mock_doc1.metadata = {"source": "chroma", "score": 0.9}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Document from pgvector"
        mock_doc2.metadata = {"source": "pgvector", "score": 0.85}

        # Create mock retrievers
        mock_retriever1 = AsyncMock()
        mock_retriever1.ainvoke = AsyncMock(return_value=[mock_doc1])

        mock_retriever2 = AsyncMock()
        mock_retriever2.ainvoke = AsyncMock(return_value=[mock_doc2])

        mock_vs1 = MagicMock()
        mock_vs1.as_retriever.return_value = mock_retriever1

        mock_vs2 = MagicMock()
        mock_vs2.as_retriever.return_value = mock_retriever2

        retriever = MultiVectorRetriever(
            vectorstores=[mock_vs1, mock_vs2],
            weights=[0.6, 0.4]
        )

        results = await retriever.invoke("test query", top_k=5)

        # Should get results from both stores
        assert len(results) == 2


class TestHybridRetriever:
    """Test HybridRetriever class (sparse + dense fusion)"""

    def test_hybrid_retriever_initialization(self):
        """Test HybridRetriever can be initialized"""
        retriever = HybridRetriever(
            sparse_weight=0.4,
            dense_weight=0.6
        )
        assert retriever.sparse_weight == 0.4
        assert retriever.dense_weight == 0.6

    def test_hybrid_retriever_default_weights(self):
        """Test default weights"""
        retriever = HybridRetriever()
        assert retriever.sparse_weight == 0.3
        assert retriever.dense_weight == 0.7

    @pytest.mark.asyncio
    async def test_hybrid_retriever_invoke(self):
        """Test HybridRetriever invoke method"""
        mock_doc = MagicMock()
        mock_doc.page_content = "Hybrid test document"
        mock_doc.metadata = {"source": "hybrid", "score": 0.8}

        # Create mock retrievers - HybridRetriever calls ainvoke directly
        mock_sparse_retriever = AsyncMock()
        mock_sparse_retriever.ainvoke = AsyncMock(return_value=[mock_doc])

        mock_dense_retriever = AsyncMock()
        mock_dense_retriever.ainvoke = AsyncMock(return_value=[mock_doc])

        retriever = HybridRetriever(
            sparse_retriever=mock_sparse_retriever,
            dense_retriever=mock_dense_retriever,
            sparse_weight=0.4,
            dense_weight=0.6
        )

        results = await retriever.invoke("test query", top_k=5)

        assert isinstance(results, list)
        assert len(results) >= 1


class TestReranker:
    """Test Reranker class"""

    def test_reranker_initialization(self):
        """Test Reranker can be initialized"""
        reranker = Reranker(top_n=10, threshold=0.7)
        assert reranker.top_n == 10
        assert reranker.threshold == 0.7

    def test_reranker_default_values(self):
        """Test default values"""
        reranker = Reranker()
        assert reranker.top_n == 5
        assert reranker.threshold == 0.0

    @pytest.mark.asyncio
    async def test_reranker_invoke(self):
        """Test Reranker invoke method"""
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Document 1"
        mock_doc1.metadata = {"score": 0.9}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Document 2"
        mock_doc2.metadata = {"score": 0.7}

        mock_doc3 = MagicMock()
        mock_doc3.page_content = "Document 3"
        mock_doc3.metadata = {"score": 0.5}

        reranker = Reranker(top_n=2, threshold=0.6)

        results = await reranker.invoke(
            query="test query",
            documents=[mock_doc1, mock_doc2, mock_doc3]
        )

        assert isinstance(results, list)
        # Should only return top_n=2 results
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_reranker_respects_threshold(self):
        """Test Reranker respects threshold"""
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Low score doc"
        mock_doc1.metadata = {"score": 0.3}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "High score doc"
        mock_doc2.metadata = {"score": 0.9}

        reranker = Reranker(top_n=5, threshold=0.6)

        results = await reranker.invoke(
            query="test query",
            documents=[mock_doc1, mock_doc2]
        )

        # Should filter out doc with score < 0.6
        assert len(results) == 1
        assert results[0].metadata["score"] >= 0.6

    @pytest.mark.asyncio
    async def test_reranker_with_empty_documents(self):
        """Test reranker with empty document list"""
        reranker = Reranker()
        results = await reranker.invoke(query="test", documents=[])
        assert results == []


class TestFusionResults:
    """Test fusion_results function"""

    @pytest.mark.asyncio
    async def test_fusion_results_rrf(self):
        """Test RRF fusion algorithm"""
        docs1 = [
            MagicMock(page_content="Doc A", metadata={"source": "vs1", "rank": 1}),
            MagicMock(page_content="Doc B", metadata={"source": "vs1", "rank": 2}),
        ]

        docs2 = [
            MagicMock(page_content="Doc B", metadata={"source": "vs2", "rank": 1}),
            MagicMock(page_content="Doc C", metadata={"source": "vs2", "rank": 2}),
        ]

        result = await fusion_results(
            results_list=[docs1, docs2],
            fusion_type=FusionType.RRF,
            top_k=3
        )

        assert isinstance(result, list)
        assert len(result) <= 3
        # Doc B should appear (common to both)
        # Doc A and Doc C should also appear

    @pytest.mark.asyncio
    async def test_fusion_results_drr(self):
        """Test DRR fusion algorithm"""
        docs1 = [
            MagicMock(page_content="Doc A", metadata={"source": "vs1", "score": 0.9}),
        ]

        docs2 = [
            MagicMock(page_content="Doc B", metadata={"source": "vs2", "score": 0.8}),
        ]

        result = await fusion_results(
            results_list=[docs1, docs2],
            fusion_type=FusionType.DRR,
            top_k=3
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fusion_results_sbert(self):
        """Test SBERT fusion algorithm"""
        docs1 = [
            MagicMock(page_content="Doc A", metadata={"source": "vs1"}),
        ]

        docs2 = [
            MagicMock(page_content="Doc B", metadata={"source": "vs2"}),
        ]

        result = await fusion_results(
            results_list=[docs1, docs2],
            fusion_type=FusionType.SBERT,
            top_k=3
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fusion_results_empty_input(self):
        """Test fusion with empty input"""
        result = await fusion_results(
            results_list=[],
            fusion_type=FusionType.RRF,
            top_k=5
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_fusion_results_single_source(self):
        """Test fusion with single source"""
        docs = [
            MagicMock(page_content="Doc A", metadata={"source": "vs1"}),
            MagicMock(page_content="Doc B", metadata={"source": "vs1"}),
        ]

        result = await fusion_results(
            results_list=[docs],
            fusion_type=FusionType.RRF,
            top_k=5
        )

        assert len(result) == 2


class TestRetrieveWithFusion:
    """Test retrieve_with_fusion function"""

    @pytest.mark.asyncio
    async def test_retrieve_with_fusion_basic(self):
        """Test basic fusion retrieval"""
        mock_vs = AsyncMock()
        mock_vs.as_retriever.return_value.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Test doc", metadata={"source": "test"})
        ])

        with patch("src.tools.rag_enhancements.get_vectorstore", return_value=mock_vs):
            result = await retrieve_with_fusion(
                query="test query",
                top_k=5,
                fusion_type=FusionType.RRF
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_retrieve_with_fusion_empty_query(self):
        """Test empty query returns empty"""
        result = await retrieve_with_fusion(
            query="",
            top_k=5,
            fusion_type=FusionType.RRF
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_retrieve_with_fusion_with_metadata_filter(self):
        """Test fusion retrieval with metadata filter"""
        mock_vs = AsyncMock()
        mock_vs.as_retriever.return_value.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Filtered doc", metadata={"type": "question"})
        ])

        with patch("src.tools.rag_enhancements.get_vectorstore", return_value=mock_vs):
            result = await retrieve_with_fusion(
                query="test query",
                top_k=5,
                fusion_type=FusionType.RRF,
                filter_metadata={"type": "question"}
            )

            assert isinstance(result, list)


class TestRAGEnhancementsIntegration:
    """Integration tests for RAG enhancements"""

    @pytest.mark.asyncio
    async def test_full_pipeline_multi_vector_fusion(self):
        """Test full pipeline with multi-vector fusion"""
        # Create mock retrievers
        mock_retriever1 = AsyncMock()
        mock_retriever1.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Doc from VS1", metadata={"source": "vs1", "score": 0.9})
        ])

        mock_retriever2 = AsyncMock()
        mock_retriever2.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Doc from VS2", metadata={"source": "vs2", "score": 0.85})
        ])

        # Create mock vectorstores that return retrievers
        mock_vs1 = MagicMock()
        mock_vs1.as_retriever.return_value = mock_retriever1

        mock_vs2 = MagicMock()
        mock_vs2.as_retriever.return_value = mock_retriever2

        # MultiVectorRetriever with fusion
        multi_retriever = MultiVectorRetriever(
            vectorstores=[mock_vs1, mock_vs2],
            weights=[0.5, 0.5]
        )

        results = await multi_retriever.invoke("test query", top_k=5)

        assert len(results) == 2
        sources = {doc.metadata.get("source") for doc in results}
        assert "vs1" in sources
        assert "vs2" in sources

    @pytest.mark.asyncio
    async def test_hybrid_with_reranking(self):
        """Test hybrid retrieval with reranking"""
        # HybridRetriever calls ainvoke directly on the retriever
        mock_sparse_retriever = AsyncMock()
        mock_sparse_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Sparse doc 1", metadata={"score": 0.7}),
            MagicMock(page_content="Sparse doc 2", metadata={"score": 0.5}),
        ])

        mock_dense_retriever = AsyncMock()
        mock_dense_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Dense doc 1", metadata={"score": 0.8}),
            MagicMock(page_content="Dense doc 2", metadata={"score": 0.6}),
        ])

        # Create hybrid retriever (pass retriever directly, not the vectorstore)
        hybrid = HybridRetriever(
            sparse_retriever=mock_sparse_retriever,
            dense_retriever=mock_dense_retriever,
            sparse_weight=0.4,
            dense_weight=0.6
        )

        # Create reranker
        reranker = Reranker(top_n=2, threshold=0.5)

        # Invoke hybrid
        hybrid_results = await hybrid.invoke("test query", top_k=4)

        # Rerank results
        reranked = await reranker.invoke("test query", hybrid_results)

        assert len(reranked) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
