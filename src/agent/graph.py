"""
AI Interview Agent - LangGraph Graph Definition

LangGraph 负责多状态、多阶段的核心面试流程控制
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import (
    InterviewState,
    InterviewContext,
    InterviewMode,
    FeedbackMode,
    Question,
    QuestionType,
    Answer,
    Feedback,
)


# =============================================================================
# Node Functions
# =============================================================================

async def load_context(state: InterviewState) -> dict:
    """
    加载面试上下文

    从 Redis 加载短中期记忆，从 RAG 加载知识库
    """
    # TODO: 从 Redis 加载会话状态
    # TODO: 从 RAG 加载知识库
    return {
        "current_series": state.current_series,
        "current_question_id": state.current_question_id,
    }


async def generate_question(
    state: InterviewState,
    llm,
    knowledge_base: list[dict] = None
) -> dict:
    """
    生成面试问题

    Args:
        state: 当前状态
        llm: 大模型实例
        knowledge_base: RAG 知识库检索结果

    Returns:
        更新后的状态字典
    """
    # TODO: 根据当前系列和简历信息生成问题
    # TODO: 如果是专项训练模式，从知识库检索相关问题
    # TODO: 支持系列间预生成缓存

    # 模拟生成问题
    question_id = f"q-{state.session_id}-{state.current_series}-{len(state.answers) + 1}"

    question = Question(
        content=f"[模拟问题 {state.current_series}-{len(state.answers) + 1}] 请介绍你的项目经验",
        question_type=QuestionType.INITIAL,
        series=state.current_series,
        number=len(state.answers) + 1,
    )

    return {
        "current_question": question,
        "current_question_id": question_id,
        "current_series": state.current_series,
    }


async def wait_for_answer(state: InterviewState) -> dict:
    """
    等待用户回答

    这是一个暂停节点，实际回答通过 API 传入
    """
    return {}


async def evaluate_answer(
    state: InterviewState,
    question_id: str,
    user_answer: str,
    llm,
    standard_answer: str = None
) -> dict:
    """
    评估用户回答

    Args:
        state: 当前状态
        question_id: 问题ID
        user_answer: 用户回答
        llm: 大模型实例
        standard_answer: 标准回答（来自知识库）

    Returns:
        包含偏差度评估结果的字典
    """
    # TODO: 使用 embedding 模型计算相似度
    # TODO: 使用 LLM 判断回答质量

    # 模拟评估结果
    deviation_score = 0.8  # 默认80%相似度

    return {
        "deviation_score": deviation_score,
        "is_correct": deviation_score >= 0.6,
    }


async def generate_feedback(
    state: InterviewState,
    llm,
    question_id: str,
    user_answer: str,
    deviation_score: float
) -> dict:
    """
    生成反馈

    Args:
        state: 当前状态
        llm: 大模型实例
        question_id: 问题ID
        user_answer: 用户回答
        deviation_score: 偏差度

    Returns:
        反馈内容字典
    """
    # TODO: 根据偏差度生成不同类型的反馈
    # TODO: 支持追问引导

    feedback_content = ""
    feedback_type = "comment"

    if deviation_score < 0.3:
        # 严重偏差 - 直接给出答案
        feedback_content = "回答偏离了主要方向。标准答案是..."
        feedback_type = "correction"
    elif deviation_score < 0.6:
        # 中等偏差 - 提示性追问
        feedback_content = "你提到的方向有一定道理，能否进一步说明..."
        feedback_type = "guidance"
    else:
        # 基本正确 - 继续深入
        feedback_content = "很好，你的理解基本正确。"
        feedback_type = "continue"

    return {
        "feedback": Feedback(
            question_id=question_id,
            content=feedback_content,
            is_correct=deviation_score >= 0.6,
            guidance=None if feedback_type == "correction" else "请进一步思考..."
        ),
        "feedback_type": feedback_type,
    }


def should_continue_interview(
    state: InterviewState,
    max_series: int = 5,
    user_end: bool = False
) -> Literal["generate_question", "end_interview"]:
    """
    判断是否继续面试

    Args:
        state: 当前状态
        max_series: 最大系列数
        user_end: 用户主动结束标志

    Returns:
        下一个节点名称
    """
    if user_end or state.current_series >= max_series:
        return "end_interview"
    return "generate_question"


async def end_interview(state: InterviewState) -> dict:
    """
    结束面试

    持久化 Q&A 到 PostgreSQL，清理 Redis 会话
    """
    # TODO: 写入 PostgreSQL
    # TODO: 清理 Redis
    # TODO: 生成最终面试报告

    return {
        "status": "completed",
    }


# =============================================================================
# Build Graph
# =============================================================================

def create_interview_graph() -> StateGraph:
    """
    创建面试 Agent Graph

    Returns:
        StateGraph 实例
    """
    # 定义图
    graph = StateGraph(InterviewState)

    # 添加节点
    graph.add_node("load_context", load_context)
    graph.add_node("generate_question", generate_question)
    graph.add_node("wait_for_answer", wait_for_answer)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("generate_feedback", generate_feedback)
    graph.add_node("should_continue", should_continue_interview)
    graph.add_node("end_interview", end_interview)

    # 定义边
    graph.add_edge("load_context", "generate_question")
    graph.add_edge("generate_question", "wait_for_answer")
    graph.add_edge("wait_for_answer", "evaluate_answer")
    graph.add_edge("evaluate_answer", "generate_feedback")

    # 条件边：根据面试状态决定下一步
    graph.add_conditional_edges(
        "generate_feedback",
        should_continue_interview,
        {
            "generate_question": "generate_question",
            "end_interview": "end_interview",
        }
    )

    # 设置入口和出口
    graph.set_entry_point("load_context")
    graph.add_edge("end_interview", END)

    return graph


# 全局图实例（单例）
interview_graph = create_interview_graph()

# 可选：带检查点的图实例（支持会话恢复）
checkpointer = MemorySaver()
interview_graph_with_checkpointer = interview_graph.compile(checkpointer=checkpointer)
