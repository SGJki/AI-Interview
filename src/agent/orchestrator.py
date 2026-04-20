"""Main Orchestrator - LangGraph main entry point."""
from langgraph.graph import StateGraph, END
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


def decide_next_node(state: InterviewState) -> dict:
    from src.config import config
    if getattr(state, "user_end_requested", False):
        return {"next_action": "end_interview"}
    if state.current_series >= config.max_series:
        return {"next_action": "end_interview"}
    if state.error_count >= config.error_threshold:
        return {"next_action": "end_interview"}
    if getattr(state, "all_responsibilities_used", False):
        return {"next_action": "end_interview"}
    return {"next_action": "question_agent"}


async def final_feedback_node(state: InterviewState) -> dict:
    return {"phase": "completed"}


async def resume_agent_node(state: InterviewState) -> dict:
    return await resume_agent_graph.ainvoke(state)


async def knowledge_agent_node(state: InterviewState) -> dict:
    return await knowledge_agent_graph.ainvoke(state)


async def question_agent_node(state: InterviewState) -> dict:
    return await question_agent_graph.ainvoke(state)


async def evaluate_agent_node(state: InterviewState) -> dict:
    return await evaluate_agent_graph.ainvoke(state)


async def feedback_agent_node(state: InterviewState) -> dict:
    return await feedback_agent_graph.ainvoke(state)


async def review_agent_node(state: InterviewState) -> dict:
    return await review_agent_graph.ainvoke(state)


async def end_interview_node(state: InterviewState) -> dict:
    """结束面试：写入 PostgreSQL + 清理 Redis"""
    from src.infrastructure.session_store import clear_session_memory
    from src.dao.interview_session_dao import InterviewSessionDAO
    from src.db.database import get_db_session
    from uuid import UUID

    # 1. 写入 PostgreSQL
    async for session in get_db_session():
        dao = InterviewSessionDAO(session)
        # state.session_id is UUID string, need to find BIGINT id first
        try:
            session_uuid = UUID(state.session_id) if state.session_id else None
        except ValueError:
            session_uuid = None

        if session_uuid:
            interview_session = await dao.find_by_uuid(session_uuid)
            if interview_session:
                await dao.end_session(interview_session.id)
        break

    # 2. 清理 Redis
    await clear_session_memory(state.session_id)

    return {"phase": "completed"}


def create_orchestrator_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("init", init_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("decide_next", decide_next_node)
    graph.add_node("end_interview", end_interview_node)
    graph.add_node("resume_agent", resume_agent_node)
    graph.add_node("knowledge_agent", knowledge_agent_node)
    graph.add_node("question_agent", question_agent_node)
    graph.add_node("evaluate_agent", evaluate_agent_node)
    graph.add_node("feedback_agent", feedback_agent_node)
    graph.add_node("review_agent", review_agent_node)
    graph.set_entry_point("init")
    graph.add_edge("init", "orchestrator")
    graph.add_edge("orchestrator", "decide_next")
    graph.add_conditional_edges(
        "decide_next",
        lambda s: s.next_action if s.next_action is not None else END,
        {
            "question_agent": "question_agent",
            "resume_agent": "resume_agent",
            "knowledge_agent": "knowledge_agent",
            "evaluate_agent": "evaluate_agent",
            "feedback_agent": "feedback_agent",
            "review_agent": "review_agent",
            "end_interview": "end_interview",
        }
    )
    graph.add_edge("question_agent", "evaluate_agent")
    graph.add_edge("evaluate_agent", "review_agent")
    graph.add_edge("review_agent", "feedback_agent")
    graph.add_edge("feedback_agent", "decide_next")
    graph.add_edge("end_interview", END)
    return graph.compile()


orchestrator_graph = create_orchestrator_graph()
