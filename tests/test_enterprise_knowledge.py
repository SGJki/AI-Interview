"""Tests for Enterprise Knowledge retrieval client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.enterprise_knowledge import (
    retrieve_enterprise_knowledge,
    ensure_enterprise_docs,
)


class TestRetrieveEnterpriseKnowledge:
    """Test retrieve_enterprise_knowledge function."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient as context manager."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        return mock_client, mock_response

    @pytest.mark.asyncio
    async def test_retrieve_by_module(self, mock_httpx_client):
        """Test retrieval by module."""
        mock_client, mock_response = mock_httpx_client
        mock_response.json.return_value = {
            "documents": [
                {
                    "content": "Token management best practices...",
                    "metadata": {"module": "用户认证", "skill_points": ["Token管理"]},
                    "score": 0.95
                }
            ],
            "total": 1
        }

        with patch('src.tools.enterprise_knowledge.get_enterprise_kb_client', return_value=mock_client):
            docs = await retrieve_enterprise_knowledge(module="用户认证", top_k=3)

        assert len(docs) == 1
        assert docs[0]["content"] == "Token management best practices..."
        assert docs[0]["metadata"]["module"] == "用户认证"

    @pytest.mark.asyncio
    async def test_retrieve_by_skill_point(self, mock_httpx_client):
        """Test retrieval by skill_point."""
        mock_client, mock_response = mock_httpx_client
        mock_response.json.return_value = {
            "documents": [
                {"content": "Redis caching strategies...", "metadata": {}, "score": 0.9}
            ],
            "total": 1
        }

        with patch('src.tools.enterprise_knowledge.get_enterprise_kb_client', return_value=mock_client):
            docs = await retrieve_enterprise_knowledge(skill_point="Redis缓存", top_k=3)

        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout returns empty list."""
        import httpx

        async def mock_post(*args, **kwargs):
            raise httpx.TimeoutException("timeout")

        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('src.tools.enterprise_knowledge.get_enterprise_kb_client', return_value=mock_client):
            docs = await retrieve_enterprise_knowledge(module="用户认证")

        assert docs == []


class TestEnsureEnterpriseDocs:
    """Test ensure_enterprise_docs helper."""

    @pytest.mark.asyncio
    async def test_returns_cached_docs(self):
        """Test returns cached docs if already retrieved."""
        from src.agent.state import InterviewState

        cached_docs = [{"content": "cached", "metadata": {}}]
        state = InterviewState(
            session_id="test",
            resume_id="r1",
            enterprise_docs=cached_docs,
            enterprise_docs_retrieved=True
        )

        docs = await ensure_enterprise_docs(state)

        assert docs == cached_docs
