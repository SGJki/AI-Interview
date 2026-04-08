"""EvaluateAgent - Answer evaluation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def evaluate_with_standard(
    state: InterviewState,
    question: str,
    user_answer: str,
    standard_answer: str
) -> dict:
    return {
        "deviation_score": 0.7,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": ["可以更具体"]
    }

async def evaluate_without_standard(
    state: InterviewState,
    question: str,
    user_answer: str
) -> dict:
    return {
        "deviation_score": 0.6,
        "is_correct": True,
        "key_points": ["理解正确"],
        "suggestions": ["补充细节"]
    }

def create_evaluate_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("evaluate_with_standard", evaluate_with_standard)
    graph.add_node("evaluate_without_standard", evaluate_without_standard)
    graph.set_entry_point("evaluate_with_standard")
    graph.add_edge("evaluate_with_standard", "__end__")
    return graph.compile()

evaluate_agent_graph = create_evaluate_agent_graph()
