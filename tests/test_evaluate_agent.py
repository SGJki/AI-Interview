"""
Tests for EvaluateAgent - Answer evaluation subgraph
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.evaluate_agent import (
    create_evaluate_agent_graph,
    evaluate_agent_graph,
    evaluate_with_standard,
    evaluate_without_standard,
)
from src.agent.state import InterviewState


class TestEvaluateAgentGraph:
    """Test EvaluateAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert evaluate_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new evaluate agent graph"""
        graph = create_evaluate_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_evaluate_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "evaluate_with_standard",
            "evaluate_without_standard",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to evaluate_with_standard"""
        graph = create_evaluate_agent_graph()
        assert "evaluate_with_standard" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_evaluate_agent_graph is already compiled"""
        graph = create_evaluate_agent_graph()
        assert hasattr(graph, "invoke")


class TestEvaluateAgentFunctions:
    """Test EvaluateAgent function signatures"""

    def test_evaluate_with_standard_is_async(self):
        """Test that evaluate_with_standard is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(evaluate_with_standard)

    def test_evaluate_without_standard_is_async(self):
        """Test that evaluate_without_standard is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(evaluate_without_standard)

    def test_evaluate_with_standard_takes_only_state(self):
        """Test evaluate_with_standard function signature extracts from state"""
        import inspect
        sig = inspect.signature(evaluate_with_standard)
        params = list(sig.parameters.keys())
        assert params == ["state"]

    def test_evaluate_without_standard_takes_only_state(self):
        """Test evaluate_without_standard function signature extracts from state"""
        import inspect
        sig = inspect.signature(evaluate_without_standard)
        params = list(sig.parameters.keys())
        assert params == ["state"]


@pytest.mark.asyncio
async def test_evaluate_with_standard_success():
    """测试使用标准答案评估"""
    from dataclasses import replace
    from src.domain.models import Question, Answer
    from src.domain.enums import QuestionType

    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question=Question(content="什么是 Redis?", question_type=QuestionType.INITIAL),
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="Redis 是一个内存数据库", deviation_score=1.0)},
        mastered_questions={"q_test": {"answer": "Redis 是一个内存数据库", "standard_answer": "Redis 是一个开源的内存数据结构存储..."}},
    )

    with patch("src.agent.evaluate_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.evaluate_answer = AsyncMock(return_value={
            "deviation_score": 0.8,
            "is_correct": True,
            "key_points": ["回答完整"],
            "suggestions": [],
        })
        mock.return_value = service

        result = await evaluate_with_standard(state)

        assert "current_answer" in result
        assert result["current_answer"].deviation_score == 0.8


@pytest.mark.asyncio
async def test_evaluate_without_standard_success():
    """测试无标准答案评估"""
    from dataclasses import replace
    from src.domain.models import Question, Answer
    from src.domain.enums import QuestionType

    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question=Question(content="介绍一下你自己", question_type=QuestionType.INITIAL),
        current_question_id="q_test2",
        answers={"q_test2": Answer(question_id="q_test2", content="我叫张三，有三年开发经验", deviation_score=1.0)},
    )

    with patch("src.agent.evaluate_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.evaluate_answer = AsyncMock(return_value={
            "deviation_score": 0.6,
            "is_correct": True,
            "key_points": ["理解正确"],
            "suggestions": ["补充细节"],
        })
        mock.return_value = service

        result = await evaluate_without_standard(state)

        assert "current_answer" in result
        assert result["current_answer"].deviation_score == 0.6


@pytest.mark.asyncio
async def test_evaluate_with_standard_error_handling():
    """测试评估失败时的错误处理"""
    from dataclasses import replace
    from src.domain.models import Question, Answer
    from src.domain.enums import QuestionType

    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question=Question(content="什么是 Redis?", question_type=QuestionType.INITIAL),
        current_question_id="q_test3",
        answers={"q_test3": Answer(question_id="q_test3", content="Redis 是一个内存数据库", deviation_score=1.0)},
        mastered_questions={"q_test3": {"answer": "Redis 是一个内存数据库", "standard_answer": "Redis 是一个开源的内存数据结构存储..."}},
    )

    with patch("src.agent.evaluate_agent.get_llm_service") as mock:
        service = AsyncMock()
        service.evaluate_answer = AsyncMock(side_effect=Exception("LLM error"))
        mock.return_value = service

        result = await evaluate_with_standard(state)

        # Should return default values on error
        assert "current_answer" in result
        assert result["current_answer"].deviation_score == 0.5
        assert result["error_count"] == 0  # is_correct=True by default on error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
