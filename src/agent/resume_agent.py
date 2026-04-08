"""ResumeAgent - Resume parsing and storage."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState
from src.services.llm_service import InterviewLLMService
from src.agent.retry import async_retryable
from src.agent.fallbacks import get_fallback_question

_llm_service: InterviewLLMService | None = None


def get_llm_service() -> InterviewLLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service


@async_retryable(max_attempts=3)
async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """
    Parse new resume and extract responsibilities using LLM.

    Args:
        state: InterviewState
        resume_text: Raw resume text content

    Returns:
        Dictionary with resume_context, responsibilities tuple, and resume_parsed
    """
    llm_service = get_llm_service()

    try:
        response = await llm_service.extract_resume_info(resume_text)

        responsibilities = []
        for project in response.get("projects", []):
            responsibilities.extend(project.get("responsibilities", []))

        return {
            "resume_context": resume_text,
            "responsibilities": tuple(responsibilities),
            "resume_parsed": response,
        }
    except Exception:
        # Fallback: use simple parsing
        fallback = get_fallback_question("initial")
        return {
            "resume_context": resume_text,
            "responsibilities": tuple(["简历解析失败，使用默认职责"]),
            "resume_parsed": {"skills": [], "projects": [], "experience": []},
        }


async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """Fetch existing resume from database."""
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session

    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        if resume:
            return {"resume_context": resume.content, "resume_id": resume_id}
        return {"resume_context": "", "resume_id": resume_id}

def create_resume_agent_graph() -> StateGraph:
    """Create ResumeAgent subgraph."""
    graph = StateGraph(InterviewState)
    graph.add_node("parse_resume", lambda s: {})
    graph.add_node("fetch_old_resume", lambda s: {})
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "__end__")
    return graph.compile()

resume_agent_graph = create_resume_agent_graph()
