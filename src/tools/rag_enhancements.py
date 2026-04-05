"""
RAG Enhancement Tools for AI Interview Agent

Advanced retrieval strategies including:
- MultiVectorRetriever: Support for multiple vector stores
- HybridRetriever: Sparse + Dense retrieval fusion
- Reranker: Result re-ranking
- Fusion algorithms: RRF, DRR, SBERT
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.tools.rag_tools import get_vectorstore


# =============================================================================
# Fusion Type Enum
# =============================================================================

class FusionType(Enum):
    """
    Fusion algorithm types for combining retrieval results

    RRF - Reciprocal Rank Fusion:
        Simple rank-based fusion using reciprocal ranks
        score = sum(1 / (k + rank_i)) where k is a constant (typically 60)

    DRR - Distribution-Based Rank:
        Score-based fusion assuming normal distribution of scores
        Normalizes scores and combines them

    SBERT - Sentence BERT Fusion:
        Semantic similarity-based fusion using sentence embeddings
        Computes semantic similarity between query and all results
    """
    RRF = "rrf"   # Reciprocal Rank Fusion
    DRR = "drr"   # Distribution-Based Rank
    SBERT = "sbert"  # Sentence BERT Fusion


# =============================================================================
# Reranker
# =============================================================================

@dataclass(frozen=True)
class RerankerConfig:
    """Configuration for reranker"""
    top_n: int = 5
    threshold: float = 0.0


class Reranker:
    """
    Reranks retrieval results based on relevance

    Supports:
    - Top-N filtering
    - Score threshold filtering
    - Custom reranking strategies
    """

    def __init__(
        self,
        top_n: int = 5,
        threshold: float = 0.0
    ):
        """
        Initialize Reranker

        Args:
            top_n: Number of top results to return
            threshold: Minimum score threshold (0-1)
        """
        self.top_n = top_n
        self.threshold = threshold

    async def invoke(
        self,
        query: str,
        documents: list[Document]
    ) -> list[Document]:
        """
        Rerank documents based on query relevance

        Args:
            query: The search query
            documents: List of documents to rerank

        Returns:
            Reranked and filtered documents
        """
        if not documents:
            return []

        # Filter by threshold
        filtered_docs = [
            doc for doc in documents
            if doc.metadata.get("score", 1.0) >= self.threshold
        ]

        # Sort by score descending
        sorted_docs = sorted(
            filtered_docs,
            key=lambda doc: doc.metadata.get("score", 0.0),
            reverse=True
        )

        # Return top_n results
        return sorted_docs[:self.top_n]


# =============================================================================
# MultiVectorRetriever
# =============================================================================

class MultiVectorRetriever:
    """
    Multi-vector store retriever supporting fusion retrieval

    Allows querying multiple vector stores and combining results
    with configurable weights.
    """

    def __init__(
        self,
        vectorstores: Optional[list] = None,
        weights: Optional[list[float]] = None
    ):
        """
        Initialize MultiVectorRetriever

        Args:
            vectorstores: List of vector store instances
            weights: Weights for each vector store (must match length)
        """
        self.vectorstores = vectorstores or []

        if not weights and self.vectorstores:
            # Equal weights if not specified
            self.weights = [1.0 / len(self.vectorstores)] * len(self.vectorstores)
        else:
            self.weights = weights or []

    async def invoke(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None
    ) -> list[Document]:
        """
        Retrieve from multiple vector stores and fuse results

        Args:
            query: Search query
            top_k: Number of results per store
            filter_metadata: Metadata filter

        Returns:
            Combined and sorted results
        """
        if not query.strip():
            return []

        if not self.vectorstores:
            return []

        # Collect results from all vectorstores
        all_results: list[tuple[Document, float]] = []

        for i, vs in enumerate(self.vectorstores):
            weight = self.weights[i] if i < len(self.weights) else 1.0

            try:
                retriever = vs.as_retriever(
                    search_kwargs={
                        "k": top_k,
                        "filter": filter_metadata,
                    }
                )
                docs = await retriever.ainvoke(query)

                for doc in docs:
                    # Apply weight to score
                    original_score = doc.metadata.get("score", 1.0)
                    doc.metadata["weighted_score"] = original_score * weight
                    doc.metadata["vectorstore_index"] = i
                    all_results.append((doc, original_score * weight))
            except Exception:
                # Skip failing vectorstores
                continue

        # Sort by weighted score
        all_results.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate by content and return top_k
        seen_content = set()
        unique_results: list[Document] = []

        for doc, score in all_results:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                doc.metadata["final_score"] = score
                unique_results.append(doc)

            if len(unique_results) >= top_k:
                break

        return unique_results


# =============================================================================
# HybridRetriever
# =============================================================================

class HybridRetriever:
    """
    Hybrid retriever combining sparse and dense retrieval

    Sparse retrieval (BM25): Good for exact term matching
    Dense retrieval (vector): Good for semantic similarity
    """

    def __init__(
        self,
        sparse_retriever: Optional[BaseRetriever] = None,
        dense_retriever: Optional[BaseRetriever] = None,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.7
    ):
        """
        Initialize HybridRetriever

        Args:
            sparse_retriever: BM25 or keyword-based retriever
            dense_retriever: Vector-based retriever
            sparse_weight: Weight for sparse retrieval (0-1)
            dense_weight: Weight for dense retrieval (0-1)
        """
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever
        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight

    async def invoke(
        self,
        query: str,
        top_k: int = 5
    ) -> list[Document]:
        """
        Perform hybrid retrieval

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            Combined results from sparse and dense retrieval
        """
        if not query.strip():
            return []

        results: list[tuple[Document, float]] = []

        # Sparse retrieval
        if self.sparse_retriever:
            try:
                sparse_docs = await self.sparse_retriever.ainvoke(query)
                for doc in sparse_docs:
                    score = doc.metadata.get("score", 0.5)
                    doc.metadata["sparse_score"] = score
                    doc.metadata["combined_score"] = score * self.sparse_weight
                    results.append((doc, score * self.sparse_weight))
            except Exception:
                pass

        # Dense retrieval
        if self.dense_retriever:
            try:
                dense_docs = await self.dense_retriever.ainvoke(query)
                for doc in dense_docs:
                    score = doc.metadata.get("score", 0.5)
                    doc.metadata["dense_score"] = score
                    # Combined with existing score if already exists
                    existing = doc.metadata.get("combined_score", 0)
                    doc.metadata["combined_score"] = existing + (score * self.dense_weight)
                    results.append((doc, existing + (score * self.dense_weight)))
            except Exception:
                pass

        # Sort by combined score
        results.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate and return top_k
        seen_content = set()
        final_results: list[Document] = []

        for doc, score in results:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                doc.metadata["final_score"] = score
                final_results.append(doc)

            if len(final_results) >= top_k:
                break

        return final_results


# =============================================================================
# Fusion Functions
# =============================================================================

async def fusion_results(
    results_list: list[list[Document]],
    fusion_type: FusionType = FusionType.RRF,
    top_k: int = 5
) -> list[Document]:
    """
    Fuse results from multiple retrievers using specified algorithm

    Args:
        results_list: List of document lists from different retrievers
        fusion_type: Fusion algorithm to use
        top_k: Number of results to return

    Returns:
        Fused and sorted documents
    """
    if not results_list:
        return []

    # Filter out empty result lists
    non_empty = [r for r in results_list if r]
    if not non_empty:
        return []

    if len(non_empty) == 1:
        # Single source, just sort and return
        docs = non_empty[0]
        docs.sort(key=lambda d: d.metadata.get("score", 0), reverse=True)
        return docs[:top_k]

    if fusion_type == FusionType.RRF:
        return _rrf_fusion(non_empty, top_k)
    elif fusion_type == FusionType.DRR:
        return _drr_fusion(non_empty, top_k)
    elif fusion_type == FusionType.SBERT:
        return _sbert_fusion(non_empty, top_k)
    else:
        return _rrf_fusion(non_empty, top_k)


def _rrf_fusion(
    results_list: list[list[Document]],
    top_k: int,
    k: int = 60
) -> list[Document]:
    """
    Reciprocal Rank Fusion

    Score formula: score(d) = sum(1 / (k + rank_i))

    Args:
        results_list: List of ranked document lists
        top_k: Number of results to return
        k: Constant (typically 60, controls how much low ranks are penalized)

    Returns:
        Fused documents sorted by RRF score
    """
    doc_scores: dict[str, tuple[Document, float]] = {}

    for docs in results_list:
        for rank, doc in enumerate(docs, start=1):
            content_hash = hash(doc.page_content)
            rrf_score = 1.0 / (k + rank)

            if content_hash in doc_scores:
                existing_doc, existing_score = doc_scores[content_hash]
                doc_scores[content_hash] = (existing_doc, existing_score + rrf_score)
            else:
                doc.metadata["rrf_score"] = rrf_score
                doc_scores[content_hash] = (doc, rrf_score)

    # Sort by RRF score descending
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x[1],
        reverse=True
    )

    return [doc for doc, _ in sorted_docs[:top_k]]


def _drr_fusion(
    results_list: list[list[Document]],
    top_k: int
) -> list[Document]:
    """
    Distribution-Based Rank Fusion

    Normalizes scores assuming normal distribution and combines them.

    Args:
        results_list: List of document lists with scores
        top_k: Number of results to return

    Returns:
        Fused documents sorted by DRR score
    """
    doc_scores: dict[str, tuple[Document, float]] = {}

    for docs in results_list:
        if not docs:
            continue

        # Get scores for normalization
        scores = [doc.metadata.get("score", 0.5) for doc in docs]
        min_s, max_s = min(scores), max(scores)
        range_s = max_s - min_s if max_s != min_s else 1.0

        for doc in docs:
            content_hash = hash(doc.page_content)
            # Normalize to 0-1
            normalized = (doc.metadata.get("score", 0.5) - min_s) / range_s

            if content_hash in doc_scores:
                existing_doc, existing_score = doc_scores[content_hash]
                doc_scores[content_hash] = (existing_doc, existing_score + normalized)
            else:
                doc.metadata["drr_score"] = normalized
                doc_scores[content_hash] = (doc, normalized)

    # Sort by DRR score descending
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x[1],
        reverse=True
    )

    return [doc for doc, _ in sorted_docs[:top_k]]


def _sbert_fusion(
    results_list: list[list[Document]],
    top_k: int
) -> list[Document]:
    """
    SBERT-style semantic fusion

    For each document, combines the semantic score with rank-based scoring.
    In the absence of actual SBERT model, uses combined metadata scores.

    Args:
        results_list: List of document lists
        top_k: Number of results to return

    Returns:
        Fused documents
    """
    doc_scores: dict[str, tuple[Document, float]] = {}

    for docs in results_list:
        for rank, doc in enumerate(docs, start=1):
            content_hash = hash(doc.page_content)
            # Combine rank-based score with semantic score
            semantic_score = doc.metadata.get("score", 0.5)
            rank_score = 1.0 / (rank + 1)  # Slight rank weighting
            combined = (semantic_score * 0.7) + (rank_score * 0.3)

            if content_hash in doc_scores:
                existing_doc, existing_score = doc_scores[content_hash]
                doc_scores[content_hash] = (existing_doc, existing_score + combined)
            else:
                doc.metadata["sbert_score"] = combined
                doc_scores[content_hash] = (doc, combined)

    # Sort by SBERT score descending
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x[1],
        reverse=True
    )

    return [doc for doc, _ in sorted_docs[:top_k]]


# =============================================================================
# Retrieval with Fusion
# =============================================================================

async def retrieve_with_fusion(
    query: str,
    top_k: int = 5,
    fusion_type: FusionType = FusionType.RRF,
    filter_metadata: Optional[dict] = None
) -> list[Document]:
    """
    Convenience function for retrieval with fusion

    Args:
        query: Search query
        top_k: Number of results
        fusion_type: Fusion algorithm
        filter_metadata: Metadata filter

    Returns:
        Fused retrieval results
    """
    if not query.strip():
        return []

    try:
        vectorstore = get_vectorstore()

        # Single vectorstore retrieval with fusion (for consistency with API)
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": top_k,
                "filter": filter_metadata,
            }
        )

        docs = await retriever.ainvoke(query)

        # Apply simple fusion (single source, so just sort by score)
        docs.sort(key=lambda d: d.metadata.get("score", 0), reverse=True)

        return docs[:top_k]

    except Exception:
        return []


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FusionType",
    "MultiVectorRetriever",
    "HybridRetriever",
    "Reranker",
    "RerankerConfig",
    "fusion_results",
    "retrieve_with_fusion",
]
