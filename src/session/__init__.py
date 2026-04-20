"""
Session Layer - 会话/持久化相关类型

包含会话上下文和快照类型。
"""

from src.session.context import InterviewContext
from src.session.snapshot import (
    FinalFeedback,
    ProgressSnapshot,
    EvaluationSnapshot,
    InsightSummary,
    ContextSnapshotData,
)

__all__ = [
    "InterviewContext",
    "FinalFeedback",
    "ProgressSnapshot",
    "EvaluationSnapshot",
    "InsightSummary",
    "ContextSnapshotData",
]
