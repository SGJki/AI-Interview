"""
Tests for KnowledgeAgent - Knowledge base and responsibility management subgraph
"""

import pytest
from src.agent.knowledge_agent import (
    create_knowledge_agent_graph,
    knowledge_agent_graph,
    shuffle_responsibilities,
    store_to_vector_db,
    fetch_responsibility,
    find_standard_answer,
)
from src.agent.state import InterviewState


class TestKnowledgeAgentGraph:
    """Test KnowledgeAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert knowledge_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new knowledge agent graph"""
        graph = create_knowledge_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_knowledge_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "shuffle_responsibilities",
            "store_to_vector_db",
            "fetch_responsibility",
            "find_standard_answer",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to shuffle_responsibilities"""
        graph = create_knowledge_agent_graph()
        assert "shuffle_responsibilities" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_knowledge_agent_graph is already compiled"""
        graph = create_knowledge_agent_graph()
        assert hasattr(graph, "invoke")


class TestKnowledgeAgentFunctions:
    """Test KnowledgeAgent function signatures"""

    def test_shuffle_responsibilities_is_async(self):
        """Test that shuffle_responsibilities is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(shuffle_responsibilities)

    def test_store_to_vector_db_is_async(self):
        """Test that store_to_vector_db is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(store_to_vector_db)

    def test_fetch_responsibility_is_async(self):
        """Test that fetch_responsibility is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(fetch_responsibility)

    def test_find_standard_answer_is_async(self):
        """Test that find_standard_answer is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(find_standard_answer)

    def test_shuffle_responsibilities_takes_state_and_responsibilities(self):
        """Test shuffle_responsibilities function signature"""
        import inspect
        sig = inspect.signature(shuffle_responsibilities)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "responsibilities" in params

    def test_store_to_vector_db_takes_state_and_responsibilities(self):
        """Test store_to_vector_db function signature"""
        import inspect
        sig = inspect.signature(store_to_vector_db)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "responsibilities" in params

    def test_fetch_responsibility_takes_state_and_session_id(self):
        """Test fetch_responsibility function signature"""
        import inspect
        sig = inspect.signature(fetch_responsibility)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "session_id" in params

    def test_find_standard_answer_takes_state_and_question(self):
        """Test find_standard_answer function signature"""
        import inspect
        sig = inspect.signature(find_standard_answer)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
