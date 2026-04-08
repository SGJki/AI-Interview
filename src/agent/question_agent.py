"""QuestionAgent - Question generation and deduplication."""
import logging
import uuid
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.state import InterviewState, Question, QuestionType
from src.services.llm_service import InterviewLLMService
from src.agent.retry import async_retryable

logger = logging.getLogger(__name__)

_llm_service: InterviewLLMService | None = None


def get_llm_service() -> InterviewLLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service


def generate_question_id() -> str:
    """Generate a unique question ID."""
    return f"q_{uuid.uuid4().hex[:12]}"


@async_retryable(max_attempts=3)
async def generate_warmup(state: InterviewState, resume_context: str = "") -> dict:
    """生成预热问题"""
    llm_service = get_llm_service()

    try:
        question = await llm_service.generate_question(
            series_num=0,
            question_num=0,
            interview_mode="warmup",
            knowledge_context="预热阶段",
        )
        question_content = question.content.strip() if question and question.content else ""
        if not question_content:
            question_content = "请简单介绍一下你自己"
    except Exception as e:
        logger.warning(f"generate_warmup LLM call failed: {e}, using fallback")
        question_content = "请简单介绍一下你自己"

    question_id = generate_question_id()

    return {
        "current_question": Question(
            content=question_content,
            question_type=QuestionType.INITIAL,
            series=0,
            number=0,
            parent_question_id=None,
        ),
        "current_question_id": question_id,
        "followup_depth": 0,
        "followup_chain": [question_id],
    }


@async_retryable(max_attempts=3)
async def generate_initial(
    state: InterviewState,
    resume_context: str,
    responsibility: str,
) -> dict:
    """生成初始问题"""
    llm_service = get_llm_service()

    try:
        question = await llm_service.generate_question(
            series_num=state.current_series,
            question_num=1,
            interview_mode=state.interview_mode.value if hasattr(state.interview_mode, 'value') else str(state.interview_mode),
            knowledge_context=state.knowledge_context or "",
            responsibility_context=responsibility,
        )
        question_content = question.content.strip() if question and question.content else ""
        if not question_content:
            question_content = f"请谈谈你对{responsibility}的经验"
    except Exception as e:
        logger.warning(f"generate_initial LLM call failed: {e}, using fallback")
        question_content = f"请谈谈你对{responsibility}的经验"

    question_id = generate_question_id()

    return {
        "current_question": Question(
            content=question_content,
            question_type=QuestionType.INITIAL,
            series=state.current_series,
            number=1,
            parent_question_id=None,
        ),
        "current_question_id": question_id,
        "followup_depth": 0,
        "followup_chain": [question_id],
    }


@async_retryable(max_attempts=3)
async def generate_followup(
    state: InterviewState,
    qa_history: list,
    evaluation: dict,
) -> dict:
    """生成追问"""
    llm_service = get_llm_service()

    if not state.current_question:
        return {"current_question": None, "current_question_id": None}

    history_str = ""
    for item in qa_history[-3:]:
        history_str += f"Q: {item.get('question', '')}\n"
        history_str += f"A: {item.get('answer', '')}\n\n"

    followup_direction = ""
    if evaluation and not evaluation.get("is_correct", True):
        followup_direction = "深入技术细节，说明具体实践"

    try:
        followup_question = await llm_service.generate_followup_question(
            original_question=state.current_question,
            user_answer=qa_history[-1].get("answer", "") if qa_history else "",
            followup_direction=followup_direction,
            conversation_history=history_str,
        )
        followup_content = followup_question.content.strip() if followup_question and followup_question.content else ""
        if not followup_content:
            followup_content = "能详细说说吗？"
    except Exception as e:
        logger.warning(f"generate_followup LLM call failed: {e}, using fallback")
        followup_content = "能详细说说吗？"

    new_question_id = generate_question_id()
    new_depth = state.followup_depth + 1

    return {
        "current_question": Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=state.current_series,
            number=state.current_question.number + 1 if state.current_question else 1,
            parent_question_id=state.current_question_id,
        ),
        "current_question_id": new_question_id,
        "followup_depth": new_depth,
        "followup_chain": state.followup_chain + [new_question_id],
    }

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
