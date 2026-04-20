"""
Tests for Training API Endpoints - Enhanced Coverage

Target: src/api/training.py (currently 20%)

Key areas to test:
- POST /train/start - start training
- POST /train/answer - submit training answer
- POST /train/end - end training
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from src.api import training_router
from src.api.models import (
    StartTrainingRequest,
    SubmitAnswerRequest,
    TrainingResult,
    QAResponse,
    FeedbackData,
)
from src.domain.enums import InterviewMode, FeedbackMode, QuestionType, FeedbackType
from src.domain.models import Question, Answer
from src.services.interview_service import InterviewService


class TestStartTrainingEndpoint:
    """Test POST /train/start endpoint"""

    @pytest.mark.asyncio
    async def test_start_training_success(self):
        """Test successful training start"""
        from src.api.training import start_training

        request = StartTrainingRequest(
            resume_id="resume-123",
            session_id="session-456",
            knowledge_base_id="kb-789",
            skill_point="Python编程",
        )

        mock_question = Question(
            content="关于Python编程的问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch('src.api.training.InterviewService') as MockService:
            mock_service = MagicMock()
            mock_service.state.current_question_id = "q-train-1-1"
            mock_service.start_interview = AsyncMock(return_value=mock_question)
            MockService.return_value = mock_service

            response = await start_training(request)

        assert response["session_id"] == "session-456"
        assert response["status"] == "active"
        assert response["skill_point"] == "Python编程"
        assert "first_question" in response

    @pytest.mark.asyncio
    async def test_start_training_handles_exception(self):
        """Test start_training handles exceptions"""
        from src.api.training import start_training
        from fastapi import HTTPException

        request = StartTrainingRequest(
            resume_id="resume-123",
            session_id="session-456",
            knowledge_base_id="kb-789",
            skill_point="Python",
        )

        with patch('src.api.training.InterviewService') as MockService:
            MockService.return_value.start_interview = AsyncMock(
                side_effect=Exception("Service error")
            )

            with pytest.raises(HTTPException) as exc_info:
                await start_training(request)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_start_training_uses_training_mode(self):
        """Test start_training creates service in TRAINING mode"""
        from src.api.training import start_training

        request = StartTrainingRequest(
            resume_id="resume-123",
            session_id="session-456",
            knowledge_base_id="kb-789",
            skill_point="Python",
        )

        captured_args = {}

        class MockService:
            def __init__(self, **kwargs):
                captured_args.update(kwargs)

            state = MagicMock()
            state.current_question_id = "q-1"

            async def start_interview(self):
                return Question(content="Q", question_type=QuestionType.INITIAL, series=1, number=1)

        with patch('src.api.training.InterviewService', new=MockService):
            await start_training(request)

        assert captured_args["interview_mode"] == InterviewMode.TRAINING
        assert captured_args["feedback_mode"] == FeedbackMode.RECORDED


class TestSubmitTrainingAnswerEndpoint:
    """Test POST /train/answer endpoint"""

    @pytest.mark.asyncio
    async def test_submit_training_answer_session_not_found(self):
        """Test submit_training_answer when session not found"""
        from src.api.training import submit_training_answer
        from src.infrastructure.session_store import SessionStateManager
        from fastapi import HTTPException

        request = SubmitAnswerRequest(
            session_id="nonexistent",
            question_id="q-1",
            user_answer="我的答案",
        )

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=None)
            MockSM.return_value = mock_manager

            with pytest.raises(HTTPException) as exc_info:
                await submit_training_answer(request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_training_answer_success(self):
        """Test successful training answer submission"""
        from src.api.training import submit_training_answer
        from src.infrastructure.session_store import SessionStateManager

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.TRAINING
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_question_id = "q-train-1-1"
        mock_context.answers = []
        mock_context.current_series = 1
        mock_context.followup_depth = 0
        mock_context.followup_chain = []
        mock_context.error_count = 0

        request = SubmitAnswerRequest(
            session_id="test-session",
            question_id="q-train-1-1",
            user_answer="我的训练答案",
        )

        mock_response = MagicMock()
        mock_response.question = Question(
            content="训练问题",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1
        )
        mock_response.feedback = MagicMock()
        mock_response.feedback.content = "反馈"
        mock_response.feedback.feedback_type = FeedbackType.COMMENT
        mock_response.feedback.is_correct = True
        mock_response.feedback.guidance = None
        mock_response.next_question = None
        mock_response.should_continue = False
        mock_response.interview_status = "completed"

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            mock_manager.save_interview_state = AsyncMock()
            MockSM.return_value = mock_manager

            with patch('src.api.training.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.submit_answer = AsyncMock(return_value=mock_response)
                mock_service.context = mock_context
                MockService.return_value = mock_service

                response = await submit_training_answer(request)

        assert response.question_id == "q-train-1-1"
        assert response.should_continue is False

    @pytest.mark.asyncio
    async def test_submit_training_answer_with_feedback(self):
        """Test submit_training_answer with feedback data"""
        from src.api.training import submit_training_answer
        from src.infrastructure.session_store import SessionStateManager

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.TRAINING
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_question_id = "q-1"
        mock_context.answers = []
        mock_context.current_series = 1
        mock_context.followup_depth = 0
        mock_context.followup_chain = []
        mock_context.error_count = 0

        request = SubmitAnswerRequest(
            session_id="test-session",
            question_id="q-1",
            user_answer="答案",
        )

        mock_response = MagicMock()
        mock_response.question = Question(content="Q", question_type=QuestionType.INITIAL, series=1, number=1)
        mock_response.feedback = MagicMock()
        mock_response.feedback.content = "反馈内容"
        mock_response.feedback.feedback_type = FeedbackType.GUIDANCE
        mock_response.feedback.is_correct = False
        mock_response.feedback.guidance = "建议"
        mock_response.next_question = None
        mock_response.should_continue = True
        mock_response.interview_status = "active"

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            mock_manager.save_interview_state = AsyncMock()
            MockSM.return_value = mock_manager

            with patch('src.api.training.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.submit_answer = AsyncMock(return_value=mock_response)
                mock_service.context = mock_context
                MockService.return_value = mock_service

                response = await submit_training_answer(request)

        assert response.feedback is not None
        assert response.feedback.feedback_type == "guidance"

    @pytest.mark.asyncio
    async def test_submit_training_answer_handles_exception(self):
        """Test submit_training_answer handles exceptions"""
        from src.api.training import submit_training_answer
        from src.infrastructure.session_store import SessionStateManager
        from fastapi import HTTPException

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.TRAINING
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_question_id = "q-1"
        mock_context.answers = []
        mock_context.current_series = 1
        mock_context.followup_depth = 0
        mock_context.followup_chain = []
        mock_context.error_count = 0

        request = SubmitAnswerRequest(
            session_id="test-session",
            question_id="q-1",
            user_answer="答案",
        )

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.training.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.submit_answer = AsyncMock(side_effect=Exception("Submit error"))
                mock_service.context = mock_context
                MockService.return_value = mock_service

                with pytest.raises(HTTPException) as exc_info:
                    await submit_training_answer(request)

        assert exc_info.value.status_code == 500


class TestEndTrainingEndpoint:
    """Test POST /train/end endpoint"""

    @pytest.mark.asyncio
    async def test_end_training_no_active_session(self):
        """Test end_training when no active session"""
        from src.api.training import end_training
        from src.infrastructure.session_store import SessionStateManager

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=None)
            MockSM.return_value = mock_manager

            response = await end_training(session_id="nonexistent")

        assert response.status == "no_active_session"
        assert response.questions_answered == 0

    @pytest.mark.asyncio
    async def test_end_training_success(self):
        """Test successful training end"""
        from src.api.training import end_training
        from src.infrastructure.session_store import SessionStateManager
        from src.session.snapshot import FinalFeedback

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.TRAINING
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2
        mock_context.current_series = 1
        mock_context.answers = [
            {"question_id": "q-1", "answer": "a1"},
            {"question_id": "q-2", "answer": "a2"},
        ]

        mock_result = {
            "status": "completed",
            "total_series": 1,
            "total_questions": 2,
            "final_feedback": FinalFeedback(
                overall_score=0.8,
                series_scores={1: 0.8},
                strengths=["表现良好"],
                weaknesses=["细节不够"],
                suggestions=["多练习"],
            ),
        }

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.training.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.end_interview = AsyncMock(return_value=mock_result)
                mock_service.context = mock_context
                MockService.return_value = mock_service

                response = await end_training(session_id="test-session")

        assert response.status == "completed"
        assert response.questions_answered == 2

    @pytest.mark.asyncio
    async def test_end_training_handles_exception(self):
        """Test end_training handles exceptions"""
        from src.api.training import end_training
        from src.infrastructure.session_store import SessionStateManager
        from fastapi import HTTPException

        mock_context = MagicMock()
        mock_context.resume_id = "resume-123"
        mock_context.knowledge_base_id = "kb-1"
        mock_context.interview_mode = InterviewMode.TRAINING
        mock_context.feedback_mode = FeedbackMode.RECORDED
        mock_context.error_threshold = 2

        with patch('src.infrastructure.session_store.SessionStateManager') as MockSM:
            mock_manager = MagicMock()
            mock_manager.load_interview_state = AsyncMock(return_value=mock_context)
            MockSM.return_value = mock_manager

            with patch('src.api.training.InterviewService') as MockService:
                mock_service = MagicMock()
                mock_service.end_interview = AsyncMock(side_effect=Exception("End error"))
                mock_service.context = mock_context
                MockService.return_value = mock_service

                with pytest.raises(HTTPException) as exc_info:
                    await end_training(session_id="test-session")

        assert exc_info.value.status_code == 500


class TestTrainingResultModel:
    """Test TrainingResult model"""

    def test_training_result_model(self):
        """Test TrainingResult model structure"""
        from src.api.models import TrainingResult

        result = TrainingResult(
            session_id="session-123",
            status="completed",
            skill_point="Python编程",
            questions_answered=5,
            final_feedback={
                "overall_score": 0.8,
                "strengths": ["表现好"],
                "weaknesses": [],
                "suggestions": [],
            },
        )

        assert result.session_id == "session-123"
        assert result.status == "completed"
        assert result.skill_point == "Python编程"
        assert result.questions_answered == 5


class TestStartTrainingRequestModel:
    """Test StartTrainingRequest model"""

    def test_start_training_request_required_fields(self):
        """Test StartTrainingRequest with required fields only"""
        from src.api.models import StartTrainingRequest

        request = StartTrainingRequest(
            resume_id="resume-123",
            session_id="session-456",
            knowledge_base_id="kb-789",
            skill_point="Python",
        )

        assert request.resume_id == "resume-123"
        assert request.session_id == "session-456"
        assert request.knowledge_base_id == "kb-789"
        assert request.skill_point == "Python"


class TestTrainingRouterRoutes:
    """Test training router configuration"""

    def test_training_router_has_required_routes(self):
        """Test training_router has all required routes"""
        from src.api import training_router

        route_paths = []
        for route in training_router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)

        assert any('start' in p for p in route_paths)
        assert any('answer' in p for p in route_paths)
        assert any('end' in p for p in route_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
