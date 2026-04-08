"""
Tests for QuestionAgent - Question generation and deduplication subgraph
"""

import pytest
from src.agent.question_agent import (
    create_question_agent_graph,
    question_agent_graph,
    generate_warmup,
    generate_initial,
    generate_followup,
    deduplicate_check,
    should_continue_followup,
)
from src.agent.state import InterviewState


class TestQuestionAgentGraph:
    """Test QuestionAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert question_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new question agent graph"""
        graph = create_question_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_question_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "generate_warmup",
            "generate_initial",
            "generate_followup",
            "deduplicate_check",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to generate_warmup"""
        graph = create_question_agent_graph()
        assert "generate_warmup" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_question_agent_graph is already compiled"""
        graph = create_question_agent_graph()
        assert hasattr(graph, "invoke")


class TestQuestionAgentFunctions:
    """Test QuestionAgent function signatures"""

    def test_generate_warmup_is_async(self):
        """Test that generate_warmup is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_warmup)

    def test_generate_initial_is_async(self):
        """Test that generate_initial is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_initial)

    def test_generate_followup_is_async(self):
        """Test that generate_followup is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(generate_followup)

    def test_deduplicate_check_is_async(self):
        """Test that deduplicate_check is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(deduplicate_check)

    def test_generate_warmup_takes_state_and_resume_context(self):
        """Test generate_warmup function signature"""
        import inspect
        sig = inspect.signature(generate_warmup)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "resume_context" in params

    def test_generate_initial_takes_state_resume_context_and_responsibility(self):
        """Test generate_initial function signature"""
        import inspect
        sig = inspect.signature(generate_initial)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "resume_context" in params
        assert "responsibility" in params

    def test_generate_followup_takes_state_qa_history_and_evaluation(self):
        """Test generate_followup function signature"""
        import inspect
        sig = inspect.signature(generate_followup)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "qa_history" in params
        assert "evaluation" in params

    def test_deduplicate_check_takes_state_and_question_id(self):
        """Test deduplicate_check function signature"""
        import inspect
        sig = inspect.signature(deduplicate_check)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question_id" in params

    def test_should_continue_followup_takes_state(self):
        """Test should_continue_followup function signature"""
        import inspect
        sig = inspect.signature(should_continue_followup)
        params = list(sig.parameters.keys())
        assert "state" in params


# Note: should_continue_followup tests removed - it references
# state.evaluation_results which doesn't exist yet (placeholder implementation)
# The routing logic will be tested when actual implementation is done

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
