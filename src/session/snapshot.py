"""
Session Snapshots - 会话快照类型

用于Context Catch功能的快照数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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


@dataclass(frozen=True)
class ProgressSnapshot:
    """
    进度快照 - 规则提取

    Attributes:
        current_series: 当前系列号
        current_question_index: 当前问题索引
        current_phase: 当前阶段 (init/warmup/initial/followup/final_feedback)
        series_history: 系列历史记录 {series_num: SeriesRecord}
        followup_chain: 追问链
        responsibilities: 职责列表
    """
    current_series: int = 1
    current_question_index: int = 1
    current_phase: str = "init"
    series_history: dict[int, dict] = field(default_factory=dict)
    followup_chain: list[str] = field(default_factory=list)
    responsibilities: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvaluationSnapshot:
    """
    评估快照 - 规则提取

    Attributes:
        series_scores: 各系列得分
        error_count: 当前连续错误次数
        error_threshold: 错误阈值
        mastered_questions: 已掌握问题
        asked_logical_questions: 已问的逻辑问题
    """
    series_scores: dict[int, float] = field(default_factory=dict)
    error_count: int = 0
    error_threshold: int = 2
    mastered_questions: dict[str, dict] = field(default_factory=dict)
    asked_logical_questions: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class InsightSummary:
    """
    洞察摘要 - LLM 生成

    Attributes:
        covered_technologies: 已覆盖技术点
        weak_areas: 薄弱领域
        error_patterns: 错误模式
        followup_triggers: 追问触发原因
        interview_continuity_note: 面试连续性备注
    """
    covered_technologies: list[str] = field(default_factory=list)
    weak_areas: list[str] = field(default_factory=list)
    error_patterns: list[str] = field(default_factory=list)
    followup_triggers: list[str] = field(default_factory=list)
    interview_continuity_note: str = ""


@dataclass(frozen=True)
class ContextSnapshotData:
    """
    Context Catch 压缩摘要（内存数据结构）

    Attributes:
        session_id: 会话ID
        version: 版本号
        timestamp: 时间戳
        progress: 进度快照
        evaluation: 评估快照
        insights: LLM 洞察摘要
    """
    session_id: str
    version: int
    timestamp: datetime
    progress: ProgressSnapshot
    evaluation: EvaluationSnapshot
    insights: InsightSummary
