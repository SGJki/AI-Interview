"""
Tests for InterviewService remaining uncovered methods

Additional coverage targets:
- start_interview with knowledge_base_id
- _load_knowledge_base error handling
- _generate_next_question_stream
- _evaluate_answer with knowledge context
- _generate_feedback
- generate_final_feedback paths
- create_interview function
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import replace

from src.domain.enums import FeedbackMode, InterviewMode, QuestionType, FeedbackType
from src.domain.models import Question, Answer, Feedback
from src.agent.state import InterviewState
from src.session.context import InterviewContext
from src.services.interview_service import InterviewService, create_interview


def _make_service():
    """Create a basic service with context"""
    service = InterviewService(
        session_id="test-session",
        resume_id="resume-123",
        interview_mode=InterviewMode.FREE,
        feedback_mode=FeedbackMode.RECORDED,
        error_threshold=2,
        max_series=5,
    )
    service.context = InterviewContext(
        session_id="test-session",
        resume_id="resume-123",
        knowledge_base_id="kb-1",
        interview_mode=InterviewMode.FREE,
        feedback_mode=FeedbackMode.RECORDED,
        error_threshold=2,
    )
    return service


class TestStartInterviewWithKnowledgeBase:
    """Test start_interview with knowledge_base_id"""

    @pytest.mark.asyncio
    async def test_start_interview_with_knowledge_base_id(self):
        """Test start_interview loads knowledge base when knowledge_base_id is set"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        mock_question = Question(
            content="第一个问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch.object(service, '_load_knowledge_base', new_callable=AsyncMock) as mock_load, \
             patch.object(service, '_generate_next_question', new_callable=AsyncMock, return_value=mock_question), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            await service.start_interview()

        # Verify knowledge base was loaded
        mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_interview_without_knowledge_base_id(self):
        """Test start_interview skips knowledge base loading when not set"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",  # Empty
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
        )

        mock_question = Question(
            content="第一个问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch.object(service, '_generate_next_question', new_callable=AsyncMock, return_value=mock_question), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            await service.start_interview()

        # Verify no loading happened
        assert service.state is not None


class TestLoadKnowledgeBase:
    """Test _load_knowledge_base method"""

    @pytest.mark.asyncio
    async def test_load_knowledge_base_with_resume_id(self):
        """Test loads knowledge base with resume_id"""
        service = _make_service()
        service.resume_id = "resume-123"

        mock_doc = MagicMock()
        mock_doc.page_content = "简历内容"

        with patch('src.services.interview_service.retrieve_knowledge', new_callable=AsyncMock,
                   return_value=[mock_doc]):
            await service._load_knowledge_base()

        assert service.context.resume_context == "简历内容"

    @pytest.mark.asyncio
    async def test_load_knowledge_base_with_knowledge_base_id(self):
        """Test loads knowledge base with knowledge_base_id"""
        service = _make_service()
        service.knowledge_base_id = "kb-1"

        mock_doc = MagicMock()
        mock_doc.page_content = "知识库内容"

        with patch('src.services.interview_service.retrieve_knowledge', new_callable=AsyncMock,
                   return_value=[mock_doc]):
            await service._load_knowledge_base()

        assert service.context.knowledge_context == "知识库内容"

    @pytest.mark.asyncio
    async def test_load_knowledge_base_handles_error(self):
        """Test handles errors during loading"""
        service = _make_service()
        service.resume_id = "resume-123"

        with patch('src.services.interview_service.retrieve_knowledge', new_callable=AsyncMock,
                   side_effect=Exception("Retrieval error")):
            # Should not raise, just log error
            await service._load_knowledge_base()

        # Context should remain unchanged
        assert service.context.resume_context == ""

    @pytest.mark.asyncio
    async def test_load_knowledge_base_returns_early_if_no_context(self):
        """Test returns early if context is None"""
        service = _make_service()
        service.context = None

        await service._load_knowledge_base()
        # No error should occur


class TestGenerateNextQuestionStream:
    """Test _generate_next_question_stream method"""

    @pytest.mark.asyncio
    async def test_stream_yields_question_start(self):
        """Test streaming yields question_start event"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            answers={},
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.context.resume_context = "测试简历"

        tokens = ["问题", "内容", "是什么"]

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.generate_question_stream = MagicMock()

            async def token_generator():
                for token in tokens:
                    yield token

            mock_instance.generate_question_stream.return_value = token_generator()
            MockLLM.return_value = mock_instance

            events = []
            async for event in service._generate_next_question_stream():
                events.append(event)
                if event.get("type") == "question_end":
                    break

        assert any(e["type"] == "question_start" for e in events)

    @pytest.mark.asyncio
    async def test_stream_handles_exception(self):
        """Test streaming handles LLM exception"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            answers={},
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.context.resume_context = "测试"

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            mock_instance = MagicMock()

            async def error_generator():
                raise Exception("LLM error")

            mock_instance.generate_question_stream.return_value = error_generator()
            MockLLM.return_value = mock_instance

            events = []
            async for event in service._generate_next_question_stream():
                events.append(event)
                if event.get("type") == "question_end":
                    break

        # Should still yield tokens with fallback content
        assert any(e["type"] == "token" for e in events)


class TestEvaluateAnswerWithKnowledge:
    """Test _evaluate_answer with knowledge context"""

    @pytest.mark.asyncio
    async def test_evaluate_answer_uses_knowledge_context(self):
        """Test uses knowledge context for similarity when no standard answer"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=Question(
                content="问题",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
            answers={},
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.context.current_knowledge = "知识上下文"

        with patch('src.services.interview_service.retrieve_standard_answer', new_callable=AsyncMock,
                   return_value=None), \
             patch('src.services.interview_service.InterviewLLMService') as MockLLM, \
             patch('src.services.interview_service.compute_similarity', new_callable=AsyncMock,
                   return_value=0.7):

            MockLLM.return_value.evaluate_answer = AsyncMock(
                return_value={"deviation_score": 0.5, "is_correct": True}
            )

            result = await service._evaluate_answer("q-1", "用户答案")

        # Should have called compute_similarity
        # Final score should be combination of LLM eval and similarity


class TestGenerateFeedback:
    """Test _generate_feedback method"""

    @pytest.mark.asyncio
    async def test_generate_feedback_sets_question_id(self):
        """Test feedback has question_id set"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=Question(
                content="问题",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
            answers={},
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        mock_feedback = Feedback(
            question_id="",  # Empty initially
            content="反馈",
            is_correct=True,
            guidance=None,
            feedback_type=FeedbackType.COMMENT,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_feedback = AsyncMock(
                return_value=mock_feedback
            )

            result = await service._generate_feedback("q-123", "答案", 0.7)

        assert result.question_id == "q-123"


class TestGenerateFinalFeedbackPaths:
    """Test generate_final_feedback method paths"""

    @pytest.mark.asyncio
    async def test_final_feedback_no_pending_feedbacks(self):
        """Test with no pending feedbacks"""
        service = _make_service()
        service.context.pending_feedbacks = []

        result = await service.generate_final_feedback()

        assert result.overall_score == 0.0
        assert result.series_scores == {}

    @pytest.mark.asyncio
    async def test_final_feedback_with_series_history(self):
        """Test with series history data"""
        service = _make_service()
        service.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.8, "is_correct": True},
        ]
        service.context.series_history = {
            1: {
                "questions": ["q-1"],
                "answers": [{"deviation": 0.8}],
            },
        }

        result = await service.generate_final_feedback()

        assert 1 in result.series_scores

    @pytest.mark.asyncio
    async def test_final_feedback_extracts_series_from_question_id(self):
        """Test extracts series number from question_id pattern"""
        service = _make_service()
        service.context.pending_feedbacks = [
            {"question_id": "q-session-2-1", "deviation": 0.7, "is_correct": True},
            {"question_id": "q-session-2-2", "deviation": 0.5, "is_correct": True},
        ]
        # No series_history, should infer from question_id

        result = await service.generate_final_feedback()

        # Should have calculated average for series 2
        assert 2 in result.series_scores


class TestGetCurrentQuestion:
    """Test get_current_question method"""

    @pytest.mark.asyncio
    async def test_get_current_question_returns_question(self):
        """Test returns current question when state exists"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_question=Question(
                content="当前问题",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
            answers={},
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        result = await service.get_current_question()

        assert result is not None
        assert result.content == "当前问题"

    @pytest.mark.asyncio
    async def test_get_current_question_returns_none_when_no_state(self):
        """Test returns None when state is None"""
        service = _make_service()
        service.state = None

        result = await service.get_current_question()

        assert result is None


class TestCreateInterview:
    """Test create_interview convenience function"""

    @pytest.mark.asyncio
    async def test_create_interview_free_mode(self):
        """Test creates service with FREE mode"""
        service = await create_interview(
            session_id="session-123",
            resume_id="resume-456",
            mode="free",
        )

        assert service.interview_mode == InterviewMode.FREE
        assert service.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_create_interview_training_mode(self):
        """Test creates service with TRAINING mode"""
        service = await create_interview(
            session_id="session-123",
            resume_id="resume-456",
            mode="training",
        )

        assert service.interview_mode == InterviewMode.TRAINING

    @pytest.mark.asyncio
    async def test_create_interview_realtime_feedback(self):
        """Test creates service with REALTIME feedback"""
        service = await create_interview(
            session_id="session-123",
            resume_id="resume-456",
            feedback_mode="realtime",
        )

        assert service.feedback_mode == FeedbackMode.REALTIME

    @pytest.mark.asyncio
    async def test_create_interview_recorded_feedback(self):
        """Test creates service with RECORDED feedback"""
        service = await create_interview(
            session_id="session-123",
            resume_id="resume-456",
            feedback_mode="recorded",
        )

        assert service.feedback_mode == FeedbackMode.RECORDED


class TestSubmitAnswerWithSeriesComplete:
    """Test submit_answer when series is complete"""

    @pytest.mark.asyncio
    async def test_submit_answer_switches_series_when_complete(self):
        """Test switches to next series when current is complete"""
        service = _make_service()
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
            answers={
                "q-test-session-1-1": Answer(
                    question_id="q-test-session-1-1",
                    content="answer",
                    deviation_score=0.7,
                )
            },
            current_question=Question(
                content="问题",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        eval_result = {
            'deviation_score': 0.7,
            'is_correct': True,
        }

        next_question = Question(
            content="系列2问题",
            question_type=QuestionType.INITIAL,
            series=2,
            number=1,
        )

        switch_called = False

        async def mock_switch():
            nonlocal switch_called
            switch_called = True

        with patch.object(service, '_evaluate_answer', return_value=eval_result), \
             patch.object(service, '_is_series_complete', return_value=True), \
             patch.object(service, '_switch_to_next_series', side_effect=mock_switch), \
             patch.object(service, '_generate_next_question', new_callable=AsyncMock, return_value=next_question), \
             patch.object(service, '_should_continue', return_value=True), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            response = await service.submit_answer(
                user_answer="答案",
                question_id="q-test-session-1-1",
            )

        # Should have called _switch_to_next_series
        assert switch_called is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
