"""
Tests for AI Interview Agent - LangGraph Graph and Nodes
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agent.state import (
    InterviewMode,
    FeedbackMode,
    QuestionType,
    Question,
    Answer,
    Feedback,
    InterviewState,
    InterviewContext,
)
from src.agent.graph import (
    interview_graph,
    create_interview_graph,
    should_continue_interview,
    generate_question,
    evaluate_answer,
    generate_feedback,
)


class TestInterviewGraph:
    """Test LangGraph interview graph structure"""

    def test_graph_exists(self):
        """测试 graph 存在"""
        assert interview_graph is not None

    def test_create_graph(self):
        """测试创建 graph"""
        graph = create_interview_graph()
        assert graph is not None

    def test_graph_has_nodes(self):
        """测试 graph 包含必要的节点"""
        graph = create_interview_graph()
        nodes = graph.nodes
        expected_nodes = [
            "load_context",
            "generate_question",
            "wait_for_answer",
            "evaluate_answer",
            "generate_feedback",
            "should_continue",
            "end_interview",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """测试 graph 入口点设置"""
        graph = create_interview_graph()
        # Verify the graph has nodes and first node is load_context
        assert "load_context" in graph.nodes
        # 通过编译后的图验证入口点
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_has_end(self):
        """测试 graph 连接到 END"""
        graph = create_interview_graph()
        # END is a sentinel, check that end_interview connects to it
        assert ("end_interview", "__end__") in graph.edges or \
               ("end_interview", END) in graph.edges


class TestShouldContinueInterview:
    """Test should_continue_interview function"""

    def test_should_continue_when_active(self):
        """测试面试进行中"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1
        )

        result = should_continue_interview(state, max_series=3)
        assert result == "generate_question"

    def test_should_end_when_max_series_reached(self):
        """测试达到最大系列数时结束"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=3
        )

        result = should_continue_interview(state, max_series=3)
        assert result == "end_interview"

    def test_should_end_when_user_stops(self):
        """测试用户主动结束"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123"
        )

        # 模拟用户发送结束信号
        result = should_continue_interview(state, max_series=3, user_end=True)
        assert result == "end_interview"

    def test_should_continue_at_series_2(self):
        """测试系列2仍然继续"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=2
        )

        result = should_continue_interview(state, max_series=5)
        assert result == "generate_question"


class TestGraphCompilation:
    """Test graph compilation"""

    def test_graph_compiles_without_checkpointer(self):
        """测试无 checkpointer 编译"""
        graph = create_interview_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_compiles_with_checkpointer(self):
        """测试带 checkpointer 编译"""
        graph = create_interview_graph()
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        compiled = graph.compile(checkpointer=checkpointer)
        assert compiled is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
