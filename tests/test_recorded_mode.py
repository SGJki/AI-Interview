"""
Tests for Recorded Feedback Mode - Phase 2

全程记录模式测试：
- 评估仍进行，但不立即生成反馈文本
- 将评估结果存入 pending_feedbacks
- 面试结束后统一生成反馈
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import replace
from src.domain.enums import FeedbackMode, InterviewMode
from src.agent.state import InterviewState
from src.session.context import InterviewContext
from src.session.snapshot import FinalFeedback
from src.services.interview_service import InterviewService


class TestFinalFeedbackDataclass:
    """Test FinalFeedback data class structure"""

    def test_final_feedback_exists(self):
        """测试 FinalFeedback 类存在"""
        assert FinalFeedback is not None

    def test_final_feedback_has_required_fields(self):
        """测试 FinalFeedback 包含必需字段"""
        ff = FinalFeedback(
            overall_score=0.85,
            series_scores={1: 0.9, 2: 0.8},
            strengths=["表达清晰", "逻辑性强"],
            weaknesses=["部分技术细节不够深入"],
            suggestions=["建议加强源码阅读经验"],
        )
        assert hasattr(ff, 'overall_score')
        assert hasattr(ff, 'series_scores')
        assert hasattr(ff, 'strengths')
        assert hasattr(ff, 'weaknesses')
        assert hasattr(ff, 'suggestions')

    def test_final_feedback_series_scores_is_dict(self):
        """测试 series_scores 是 dict[int, float] 类型"""
        ff = FinalFeedback(
            overall_score=0.75,
            series_scores={1: 0.8, 2: 0.7, 3: 0.75},
            strengths=[],
            weaknesses=[],
            suggestions=[],
        )
        assert isinstance(ff.series_scores, dict)
        for key, value in ff.series_scores.items():
            assert isinstance(key, int)
            assert isinstance(value, float)

    def test_final_feedback_lists_are_string_lists(self):
        """测试 strengths/weaknesses/suggestions 是 list[str] 类型"""
        ff = FinalFeedback(
            overall_score=0.75,
            series_scores={1: 0.8},
            strengths=["优点1", "优点2"],
            weaknesses=["缺点1"],
            suggestions=["建议1", "建议2", "建议3"],
        )
        assert isinstance(ff.strengths, list)
        assert isinstance(ff.weaknesses, list)
        assert isinstance(ff.suggestions, list)
        for s in ff.strengths:
            assert isinstance(s, str)
        for w in ff.weaknesses:
            assert isinstance(w, str)
        for s in ff.suggestions:
            assert isinstance(s, str)


class TestRecordedModeSubmitAnswer:
    """Test submit_answer in RECORDED mode"""

    @pytest.fixture
    def recorded_service(self):
        """创建 RECORDED 模式的面试服务实例"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        # 需要 context 才能运行 submit_answer
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        return service

    @pytest.fixture
    def recorded_context(self):
        """创建 RECORDED 模式的上下文"""
        return InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

    @pytest.mark.asyncio
    async def test_recorded_mode_no_immediate_feedback(self, recorded_service, mock_state):
        """测试 RECORDED 模式不立即生成反馈"""
        recorded_service.state = mock_state

        # 模拟评估结果
        eval_result = {
            'deviation_score': 0.75,
            'is_correct': True,
        }

        with patch.object(recorded_service, '_evaluate_answer', return_value=eval_result), \
             patch.object(recorded_service, '_generate_next_question', return_value=None), \
             patch.object(recorded_service, '_should_continue', return_value=False), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            response = await recorded_service.submit_answer(
                user_answer="我的答案是...",
                question_id="q-1",
            )

        # RECORDED 模式不应该有即时反馈
        assert response.feedback is None

    @pytest.mark.asyncio
    async def test_recorded_mode_populates_pending_feedbacks(self, recorded_service, recorded_context, mock_state):
        """测试 RECORDED 模式将评估结果存入 pending_feedbacks"""
        recorded_service.state = mock_state
        recorded_service.context = recorded_context

        # 模拟评估结果
        eval_result = {
            'deviation_score': 0.65,
            'is_correct': True,
        }

        with patch.object(recorded_service, '_evaluate_answer', return_value=eval_result), \
             patch.object(recorded_service, '_generate_next_question', return_value=None), \
             patch.object(recorded_service, '_should_continue', return_value=False), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            await recorded_service.submit_answer(
                user_answer="我的答案是...",
                question_id="q-1",
            )

        # 验证 pending_feedbacks 被正确填充
        assert len(recorded_service.context.pending_feedbacks) == 1
        pending = recorded_service.context.pending_feedbacks[0]
        assert pending["question_id"] == "q-1"
        assert pending["deviation"] == 0.65
        assert pending["is_correct"] is True

    @pytest.mark.asyncio
    async def test_recorded_mode_multiple_answers_pending(self, recorded_service, recorded_context, mock_state):
        """测试 RECORDED 模式多次回答都记录到 pending_feedbacks"""
        recorded_service.state = mock_state
        recorded_service.context = recorded_context

        eval_results = [
            {'deviation_score': 0.8, 'is_correct': True},
            {'deviation_score': 0.5, 'is_correct': True},  # borderline
            {'deviation_score': 0.25, 'is_correct': False},
        ]

        for i, eval_result in enumerate(eval_results):
            with patch.object(recorded_service, '_evaluate_answer', return_value=eval_result), \
                 patch.object(recorded_service, '_generate_next_question', return_value=None), \
                 patch.object(recorded_service, '_should_continue', return_value=False), \
                 patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

                await recorded_service.submit_answer(
                    user_answer=f"答案{i+1}",
                    question_id=f"q-{i+1}",
                )

        # 验证所有评估结果都被记录
        assert len(recorded_service.context.pending_feedbacks) == 3
        assert recorded_service.context.pending_feedbacks[0]["deviation"] == 0.8
        assert recorded_service.context.pending_feedbacks[1]["deviation"] == 0.5
        assert recorded_service.context.pending_feedbacks[2]["deviation"] == 0.25
        assert recorded_service.context.pending_feedbacks[2]["is_correct"] is False

    @pytest.mark.asyncio
    async def test_realtime_mode_generates_immediate_feedback(self):
        """测试 REALTIME 模式仍然立即生成反馈（对比测试）"""
        realtime_service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )
        # 需要 context 才能运行 submit_answer
        realtime_service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )
        mock_state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.REALTIME,
            error_threshold=2,
        )
        realtime_service.state = mock_state

        # 模拟评估结果
        eval_result = {
            'deviation_score': 0.75,
            'is_correct': True,
        }

        with patch.object(realtime_service, '_evaluate_answer', return_value=eval_result), \
             patch.object(realtime_service, '_generate_next_question', return_value=None), \
             patch.object(realtime_service, '_should_continue', return_value=False), \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):

            response = await realtime_service.submit_answer(
                user_answer="我的答案是...",
                question_id="q-1",
            )

        # REALTIME 模式应该有即时反馈
        assert response.feedback is not None


class TestGenerateFinalFeedback:
    """Test generate_final_feedback method"""

    @pytest.fixture
    def recorded_service_with_context(self):
        """创建带有完整上下文的 RECORDED 模式服务"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.context = context
        return service

    @pytest.mark.asyncio
    async def test_generate_final_feedback_returns_final_feedback(self, recorded_service_with_context):
        """测试 generate_final_feedback 返回 FinalFeedback 对象"""
        result = await recorded_service_with_context.generate_final_feedback()

        assert isinstance(result, FinalFeedback)

    @pytest.mark.asyncio
    async def test_generate_final_feedback_with_no_answers(self, recorded_service_with_context):
        """测试无回答时生成默认反馈"""
        result = await recorded_service_with_context.generate_final_feedback()

        # 无回答时应该有默认结构
        assert isinstance(result, FinalFeedback)
        assert result.overall_score == 0.0
        assert result.series_scores == {}

    @pytest.mark.asyncio
    async def test_generate_final_feedback_calculates_overall_score(self, recorded_service_with_context):
        """测试 generate_final_feedback 计算整体评分"""
        # 添加多个评估结果
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.8, "is_correct": True},
            {"question_id": "q-2", "deviation": 0.6, "is_correct": True},
            {"question_id": "q-3", "deviation": 0.4, "is_correct": False},
        ]

        result = await recorded_service_with_context.generate_final_feedback()

        # (0.8 + 0.6 + 0.4) / 3 = 0.6
        assert result.overall_score == pytest.approx(0.6, rel=0.01)

    @pytest.mark.asyncio
    async def test_generate_final_feedback_includes_series_scores(self, recorded_service_with_context):
        """测试 generate_final_feedback 包含各系列评分"""
        # 添加按系列分组的评估结果
        recorded_service_with_context.context.series_history = {
            1: {
                "questions": ["q-1", "q-2"],
                "answers": [
                    {"question_id": "q-1", "deviation": 0.9},
                    {"question_id": "q-2", "deviation": 0.7},
                ],
            },
            2: {
                "questions": ["q-3"],
                "answers": [
                    {"question_id": "q-3", "deviation": 0.5},
                ],
            },
        }
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.9, "is_correct": True},
            {"question_id": "q-2", "deviation": 0.7, "is_correct": True},
            {"question_id": "q-3", "deviation": 0.5, "is_correct": False},
        ]

        result = await recorded_service_with_context.generate_final_feedback()

        # 系列1: (0.9 + 0.7) / 2 = 0.8
        # 系列2: 0.5
        assert 1 in result.series_scores
        assert 2 in result.series_scores
        assert result.series_scores[1] == pytest.approx(0.8, rel=0.01)
        assert result.series_scores[2] == pytest.approx(0.5, rel=0.01)

    @pytest.mark.asyncio
    async def test_generate_final_feedback_identifies_strengths(self, recorded_service_with_context):
        """测试 generate_final_feedback 识别优点"""
        # 添加高分回答
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.95, "is_correct": True},
            {"question_id": "q-2", "deviation": 0.9, "is_correct": True},
        ]

        result = await recorded_service_with_context.generate_final_feedback()

        # 高分回答应该被识别为优点
        assert len(result.strengths) > 0

    @pytest.mark.asyncio
    async def test_generate_final_feedback_identifies_weaknesses(self, recorded_service_with_context):
        """测试 generate_final_feedback 识别缺点"""
        # 添加低分回答
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.2, "is_correct": False},
            {"question_id": "q-2", "deviation": 0.3, "is_correct": False},
        ]

        result = await recorded_service_with_context.generate_final_feedback()

        # 低分回答应该被识别为缺点
        assert len(result.weaknesses) > 0

    @pytest.mark.asyncio
    async def test_generate_final_feedback_provides_suggestions(self, recorded_service_with_context):
        """测试 generate_final_feedback 提供建议"""
        # 添加混合回答
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.95, "is_correct": True},
            {"question_id": "q-2", "deviation": 0.2, "is_correct": False},
        ]

        result = await recorded_service_with_context.generate_final_feedback()

        # 应该有建议
        assert len(result.suggestions) > 0


class TestEndInterviewIntegration:
    """Test end_interview with final feedback generation"""

    @pytest.fixture
    def recorded_service_with_context(self):
        """创建带有完整上下文的 RECORDED 模式服务"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.context = context
        return service

    @pytest.mark.asyncio
    async def test_end_interview_includes_final_feedback(self, recorded_service_with_context):
        """测试 end_interview 返回最终反馈"""
        # 添加评估数据
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.8, "is_correct": True},
        ]

        with patch('src.services.interview_service.clear_session_memory', new_callable=AsyncMock):
            result = await recorded_service_with_context.end_interview()

        # 验证结果包含最终反馈
        assert "final_feedback" in result
        assert isinstance(result["final_feedback"], FinalFeedback)

    @pytest.mark.asyncio
    async def test_end_interview_clears_pending_feedbacks(self, recorded_service_with_context):
        """测试 end_interview 清理 pending_feedbacks"""
        # 添加评估数据
        recorded_service_with_context.context.pending_feedbacks = [
            {"question_id": "q-1", "deviation": 0.8, "is_correct": True},
        ]

        with patch('src.services.interview_service.clear_session_memory', new_callable=AsyncMock):
            result = await recorded_service_with_context.end_interview()

        # 验证 pending_feedbacks 被清空
        assert len(recorded_service_with_context.context.pending_feedbacks) == 0

    @pytest.mark.asyncio
    async def test_end_interview_no_context(self):
        """测试无活动面试时结束"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            feedback_mode=FeedbackMode.RECORDED,
        )

        result = await service.end_interview()

        assert result["status"] == "no_active_interview"


class TestPendingFeedbacksStructure:
    """Test pending_feedbacks data structure"""

    def test_pending_feedbacks_is_list_of_dicts(self):
        """测试 pending_feedbacks 是 list[dict] 类型"""
        context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        # pending_feedbacks 应该是 list
        assert isinstance(context.pending_feedbacks, list)

    def test_pending_feedback_item_has_required_fields(self):
        """测试单个 pending_feedback 条目包含必需字段"""
        context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="kb-1",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        # 添加一条记录
        context.pending_feedbacks.append({
            "question_id": "q-1",
            "deviation": 0.75,
            "is_correct": True,
        })

        item = context.pending_feedbacks[0]
        assert "question_id" in item
        assert "deviation" in item
        assert "is_correct" in item


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
