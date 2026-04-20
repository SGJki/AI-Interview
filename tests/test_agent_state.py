"""
Tests for AI Interview Agent - LangGraph State and Core Architecture
"""

import pytest
from datetime import datetime
from src.domain.enums import (
    InterviewMode,
    FeedbackMode,
    SessionStatus,
    QuestionType,
)
from src.domain.models import (
    Question,
    Answer,
    Feedback,
)
from src.agent.state import InterviewState
from src.session.context import InterviewContext


class TestInterviewState:
    """Test InterviewState dataclass"""

    def test_create_interview_state(self):
        """测试创建面试状态"""
        state = InterviewState(
            session_id="test-session-123",
            resume_id="resume-456"
        )

        assert state.session_id == "test-session-123"
        assert state.resume_id == "resume-456"
        assert state.current_series == 1
        assert state.current_question is None
        assert state.followup_depth == 0
        assert len(state.answers) == 0
        assert state.interview_mode == InterviewMode.FREE

    def test_interview_state_new_fields_default_values(self):
        """测试 InterviewState 新字段默认值"""
        state = InterviewState(
            session_id="test-session-123",
            resume_id="resume-456"
        )

        # Series state tracking
        assert state.asked_logical_questions == set()
        assert state.mastered_questions == {}
        assert state.all_responsibilities_used is False

        # Review info
        assert state.review_retry_count == 0
        assert state.last_review_feedback is None

        # Phase tracking
        assert state.phase == "init"

    def test_interview_state_new_fields_with_values(self):
        """测试 InterviewState 新字段赋值"""
        state = InterviewState(
            session_id="test-session-123",
            resume_id="resume-456",
            asked_logical_questions={"q1", "q2"},
            mastered_questions={"q1": {"answer": "a1", "standard_answer": "s1"}},
            all_responsibilities_used=True,
            review_retry_count=2,
            last_review_feedback="Good improvement",
            phase="followup"
        )

        assert state.asked_logical_questions == {"q1", "q2"}
        assert state.mastered_questions == {"q1": {"answer": "a1", "standard_answer": "s1"}}
        assert state.all_responsibilities_used is True
        assert state.review_retry_count == 2
        assert state.last_review_feedback == "Good improvement"
        assert state.phase == "followup"

    def test_interview_state_immutable(self):
        """测试 InterviewState 不可变性"""
        state = InterviewState(
            session_id="test-session-123",
            resume_id="resume-456"
        )

        with pytest.raises(Exception):  # dataclass frozen=True raises FrozenInstanceError
            state.session_id = "new-session"

    def test_question_creation(self):
        """测试问题创建"""
        question = Question(
            content="请介绍一下你在项目中使用的缓存方案",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1
        )

        assert question.content == "请介绍一下你在项目中使用的缓存方案"
        assert question.question_type == QuestionType.INITIAL
        assert question.series == 1

    def test_answer_creation(self):
        """测试回答创建"""
        answer = Answer(
            question_id="q-1",
            content="我使用了Redis作为缓存方案...",
            deviation_score=0.8
        )

        assert answer.question_id == "q-1"
        assert answer.deviation_score == 0.8

    def test_feedback_creation(self):
        """测试反馈创建"""
        feedback = Feedback(
            question_id="q-1",
            content="回答得很好，但可以进一步说明缓存过期策略",
            is_correct=True,
            guidance="可以补充TTL设置和淘汰策略"
        )

        assert feedback.is_correct is True
        assert feedback.guidance is not None


class TestInterviewModeEnum:
    """Test InterviewMode enum"""

    def test_interview_mode_values(self):
        """测试面试模式枚举值"""
        assert InterviewMode.FREE == "free"
        assert InterviewMode.TRAINING == "training"

    def test_feedback_mode_values(self):
        """测试反馈模式枚举值"""
        assert FeedbackMode.REALTIME == "realtime"
        assert FeedbackMode.RECORDED == "recorded"

    def test_session_status_values(self):
        """测试会话状态枚举值"""
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.CANCELLED == "cancelled"


class TestQuestionType:
    """Test QuestionType enum"""

    def test_question_type_values(self):
        """测试问题类型枚举值"""
        assert QuestionType.INITIAL == "initial"
        assert QuestionType.FOLLOWUP == "followup"
        assert QuestionType.GUIDANCE == "guidance"
        assert QuestionType.CLARIFICATION == "clarification"


class TestInterviewContext:
    """Test InterviewContext dataclass"""

    def test_create_interview_context(self):
        """测试创建面试上下文"""
        context = InterviewContext(
            session_id="test-session-123",
            resume_id="resume-456",
            knowledge_base_id="kb-789"
        )

        assert context.session_id == "test-session-123"
        assert context.resume_id == "resume-456"
        assert context.knowledge_base_id == "kb-789"
        assert context.current_series == 1
        assert context.error_threshold == 2

    def test_interview_context_mutable(self):
        """测试 InterviewContext 可变性（用于状态更新）"""
        context = InterviewContext(
            session_id="test-session-123",
            resume_id="resume-456",
            knowledge_base_id="kb-789"
        )

        # 可以正常修改（不是 frozen）
        context.current_series = 2
        context.answers.append({
            "question_id": "q-1",
            "answer": "test answer"
        })

        assert context.current_series == 2
        assert len(context.answers) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
