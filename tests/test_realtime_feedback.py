"""
Tests for Real-time Feedback Mode - Phase 2

实时点评模式测试：
- 每题点评
- 追问引导
- 错题提醒
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.agent.state import (
    Feedback,
    FeedbackMode,
    InterviewMode,
    InterviewState,
)
from src.services.interview_service import InterviewService


class TestFeedbackType:
    """Test FeedbackType enum"""

    def test_feedback_type_enum_exists(self):
        """测试 FeedbackType 枚举存在"""
        from src.agent.state import FeedbackType
        assert FeedbackType is not None

    def test_feedback_type_values(self):
        """测试 FeedbackType 枚举值"""
        from src.agent.state import FeedbackType
        assert FeedbackType.COMMENT.value == "comment"
        assert FeedbackType.CORRECTION.value == "correction"
        assert FeedbackType.GUIDANCE.value == "guidance"
        assert FeedbackType.REMINDER.value == "reminder"


class TestFeedbackStructure:
    """Test Feedback data class structure"""

    def test_feedback_has_feedback_type_field(self):
        """测试 Feedback 包含 feedback_type 字段"""
        feedback = Feedback(
            question_id="q-1",
            content="测试反馈",
            is_correct=True,
            feedback_type=None,  # 新字段
        )
        assert hasattr(feedback, 'feedback_type')

    def test_feedback_accepts_feedback_type(self):
        """测试 Feedback 接受 feedback_type 参数"""
        from src.agent.state import FeedbackType
        feedback = Feedback(
            question_id="q-1",
            content="测试反馈",
            is_correct=True,
            feedback_type=FeedbackType.COMMENT,
        )
        assert feedback.feedback_type == FeedbackType.COMMENT


class TestRealtimeFeedback:
    """Test real-time feedback generation"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例"""
        return InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )

    @pytest.mark.asyncio
    async def test_generate_feedback_correction_low_deviation(self, service, mock_state):
        """测试 deviation_score < 0.3 时生成 CORRECTION 类型反馈"""
        from src.agent.state import FeedbackType

        service.state = mock_state

        # deviation_score < 0.3 应该产生 CORRECTION
        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="错误答案",
            deviation_score=0.2,  # < 0.3
        )

        assert feedback.feedback_type == FeedbackType.CORRECTION
        assert feedback.is_correct is False

    @pytest.mark.asyncio
    async def test_generate_feedback_guidance_medium_deviation(self, service, mock_state):
        """测试 0.3 <= deviation_score < 0.6 时生成 GUIDANCE 类型反馈"""
        from src.agent.state import FeedbackType

        service.state = mock_state

        # 0.3 <= deviation < 0.6 应该产生 GUIDANCE
        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="部分正确",
            deviation_score=0.45,
        )

        assert feedback.feedback_type == FeedbackType.GUIDANCE
        assert feedback.is_correct is False

    @pytest.mark.asyncio
    async def test_generate_feedback_comment_high_deviation(self, service, mock_state):
        """测试 deviation_score >= 0.6 时生成 COMMENT 类型反馈"""
        from src.agent.state import FeedbackType

        service.state = mock_state

        # deviation >= 0.6 应该产生 COMMENT
        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="正确答案",
            deviation_score=0.8,
        )

        assert feedback.feedback_type == FeedbackType.COMMENT
        assert feedback.is_correct is True

    @pytest.mark.asyncio
    async def test_generate_feedback_boundary_0_3(self, service, mock_state):
        """测试 deviation_score = 0.3 边界情况"""
        from src.agent.state import FeedbackType

        service.state = mock_state

        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="边界答案",
            deviation_score=0.3,
        )

        # 0.3 是 GUIDANCE 的下限
        assert feedback.feedback_type == FeedbackType.GUIDANCE

    @pytest.mark.asyncio
    async def test_generate_feedback_boundary_0_6(self, service, mock_state):
        """测试 deviation_score = 0.6 边界情况"""
        from src.agent.state import FeedbackType

        service.state = mock_state

        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="边界答案",
            deviation_score=0.6,
        )

        # 0.6 是 COMMENT 的下限
        assert feedback.feedback_type == FeedbackType.COMMENT


class TestReminderLogic:
    """Test reminder functionality"""

    @pytest.fixture
    def service_with_context(self):
        """创建面试服务实例及上下文"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )
        # 创建 context
        from src.agent.state import InterviewContext
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )
        return service

    @pytest.fixture
    def mock_state_with_error(self):
        """创建模拟状态（已错一次）"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            error_count=1,  # 已经错了一次
        )

    @pytest.fixture
    def mock_state_no_error(self):
        """创建模拟状态（无错误）"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            error_count=0,  # 未犯错
        )

    @pytest.mark.asyncio
    async def test_reminder_triggered_on_threshold(self, service_with_context, mock_state_with_error):
        """测试连续答错达到阈值时触发 REMINDER"""
        from src.agent.state import FeedbackType

        service_with_context.state = mock_state_with_error

        # error_count = 1，当再错一次就达到阈值 2
        # 模拟一次错误的回答
        with patch.object(service_with_context, '_evaluate_answer', return_value={
            'deviation_score': 0.2,
            'is_correct': False,
        }), \
        patch.object(service_with_context, '_generate_next_question', return_value=None), \
        patch.object(service_with_context, '_should_continue', return_value=False):
            # 提交答案触发 reminder
            response = await service_with_context.submit_answer(
                user_answer="错误答案",
                question_id="q-1",
            )

        # 检查是否有 feedback 且包含 reminder
        assert response.feedback is not None
        # REMINDER 类型由 error_count >= error_threshold 触发
        assert response.feedback.feedback_type == FeedbackType.REMINDER or \
               (response.feedback.guidance and "连续答错" in response.feedback.guidance)

    @pytest.mark.asyncio
    async def test_no_reminder_below_threshold(self, service_with_context, mock_state_no_error):
        """测试连续答错未达到阈值时不触发 REMINDER"""
        from src.agent.state import FeedbackType
        from dataclasses import replace

        # error_count = 0，未达到阈值 2
        service_with_context.state = replace(mock_state_no_error, error_count=0)

        # 模拟一次错误的回答
        with patch.object(service_with_context, '_evaluate_answer', return_value={
            'deviation_score': 0.2,
            'is_correct': False,
        }), \
        patch.object(service_with_context, '_generate_next_question', return_value=None), \
        patch.object(service_with_context, '_should_continue', return_value=False):
            response = await service_with_context.submit_answer(
                user_answer="错误答案",
                question_id="q-1",
            )

        # 不应该有 REMINDER 类型的 feedback
        assert response.feedback is not None
        assert response.feedback.feedback_type != FeedbackType.REMINDER


class TestFeedbackContent:
    """Test feedback content generation"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例"""
        return InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )

    @pytest.mark.asyncio
    async def test_correction_feedback_has_guidance(self, service, mock_state):
        """测试 CORRECTION 反馈包含引导建议"""
        service.state = mock_state

        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="错误答案",
            deviation_score=0.2,
        )

        assert feedback.feedback_type.value == "correction"
        assert feedback.guidance is not None
        assert len(feedback.guidance) > 0

    @pytest.mark.asyncio
    async def test_guidance_feedback_is_interrogative(self, service, mock_state):
        """测试 GUIDANCE 反馈是引导性问题"""
        service.state = mock_state

        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="部分答案",
            deviation_score=0.45,
        )

        assert feedback.feedback_type.value == "guidance"
        # GUIDANCE 应该是提示性追问，以问号结尾
        assert "?" in feedback.content or "能否" in feedback.content or "是否" in feedback.content

    @pytest.mark.asyncio
    async def test_comment_feedback_is_positive(self, service, mock_state):
        """测试 COMMENT 反馈是正面点评"""
        service.state = mock_state

        feedback = await service._generate_feedback(
            question_id="q-1",
            user_answer="正确答案",
            deviation_score=0.8,
        )

        assert feedback.feedback_type.value == "comment"
        assert feedback.is_correct is True
        assert feedback.guidance is None or len(feedback.guidance) == 0


class TestStreamingFeedback:
    """Test streaming feedback support"""

    def test_feedback_type_for_sse_streaming(self):
        """测试反馈类型适合 SSE 流式输出"""
        from src.agent.state import FeedbackType

        # 验证 FeedbackType 可以用于 SSE 事件类型标记
        feedback_types = [
            FeedbackType.COMMENT,
            FeedbackType.CORRECTION,
            FeedbackType.GUIDANCE,
            FeedbackType.REMINDER,
        ]

        for fb_type in feedback_types:
            # SSE 事件类型应该是字符串
            assert isinstance(fb_type.value, str)
            # 事件类型不应该包含空格
            assert " " not in fb_type.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
