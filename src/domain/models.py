"""
Domain Models - 共享数据模型

所有跨层共享的数据类定义。
"""

from dataclasses import dataclass, field
from typing import Optional

from src.domain.enums import QuestionType


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
    feedback_type: Optional[str] = None  # FeedbackType value


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


# Pydantic 模型用于 LLM 结构化输出
from pydantic import BaseModel, Field


class QuestionResult(BaseModel):
    """问题生成的结构化结果（用于 LangChain with_structured_output）"""
    question: str = Field(description="面试问题文本，中文问号结尾")
    module: str = Field(default="", description="所属模块名称，如'用户认证'")
    skill_point: str = Field(default="", description="关联技能点，如'Token管理'")
