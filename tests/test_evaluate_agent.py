"""
Tests for EvaluateAgent - Answer evaluation subgraph
"""

import pytest
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

    def test_evaluate_with_standard_takes_state_question_user_answer_and_standard_answer(self):
        """Test evaluate_with_standard function signature"""
        import inspect
        sig = inspect.signature(evaluate_with_standard)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params
        assert "user_answer" in params
        assert "standard_answer" in params

    def test_evaluate_without_standard_takes_state_question_and_user_answer(self):
        """Test evaluate_without_standard function signature"""
        import inspect
        sig = inspect.signature(evaluate_without_standard)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params
        assert "user_answer" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
