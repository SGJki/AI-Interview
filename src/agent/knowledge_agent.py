"""KnowledgeAgent - Knowledge base and responsibility management."""
import logging
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState
from src.agent.retry import async_retryable

logger = logging.getLogger(__name__)


async def shuffle_responsibilities(state: InterviewState, responsibilities: tuple) -> dict:
    import random
    shuffled = list(responsibilities)
    random.shuffle(shuffled)
    return {"responsibilities": tuple(shuffled)}


@async_retryable(max_attempts=3)
async def find_standard_answer(state: InterviewState, question: str) -> dict:
    """
    在 mastered_questions 中查找标准答案

    Args:
        state: InterviewState
        question: 问题内容

    Returns:
        {standard_answer: str | None, similarity_score: float}
    """
    from src.services.embedding_service import compute_similarity

    # 从 mastered_questions 查找（dev >= 0.8 的问答对）
    mastered = state.mastered_questions

    best_match = None
    best_score = 0.0

    for q_id, q_data in mastered.items():
        if q_data.get("deviation_score", 0) >= 0.8:
            # 计算语义相似度
            score = await compute_similarity(question, q_id)
            if score > best_score:
                best_score = score
                best_match = q_data.get("standard_answer")

    if best_match and best_score > 0.8:
        return {"standard_answer": best_match, "similarity_score": best_score}

    return {"standard_answer": None, "similarity_score": 0.0}


async def store_to_vector_db(state: InterviewState, responsibilities: tuple) -> dict:
    """将职责存储到向量数据库"""
    from src.db.vector_store import VectorStore
    from src.services.embedding_service import get_text_embedding

    vector_store = VectorStore()

    try:
        for idx, responsibility in enumerate(responsibilities):
            embedding = await get_text_embedding(responsibility)
            vector_store.add(
                text=responsibility,
                embedding=embedding,
                metadata={"index": idx, "session_id": state.session_id}
            )
        return {"stored": True, "count": len(responsibilities)}
    except Exception as e:
        logger.error("Failed to store responsibilities to vector db: %s", str(e))
        return {"stored": False, "error": str(e)}


async def fetch_responsibility(state: InterviewState, session_id: str) -> dict:
    return {"current_responsibility": ""}

def create_knowledge_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("shuffle_responsibilities", shuffle_responsibilities)
    graph.add_node("store_to_vector_db", store_to_vector_db)
    graph.add_node("fetch_responsibility", fetch_responsibility)
    graph.add_node("find_standard_answer", find_standard_answer)
    graph.set_entry_point("shuffle_responsibilities")
    graph.add_edge("shuffle_responsibilities", "store_to_vector_db")
    graph.add_edge("store_to_vector_db", "__end__")
    return graph.compile()

knowledge_agent_graph = create_knowledge_agent_graph()
