"""FeedBackAgent - Feedback generation."""
import logging
from typing import Optional

from langgraph.graph import StateGraph

from src.agent.retry import async_retryable
from src.agent.state import InterviewState
from src.domain.enums import FeedbackType
from src.domain.models import Feedback
from src.services.llm_service import InterviewLLMService

logger = logging.getLogger(__name__)

# Global LLM service instance
_llm_service: Optional[InterviewLLMService] = None


def get_llm_service() -> InterviewLLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service


@async_retryable(max_attempts=3)
async def generate_correction(state: InterviewState) -> dict:
    """生成纠正反馈（dev < 0.3）

    Extracts question, user_answer, and evaluation from state.
    """
    # Extract from state
    question = state.current_question.content if state.current_question else ""
    question_id = state.current_question_id or ""
    user_answer_obj = state.answers.get(question_id) if question_id else None
    user_answer = user_answer_obj.content if user_answer_obj else ""
    evaluation = getattr(state, "evaluation_results", {}).get(question_id, {}) if question_id else {}

    # Get cached enterprise docs
    enterprise_docs = state.enterprise_docs

    llm_service = get_llm_service()

    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", False)

    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
            enterprise_docs=enterprise_docs if enterprise_docs else None,
        )
        feedback_content = feedback.content
    except Exception as e:
        logger.error(f"Failed to generate correction feedback: {e}")
        feedback_content = "你对这个问题的理解有偏差，让我来纠正一下..."

    final_question_id = question_id or f"q_{hash(question) % 10000}"

    new_feedback = Feedback(
        question_id=final_question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance="建议回顾相关技术原理",
        feedback_type=FeedbackType.CORRECTION,
    )

    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    pending_feedbacks.append({
        "question_id": final_question_id,
        "feedback": new_feedback,
        "is_correct": is_correct,
    })

    return {
        "feedbacks": {**state.feedbacks, final_question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }


@async_retryable(max_attempts=3)
async def generate_guidance(state: InterviewState) -> dict:
    """生成引导反馈（0.3 <= dev < 0.6）

    Extracts question, user_answer, and evaluation from state.
    """
    # Extract from state
    question = state.current_question.content if state.current_question else ""
    question_id = state.current_question_id or ""
    user_answer_obj = state.answers.get(question_id) if question_id else None
    user_answer = user_answer_obj.content if user_answer_obj else ""
    evaluation = getattr(state, "evaluation_results", {}).get(question_id, {}) if question_id else {}

    # Get cached enterprise docs
    enterprise_docs = state.enterprise_docs

    llm_service = get_llm_service()

    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", False)

    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
            enterprise_docs=enterprise_docs if enterprise_docs else None,
        )
        feedback_content = feedback.content
    except Exception as e:
        logger.error(f"Failed to generate guidance feedback: {e}")
        feedback_content = "你的回答方向正确，但可以更深入一些..."

    final_question_id = question_id or f"q_{hash(question) % 10000}"

    new_feedback = Feedback(
        question_id=final_question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance="请尝试从项目实践角度更详细地说明",
        feedback_type=FeedbackType.GUIDANCE,
    )

    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    pending_feedbacks.append({
        "question_id": final_question_id,
        "feedback": new_feedback,
        "is_correct": is_correct,
    })

    return {
        "feedbacks": {**state.feedbacks, final_question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }


@async_retryable(max_attempts=3)
async def generate_comment(state: InterviewState) -> dict:
    """生成评论反馈（dev >= 0.6）

    Extracts question, user_answer, and evaluation from state.
    """
    # Extract from state
    question = state.current_question.content if state.current_question else ""
    question_id = state.current_question_id or ""
    user_answer_obj = state.answers.get(question_id) if question_id else None
    user_answer = user_answer_obj.content if user_answer_obj else ""
    evaluation = getattr(state, "evaluation_results", {}).get(question_id, {}) if question_id else {}

    # Get cached enterprise docs
    enterprise_docs = state.enterprise_docs

    llm_service = get_llm_service()

    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", False)

    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
            enterprise_docs=enterprise_docs if enterprise_docs else None,
        )
        feedback_content = feedback.content
    except Exception as e:
        logger.error(f"Failed to generate comment feedback: {e}")
        feedback_content = "回答得很好！继续深入。"

    final_question_id = question_id or f"q_{hash(question) % 10000}"

    new_feedback = Feedback(
        question_id=final_question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance=None,
        feedback_type=FeedbackType.COMMENT,
    )

    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    pending_feedbacks.append({
        "question_id": final_question_id,
        "feedback": new_feedback,
        "is_correct": is_correct,
    })

    return {
        "feedbacks": {**state.feedbacks, final_question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }


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
