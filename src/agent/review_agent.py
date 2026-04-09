"""ReviewAgent - Review evaluation results with 3-instance voting."""
import logging

from langgraph.graph import StateGraph

from src.agent.base import create_review_voters
from src.agent.state import InterviewState
from src.agent.prompts import REVIEW_EVALUATION_BASED_ON_QA
from src.llm.client import invoke_llm

logger = logging.getLogger(__name__)


# Global LLM service instance
_llm_service = None


def get_llm_service():
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        from src.services.llm_service import InterviewLLMService
        _llm_service = InterviewLLMService()
    return _llm_service


async def review_evaluation(state: InterviewState) -> dict:
    """
    审查 EvaluateAgent 的评估结果

    Extracts evaluation_result and standard_answer from state.

    Args:
        state: InterviewState

    Returns:
        审查结果: {passed: bool, failures: list[str]}
    """
    question = ""
    user_answer = ""
    evaluation_result = {}
    standard_answer = None

    if state.current_question:
        question = state.current_question.content

    question_id = state.current_question_id
    if question_id:
        if question_id in state.answers:
            user_answer = state.answers[question_id].content
        if hasattr(state, "evaluation_results") and question_id in state.evaluation_results:
            evaluation_result = state.evaluation_results[question_id]
        if question_id in state.mastered_questions:
            standard_answer = state.mastered_questions[question_id].get("standard_answer")

    # 创建 3 个投票器，使用默认参数捕获当前值避免闭包问题
    # Voter 0: async function that uses LLM to check if evaluation is based on Q&A
    async def voter_0(e, q=question, u=user_answer):
        return await _check_evaluation_based_on_qa(q, u, e)

    # Voter 1: sync function that checks deviation score reasonableness
    def voter_1(e, q=question, u=user_answer):
        return _check_evaluation_reasonableness(q, u, e)

    # Voter 2: async function that checks standard answer fit
    async def voter_2(e, q=question, sa=standard_answer):
        return await _check_standard_answer_fit(q, e, sa) if sa else True

    voters = [voter_0, voter_1, voter_2]

    voter = create_review_voters(voters)
    passed, failures = await voter.vote(evaluation_result)

    failure_reasons = []
    if not passed:
        if "Voter 0" in failures:
            failure_reasons.append("evaluation_not_based_on_qa")
        if "Voter 1" in failures:
            failure_reasons.append("evaluation_unreasonable")
        if "Voter 2" in failures:
            failure_reasons.append("standard_answer_mismatch")

    return {
        "review_passed": passed,
        "review_failures": failures,
        "failure_reasons": failure_reasons,
    }


async def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """使用 LLM 判断评估是否基于问答内容"""
    prompt = REVIEW_EVALUATION_BASED_ON_QA.format(
        question=question,
        user_answer=user_answer,
        evaluation=evaluation,
    )
    result = await invoke_llm(
        system_prompt="You are a rigorous evaluation reviewer.",
        user_prompt=prompt,
        temperature=0.3,
    )
    return "YES" in result.upper()


def _check_evaluation_reasonableness(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否合理"""
    dev = evaluation.get("deviation_score", 0.5)
    return 0 <= dev <= 1


async def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str | None) -> bool:
    """使用语义相似度检查标准答案与问题是否契合"""
    if not standard_answer:
        return True
    from src.services.embedding_service import compute_similarity
    score = await compute_similarity(question, standard_answer)
    return score > 0.7


def create_review_agent_graph() -> StateGraph:
    """创建 ReviewAgent 子图"""
    graph = StateGraph(InterviewState)
    graph.add_node("review_evaluation", review_evaluation)
    graph.set_entry_point("review_evaluation")
    graph.add_edge("review_evaluation", "__end__")
    return graph.compile()


review_agent_graph = create_review_agent_graph()
