"""EvaluateAgent - Answer evaluation."""
import logging
from typing import Optional

from langgraph.graph import StateGraph

from src.agent.retry import async_retryable
from src.agent.state import InterviewState
from src.domain.models import Answer
from src.services.llm_service import InterviewLLMService
from src.tools.enterprise_knowledge import ensure_enterprise_docs

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
async def evaluate_with_standard(state: InterviewState) -> dict:
    """使用标准答案评估用户回答

    Extracts question, user_answer, and standard_answer from state.
    """
    # Ensure enterprise docs are retrieved
    docs, kb_state_updates = await ensure_enterprise_docs(state)

    # Extract from state
    question = state.current_question.content if state.current_question else ""
    question_id = state.current_question_id or ""
    user_answer_obj = state.answers.get(question_id) if question_id else None
    user_answer = user_answer_obj.content if user_answer_obj else ""

    # Get standard_answer from mastered_questions if available
    standard_answer = ""
    if question_id and question_id in state.mastered_questions:
        standard_answer = state.mastered_questions[question_id].get("standard_answer", "")

    llm_service = get_llm_service()

    try:
        # Build prompt with enterprise docs if available
        if docs:
            # Compute similarity score (placeholder - we'll add this later)
            similarity_score = 0.8  # TODO: implement similarity calculation
            _build_evaluation_prompt_with_similarity(
                question=question,
                user_answer=user_answer,
                enterprise_docs=docs,
                similarity_score=similarity_score,
            )

        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=standard_answer,
        )

        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {e}")
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": ["评估出错"],
            "suggestions": ["请详细描述你的经验"],
        }

    final_question_id = question_id or f"q_{hash(question) % 10000}"

    new_answer = Answer(
        question_id=final_question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )

    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0

    evaluation_results = getattr(state, "evaluation_results", {})
    evaluation_results[final_question_id] = result

    # Merge state updates from KB retrieval
    updates = {
        "answers": {**state.answers, final_question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
        **kb_state_updates,  # Include KB state updates
    }

    return updates


@async_retryable(max_attempts=3)
async def evaluate_without_standard(state: InterviewState) -> dict:
    """无标准答案时评估用户回答

    Extracts question and user_answer from state.
    """
    # Ensure enterprise docs are retrieved
    docs, kb_state_updates = await ensure_enterprise_docs(state)

    # Extract from state
    question = state.current_question.content if state.current_question else ""
    question_id = state.current_question_id or ""
    user_answer_obj = state.answers.get(question_id) if question_id else None
    user_answer = user_answer_obj.content if user_answer_obj else ""

    llm_service = get_llm_service()

    try:
        # Build prompt with enterprise docs if available
        if docs:
            # Compute similarity score (placeholder - we'll add this later)
            similarity_score = 0.8  # TODO: implement similarity calculation
            _build_evaluation_prompt_with_similarity(
                question=question,
                user_answer=user_answer,
                enterprise_docs=docs,
                similarity_score=similarity_score,
            )

        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=None,
        )

        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {e}")
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": ["暂时无法评估"],
            "suggestions": ["请详细描述你的经验"],
        }

    final_question_id = question_id or f"q_{hash(question) % 10000}"

    new_answer = Answer(
        question_id=final_question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )

    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0

    evaluation_results = getattr(state, "evaluation_results", {})
    evaluation_results[final_question_id] = result

    # Merge state updates from KB retrieval
    updates = {
        "answers": {**state.answers, final_question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
        **kb_state_updates,  # Include KB state updates
    }

    return updates


def create_evaluate_agent_graph() -> "CompiledStateGraph":
    graph = StateGraph(InterviewState)
    graph.add_node("evaluate_with_standard", evaluate_with_standard)
    graph.add_node("evaluate_without_standard", evaluate_without_standard)
    graph.set_entry_point("evaluate_with_standard")
    graph.add_edge("evaluate_with_standard", "__end__")
    return graph.compile()


evaluate_agent_graph = create_evaluate_agent_graph()


def _build_evaluation_prompt_with_similarity(
    question: str,
    user_answer: str,
    enterprise_docs: list[dict],
    similarity_score: float,
) -> str:
    """构建含相似度分数和企业知识的评估提示词"""
    prompt = f"""你是一个面试评估专家。请根据以下信息评估候选人的回答。

## 问题
{question}

## 候选人回答
{user_answer}

## 回答与参考答案的相似度
{similarity_score:.2%}

## 企业最佳实践参考答案
"""
    for i, doc in enumerate(enterprise_docs, 1):
        prompt += f"\n{i}. {doc['content']}\n"

    prompt += """
请结合相似度分数和参考答案，从以下几个方面评估：
1. 回答的正确性
2. 回答的完整性
3. 与企业最佳实践的差距
"""
    return prompt
