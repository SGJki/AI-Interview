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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
