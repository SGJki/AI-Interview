"""ResumeAgent - Resume parsing and storage."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """Parse new resume and extract responsibilities."""
    from src.services.resume_parser import ResumeParser

    parser = ResumeParser()
    parsed = await parser.aparse(resume_text)

    responsibilities = []
    for project in parsed.projects:
        responsibilities.extend(project.responsibilities)

    return {
        "resume_context": parsed.raw_text,
        "responsibilities": tuple(responsibilities),
    }

async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """Fetch existing resume from database."""
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session

    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        if resume:
            return {"resume_context": resume.content}
        return {"resume_context": ""}

def create_resume_agent_graph() -> StateGraph:
    """Create ResumeAgent subgraph."""
    graph = StateGraph(InterviewState)
    graph.add_node("parse_resume", lambda s: {})
    graph.add_node("fetch_old_resume", lambda s: {})
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "__end__")
    return graph.compile()

resume_agent_graph = create_resume_agent_graph()
