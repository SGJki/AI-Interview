"""FeedBackAgent - Feedback generation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState


async def generate_correction(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    return {"feedback_content": "正确答案是...", "feedback_type": "correction"}


async def generate_guidance(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    return {"feedback_content": "提示：想想...?", "feedback_type": "guidance"}


async def generate_comment(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    return {"feedback_content": "很好，继续...", "feedback_type": "comment"}


async def generate_fallback_feedback(state: InterviewState) -> dict:
    return {"feedback_content": "感谢您的回答，我们继续下一个问题。", "feedback_type": "comment"}


def create_feedback_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("generate_correction", generate_correction)
    graph.add_node("generate_guidance", generate_guidance)
    graph.add_node("generate_comment", generate_comment)
    graph.add_node("generate_fallback_feedback", generate_fallback_feedback)
    graph.set_entry_point("generate_correction")
    graph.add_edge("generate_correction", "__end__")
    return graph.compile()


feedback_agent_graph = create_feedback_agent_graph()
