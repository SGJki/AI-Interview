"""
Domain Enums - 共享枚举类型

所有跨层共享的枚举定义。
"""

from enum import Enum


class InterviewMode(str, Enum):
    """面试模式"""
    FREE = "free"           # 自由问答
    TRAINING = "training"   # 专项训练


class FeedbackMode(str, Enum):
    """反馈模式"""
    REALTIME = "realtime"   # 实时点评
    RECORDED = "recorded"    # 全程记录


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
