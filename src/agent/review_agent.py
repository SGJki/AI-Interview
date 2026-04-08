"""ReviewAgent - Review evaluation results with 3-instance voting."""
import logging

from langgraph.graph import StateGraph

from src.agent.base import ReviewVoter, create_review_voters
from src.agent.state import InterviewState

logger = logging.getLogger(__name__)


async def review_evaluation(
    state: InterviewState,
    evaluation_result: dict,
    standard_answer: str | None
) -> dict:
    """
    审查 EvaluateAgent 的评估结果

    Args:
        state: InterviewState
        evaluation_result: EvaluateAgent 返回的评估结果
        standard_answer: 标准答案（如果有）

    Returns:
        审查结果: {passed: bool, failures: list[str]}
    """
    question = ""
    user_answer = ""

    if state.current_question:
        question = state.current_question.content
    if state.current_question_id and state.current_question_id in state.answers:
        user_answer = state.answers[state.current_question_id].content

    # 创建 3 个投票器，使用默认参数捕获当前值避免闭包问题
    voters = [
        lambda e, q=question, u=user_answer: _check_evaluation_based_on_qa(q, u, e),
        lambda e, q=question, u=user_answer: _check_evaluation_reasonableness(q, u, e),
        lambda e, q=question, sa=standard_answer: _check_standard_answer_fit(q, e, sa) if sa else True,
    ]

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


def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否基于问答内容"""
    # TODO: 实现 LLM 调用判断
    return True


def _check_evaluation_reasonableness(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否合理"""
    dev = evaluation.get("deviation_score", 0.5)
    return 0 <= dev <= 1


def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str | None) -> bool:
    """检查标准答案与问题是否契合"""
    # TODO: 实现语义相似度检查
    return True


def create_review_agent_graph() -> StateGraph:
    """创建 ReviewAgent 子图"""
    graph = StateGraph(InterviewState)
    graph.add_node("review_evaluation", review_evaluation)
    graph.set_entry_point("review_evaluation")
    graph.add_edge("review_evaluation", "__end__")
    return graph.compile()


review_agent_graph = create_review_agent_graph()
