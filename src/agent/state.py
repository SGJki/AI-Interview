"""
Interview Agent State Definitions - Agent层专用状态

仅保留LangGraph运行时专用的 InterviewState 类型。
其他类型已迁移到 domain/ 和 session/ 层。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from src.domain.enums import InterviewMode, FeedbackMode
from src.domain.models import Question, Answer, Feedback, SeriesRecord


@dataclass(frozen=True)
class InterviewState:
    """
    LangGraph 面试状态 - 短期记忆

    Attributes:
        session_id: 会话ID
        resume_id: 简历ID
        current_series: 当前系列号
        current_question: 当前问题
        current_question_id: 当前问题ID
        followup_depth: 追问深度
        max_followup_depth: 最大追问深度
        followup_chain: 追问链
        series_history: 系列历史记录 {series_number: SeriesRecord}
        answers: 回答记录 {question_id: Answer}
        feedbacks: 反馈记录 {question_id: Feedback}
        interview_mode: 面试模式
        feedback_mode: 反馈模式
        error_threshold: 连续答错阈值
        created_at: 创建时间
        error_count: 当前系列连续错误次数
    """
    session_id: str
    resume_id: str

    # 当前面试进度
    current_series: int = 1
    current_question: Optional[Question] = None
    current_question_id: Optional[str] = None

    # 追问链追踪
    followup_depth: int = 0
    max_followup_depth: int = 3
    followup_chain: list[str] = field(default_factory=list)

    # 系列历史记录
    series_history: dict[int, SeriesRecord] = field(default_factory=dict)

    # 回答记录
    answers: dict[str, Answer] = field(default_factory=dict)
    feedbacks: dict[str, Feedback] = field(default_factory=dict)
    evaluation_results: dict[str, dict] = field(default_factory=dict)  # question_id -> evaluation result

    # 配置
    interview_mode: InterviewMode = InterviewMode.FREE
    feedback_mode: FeedbackMode = FeedbackMode.RECORDED
    error_threshold: int = 2  # 连续答错阈值

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    error_count: int = 0  # 当前系列连续错误次数

    # Series state tracking
    asked_logical_questions: set[str] = field(default_factory=set)  # dev >= 0.8 后加入
    mastered_questions: dict[str, dict] = field(default_factory=dict)  # question_id -> {answer, standard_answer}
    all_responsibilities_used: bool = False

    # Review info
    review_retry_count: int = 0
    last_review_feedback: Optional[str] = None

    # Phase tracking
    phase: Literal["init", "warmup", "initial", "followup", "final_feedback"] = "init"

    # Enterprise KB 相关字段
    enterprise_docs: list = field(default_factory=list)  # 当前问题相关的企业知识文档
    enterprise_docs_retrieved: bool = False  # 是否已查询过企业知识库
    current_module: Optional[str] = None  # 当前问题所属 module
    current_skill_point: Optional[str] = None  # 当前问题关联的 skill_point
    identified_modules: list[str] = field(default_factory=list)  # 简历中识别的所有 module

    # Routing action (used by decide_next_node and conditional edges)
    next_action: Optional[str] = None
