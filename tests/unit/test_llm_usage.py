"""
Unit tests for LLM Usage data types and invoke_llm_with_usage
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.llm.usage import LLMUsage, LLMResponse, PromptTokensDetails
from src.llm.client import invoke_llm_with_usage


class TestPromptTokensDetails:
    """Test PromptTokensDetails dataclass"""

    def test_creation_with_defaults(self):
        details = PromptTokensDetails()
        assert details.cached_tokens == 0

    def test_creation_with_value(self):
        details = PromptTokensDetails(cached_tokens=800)
        assert details.cached_tokens == 800


class TestLLMUsage:
    """Test LLMUsage dataclass"""

    def test_creation_with_defaults(self):
        usage = LLMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.prompt_tokens_details.cached_tokens == 0

    def test_creation_with_values(self):
        details = PromptTokensDetails(cached_tokens=500)
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=200,
            prompt_tokens_details=details,
        )
        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 200
        assert usage.prompt_tokens_details.cached_tokens == 500


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_creation(self):
        details = PromptTokensDetails(cached_tokens=800)
        usage = LLMUsage(prompt_tokens=1000, completion_tokens=200, prompt_tokens_details=details)
        response = LLMResponse(content="test content", usage=usage)
        assert response.content == "test content"
        assert response.usage.prompt_tokens_details.cached_tokens == 800


class TestInvokeLlmWithUsage:
    """Test invoke_llm_with_usage function"""

    @pytest.mark.asyncio
    async def test_extracts_cached_tokens_from_response(self):
        """Verify cached_tokens is extracted correctly from LangChain response"""
        mock_response = MagicMock()
        mock_response.content = "Test answer"
        mock_response.usage_metadata = {"input_tokens": 1000, "output_tokens": 200}
        mock_response.response_metadata = {"cache_tokens": 800}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            result = await invoke_llm_with_usage(
                system_prompt="System prompt",
                user_prompt="User question",
                temperature=0.0,
            )

            assert result.content == "Test answer"
            assert result.usage.prompt_tokens == 1000
            assert result.usage.completion_tokens == 200
            assert result.usage.prompt_tokens_details.cached_tokens == 800

    @pytest.mark.asyncio
    async def test_returns_clean_content_without_thinking_tags(self):
        """Verify thinking tags are removed when include_reasoning=False"""
        mock_response = MagicMock()
        mock_response.content = "<thinking>thought process</thinking>final answer"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        mock_response.response_metadata = {}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            result = await invoke_llm_with_usage(
                system_prompt="System",
                user_prompt="Question",
                include_reasoning=False,
            )

            assert "<thinking>" not in result.content
            assert "final answer" in result.content

    @pytest.mark.asyncio
    async def test_includes_reasoning_when_requested(self):
        """Verify thinking tags are included when include_reasoning=True"""
        mock_response = MagicMock()
        mock_response.content = "<thinking>thought content</thinking>final answer"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        mock_response.response_metadata = {}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            result = await invoke_llm_with_usage(
                system_prompt="System",
                user_prompt="Question",
                include_reasoning=True,
            )

            assert "<thinking>" in result.content
            assert "final answer" in result.content

    @pytest.mark.asyncio
    async def test_handles_missing_usage_metadata(self):
        """Verify default values when usage_metadata is None"""
        mock_response = MagicMock()
        mock_response.content = "answer content"
        mock_response.usage_metadata = None
        mock_response.response_metadata = {}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            result = await invoke_llm_with_usage(
                system_prompt="System",
                user_prompt="Question",
            )

            assert result.content == "answer content"
            assert result.usage.prompt_tokens == 0
            assert result.usage.completion_tokens == 0
            assert result.usage.prompt_tokens_details.cached_tokens == 0
