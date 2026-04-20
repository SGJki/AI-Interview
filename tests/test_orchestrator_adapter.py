"""
Tests for OrchestratorAdapter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.orchestrator_adapter import OrchestratorAdapter, QAResponse
from src.agent.state import InterviewState
from src.domain.models import Question, Answer


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


class TestFinalFeedbackAggregation:
    """Tests for final feedback aggregation logic."""

    def test_aggregate_series_score_single_evaluation(self):
        """Test series score with single evaluation."""
        from src.services.orchestrator_adapter import aggregate_series_score
        evaluations = [
            {"deviation_score": 0.8, "is_correct": True},
        ]
        result = aggregate_series_score(evaluations)
        assert result == 0.8

    def test_aggregate_series_score_multiple_evaluations(self):
        """Test series score with multiple evaluations."""
        from src.services.orchestrator_adapter import aggregate_series_score
        evaluations = [
            {"deviation_score": 0.9, "is_correct": True},
            {"deviation_score": 0.7, "is_correct": True},
            {"deviation_score": 0.5, "is_correct": False},
        ]
        result = aggregate_series_score(evaluations)
        assert result == pytest.approx(0.7)

    def test_aggregate_series_score_empty(self):
        """Test series score with empty evaluations returns 0.0."""
        from src.services.orchestrator_adapter import aggregate_series_score
        result = aggregate_series_score([])
        assert result == 0.0

    def test_aggregate_overall_score_basic(self):
        """Test overall score calculation."""
        from src.services.orchestrator_adapter import aggregate_overall_score
        series_scores = {1: 0.8, 2: 0.7, 3: 0.9}
        result = aggregate_overall_score(series_scores)
        assert result == pytest.approx(0.8)  # Average

    def test_aggregate_overall_score_empty(self):
        """Test overall score with no series returns 0.0."""
        from src.services.orchestrator_adapter import aggregate_overall_score
        result = aggregate_overall_score({})
        assert result == 0.0

    def test_extract_strengths_from_high_scores(self):
        """Test extracting strengths from high-scoring evaluations."""
        from src.services.orchestrator_adapter import extract_strengths
        evaluations = [
            {"deviation_score": 0.9, "is_correct": True, "key_points": ["技术深度好"]},
            {"deviation_score": 0.8, "is_correct": True, "key_points": ["表达清晰"]},
        ]
        feedbacks = []
        result = extract_strengths(evaluations, feedbacks)
        assert len(result) > 0

    def test_extract_weaknesses_from_low_scores(self):
        """Test extracting weaknesses from low-scoring evaluations."""
        from src.services.orchestrator_adapter import extract_weaknesses
        evaluations = [
            {"deviation_score": 0.3, "is_correct": False, "key_points": ["不够深入"]},
            {"deviation_score": 0.2, "is_correct": False, "key_points": ["缺乏细节"]},
        ]
        feedbacks = []
        result = extract_weaknesses(evaluations, feedbacks)
        assert len(result) > 0

    def test_generate_suggestions_low_score(self):
        """Test suggestions generated for low overall score."""
        from src.services.orchestrator_adapter import generate_suggestions
        weaknesses = ["有 2 个问题回答不够深入，需要加强"]
        overall_score = 0.4
        result = generate_suggestions(weaknesses, overall_score)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_end_interview_generates_real_final_feedback():
    """Test end_interview generates aggregated final feedback instead of placeholder."""
    from dataclasses import replace
    from src.services.orchestrator_adapter import OrchestratorAdapter

    adapter = OrchestratorAdapter(
        session_id="test-session",
        resume_id="resume-123",
    )

    # Create mock state with evaluation results
    mock_state = replace(
        InterviewState(session_id="test-session", resume_id="resume-123"),
        answers={
            "q1": Answer(question_id="q1", content="回答1", deviation_score=0.8),
            "q2": Answer(question_id="q2", content="回答2", deviation_score=0.6),
        },
        evaluation_results={
            "q1": {"deviation_score": 0.8, "is_correct": True, "key_points": ["技术深度好"]},
            "q2": {"deviation_score": 0.6, "is_correct": True, "key_points": ["基本准确"]},
        },
        feedbacks={},
        series_history={},
        current_series=1,
    )

    adapter.state = mock_state

    # Mock graph.ainvoke to avoid actual execution
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=mock_state)
    adapter.set_graph(mock_graph)
    result = await adapter.end_interview()

    # Verify final_feedback is not the hardcoded placeholder
    final_feedback = result["final_feedback"]
    assert "overall_score" in final_feedback
    assert "series_scores" in final_feedback
    assert "strengths" in final_feedback
    assert "weaknesses" in final_feedback
    assert "suggestions" in final_feedback

    # Should NOT be the hardcoded placeholder values
    # The real aggregation should calculate based on evaluation_results
    # With eval results of 0.8 and 0.6, avg should be 0.7
    assert final_feedback["overall_score"] == pytest.approx(0.7), \
        f"Expected 0.7, got {final_feedback['overall_score']} - placeholder may be used"
    assert 1 in final_feedback["series_scores"]
    assert final_feedback["series_scores"][1] == pytest.approx(0.7)
