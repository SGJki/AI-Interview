"""Integration test for enterprise KB in interview flow."""
import pytest
from dataclasses import replace
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.state import InterviewState
from src.domain.models import Question
from src.domain.enums import QuestionType
from src.agent.evaluate_agent import evaluate_with_standard
from src.agent.feedback_agent import generate_correction, generate_guidance, generate_comment
from src.tools.enterprise_knowledge import ensure_enterprise_docs, retrieve_enterprise_knowledge


class TestEnterpriseKBIntegration:
    """Test that evaluate and feedback use the same cached enterprise docs."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock InterviewState for integration testing."""
        question = Question(
            content="请谈谈Token管理的经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=question,
            enterprise_docs=[],
            enterprise_docs_retrieved=False,
            current_module="用户认证",
            current_skill_point="Token管理",
        )
        return state

    @pytest.mark.asyncio
    async def test_ensure_enterprise_docs_first_call_queries_kb(self, mock_state):
        """Test ensure_enterprise_docs queries KB on first call when not cached."""
        mock_docs = [
            {"content": "Token best practice for authentication...",
             "metadata": {"module": "用户认证", "skill_points": ["Token管理"]},
             "score": 0.95}
        ]

        with patch('src.tools.enterprise_knowledge.retrieve_enterprise_knowledge') as mock_retrieve:
            mock_retrieve.return_value = mock_docs

            # First call - should query KB
            docs, state_updates = await ensure_enterprise_docs(mock_state)

            # Verify KB was queried
            mock_retrieve.assert_called_once_with(
                module="用户认证",
                skill_point="Token管理",
                top_k=3,
            )

            # Verify return values
            assert docs == mock_docs
            assert state_updates == {
                "enterprise_docs": mock_docs,
                "enterprise_docs_retrieved": True,
            }

    @pytest.mark.asyncio
    async def test_ensure_enterprise_docs_second_call_uses_cache(self, mock_state):
        """Test ensure_enterprise_docs doesn't re-query on second call when cached."""
        mock_docs = [{"content": "cached doc", "metadata": {}, "score": 0.9}]

        # First call - sets enterprise_docs_retrieved=True
        state_with_cache = replace(mock_state, enterprise_docs=mock_docs, enterprise_docs_retrieved=True)

        with patch('src.tools.enterprise_knowledge.retrieve_enterprise_knowledge') as mock_retrieve:
            mock_retrieve.return_value = []

            # Second call - should use cache
            docs, state_updates = await ensure_enterprise_docs(state_with_cache)

            # Verify KB was NOT queried (cache hit)
            mock_retrieve.assert_not_called()

            # Verify cached docs returned
            assert docs == mock_docs
            assert state_updates == {}  # No updates needed when using cache

    @pytest.mark.asyncio
    async def test_evaluate_with_standard_integration(self, mock_state):
        """Test that evaluate_with_standard reads from cached enterprise_docs.

        Architecture: question_agent calls ensure_enterprise_docs first (eager query),
        then evaluate_agent reads from state.enterprise_docs (no extra KB call).
        """
        mock_docs = [
            {"content": "Token best practice for authentication...",
             "metadata": {"module": "用户认证", "skill_points": ["Token管理"]},
             "score": 0.95}
        ]

        # Simulate state after question_agent has cached KB docs
        state_with_docs = replace(
            mock_state,
            enterprise_docs=mock_docs,
            enterprise_docs_retrieved=True,
        )

        with patch('src.agent.evaluate_agent.get_llm_service') as mock_llm_getter:
            mock_llm = AsyncMock()
            mock_llm.evaluate_answer.return_value = {
                "deviation_score": 0.8,
                "is_correct": True,
                "key_points": ["good answer"],
                "suggestions": ["continue"],
            }
            mock_llm_getter.return_value = mock_llm

            # Call evaluate_with_standard - should read from cached state.enterprise_docs
            result = await evaluate_with_standard(state_with_docs)

            # Verify evaluate_answer was called with enterprise_docs from state
            mock_llm.evaluate_answer.assert_called_once()
            call_kwargs = mock_llm.evaluate_answer.call_args.kwargs
            assert call_kwargs["enterprise_docs"] == mock_docs

            # Note: enterprise_docs is in state, not in result updates dict
            assert "answers" in result  # Basic sanity check

    @pytest.mark.asyncio
    async def test_feedback_agents_read_from_state_enterprise_docs(self, mock_state):
        """Test that feedback agents read enterprise_docs from state.

        This verifies the pattern: evaluate sets enterprise_docs in state,
        and feedback agents read from state.enterprise_docs directly.
        """
        mock_docs = [
            {"content": "Token best practice for authentication...",
             "metadata": {"module": "用户认证", "skill_points": ["Token管理"]},
             "score": 0.95}
        ]

        # State after evaluate_with_standard has been called
        state_with_docs = replace(
            mock_state,
            enterprise_docs=mock_docs,
            enterprise_docs_retrieved=True,
        )

        with patch('src.agent.feedback_agent.get_llm_service') as mock_llm_getter:
            mock_llm = AsyncMock()
            mock_llm.generate_feedback.return_value = MagicMock(
                content="Good feedback on token management",
                is_correct=True,
            )
            mock_llm_getter.return_value = mock_llm

            # Set up evaluation result
            state_with_docs = replace(
                state_with_docs,
                evaluation_results={"q1": {"deviation_score": 0.8, "is_correct": True}},
            )

            # Call generate_correction - should read from state.enterprise_docs
            result = await generate_correction(state_with_docs)

            # Verify LLM was called with enterprise_docs
            mock_llm.generate_feedback.assert_called_once()
            call_kwargs = mock_llm.generate_feedback.call_args.kwargs
            assert call_kwargs["enterprise_docs"] == mock_docs

    @pytest.mark.asyncio
    async def test_empty_module_and_skill_point_returns_empty(self):
        """Test that ensure_enterprise_docs handles missing module/skill_point gracefully."""
        with patch('src.tools.enterprise_knowledge.retrieve_enterprise_knowledge') as mock_retrieve:
            mock_retrieve.return_value = []

            # With both None, should return empty
            docs = await retrieve_enterprise_knowledge(module=None, skill_point=None)
            assert docs == []
            mock_retrieve.assert_not_called()