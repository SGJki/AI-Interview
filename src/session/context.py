"""
Session Context - 会话上下文

包含面试完整上下文及持久化相关类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from src.domain.enums import InterviewMode, FeedbackMode


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
    phase: Literal["init", "warmup", "initial", "followup", "final_feedback"] = "init"

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
