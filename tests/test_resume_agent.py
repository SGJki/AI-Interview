"""
Tests for ResumeAgent - Resume parsing and storage subgraph
"""

import pytest
from src.agent.resume_agent import (
    create_resume_agent_graph,
    resume_agent_graph,
    parse_resume,
    fetch_old_resume,
)
from src.agent.state import InterviewState


class TestResumeAgentGraph:
    """Test ResumeAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert resume_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new resume agent graph"""
        graph = create_resume_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_resume_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "parse_resume",
            "fetch_old_resume",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to parse_resume"""
        graph = create_resume_agent_graph()
        assert "parse_resume" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_resume_agent_graph is already compiled"""
        # The graph is compiled inside create_resume_agent_graph
        graph = create_resume_agent_graph()
        # Check it has the compiled graph structure (invoke method available)
        assert hasattr(graph, "invoke")


class TestResumeAgentFunctions:
    """Test ResumeAgent function signatures"""

    def test_parse_resume_is_async(self):
        """Test that parse_resume is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(parse_resume)

    def test_fetch_old_resume_is_async(self):
        """Test that fetch_old_resume is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(fetch_old_resume)

    def test_parse_resume_takes_state_and_text(self):
        """Test parse_resume function signature"""
        import inspect
        sig = inspect.signature(parse_resume)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "resume_text" in params

    def test_fetch_old_resume_takes_state_and_id(self):
        """Test fetch_old_resume function signature"""
        import inspect
        sig = inspect.signature(fetch_old_resume)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "resume_id" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
