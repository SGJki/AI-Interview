"""Main Orchestrator - LangGraph main entry point."""
from typing import Literal
from langgraph.graph import StateGraph, END, START
from src.agent.state import InterviewState
from src.agent.resume_agent import resume_agent_graph
from src.agent.knowledge_agent import knowledge_agent_graph
from src.agent.question_agent import question_agent_graph
from src.agent.evaluate_agent import evaluate_agent_graph
from src.agent.feedback_agent import feedback_agent_graph
from src.agent.review_agent import review_agent_graph


async def init_node(state: InterviewState) -> dict:
    return {
        "phase": "init",
        "current_series": 1,
        "followup_depth": 0,
    }


async def orchestrator_node(state: InterviewState) -> dict:
    if state.phase == "init":
        return {"phase": "warmup"}
    elif state.phase == "warmup":
        return {"phase": "initial"}
    elif state.phase == "initial":
        return {"phase": "followup"}
    return {"phase": "final_feedback"}


def decide_next_node(state: InterviewState) -> Literal["question_agent", "final_feedback", END]:
    from src.config import config
    if getattr(state, "user_end_requested", False):
        return "final_feedback"
    if state.current_series >= config.max_series:
        return "final_feedback"
    if state.error_count >= config.error_threshold:
        return "final_feedback"
    if getattr(state, "all_responsibilities_used", False):
        return "final_feedback"
    return "question_agent"


async def final_feedback_node(state: InterviewState) -> dict:
    return {"phase": "completed"}


def create_orchestrator_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("init", init_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("decide_next", decide_next_node)
    graph.add_node("final_feedback", final_feedback_node)
    graph.add_node("resume_agent", resume_agent_graph)
    graph.add_node("knowledge_agent", knowledge_agent_graph)
    graph.add_node("question_agent", question_agent_graph)
    graph.add_node("evaluate_agent", evaluate_agent_graph)
    graph.add_node("feedback_agent", feedback_agent_graph)
    graph.add_node("review_agent", review_agent_graph)
    graph.set_entry_point("init")
    graph.add_edge("init", "orchestrator")
    graph.add_edge("orchestrator", "decide_next")
    graph.add_conditional_edges(
        "decide_next",
        lambda s: s.get("next_action", END),
        {
            "question_agent": "question_agent",
            "resume_agent": "resume_agent",
            "knowledge_agent": "knowledge_agent",
            "evaluate_agent": "evaluate_agent",
            "feedback_agent": "feedback_agent",
            "review_agent": "review_agent",
            "final_feedback": "final_feedback",
        }
    )
    graph.add_edge("question_agent", "evaluate_agent")
    graph.add_edge("evaluate_agent", "review_agent")
    graph.add_edge("review_agent", "feedback_agent")
    graph.add_edge("feedback_agent", "decide_next")
    graph.add_edge("final_feedback", END)
    return graph.compile()


orchestrator_graph = create_orchestrator_graph()
