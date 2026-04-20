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
    BM25SparseRetriever,
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


class TestBM25SparseRetriever:
    """Test BM25SparseRetriever class for keyword-based sparse retrieval"""

    def test_bm25_initialization(self):
        """Test BM25SparseRetriever can be initialized"""
        retriever = BM25SparseRetriever(top_k=5)
        assert retriever._top_k == 5
        assert retriever._k1 == 1.5
        assert retriever._b == 0.75
        assert retriever._documents == []

    def test_bm25_initialization_with_documents(self):
        """Test BM25SparseRetriever with documents"""
        mock_doc = MagicMock()
        mock_doc.page_content = "Python programming language"

        retriever = BM25SparseRetriever(
            documents=[mock_doc],
            k1=1.8,
            b=0.8,
            top_k=3
        )
        assert retriever._top_k == 3
        assert len(retriever._documents) == 1

    def test_bm25_tokenize(self):
        """Test BM25 tokenization"""
        retriever = BM25SparseRetriever()
        tokens = retriever._tokenize("Python Programming Language 123")
        assert "python" in tokens
        assert "programming" in tokens
        assert "language" in tokens
        assert "123" in tokens

    def test_bm25_tokenize_removes_special_chars(self):
        """Test BM25 tokenization removes special characters"""
        retriever = BM25SparseRetriever()
        tokens = retriever._tokenize("Hello, World! @2024 #test")
        assert "," not in tokens
        assert "!" not in tokens
        assert "@" not in tokens
        assert "hello" in tokens
        assert "world" in tokens

    def test_bm25_with_mock_documents(self):
        """Test BM25 retrieval with mock documents"""
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Python programming language"
        mock_doc1.metadata = {"type": "skill"}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Java Spring Boot microservices"
        mock_doc2.metadata = {"type": "skill"}

        mock_doc3 = MagicMock()
        mock_doc3.page_content = "Distributed system design"
        mock_doc3.metadata = {"type": "responsibility"}

        retriever = BM25SparseRetriever(
            documents=[mock_doc1, mock_doc2, mock_doc3],
            top_k=2
        )

        # Test exact match
        results = retriever._get_relevant_documents("Python")
        assert len(results) <= 2
        assert results[0].page_content == "Python programming language"
        assert "score" in results[0].metadata

    def test_bm25_returns_empty_for_empty_query(self):
        """Test BM25 returns empty for empty query"""
        retriever = BM25SparseRetriever()
        results = retriever._get_relevant_documents("")
        assert results == []

    def test_bm25_returns_empty_when_no_documents(self):
        """Test BM25 returns empty when no documents indexed"""
        retriever = BM25SparseRetriever()
        results = retriever._get_relevant_documents("Python")
        assert results == []

    def test_bm25_scores_higher_for_exact_match(self):
        """Test BM25 gives higher score to exact matches"""
        # Use corpus where search term appears in <50% of docs for positive IDF
        # python appears in 2/5 = 40% of docs
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Python Django web"
        mock_doc1.metadata = {}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Java Spring backend"
        mock_doc2.metadata = {}

        mock_doc3 = MagicMock()
        mock_doc3.page_content = "Ruby Rails web"
        mock_doc3.metadata = {}

        mock_doc4 = MagicMock()
        mock_doc4.page_content = "Python Flask API"
        mock_doc4.metadata = {}

        mock_doc5 = MagicMock()
        mock_doc5.page_content = "JavaScript React"
        mock_doc5.metadata = {}

        retriever = BM25SparseRetriever(
            documents=[mock_doc1, mock_doc2, mock_doc3, mock_doc4, mock_doc5],
            top_k=2
        )

        results = retriever._get_relevant_documents("Python")
        # Python docs should be returned first
        assert results[0].page_content == "Python Django web"
        # Score should be higher than 0 (positive IDF since python appears in <50% docs)
        assert results[0].metadata["score"] > 0

    @pytest.mark.asyncio
    async def test_bm25_aget_relevant_documents(self):
        """Test async version of BM25 retrieval"""
        mock_doc = MagicMock()
        mock_doc.page_content = "Test document"
        mock_doc.metadata = {"type": "test"}

        retriever = BM25SparseRetriever(
            documents=[mock_doc],
            top_k=1
        )

        results = await retriever._aget_relevant_documents("Test")
        assert len(results) == 1
        assert results[0].page_content == "Test document"

    def test_bm25_add_documents(self):
        """Test adding documents to BM25 index"""
        retriever = BM25SparseRetriever()

        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Document 1"
        mock_doc1.metadata = {}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Document 2"
        mock_doc2.metadata = {}

        retriever.add_documents([mock_doc1])
        assert len(retriever._documents) == 1

        retriever.add_documents([mock_doc2])
        assert len(retriever._documents) == 2


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
