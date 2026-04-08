"""QuestionAgent - Question generation and deduplication."""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.state import InterviewState

async def generate_warmup(state: InterviewState, resume_context: str) -> dict:
    return {"current_question": {"content": "请简单介绍一下你自己", "type": "warmup"}}

async def generate_initial(state: InterviewState, resume_context: str, responsibility: str) -> dict:
    return {"current_question": {"content": f"请谈谈你对{responsibility}的经验", "type": "initial"}}

async def generate_followup(state: InterviewState, qa_history: list, evaluation: dict) -> dict:
    return {"current_question": {"content": "能详细说说吗？", "type": "followup"}}

async def deduplicate_check(state: InterviewState, question_id: str) -> dict:
    from src.agent.base import create_review_voters
    voters = [
        lambda q: q.get("question_id") not in state.asked_logical_questions,
        lambda q: True,
        lambda q: True,
    ]
    voter = create_review_voters(voters)
    passed, failures = await voter.vote({"question_id": question_id})
    return {"deduplicate_passed": passed, "deduplicate_failures": failures}

def should_continue_followup(state: InterviewState) -> Literal["generate_followup", END]:
    from src.config import config
    # Get deviation_score from state.answers (dict of question_id -> Answer)
    if state.current_question_id and state.current_question_id in state.answers:
        dev = state.answers[state.current_question_id].deviation_score
    else:
        dev = 0
    depth = state.followup_depth
    if dev >= config.deviation_threshold and depth >= config.max_followup_depth:
        return END
    return "generate_followup"

def create_question_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("generate_warmup", generate_warmup)
    graph.add_node("generate_initial", generate_initial)
    graph.add_node("generate_followup", generate_followup)
    graph.add_node("deduplicate_check", deduplicate_check)
    graph.set_entry_point("generate_warmup")
    graph.add_edge("generate_warmup", "__end__")
    return graph.compile()

question_agent_graph = create_question_agent_graph()
