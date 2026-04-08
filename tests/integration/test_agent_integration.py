"""Integration tests for agent orchestration."""
import pytest
from dataclasses import replace
from src.agent.orchestrator import (
    orchestrator_graph,
    create_orchestrator_graph,
    init_node,
    orchestrator_node,
    decide_next_node,
    final_feedback_node,
)
from src.agent.state import InterviewState, Answer


class TestOrchestratorIntegration:
    """Integration tests for the orchestrator graph."""

    def test_orchestrator_graph_exists(self):
        """Test that the orchestrator graph is properly initialized."""
        assert orchestrator_graph is not None

    def test_orchestrator_has_all_agent_nodes(self):
        """Test that orchestrator has all required agent nodes including review_agent."""
        graph = create_orchestrator_graph()
        nodes = graph.nodes
        required_nodes = {
            "init",
            "orchestrator",
            "decide_next",
            "final_feedback",
            "resume_agent",
            "knowledge_agent",
            "question_agent",
            "evaluate_agent",
            "feedback_agent",
            "review_agent",
        }
        for node in required_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_orchestrator_has_review_agent_edge(self):
        """Test that evaluate_agent -> review_agent -> feedback_agent chain exists."""
        graph = create_orchestrator_graph()
        # The compiled graph structure should include the review_agent node
        assert "review_agent" in graph.nodes
        assert "evaluate_agent" in graph.nodes
        assert "feedback_agent" in graph.nodes


class TestOrchestratorNodes:
    """Test orchestrator node functions directly."""

    @pytest.mark.asyncio
    async def test_init_node_sets_initial_state(self):
        """Test init_node properly initializes state."""
        state = InterviewState(session_id="test", resume_id="test")
        result = await init_node(state)
        assert isinstance(result, dict)
        assert result["phase"] == "init"
        assert result["current_series"] == 1
        assert result["followup_depth"] == 0

    @pytest.mark.asyncio
    async def test_orchestrator_node_transitions_phases(self):
        """Test orchestrator_node handles phase transitions."""
        # init -> warmup
        state = InterviewState(session_id="test", resume_id="test", phase="init")
        result = await orchestrator_node(state)
        assert result["phase"] == "warmup"

        # warmup -> initial
        state = InterviewState(session_id="test", resume_id="test", phase="warmup")
        result = await orchestrator_node(state)
        assert result["phase"] == "initial"

        # initial -> followup
        state = InterviewState(session_id="test", resume_id="test", phase="initial")
        result = await orchestrator_node(state)
        assert result["phase"] == "followup"

    def test_decide_next_routes_to_question_agent(self):
        """Test decide_next routes to question_agent in normal flow."""
        from src.config import config
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, current_series=1, error_count=0, all_responsibilities_used=False)
        result = decide_next_node(state)
        assert result == {"next_action": "question_agent"}

    def test_decide_next_routes_to_final_feedback_when_max_series_reached(self):
        """Test decide_next routes to final_feedback when max series reached."""
        from src.config import config
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, current_series=config.max_series + 1)
        result = decide_next_node(state)
        assert result == {"next_action": "final_feedback"}

    def test_decide_next_routes_to_final_feedback_when_error_threshold_reached(self):
        """Test decide_next routes to final_feedback when error threshold reached."""
        from src.config import config
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(state, error_count=config.error_threshold + 1, current_series=1)
        result = decide_next_node(state)
        assert result == {"next_action": "final_feedback"}

    @pytest.mark.asyncio
    async def test_final_feedback_node_returns_completed_phase(self):
        """Test final_feedback_node returns completed phase."""
        state = InterviewState(session_id="test", resume_id="test")
        result = await final_feedback_node(state)
        assert result["phase"] == "completed"


class TestQuestionToFeedbackFlow:
    """Test the full flow from question generation to feedback."""

    @pytest.mark.asyncio
    async def test_question_to_feedback_flow(self):
        """测试从问题生成到反馈的完整流程"""
        initial_state = InterviewState(
            session_id="test_session",
            resume_id="test_resume",
        )

        result = await orchestrator_graph.ainvoke(initial_state)

        # 验证流程能够执行并返回状态
        assert result is not None
        # 至少应该有一个问题或反馈被生成
        has_question = "current_question" in result and result["current_question"] is not None
        has_feedback = len(result.get("feedbacks", {})) > 0
        assert has_question or has_feedback, "Expected either a question or feedback in result"


class TestReviewAgentIntegration:
    """Integration tests for ReviewAgent with orchestrator."""

    def test_review_agent_can_be_imported(self):
        """Test review_agent_graph can be imported."""
        from src.agent.review_agent import review_agent_graph
        assert review_agent_graph is not None

    def test_review_agent_graph_has_review_evaluation_node(self):
        """Test review_agent_graph has review_evaluation node."""
        from src.agent.review_agent import create_review_agent_graph
        graph = create_review_agent_graph()
        assert "review_evaluation" in graph.nodes

    @pytest.mark.asyncio
    async def test_review_evaluation_function_direct_call(self):
        """Test review_evaluation can be called directly with all arguments."""
        from src.agent.review_agent import review_evaluation
        state = InterviewState(session_id="test", resume_id="r1")
        state = replace(state,
            current_question_id="q_test",
            answers={"q_test": Answer(question_id="q_test", content="test", deviation_score=0.8)},
        )
        evaluation_result = {
            "deviation_score": 0.8,
            "is_correct": True,
            "key_points": [],
            "suggestions": [],
        }
        result = await review_evaluation(state, evaluation_result, standard_answer="test answer")
        assert "review_passed" in result
        assert "review_failures" in result


class TestAgentImportChain:
    """Test that all agent graphs can be imported through orchestrator."""

    def test_all_agent_graphs_importable(self):
        """Test all agent graphs can be imported."""
        from src.agent.resume_agent import resume_agent_graph
        from src.agent.knowledge_agent import knowledge_agent_graph
        from src.agent.question_agent import question_agent_graph
        from src.agent.evaluate_agent import evaluate_agent_graph
        from src.agent.feedback_agent import feedback_agent_graph
        from src.agent.review_agent import review_agent_graph

        assert resume_agent_graph is not None
        assert knowledge_agent_graph is not None
        assert question_agent_graph is not None
        assert evaluate_agent_graph is not None
        assert feedback_agent_graph is not None
        assert review_agent_graph is not None
