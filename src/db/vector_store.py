"""
Vector Store using pgvector for embedding storage and similarity search

Provides:
- Text embedding generation (via configurable embedding function)
- In-memory vector storage with optional pgvector persistence
- Cosine similarity search
- Document management (add, delete, get)
"""

from typing import Callable, Optional
from uuid import uuid4
import numpy as np


class VectorStore:
    """
    Vector store for text embeddings with similarity search.

    Supports:
    - Configurable embedding function (OpenAI, local models, etc.)
    - In-memory storage with optional database persistence
    - Cosine similarity search
    - Document CRUD operations

    Example:
        def embed_fn(texts):
            return openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            ).data[0].embedding

        store = VectorStore(embed_fn, dimensions=1536)
        doc_id = store.add_text("Hello world", metadata={"source": "test"})
        results = store.find_similar("Hi there", top_k=5)
    """

    def __init__(
        self,
        embed_fn: Callable[[list[str]], list[list[float]]],
        dimensions: int = 1536,
    ):
        """
        Initialize vector store.

        Args:
            embed_fn: Function that takes a list of texts and returns embeddings.
                     Should return a list of float lists, one per input text.
            dimensions: Embedding dimensions (e.g., 1536 for OpenAI text-embedding-3-small)
        """
        self._embed_fn = embed_fn
        self.dimensions = dimensions

        # In-memory storage
        self._documents: dict[str, dict] = {}
        self._embeddings: dict[str, list[float]] = {}

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        embeddings = self._embed_fn([text])
        return embeddings[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        return self._embed_fn(texts)

    def add_text(
        self,
        text: str,
        metadata: Optional[dict] = None,
        embedding: Optional[list[float]] = None,
    ) -> str:
        """
        Add text to the vector store.

        Args:
            text: Text content to store
            metadata: Optional metadata dictionary
            embedding: Pre-computed embedding (if None, will be computed)

        Returns:
            Document ID (UUID string)
        """
        doc_id = str(uuid4())

        # Compute embedding if not provided
        if embedding is None:
            embedding = self.embed_text(text)

        self._documents[doc_id] = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        }
        self._embeddings[doc_id] = embedding

        return doc_id

    def add_texts(
        self,
        texts: list[str],
        metadata_list: Optional[list[dict]] = None,
    ) -> list[str]:
        """
        Add multiple texts to the vector store.

        Args:
            texts: List of text contents to store
            metadata_list: Optional list of metadata dictionaries

        Returns:
            List of document IDs
        """
        if metadata_list is None:
            metadata_list = [{}] * len(texts)

        # Batch embed
        embeddings = self.embed_texts(texts)

        doc_ids = []
        for i, text in enumerate(texts):
            doc_id = str(uuid4())
            self._documents[doc_id] = {
                "id": doc_id,
                "text": text,
                "metadata": metadata_list[i] if i < len(metadata_list) else {},
            }
            self._embeddings[doc_id] = embeddings[i]
            doc_ids.append(doc_id)

        return doc_ids

    def get_document(self, doc_id: str) -> Optional[dict]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dict with id, text, metadata, or None if not found
        """
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document from store.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        if doc_id in self._documents:
            del self._documents[doc_id]
            del self._embeddings[doc_id]
            return True
        return False

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (1.0 = identical, 0.0 = orthogonal)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_similar(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict]:
        """
        Find most similar documents to query.

        Args:
            query: Query text
            top_k: Maximum number of results to return
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of dicts with id, text, metadata, and score, sorted by similarity
        """
        # Embed query
        query_embedding = self.embed_text(query)

        # Calculate similarities
        similarities = []
        for doc_id, embedding in self._embeddings.items():
            score = self.cosine_similarity(query_embedding, embedding)
            if score >= threshold:
                similarities.append({
                    "id": doc_id,
                    "score": score,
                })

        # Sort by score descending
        similarities.sort(key=lambda x: x["score"], reverse=True)

        # Enrich with document data and limit to top_k
        results = []
        for sim in similarities[:top_k]:
            doc = self._documents.get(sim["id"])
            if doc:
                results.append({
                    "id": sim["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": sim["score"],
                })

        return results

    def find_similar_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict]:
        """
        Find most similar documents to a pre-computed embedding vector.

        Args:
            embedding: Query embedding vector
            top_k: Maximum number of results to return
            threshold: Minimum similarity score

        Returns:
            List of dicts with id, text, metadata, and score
        """
        similarities = []
        for doc_id, doc_embedding in self._embeddings.items():
            score = self.cosine_similarity(embedding, doc_embedding)
            if score >= threshold:
                similarities.append({
                    "id": doc_id,
                    "score": score,
                })

        similarities.sort(key=lambda x: x["score"], reverse=True)

        results = []
        for sim in similarities[:top_k]:
            doc = self._documents.get(sim["id"])
            if doc:
                results.append({
                    "id": sim["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": sim["score"],
                })

        return results

    @property
    def document_count(self) -> int:
        """Get number of documents in store."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents from store."""
        self._documents.clear()
        self._embeddings.clear()
