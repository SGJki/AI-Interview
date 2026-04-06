"""
Tests for Interview API Endpoints - Enhanced Coverage

Target: src/api/interview.py (currently 16%)

Key areas to test:
- /interview/start endpoint
- /interview/question endpoint (SSE)
- /interview/answer endpoint
- /interview/end endpoint
- Helper functions
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
import json

from src.api import interview_router
from src.api.models import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    StartInterviewResponse,
    QAResponse,
    FeedbackData,
    InterviewResult,
)
from src.agent.state import InterviewMode, FeedbackMode, Question, QuestionType, Answer
from src.services.interview_service import InterviewService


class TestCreateServiceFromRequest:
    """Test _create_service_from_request helper"""

    def test_creates_free_interview_mode(self):
        """Test creates FREE interview mode from request"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            interview_mode="free",
        )

        service = _create_service_from_request(request)

        assert service.interview_mode == InterviewMode.FREE
        assert service.session_id == "session-456"
        assert service.resume_id == "resume-123"

    def test_creates_training_interview_mode(self):
        """Test creates TRAINING interview mode from request"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            interview_mode="training",
        )

        service = _create_service_from_request(request)

        assert service.interview_mode == InterviewMode.TRAINING

    def test_creates_recorded_feedback_mode(self):
        """Test creates RECORDED feedback mode from request"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            feedback_mode="recorded",
        )

        service = _create_service_from_request(request)

        assert service.feedback_mode == FeedbackMode.RECORDED

    def test_creates_realtime_feedback_mode(self):
        """Test creates REALTIME feedback mode from request"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            feedback_mode="realtime",
        )

        service = _create_service_from_request(request)

        assert service.feedback_mode == FeedbackMode.REALTIME

    def test_uses_resume_id_as_knowledge_base_id_when_not_provided(self):
        """Test uses resume_id as knowledge_base_id when not explicitly provided"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
        )

        service = _create_service_from_request(request)

        assert service.knowledge_base_id == "resume-123"

    def test_uses_session_id_as_resume_id_when_not_provided(self):
        """Test uses session_id as resume_id when not provided"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            session_id="session-456",
        )

        service = _create_service_from_request(request)

        assert service.resume_id == "session-456"

    def test_respects_max_series_parameter(self):
        """Test respects max_series parameter"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            max_series=3,
        )

        service = _create_service_from_request(request)

        assert service.max_series == 3

    def test_respects_error_threshold_parameter(self):
        """Test respects error_threshold parameter"""
        from src.api.interview import _create_service_from_request

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            error_threshold=3,
        )

        service = _create_service_from_request(request)

        assert service.error_threshold == 3


class TestQuestionToData:
    """Test _question_to_data helper"""

    def test_converts_question_with_enum_type(self):
        """Test converts question with enum question_type"""
        from src.api.interview import _question_to_data

        question = Question(
            content="测试问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        result = _question_to_data(question, "q-123")

        assert result.question_id == "q-123"
        assert result.series == 1
        assert result.number == 1
        assert result.content == "测试问题"

    def test_handles_string_question_type(self):
        """Test handles question_type as string"""
        from src.api.interview import _question_to_data

        question = Question(
            content="测试问题",
            question_type="initial",  # String instead of enum
            series=1,
            number=1,
        )

        result = _question_to_data(question, "q-123")

        assert result.question_type == "initial"


class TestFeedbackToData:
    """Test _feedback_to_data helper"""

    def test_returns_none_when_feedback_is_none(self):
        """Test returns None when feedback is None"""
        from src.api.interview import _feedback_to_data

        result = _feedback_to_data(None)

        assert result is None

    def test_converts_feedback_with_enum_type(self):
        """Test converts feedback with enum feedback_type"""
        from src.api.interview import _feedback_to_data
        from src.agent.state import Feedback, FeedbackType

        feedback = Feedback(
            question_id="q-123",
            content="反馈内容",
            is_correct=True,
            guidance="建议",
            feedback_type=FeedbackType.COMMENT,
        )

        result = _feedback_to_data(feedback)

        assert result.content == "反馈内容"
        assert result.feedback_type == "comment"
        assert result.is_correct is True
        assert result.guidance == "建议"

    def test_handles_string_feedback_type(self):
        """Test handles feedback_type as string"""
        from src.api.interview import _feedback_to_data
        from src.agent.state import Feedback

        feedback = Feedback(
            question_id="q-123",
            content="反馈",
            is_correct=True,
            feedback_type="comment",
        )

        result = _feedback_to_data(feedback)

        assert result.feedback_type == "comment"


class TestStartInterviewEndpoint:
    """Test /interview/start endpoint"""

    @pytest.mark.asyncio
    async def test_start_interview_success(self):
        """Test successful interview start"""
        from src.api.interview import start_interview, _create_service_from_request
        from src.api.interview import _question_to_data

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
        )

        mock_question = Question(
            content="第一个问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch('src.api.interview._create_service_from_request') as mock_create:
            mock_service = MagicMock()
            mock_service.state.current_question_id = "q-session-1-1"
            mock_service.start_interview = AsyncMock(return_value=mock_question)
            mock_create.return_value = mock_service

            response = await start_interview(request)

        assert response.session_id == "session-456"
        assert response.status == "active"

    @pytest.mark.asyncio
    async def test_start_interview_handles_exception(self):
        """Test start_interview handles exceptions"""
        from src.api.interview import start_interview
        from fastapi import HTTPException

        request = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
        )

        with patch('src.api.interview._create_service_from_request') as mock_create:
            mock_service = MagicMock()
            mock_service.start_interview = AsyncMock(side_effect=Exception("DB error"))
            mock_create.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await start_interview(request)

        assert exc_info.value.status_code == 500


class TestGetQuestionEndpoint:
    """Test /interview/question endpoint"""

    @pytest.mark.asyncio
    async def test_get_question_returns_eventsource_response(self):
        """Test get_question returns EventSourceResponse"""
        from src.api.interview import get_question
        from sse_starlette.sse import EventSourceResponse

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.FREE
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.answers = []
        mock_context.current_series = 1
        mock_context.current_question_id = "q-test-1-1"
        mock_context.followup_depth = 0
        mock_context.followup_chain = []
        mock_context.error_count = 0
        mock_context.pending_feedbacks = []
        mock_context.question_contents = {"q-test-1-1": "测试问题内容"}

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.interview.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.state = MagicMock()
                mock_service.state.current_question_id = "q-test-1-1"
                mock_service.state.current_question = Question(
                    content="test",
                    question_type=QuestionType.INITIAL,
                    series=1,
                    number=1,
                )
                MockService.return_value = mock_service

                response = await get_question(session_id="test-session", stream=False)

                assert isinstance(response, EventSourceResponse)


class TestSubmitAnswerEndpoint:
    """Test /interview/answer endpoint"""

    @pytest.mark.asyncio
    async def test_submit_answer_session_not_found(self):
        """Test submit_answer when session not found"""
        from src.api.interview import submit_answer
        from src.tools.memory_tools import SessionStateManager
        from fastapi import HTTPException

        request = SubmitAnswerRequest(
            session_id="nonexistent",
            question_id="q-1",
            user_answer="我的答案",
        )

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=None)
            MockSM.return_value = mock_manager

            with pytest.raises(HTTPException) as exc_info:
                await submit_answer(request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_answer_success(self):
        """Test successful answer submission"""
        from src.api.interview import submit_answer
        from src.tools.memory_tools import SessionStateManager

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.FREE
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_question_id = "q-test-1-1"
        mock_context.answers = []
        mock_context.current_series = 1
        mock_context.followup_depth = 0
        mock_context.followup_chain = []
        mock_context.error_count = 0
        mock_context.resume_context = "简历内容"
        mock_context.pending_feedbacks = []
        mock_context.question_contents = {"q-test-1-1": "问题内容"}

        request = SubmitAnswerRequest(
            session_id="test-session",
            question_id="q-test-1-1",
            user_answer="我的答案",
        )

        mock_response = MagicMock()
        mock_response.question = Question(content="问题", question_type=QuestionType.INITIAL, series=1, number=1)
        mock_response.feedback = None
        mock_response.next_question = None
        mock_response.should_continue = False
        mock_response.interview_status = "completed"

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            mock_manager.save_interview_state = AsyncMock()
            MockSM.return_value = mock_manager

            with patch('src.api.interview.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.submit_answer = AsyncMock(return_value=mock_response)
                mock_service.context = mock_context
                MockService.return_value = mock_service

                response = await submit_answer(request)

        assert response.question_id == "q-test-1-1"


class TestEndInterviewEndpoint:
    """Test /interview/end endpoint"""

    @pytest.mark.asyncio
    async def test_end_interview_no_active_session(self):
        """Test end_interview when no active session"""
        from src.api.interview import end_interview
        from src.tools.memory_tools import SessionStateManager

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=None)
            MockSM.return_value = mock_manager

            response = await end_interview(session_id="nonexistent")

        assert response.status == "no_active_interview"
        assert response.total_questions == 0

    @pytest.mark.asyncio
    async def test_end_interview_success(self):
        """Test successful interview end"""
        from src.api.interview import end_interview
        from src.tools.memory_tools import SessionStateManager
        from src.agent.state import FinalFeedback

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.FREE
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_series = 2
        mock_context.answers = [
            {"question_id": "q-1", "answer": "a1"},
            {"question_id": "q-2", "answer": "a2"},
        ]

        mock_result = {
            "status": "completed",
            "total_series": 2,
            "total_questions": 2,
            "final_feedback": FinalFeedback(
                overall_score=0.75,
                series_scores={1: 0.8, 2: 0.7},
                strengths=["表现良好"],
                weaknesses=["部分细节不够深入"],
                suggestions=["建议加强练习"],
            ),
        }

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.interview.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.end_interview = AsyncMock(return_value=mock_result)
                mock_service.context = mock_context
                MockService.return_value = mock_service

                response = await end_interview(session_id="test-session")

        assert response.status == "completed"
        assert response.total_questions == 2
        assert response.total_series == 2

    @pytest.mark.asyncio
    async def test_end_interview_handles_exception(self):
        """Test end_interview handles exceptions"""
        from src.api.interview import end_interview
        from src.tools.memory_tools import SessionStateManager
        from fastapi import HTTPException

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.FREE
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2

        with patch('src.tools.memory_tools.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.interview.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.end_interview = AsyncMock(side_effect=Exception("DB error"))
                mock_service.context = mock_context
                MockService.return_value = mock_service

                with pytest.raises(HTTPException) as exc_info:
                    await end_interview(session_id="test-session")

        assert exc_info.value.status_code == 500


class TestQAResponseModel:
    """Test QAResponse model edge cases"""

    def test_qa_response_with_no_next_question(self):
        """Test QAResponse when there's no next question"""
        from src.api.models import QAResponse

        response = QAResponse(
            question_id="q-1",
            question_content="第一题",
            feedback=None,
            next_question_id=None,
            next_question_content=None,
            should_continue=False,
            interview_status="completed",
        )

        assert response.next_question_id is None
        assert response.next_question_content is None

    def test_qa_response_with_all_fields(self):
        """Test QAResponse with all fields populated"""
        from src.api.models import QAResponse, FeedbackData

        response = QAResponse(
            question_id="q-1",
            question_content="第一题内容",
            feedback=FeedbackData(
                content="反馈内容",
                feedback_type="comment",
                is_correct=True,
                guidance="建议",
            ),
            next_question_id="q-2",
            next_question_content="第二题内容",
            should_continue=True,
            interview_status="active",
        )

        assert response.feedback is not None
        assert response.next_question_id == "q-2"


class TestInterviewResultModel:
    """Test InterviewResult model"""

    def test_interview_result_with_final_feedback(self):
        """Test InterviewResult with final feedback"""
        from src.api.models import InterviewResult

        result = InterviewResult(
            session_id="session-123",
            status="completed",
            total_questions=5,
            total_series=2,
            final_feedback={
                "overall_score": 0.8,
                "series_scores": {1: 0.9, 2: 0.7},
                "strengths": ["表现优秀"],
                "weaknesses": ["细节不够"],
                "suggestions": ["多练习"],
            },
        )

        assert result.final_feedback["overall_score"] == 0.8


class TestAPIEndpointIntegration:
    """Integration tests for API endpoints"""

    def test_interview_router_routes_exist(self):
        """Test all required routes exist in interview_router"""
        from src.api import interview_router

        route_paths = []
        for route in interview_router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)

        # Verify required endpoints
        assert any('/start' in p for p in route_paths)
        assert any('/question' in p for p in route_paths)
        assert any('/answer' in p for p in route_paths)
        assert any('/end' in p for p in route_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
