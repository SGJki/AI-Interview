"""
Pydantic Models for FastAPI Interview API

面试 API 请求/响应模型
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# Request Models
# =============================================================================

class StartInterviewRequest(BaseModel):
    """开始面试请求"""
    session_id: str = Field(..., description="会话ID")
    resume_id: Optional[str] = Field(None, description="简历ID/知识库ID（当提供简历内容时构建）")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")
    interview_mode: str = Field("free", description="面试模式: free/training")
    feedback_mode: str = Field("recorded", description="反馈模式: realtime/recorded")
    max_series: int = Field(5, ge=1, le=10, description="最大系列数")
    error_threshold: int = Field(2, ge=1, description="连续答错阈值")


class SubmitAnswerRequest(BaseModel):
    """提交回答请求"""
    session_id: str = Field(..., description="会话ID")
    question_id: str = Field(..., description="问题ID")
    user_answer: str = Field(..., description="用户回答")


class StartTrainingRequest(BaseModel):
    """开始专项训练请求"""
    resume_id: str = Field(..., description="简历ID")
    session_id: str = Field(..., description="会话ID")
    skill_point: str = Field(..., description="技能点")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")


class RagQueryRequest(BaseModel):
    """RAG 查询请求"""
    query: str = Field(..., description="查询文本")
    knowledge_base_id: str = Field(..., description="知识库ID")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")


class BuildKnowledgeRequest(BaseModel):
    """构建知识库请求"""
    knowledge_base_id: str = Field(..., description="知识库ID")
    source_type: str = Field(..., description="数据源类型: resume/preset/standard/skill_point/full")
    source_path: Optional[str] = Field(None, description="数据源路径")
    content: Optional[str] = Field(None, description="简历文本内容（当 source_type=resume 时使用）")
    skill_points: Optional[list[str]] = Field(None, description="技能点列表（当 source_type=skill_point 时使用）")


# =============================================================================
# Response Models
# =============================================================================

class FeedbackData(BaseModel):
    """反馈数据"""
    content: str = Field(..., description="反馈内容")
    feedback_type: str = Field(..., description="反馈类型: comment/correction/guidance/reminder")
    is_correct: bool = Field(..., description="是否正确")
    guidance: Optional[str] = Field(None, description="引导建议")


class QuestionData(BaseModel):
    """问题数据"""
    question_id: str = Field(..., description="问题ID")
    series: int = Field(..., description="系列号")
    number: int = Field(..., description="问题序号")
    content: str = Field(..., description="问题内容")
    question_type: str = Field(..., description="问题类型: initial/followup")


class QAResponse(BaseModel):
    """问答响应"""
    question_id: str = Field(..., description="当前问题ID")
    question_content: str = Field(..., description="当前问题内容")
    feedback: Optional[FeedbackData] = Field(None, description="即时反馈")
    next_question_id: Optional[str] = Field(None, description="下一问题ID")
    next_question_content: Optional[str] = Field(None, description="下一问题内容")
    should_continue: bool = Field(..., description="是否继续")
    interview_status: str = Field(..., description="面试状态: active/completed")


class StartInterviewResponse(BaseModel):
    """开始面试响应"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态")
    first_question: QuestionData = Field(..., description="第一个问题")


class InterviewResult(BaseModel):
    """面试结果"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态: completed/no_active_interview")
    total_questions: int = Field(0, description="总问题数")
    total_series: int = Field(0, description="总系列数")
    final_feedback: dict = Field(default_factory=dict, description="最终反馈")


class TrainingResult(BaseModel):
    """训练结果"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态")
    skill_point: str = Field(..., description="技能点")
    questions_answered: int = Field(0, description="已回答问题数")
    final_feedback: dict = Field(default_factory=dict, description="最终反馈")


class RagQueryResult(BaseModel):
    """RAG 查询结果"""
    query: str = Field(..., description="查询文本")
    results: list[dict] = Field(default_factory=list, description="检索结果")
    total: int = Field(0, description="结果总数")


class BuildKnowledgeResult(BaseModel):
    """构建知识库结果"""
    knowledge_base_id: str = Field(..., description="知识库ID")
    status: str = Field(..., description="状态: building/completed/failed")
    documents_count: int = Field(0, description="处理文档数")


# =============================================================================
# SSE Event Models
# =============================================================================

class SSEEvent(BaseModel):
    """SSE 事件"""
    event: str = Field(..., description="事件类型")
    data: dict = Field(..., description="事件数据")


class SSEMessage(BaseModel):
    """SSE 消息"""
    type: str = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    metadata: Optional[dict] = Field(None, description="元数据")


# =============================================================================
# Context Catch Models
# =============================================================================

class SnapshotRequest(BaseModel):
    """创建快照请求"""
    session_id: str = Field(..., description="会话ID")
    trigger: Literal["auto", "manual"] = Field("manual", description="触发方式: auto=系列结束, manual=用户主动")


class RestoreRequest(BaseModel):
    """恢复会话请求"""
    session_id: str = Field(..., description="会话ID")
    mode: Literal["full", "key_points"] = Field("full", description="恢复模式: full=完整恢复, key_points=从关键点重新开始")


class SnapshotResponse(BaseModel):
    """快照响应"""
    session_id: str = Field(..., description="会话ID")
    version: int = Field(..., description="快照版本号")
    timestamp: datetime = Field(..., description="快照时间戳")
    compressed_summary: dict = Field(..., description="压缩摘要内容")
