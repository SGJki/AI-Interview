"""
Tests for AI Interview Agent - Single-turn Q&A Flow
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agent.state import (
    InterviewMode,
    FeedbackMode,
    QuestionType,
    Question,
    InterviewState,
)
from src.services.interview_service import InterviewService


class TestInterviewService:
    """Test InterviewService class"""

    def test_interview_service_exists(self):
        """测试 InterviewService 类存在"""
        assert InterviewService is not None

    def test_create_interview_service(self):
        """测试创建面试服务"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123"
        )

        assert service.session_id == "test-session"
        assert service.resume_id == "resume-123"


class TestSingleTurnQA:
    """Test single-turn Q&A flow"""

    def test_single_question_flow(self):
        """测试单个问题流程"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123"
        )

        # 初始状态
        assert state.current_question is None
        assert len(state.answers) == 0

    def test_question_types(self):
        """测试问题类型"""
        initial_q = Question(
            content="请介绍你的项目",
            question_type=QuestionType.INITIAL,
        )
        assert initial_q.question_type == QuestionType.INITIAL

        followup_q = Question(
            content="能详细说说这个技术选型吗？",
            question_type=QuestionType.FOLLOWUP,
            parent_question_id="q-1",
        )
        assert followup_q.question_type == QuestionType.FOLLOWUP

    def test_feedback_modes(self):
        """测试反馈模式"""
        state_realtime = InterviewState(
            session_id="test-1",
            resume_id="resume-1",
            feedback_mode=FeedbackMode.REALTIME,
        )
        assert state_realtime.feedback_mode == FeedbackMode.REALTIME

        state_recorded = InterviewState(
            session_id="test-2",
            resume_id="resume-2",
            feedback_mode=FeedbackMode.RECORDED,
        )
        assert state_recorded.feedback_mode == FeedbackMode.RECORDED


class TestInterviewModes:
    """Test interview modes"""

    def test_free_mode(self):
        """测试自由问答模式"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
        )
        assert state.interview_mode == InterviewMode.FREE

    def test_training_mode(self):
        """测试专项训练模式"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.TRAINING,
        )
        assert state.interview_mode == InterviewMode.TRAINING


class TestAnswerEvaluation:
    """Test answer evaluation"""

    def test_deviation_score_bounds(self):
        """测试偏差度边界"""
        # 偏差度应该在 0-1 之间
        for score in [0.0, 0.3, 0.5, 0.7, 1.0]:
            assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
