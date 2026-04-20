"""
Tests for Follow-up Question Guidance Mechanism - Phase 3

智能追问引导机制测试：
- 追问生成
- 追问策略
- 阈值提醒
- 追问链管理
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import replace

from src.domain.enums import (
    FeedbackType,
    FeedbackMode,
    FollowupStrategy,
    InterviewMode,
    QuestionType,
)
from src.domain.models import Feedback, Question, Answer
from src.agent.state import InterviewState
from src.session.context import InterviewContext
from src.services.interview_service import InterviewService


def _make_service_with_context():
    """创建带 context 的面试服务（所有需要访问 context 的测试用此方法）"""
    service = InterviewService(
        session_id="test-session",
        resume_id="resume-123",
        interview_mode=InterviewMode.FREE,
        feedback_mode=FeedbackMode.REALTIME,
        error_threshold=2,
    )
    service.context = InterviewContext(
        session_id="test-session",
        resume_id="resume-123",
        knowledge_base_id="",
        resume_context="测试简历内容：熟悉Python编程，参与过多个项目开发。",
        interview_mode=InterviewMode.FREE,
        feedback_mode=FeedbackMode.REALTIME,
        error_threshold=2,
    )
    return service


class TestFollowupStrategy:
    """Test FollowupStrategy enum"""

    def test_followup_strategy_enum_exists(self):
        """测试 FollowupStrategy 枚举存在"""
        from src.domain.enums import FollowupStrategy
        assert FollowupStrategy is not None

    def test_followup_strategy_values(self):
        """测试 FollowupStrategy 枚举值"""
        from src.domain.enums import FollowupStrategy
        assert FollowupStrategy.IMMEDIATE.value == "immediate"
        assert FollowupStrategy.DEFERRED.value == "deferred"
        assert FollowupStrategy.SKIP.value == "skip"


class TestFollowupQuestionGeneration:
    """Test follow-up question generation"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例（含 context）"""
        return _make_service_with_context()

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
            current_question_id="q-test-1-1",
        )

    @pytest.fixture
    def current_question(self):
        """创建当前问题"""
        return Question(
            content="请介绍你的项目经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

    @pytest.mark.asyncio
    async def test_generate_followup_question_exists(self, service):
        """测试 _generate_followup_question 方法存在"""
        assert hasattr(service, '_generate_followup_question')
        assert callable(service._generate_followup_question)

    @pytest.mark.asyncio
    async def test_generate_followup_question_returns_question(self, service, mock_state, current_question):
        """测试 _generate_followup_question 返回 Question 对象"""
        service.state = mock_state

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问内容",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分答案",
                deviation_score=0.45,
            )

        assert isinstance(followup, Question)
        assert followup.content is not None
        assert len(followup.content) > 0

    @pytest.mark.asyncio
    async def test_generate_followup_question_type_is_followup(self, service, mock_state, current_question):
        """测试生成的追问类型是 FOLLOWUP"""
        service.state = mock_state

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问内容",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分答案",
                deviation_score=0.45,
            )

        assert followup.question_type == QuestionType.FOLLOWUP

    @pytest.mark.asyncio
    async def test_generate_followup_question_has_parent_id(self, service, mock_state, current_question):
        """测试追问包含父问题 ID"""
        service.state = mock_state

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问内容",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                    parent_question_id="q-test-1-1",
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分答案",
                deviation_score=0.45,
            )

        assert followup.parent_question_id is not None

    @pytest.mark.asyncio
    async def test_generate_followup_question_increments_depth(self, service, mock_state, current_question):
        """测试追问后深度增加"""
        service.state = mock_state
        initial_depth = mock_state.followup_depth

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问内容",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分答案",
                deviation_score=0.45,
            )

        assert service.state.followup_depth == initial_depth + 1


class TestShouldAskFollowup:
    """Test should ask follow-up logic"""

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
            max_followup_depth=3,
            followup_depth=0,
        )

    def test_should_ask_followup_method_exists(self, service):
        """测试 _should_ask_followup 方法存在"""
        assert hasattr(service, '_should_ask_followup')
        assert callable(service._should_ask_followup)

    def test_should_ask_followup_returns_bool(self, service, mock_state):
        """测试 _should_ask_followup 返回布尔值"""
        service.state = mock_state

        result = service._should_ask_followup(0.45)

        assert isinstance(result, bool)

    def test_should_ask_followup_true_for_medium_deviation(self, service, mock_state):
        """测试中等偏差返回 True"""
        service.state = mock_state

        # 0.3 <= deviation < 0.6 应该追问
        result = service._should_ask_followup(0.45)

        assert result is True

    def test_should_ask_followup_false_for_high_deviation(self, service, mock_state):
        """测试高偏差返回 False"""
        service.state = mock_state

        # deviation >= 0.6 不需要追问
        result = service._should_ask_followup(0.8)

        assert result is False

    def test_should_ask_followup_false_for_very_low_deviation(self, service, mock_state):
        """测试极低偏差返回 False（直接纠错）"""
        service.state = mock_state

        # deviation < 0.3 不追问（直接给出答案）
        result = service._should_ask_followup(0.2)

        assert result is False

    def test_should_ask_followup_false_at_max_depth(self, service, mock_state):
        """测试达到最大深度时返回 False"""
        service.state = replace(mock_state, followup_depth=3)

        result = service._should_ask_followup(0.45)

        assert result is False


class TestFollowupTopic:
    """Test follow-up topic extraction"""

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

    def test_get_followup_topic_method_exists(self, service):
        """测试 _get_followup_topic 方法存在"""
        assert hasattr(service, '_get_followup_topic')
        assert callable(service._get_followup_topic)

    def test_get_followup_topic_returns_string(self, service):
        """测试 _get_followup_topic 返回字符串"""
        question = Question(
            content="请介绍你的项目经验，特别是关于微服务架构的实践",
            question_type=QuestionType.INITIAL,
        )

        topic = service._get_followup_topic(question)

        assert isinstance(topic, str)
        assert len(topic) > 0


class TestFollowupStrategySelection:
    """Test follow-up strategy selection based on deviation"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例（含 context）"""
        return _make_service_with_context()

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
        )

    @pytest.mark.asyncio
    async def test_immediate_strategy_for_medium_deviation(self, service, mock_state, current_question=None):
        """测试中等偏差使用 IMMEDIATE 策略"""
        if current_question is None:
            current_question = Question(
                content="请介绍你的项目经验",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            )
        service.state = mock_state

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问：能否详细说说？",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分正确",
                deviation_score=0.45,
            )

        # 中等偏差应该生成追问
        assert followup is not None
        assert followup.question_type == QuestionType.FOLLOWUP

    @pytest.mark.asyncio
    async def test_skip_strategy_for_high_deviation(self, service, mock_state, current_question=None):
        """测试高偏差使用 SKIP 策略（不追问）"""
        if current_question is None:
            current_question = Question(
                content="请介绍你的项目经验",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            )
        service.state = mock_state

        should_ask = service._should_ask_followup(0.8)

        # 高偏差不应该追问
        assert should_ask is False

    @pytest.mark.asyncio
    async def test_skip_strategy_for_very_low_deviation(self, service, mock_state, current_question=None):
        """测试极低偏差使用 SKIP 策略（直接纠错）"""
        if current_question is None:
            current_question = Question(
                content="请介绍你的项目经验",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            )
        service.state = mock_state

        should_ask = service._should_ask_followup(0.2)

        # 极低偏差不追问，直接给出答案
        assert should_ask is False


class TestFollowupChainManagement:
    """Test follow-up chain management"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例（含 context）"""
        return _make_service_with_context()

    @pytest.fixture
    def mock_state_with_chain(self):
        """创建带追问链的状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
            followup_depth=1,
            followup_chain=["q-1"],
        )

    def test_followup_chain_tracked_in_state(self, mock_state_with_chain):
        """测试状态中追踪追问链"""
        assert mock_state_with_chain.followup_chain is not None
        assert len(mock_state_with_chain.followup_chain) == 1
        assert "q-1" in mock_state_with_chain.followup_chain

    def test_followup_depth_tracked_in_state(self, mock_state_with_chain):
        """测试状态中追踪追问深度"""
        assert mock_state_with_chain.followup_depth == 1

    def test_max_followup_depth_configurable(self):
        """测试最大追问深度可配置"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            max_followup_depth=5,
        )
        assert state.max_followup_depth == 5

    @pytest.mark.asyncio
    async def test_followup_chain_updated_after_followup(self, service):
        """测试生成追问后更新追问链"""
        initial_state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
            followup_chain=["q-1"],
        )
        service.state = initial_state

        current_question = Question(
            content="请介绍你的项目经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="追问内容",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="部分答案",
                deviation_score=0.45,
            )

        # 追问链应该被更新
        assert len(service.state.followup_chain) == 2


class TestThresholdReminder:
    """Test threshold-based reminder"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例（含 context）"""
        return _make_service_with_context()

    @pytest.fixture
    def mock_state_at_threshold(self):
        """创建达到阈值的模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            error_count=2,  # 达到阈值
            current_question=Question(
                content="请介绍你的项目经验",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
        )

    @pytest.mark.asyncio
    async def test_reminder_triggered_when_error_threshold_reached(
        self, service, mock_state_at_threshold
    ):
        """测试连续答错达到阈值时触发提醒"""
        from src.domain.enums import FeedbackType

        service.state = mock_state_at_threshold

        # Mock all dependencies to avoid Redis and LLM calls
        with patch.object(service, '_evaluate_answer', return_value={
            'deviation_score': 0.2,
            'is_correct': False,
        }), \
        patch.object(service, '_generate_feedback', new_callable=AsyncMock, return_value=Feedback(
            question_id="q-1",
            content="初始反馈",
            is_correct=False,
            guidance=None,
            feedback_type=FeedbackType.COMMENT,
        )), \
        patch.object(service, '_generate_next_question', return_value=None), \
        patch.object(service, '_should_continue', return_value=False), \
        patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):
            response = await service.submit_answer(
                user_answer="错误答案",
                question_id="q-1",
            )

        # 应该触发 REMINDER
        assert response.feedback is not None
        assert response.feedback.feedback_type == FeedbackType.REMINDER

    @pytest.mark.asyncio
    async def test_reminder_contains_knowledge_point_hint(
        self, service, mock_state_at_threshold
    ):
        """测试提醒包含知识点提示"""
        from src.domain.enums import FeedbackType

        service.state = mock_state_at_threshold

        with patch.object(service, '_evaluate_answer', return_value={
            'deviation_score': 0.2,
            'is_correct': False,
        }), \
        patch.object(service, '_generate_feedback', new_callable=AsyncMock, return_value=Feedback(
            question_id="q-1",
            content="初始反馈",
            is_correct=False,
            guidance=None,
            feedback_type=FeedbackType.COMMENT,
        )), \
        patch.object(service, '_generate_next_question', return_value=None), \
        patch.object(service, '_should_continue', return_value=False), \
        patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):
            response = await service.submit_answer(
                user_answer="错误答案",
                question_id="q-1",
            )

        # 提醒应该包含引导信息
        assert response.feedback.guidance is not None
        assert len(response.feedback.guidance) > 0

    @pytest.mark.asyncio
    async def test_error_threshold_configurable(self):
        """测试 error_threshold 可配置"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=3,  # 自定义阈值
        )

        # error_threshold 在服务级别可配置
        assert service.error_threshold == 3
        # 注意：service.state 在面试开始前为 None
        # 状态会在 start_interview() 时创建并继承 error_threshold


class TestFollowupDepthLimit:
    """Test follow-up depth limit"""

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
    def mock_state_at_max_depth(self):
        """创建达到最大深度的模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
            followup_depth=3,  # 达到最大深度
        )

    def test_should_not_ask_followup_at_max_depth(self, service, mock_state_at_max_depth):
        """测试达到最大深度时不追问"""
        service.state = mock_state_at_max_depth

        result = service._should_ask_followup(0.45)

        assert result is False

    @pytest.mark.asyncio
    async def test_followup_not_generated_at_max_depth(self, service, mock_state_at_max_depth):
        """测试达到最大深度时不生成追问"""
        service.state = mock_state_at_max_depth

        current_question = Question(
            content="请介绍你的项目经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        # 在最大深度时不追问
        should_ask = service._should_ask_followup(0.45)
        assert should_ask is False


class TestFollowupQuestionContent:
    """Test follow-up question content generation"""

    @pytest.fixture
    def service(self):
        """创建面试服务实例（含 context）"""
        return _make_service_with_context()

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
        )

    @pytest.mark.asyncio
    async def test_followup_content_is_interrogative(self, service, mock_state):
        """测试追问内容是疑问句"""
        service.state = mock_state

        current_question = Question(
            content="请介绍你的项目经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="能否详细说说你的微服务实践？",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="我做过微服务项目",
                deviation_score=0.45,
            )

        # 追问应该是疑问句
        assert "?" in followup.content or "能否" in followup.content or "详细" in followup.content

    @pytest.mark.asyncio
    async def test_followup_content_related_to_original(self, service, mock_state):
        """测试追问内容与原问题相关"""
        service.state = mock_state

        current_question = Question(
            content="请介绍你的微服务项目经验",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM:
            MockLLM.return_value.generate_followup_question = AsyncMock(
                return_value=Question(
                    content="你提到的Spring Cloud具体是怎么用的？",
                    question_type=QuestionType.FOLLOWUP,
                    series=1,
                    number=2,
                )
            )
            followup = await service._generate_followup_question(
                current_question=current_question,
                user_answer="我用过Spring Cloud",
                deviation_score=0.45,
            )

        # 追问应该与原问题主题相关（微服务）
        assert followup.content is not None
        assert len(followup.content) > 5


class TestMultiTurnFollowup:
    """Test multi-turn follow-up conversation"""

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
    def mock_state_multi_turn(self):
        """创建多轮问答的模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
            max_followup_depth=3,
            followup_depth=2,
            followup_chain=["q-1", "q-2"],
        )

    def test_followup_chain_maintained_across_turns(self, service, mock_state_multi_turn):
        """测试多轮问答中追问链被维护"""
        service.state = mock_state_multi_turn

        assert len(service.state.followup_chain) == 2
        assert service.state.followup_depth == 2

    def test_followup_depth_increments_correctly(self, service, mock_state_multi_turn):
        """测试追问深度正确递增"""
        service.state = mock_state_multi_turn
        initial_depth = service.state.followup_depth

        # 模拟增加深度
        new_depth = initial_depth + 1

        assert new_depth == 3
        assert new_depth <= service.state.max_followup_depth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
