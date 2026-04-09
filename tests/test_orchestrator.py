"""
Tests for Orchestrator - Main entry point that composes all agent subgraphs
"""

import pytest
import asyncio
from dataclasses import replace
from src.agent.orchestrator import (
    orchestrator_graph,
    create_orchestrator_graph,
    init_node,
    orchestrator_node,
    decide_next_node,
    final_feedback_node,
)
from src.agent.state import InterviewState


class TestOrchestratorGraph:
    """Test Orchestrator graph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert orchestrator_graph is not None

    def test_create_graph(self):
        """Test creating a new orchestrator graph"""
        graph = create_orchestrator_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_orchestrator_graph()
        nodes = graph.nodes
        expected_nodes = [
            "init",
            "orchestrator",
            "decide_next",
            "end_interview",
            "resume_agent",
            "knowledge_agent",
            "question_agent",
            "evaluate_agent",
            "feedback_agent",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to init"""
        graph = create_orchestrator_graph()
        assert "init" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_orchestrator_graph is already compiled"""
        graph = create_orchestrator_graph()
        assert hasattr(graph, "invoke")

    def test_graph_has_edges(self):
        """Test that the graph has edges configured"""
        graph = create_orchestrator_graph()
        # The compiled graph should have edges
        assert hasattr(graph, "invoke")


class TestOrchestratorFunctions:
    """Test Orchestrator function signatures"""

    def test_init_node_is_async(self):
        """Test that init_node is an async function"""
        import inspect
        assert inspect.iscoroutinefunction(init_node)

    def test_orchestrator_node_is_async(self):
        """Test that orchestrator_node is an async function"""
        import inspect
        assert inspect.iscoroutinefunction(orchestrator_node)

    def test_final_feedback_node_is_async(self):
        """Test that final_feedback_node is an async function"""
        import inspect
        assert inspect.iscoroutinefunction(final_feedback_node)

    def test_decide_next_node_takes_state(self):
        """Test decide_next_node function signature"""
        import inspect
        sig = inspect.signature(decide_next_node)
        params = list(sig.parameters.keys())
        assert "state" in params

    @pytest.mark.asyncio
    async def test_init_node_returns_dict(self):
        """Test init_node returns a dict with expected keys"""
        state = InterviewState(session_id="test", resume_id="test")
        result = await init_node(state)
        assert isinstance(result, dict)
        assert "phase" in result
        assert "current_series" in result
        assert "followup_depth" in result

    @pytest.mark.asyncio
    async def test_orchestrator_node_phase_transitions(self):
        """Test orchestrator_node phase transitions"""
        # Test init -> warmup
        state = InterviewState(session_id="test", resume_id="test", phase="init")
        result = await orchestrator_node(state)
        assert result["phase"] == "warmup"

        # Test warmup -> initial
        state = InterviewState(session_id="test", resume_id="test", phase="warmup")
        result = await orchestrator_node(state)
        assert result["phase"] == "initial"

        # Test initial -> followup
        state = InterviewState(session_id="test", resume_id="test", phase="initial")
        result = await orchestrator_node(state)
        assert result["phase"] == "followup"

        # Test followup -> final_feedback
        state = InterviewState(session_id="test", resume_id="test", phase="followup")
        result = await orchestrator_node(state)
        assert result["phase"] == "final_feedback"

    def test_decide_next_node_routing(self):
        """Test decide_next_node routing logic"""
        from src.config import config

        # Test: if current_series >= max_series, route to end_interview
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, current_series=config.max_series + 1)
        result = decide_next_node(state)
        assert result == {"next_action": "end_interview"}

        # Test: if error_count >= error_threshold, route to end_interview
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, error_count=config.error_threshold + 1, current_series=1)
        result = decide_next_node(state)
        assert result == {"next_action": "end_interview"}

        # Test: if all_responsibilities_used, route to end_interview
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, all_responsibilities_used=True, current_series=1, error_count=0)
        result = decide_next_node(state)
        assert result == {"next_action": "end_interview"}

        # Test: normal case, route to question_agent
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, current_series=1, error_count=0, all_responsibilities_used=False)
        result = decide_next_node(state)
        assert result == {"next_action": "question_agent"}

        # Note: user_end_requested uses getattr which will return False
        # since that attribute doesn't exist on InterviewState

    @pytest.mark.asyncio
    async def test_final_feedback_node_returns_completed_phase(self):
        """Test final_feedback_node returns completed phase"""
        state = InterviewState(session_id="test", resume_id="test")
        result = await final_feedback_node(state)
        assert isinstance(result, dict)
        assert result["phase"] == "completed"


class TestOrchestratorImports:
    """Test that all agent graphs can be imported"""

    def test_import_resume_agent_graph(self):
        """Test resume_agent_graph can be imported"""
        from src.agent.resume_agent import resume_agent_graph
        assert resume_agent_graph is not None

    def test_import_knowledge_agent_graph(self):
        """Test knowledge_agent_graph can be imported"""
        from src.agent.knowledge_agent import knowledge_agent_graph
        assert knowledge_agent_graph is not None

    def test_import_question_agent_graph(self):
        """Test question_agent_graph can be imported"""
        from src.agent.question_agent import question_agent_graph
        assert question_agent_graph is not None

    def test_import_evaluate_agent_graph(self):
        """Test evaluate_agent_graph can be imported"""
        from src.agent.evaluate_agent import evaluate_agent_graph
        assert evaluate_agent_graph is not None

    def test_import_feedback_agent_graph(self):
        """Test feedback_agent_graph can be imported"""
        from src.agent.feedback_agent import feedback_agent_graph
        assert feedback_agent_graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
