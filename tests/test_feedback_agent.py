"""
Tests for FeedBackAgent - Feedback generation subgraph
"""

import pytest
from src.agent.feedback_agent import (
    create_feedback_agent_graph,
    feedback_agent_graph,
    generate_correction,
    generate_guidance,
    generate_comment,
    generate_fallback_feedback,
)
from src.agent.state import InterviewState


class TestFeedBackAgentGraph:
    """Test FeedBackAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert feedback_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new feedback agent graph"""
        graph = create_feedback_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_feedback_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "generate_correction",
            "generate_guidance",
            "generate_comment",
            "generate_fallback_feedback",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to generate_correction"""
        graph = create_feedback_agent_graph()
        assert "generate_correction" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_feedback_agent_graph is already compiled"""
        graph = create_feedback_agent_graph()
        assert hasattr(graph, "invoke")


class TestFeedBackAgentFunctions:
    """Test FeedBackAgent function signatures"""

    def test_generate_correction_is_async(self):
        """Test that generate_correction is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_correction)

    def test_generate_guidance_is_async(self):
        """Test that generate_guidance is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_guidance)

    def test_generate_comment_is_async(self):
        """Test that generate_comment is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_comment)

    def test_generate_fallback_feedback_is_async(self):
        """Test that generate_fallback_feedback is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_fallback_feedback)

    def test_generate_correction_takes_state_question_user_answer_and_evaluation(self):
        """Test generate_correction function signature"""
        import inspect
        sig = inspect.signature(generate_correction)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params
        assert "user_answer" in params
        assert "evaluation" in params

    def test_generate_guidance_takes_state_question_user_answer_and_evaluation(self):
        """Test generate_guidance function signature"""
        import inspect
        sig = inspect.signature(generate_guidance)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params
        assert "user_answer" in params
        assert "evaluation" in params

    def test_generate_comment_takes_state_question_user_answer_and_evaluation(self):
        """Test generate_comment function signature"""
        import inspect
        sig = inspect.signature(generate_comment)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params
        assert "user_answer" in params
        assert "evaluation" in params

    def test_generate_fallback_feedback_takes_only_state(self):
        """Test generate_fallback_feedback function signature"""
        import inspect
        sig = inspect.signature(generate_fallback_feedback)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert len(params) == 1


@pytest.mark.asyncio
async def test_generate_correction_success():
    """测试生成纠正反馈"""
    from unittest.mock import AsyncMock, patch
    from src.agent.feedback_agent import get_llm_service
    from src.agent.state import Feedback, FeedbackType

    state = InterviewState(session_id="test", resume_id="r1", current_question_id="q_test")

    with patch("src.agent.feedback_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.generate_feedback = AsyncMock(return_value=Feedback(
            question_id="q_test",
            content="正确答案是...",
            is_correct=False,
            guidance="建议回顾相关技术原理",
            feedback_type=FeedbackType.CORRECTION,
        ))
        mock.return_value = service

        result = await generate_correction(
            state,
            question="什么是 Redis?",
            user_answer="Redis 是一个数据库",
            evaluation={"deviation_score": 0.2, "is_correct": False}
        )

        assert "last_feedback" in result
        assert result["last_feedback"].feedback_type == FeedbackType.CORRECTION
        assert result["last_feedback"].is_correct is False


@pytest.mark.asyncio
async def test_generate_guidance_success():
    """测试生成引导反馈"""
    from unittest.mock import AsyncMock, patch
    from src.agent.feedback_agent import get_llm_service
    from src.agent.state import Feedback, FeedbackType

    state = InterviewState(session_id="test", resume_id="r1", current_question_id="q_test2")

    with patch("src.agent.feedback_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.generate_feedback = AsyncMock(return_value=Feedback(
            question_id="q_test2",
            content="你的回答方向正确，但可以更深入一些...",
            is_correct=True,
            guidance="请尝试从项目实践角度更详细地说明",
            feedback_type=FeedbackType.GUIDANCE,
        ))
        mock.return_value = service

        result = await generate_guidance(
            state,
            question="介绍一下 Redis 的持久化机制",
            user_answer="Redis 可以做 RDB 和 AOF 持久化",
            evaluation={"deviation_score": 0.5, "is_correct": True}
        )

        assert "last_feedback" in result
        assert result["last_feedback"].feedback_type == FeedbackType.GUIDANCE
        assert result["last_feedback"].is_correct is True


@pytest.mark.asyncio
async def test_generate_comment_success():
    """测试生成评论反馈"""
    from unittest.mock import AsyncMock, patch
    from src.agent.feedback_agent import get_llm_service
    from src.agent.state import Feedback, FeedbackType

    state = InterviewState(session_id="test", resume_id="r1", current_question_id="q_test3")

    with patch("src.agent.feedback_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.generate_feedback = AsyncMock(return_value=Feedback(
            question_id="q_test3",
            content="回答得很好！继续深入。",
            is_correct=True,
            guidance=None,
            feedback_type=FeedbackType.COMMENT,
        ))
        mock.return_value = service

        result = await generate_comment(
            state,
            question="你使用过哪些缓存方案？",
            user_answer="我主要使用 Redis 作为缓存，配合本地缓存一起使用",
            evaluation={"deviation_score": 0.8, "is_correct": True}
        )

        assert "last_feedback" in result
        assert result["last_feedback"].feedback_type == FeedbackType.COMMENT
        assert result["last_feedback"].is_correct is True


@pytest.mark.asyncio
async def test_generate_correction_updates_feedbacks_dict():
    """测试 generate_correction 更新 feedbacks 字典"""
    from unittest.mock import AsyncMock, patch
    from src.agent.feedback_agent import get_llm_service
    from src.agent.state import Feedback, FeedbackType

    state = InterviewState(session_id="test", resume_id="r1", current_question_id="q_test7")

    with patch("src.agent.feedback_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.generate_feedback = AsyncMock(return_value=Feedback(
            question_id="q_test7",
            content="纠错内容",
            is_correct=False,
            guidance="建议回顾原理",
            feedback_type=FeedbackType.CORRECTION,
        ))
        mock.return_value = service

        result = await generate_correction(
            state,
            question="什么是 Redis?",
            user_answer="Redis 是一个数据库",
            evaluation={"deviation_score": 0.1, "is_correct": False}
        )

        assert "feedbacks" in result
        assert "q_test7" in result["feedbacks"]
        assert result["feedbacks"]["q_test7"].feedback_type == FeedbackType.CORRECTION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
