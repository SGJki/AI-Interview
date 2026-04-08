"""
Interview Agent State Definitions - 短期记忆 (LangGraph State)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Literal


class InterviewMode(str, Enum):
    """面试模式"""
    FREE = "free"           # 自由问答
    TRAINING = "training"   # 专项训练


class FeedbackMode(str, Enum):
    """反馈模式"""
    REALTIME = "realtime"   # 实时点评
    RECORDED = "recorded"   # 全程记录


class FeedbackType(str, Enum):
    """反馈类型"""
    COMMENT = "comment"       # 点评 - 正面评价
    CORRECTION = "correction" # 纠错 - 直接给出正确答案
    GUIDANCE = "guidance"     # 引导 - 提示性追问
    REMINDER = "reminder"     # 提醒 - 连续答错提醒


class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QuestionType(str, Enum):
    """问题类型"""
    INITIAL = "initial"           # 初始问题
    FOLLOWUP = "followup"         # 追问
    GUIDANCE = "guidance"         # 引导性问题
    CLARIFICATION = "clarification"  # 澄清问题


class FollowupStrategy(str, Enum):
    """追问策略"""
    IMMEDIATE = "immediate"       # 立即追问 - 中等偏差时使用
    DEFERRED = "deferred"         # 延迟追问 - 轻微偏差时使用
    SKIP = "skip"                 # 跳过追问 - 高偏差或低偏差时使用


@dataclass(frozen=True)
class Question:
    """面试问题"""
    content: str
    question_type: QuestionType = QuestionType.INITIAL
    series: int = 1
    number: int = 1
    parent_question_id: Optional[str] = None  # 追问链父问题


@dataclass(frozen=True)
class Answer:
    """用户回答"""
    question_id: str
    content: str
    deviation_score: float = 1.0  # 0-1, 1表示完全符合标准回答


@dataclass(frozen=True)
class Feedback:
    """面试反馈"""
    question_id: str
    content: str
    is_correct: bool = True
    guidance: Optional[str] = None
    feedback_type: Optional["FeedbackType"] = None


@dataclass(frozen=True)
class SeriesRecord:
    """
    单个系列的状态记录

    Attributes:
        series: 系列号
        questions: 该系列的问题列表
        answers: 该系列的回答列表
        completed: 该系列是否已完成
    """
    series: int
    questions: tuple[Question, ...] = field(default_factory=tuple)
    answers: tuple[Answer, ...] = field(default_factory=tuple)
    completed: bool = False


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

    # Routing action (used by decide_next_node and conditional edges)
    next_action: Optional[str] = None


@dataclass
class InterviewContext:
    """
    面试完整上下文 - 包含短期+短中期记忆

    面试前加载，面试中更新，面试结束持久化
    """
    session_id: str
    resume_id: str
    knowledge_base_id: str  # RAG 知识库ID

    # 面试配置
    interview_mode: InterviewMode = InterviewMode.FREE
    feedback_mode: FeedbackMode = FeedbackMode.RECORDED
    error_threshold: int = 2
    max_followup_depth: int = 3  # 最大追问深度

    # 面试进度
    current_series: int = 1
    current_question_id: Optional[str] = None

    # 系列历史记录
    series_history: dict[int, dict] = field(default_factory=dict)

    # 回答记录
    answers: list[dict] = field(default_factory=list)  # [{question_id, question, answer, deviation}]
    feedbacks: list[dict] = field(default_factory=list)  # [{question_id, feedback, is_correct}]

    # 追问链追踪
    followup_depth: int = 0
    followup_chain: list[str] = field(default_factory=list)

    # 实时点评队列（用于流式输出）
    # RECORDED 模式： [{question_id, deviation, is_correct}]
    pending_feedbacks: list[dict] = field(default_factory=list)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    error_count: int = 0

    # LLM 上下文（运行时）
    resume_context: str = ""  # 简历提取的上下文信息
    knowledge_context: str = ""  # 知识库检索的上下文
    current_knowledge: str = ""  # 当前问题相关的知识
    question_contents: dict[str, str] = field(default_factory=dict)  # question_id -> question content

    # 职责追踪（用于针对性提问）
    responsibilities: tuple[str, ...] = field(default_factory=tuple)  # 所有职责列表
    series_responsibility_map: dict[int, int] = field(default_factory=dict)  # series_num -> responsibility_index (shuffled)
    current_responsibility_index: int = 0  # 当前职责索引
    current_project_index: int = 0  # 当前项目索引


@dataclass(frozen=True)
class FinalFeedback:
    """
    最终面试反馈

    适用于 RECORDED 模式，面试结束时统一生成

    Attributes:
        overall_score: 整体评分 (0-1)
        series_scores: 各系列评分 {series_number: score}
        strengths: 优点列表
        weaknesses: 缺点列表
        suggestions: 建议列表
    """
    overall_score: float
    series_scores: dict[int, float]
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
