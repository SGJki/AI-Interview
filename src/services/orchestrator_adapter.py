"""
OrchestratorAdapter - 用增量 API 包装 LangGraph Orchestrator

提供与 InterviewService 兼容的接口:
- start_interview() -> Question
- submit_answer() -> QAResponse
- end_interview() -> dict
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any

from src.agent.state import (
    InterviewState,
    Question,
    Answer,
    Feedback,
    InterviewMode,
    FeedbackMode,
)

logger = logging.getLogger(__name__)


@dataclass
class QAResponse:
    """问答响应"""
    question: Question
    feedback: Optional[Feedback]
    next_question: Optional[Question]
    should_continue: bool
    interview_status: str


@dataclass
class OrchestratorAdapter:
    """
    Orchestrator 适配器 - 将 LangGraph orchestrator 包装为增量 API

    这个适配器允许 orchestrator 以增量方式工作，
    模拟 InterviewService 的 start → submit_answer → end 模式。
    """
    session_id: str
    resume_id: str
    knowledge_base_id: str = ""

    # 内部状态
    state: Optional[InterviewState] = None

    # 配置选项
    interview_mode: InterviewMode = InterviewMode.FREE
    feedback_mode: FeedbackMode = FeedbackMode.RECORDED
    max_series: int = 5
    error_threshold: int = 2

    # Graph instance (可以注入用于测试)
    _graph: Optional[Any] = None

    @property
    def graph(self):
        """获取 orchestrator graph，延迟加载"""
        if self._graph is None:
            from src.agent.orchestrator import orchestrator_graph
            self._graph = orchestrator_graph
        return self._graph

    def set_graph(self, graph: Any) -> None:
        """设置 mock graph (用于测试)"""
        self._graph = graph

    async def start_interview(self) -> Question:
        """
        开始面试，返回第一个问题

        Returns:
            Question: 第一个面试问题
        """
        # 创建初始状态
        self.state = InterviewState(
            session_id=self.session_id,
            resume_id=self.resume_id,
            interview_mode=self.interview_mode,
            feedback_mode=self.feedback_mode,
            error_threshold=self.error_threshold,
            max_followup_depth=3,
            current_series=1,
        )

        # 运行 orchestrator 直到得到问题
        logger.info(f"Starting interview for session {self.session_id}")

        result = await self.graph.ainvoke(self.state)

        # 更新内部状态
        if isinstance(result, InterviewState):
            self.state = result
        elif isinstance(result, dict):
            # 提取可能的状态更新
            self.state = self._merge_state(self.state, result)

        # 确保有当前问题
        if not self.state.current_question:
            raise ValueError("Failed to generate initial question")

        logger.info(f"Interview started, first question: {self.state.current_question.content[:50]}...")
        return self.state.current_question

    async def submit_answer(self, user_answer: str, question_id: str) -> QAResponse:
        """
        提交回答，获取评估和可能的下一个问题

        Args:
            user_answer: 用户回答
            question_id: 问题 ID

        Returns:
            QAResponse: 包含评估、反馈和下一个问题
        """
        if not self.state:
            raise ValueError("Interview not started. Call start_interview() first.")

        # 创建回答记录
        answer = Answer(
            question_id=question_id,
            content=user_answer,
            deviation_score=1.0,  # 默认值，会被 evaluate_agent 更新
        )

        # 更新状态
        self.state.answers[question_id] = answer

        logger.info(f"Submitting answer for question {question_id}")

        # 运行评估流程
        result = await self.graph.ainvoke(self.state)

        # 更新状态
        if isinstance(result, InterviewState):
            self.state = result
        elif isinstance(result, dict):
            self.state = self._merge_state(self.state, result)

        # 决定下一步
        decision = await self.graph.ainvoke(
            self.state,
            interrupt_before=["question_agent"]
        )

        next_question = None
        should_continue = False

        # 检查是否应该继续
        if hasattr(self.state, 'next_action') and self.state.next_action == "question_agent":
            # 生成下一个问题
            next_result = await self.graph.ainvoke(
                self.state,
                interrupt_before=["evaluate_agent", "review_agent", "feedback_agent"]
            )
            if isinstance(next_result, dict) and 'current_question' in next_result:
                next_question = next_result['current_question']
            elif self.state.current_question:
                next_question = self.state.current_question
            should_continue = True

        # 获取当前问题的反馈
        feedback = self.state.feedbacks.get(question_id)

        return QAResponse(
            question=self.state.current_question,
            feedback=feedback,
            next_question=next_question,
            should_continue=should_continue,
            interview_status="completed" if not should_continue else "active",
        )

    async def end_interview(self) -> dict:
        """
        结束面试，返回最终反馈

        Returns:
            dict: 包含 status, session_id, total_series, total_questions, final_feedback
        """
        if not self.state:
            raise ValueError("Interview not started. Call start_interview() first.")

        logger.info(f"Ending interview for session {self.session_id}")

        # 运行结束节点
        await self.graph.ainvoke(
            self.state,
            interrupt_before=["question_agent", "evaluate_agent", "review_agent", "feedback_agent"]
        )

        # 计算统计
        total_questions = len(self.state.answers)
        total_series = self.state.current_series

        # TODO: 生成最终反馈 (需要 aggregation 逻辑)
        final_feedback = {
            "overall_score": 0.8,  # 占位
            "series_scores": {i: 0.8 for i in range(1, total_series + 1)},
            "strengths": ["表达清晰", "技术深度好"],
            "weaknesses": ["可以更详细"],
            "suggestions": ["多练习系统设计"],
        }

        return {
            "status": "completed",
            "session_id": self.session_id,
            "total_series": total_series,
            "total_questions": total_questions,
            "final_feedback": final_feedback,
        }

    def _merge_state(self, current: InterviewState, updates: dict) -> InterviewState:
        """
        将更新字典合并到当前状态

        这是一个简化版本，LangGraph 返回的 dict 会被转换
        """
        if not updates:
            return current

        # 创建新的状态快照 (frozen dataclass 需要用 replace)
        try:
            from dataclasses import replace
            return replace(current, **{
                k: v for k, v in updates.items()
                if hasattr(current, k)
            })
        except Exception as e:
            logger.warning(f"Failed to merge state: {e}")
            return current
