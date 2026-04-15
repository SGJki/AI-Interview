"""
Tests for OrchestratorAdapter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.orchestrator_adapter import OrchestratorAdapter, QAResponse
from src.agent.state import InterviewState, Question, Answer, QuestionType


class TestOrchestratorAdapter:
    """Test OrchestratorAdapter class"""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance for testing"""
        return OrchestratorAdapter(
            session_id="test-session-123",
            resume_id="resume-456",
            knowledge_base_id="kb-789"
        )

    def test_adapter_creation(self, adapter):
        """Test that adapter can be created"""
        assert adapter.session_id == "test-session-123"
        assert adapter.resume_id == "resume-456"
        assert adapter.knowledge_base_id == "kb-789"
        assert adapter.state is None

    def test_adapter_has_start_interview(self, adapter):
        """Test that adapter has start_interview method"""
        assert hasattr(adapter, 'start_interview')
        assert callable(adapter.start_interview)

    def test_adapter_has_submit_answer(self, adapter):
        """Test that adapter has submit_answer method"""
        assert hasattr(adapter, 'submit_answer')
        assert callable(adapter.submit_answer)

    def test_adapter_has_end_interview(self, adapter):
        """Test that adapter has end_interview method"""
        assert hasattr(adapter, 'end_interview')
        assert callable(adapter.end_interview)


class TestQAResponse:
    """Test QAResponse dataclass"""

    def test_qa_response_creation(self):
        """Test QAResponse can be created"""
        question = Question(content="What is Python?")
        feedback = None

        response = QAResponse(
            question=question,
            feedback=feedback,
            next_question=None,
            should_continue=False,
            interview_status="completed"
        )

        assert response.question == question
        assert response.feedback is None
        assert response.next_question is None
        assert response.should_continue is False
        assert response.interview_status == "completed"


class TestAdapterStartInterview:
    """Test adapter start_interview method"""

    @pytest.mark.asyncio
    async def test_start_interview_returns_question(self):
        """Test that start_interview returns a Question"""
        adapter = OrchestratorAdapter(
            session_id="test-session",
            resume_id="resume-123"
        )

        # Mock orchestrator_graph.ainvoke
        mock_question = Question(content="Tell me about yourself")
        mock_state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=mock_question
        )

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_state)
        adapter.set_graph(mock_graph)

        question = await adapter.start_interview()

        assert question is not None
        assert isinstance(question, Question)
        assert question.content == "Tell me about yourself"

    @pytest.mark.asyncio
    async def test_start_interview_updates_state(self):
        """Test that start_interview updates adapter state"""
        adapter = OrchestratorAdapter(
            session_id="test-session",
            resume_id="resume-123"
        )

        mock_question = Question(content="What is your experience?")
        mock_state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=mock_question
        )

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_state)
        adapter.set_graph(mock_graph)

        await adapter.start_interview()

        assert adapter.state is not None
        assert adapter.state.session_id == "test-session"


class TestAdapterSubmitAnswer:
    """Test adapter submit_answer method"""

    @pytest.mark.asyncio
    async def test_submit_answer_requires_started_interview(self):
        """Test that submit_answer raises if interview not started"""
        adapter = OrchestratorAdapter(
            session_id="test-session",
            resume_id="resume-123"
        )

        with pytest.raises(ValueError, match="Interview not started"):
            await adapter.submit_answer("My answer", "q-1")


class TestAdapterEndInterview:
    """Test adapter end_interview method"""

    @pytest.mark.asyncio
    async def test_end_interview_requires_started_interview(self):
        """Test that end_interview raises if interview not started"""
        adapter = OrchestratorAdapter(
            session_id="test-session",
            resume_id="resume-123"
        )

        with pytest.raises(ValueError, match="Interview not started"):
            await adapter.end_interview()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
