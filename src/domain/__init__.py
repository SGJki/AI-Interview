"""
Domain Layer - 共享域类型

包含跨层共享的枚举和模型。
"""

from src.domain.enums import (
    InterviewMode,
    FeedbackMode,
    FeedbackType,
    SessionStatus,
    QuestionType,
    FollowupStrategy,
)

from src.domain.models import (
    Question,
    Answer,
    Feedback,
    SeriesRecord,
)

__all__ = [
    # Enums
    "InterviewMode",
    "FeedbackMode",
    "FeedbackType",
    "SessionStatus",
    "QuestionType",
    "FollowupStrategy",
    # Models
    "Question",
    "Answer",
    "Feedback",
    "SeriesRecord",
]
