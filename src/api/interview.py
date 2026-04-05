"""
Interview API Endpoints - FastAPI Route Handlers

面试相关 API 端点：
- POST /interview/start - 开始面试
- GET /interview/question - 获取当前问题（SSE 流式）
- POST /interview/answer - 提交回答
- POST /interview/end - 结束面试
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from src.api.routers import interview_router
from src.api.models import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    StartInterviewResponse,
    QuestionData,
    QAResponse,
    FeedbackData,
    InterviewResult,
)
from src.agent.state import InterviewMode, FeedbackMode, QuestionType
from src.services.interview_service import InterviewService, create_interview


# =============================================================================
# Helper Functions
# =============================================================================

def _create_service_from_request(request: StartInterviewRequest) -> InterviewService:
    """从请求创建 InterviewService"""
    interview_mode = InterviewMode.FREE if request.interview_mode == "free" else InterviewMode.TRAINING
    feedback_mode = FeedbackMode.REALTIME if request.feedback_mode == "realtime" else FeedbackMode.RECORDED

    return InterviewService(
        session_id=request.session_id,
        resume_id=request.resume_id,
        knowledge_base_id=request.knowledge_base_id,
        interview_mode=interview_mode,
        feedback_mode=feedback_mode,
        max_series=request.max_series,
        error_threshold=request.error_threshold,
    )


def _question_to_data(question, question_id: str) -> QuestionData:
    """将 Question 转换为 QuestionData"""
    return QuestionData(
        question_id=question_id,
        series=question.series,
        number=question.number,
        content=question.content,
        question_type=question.question_type.value if hasattr(question.question_type, 'value') else str(question.question_type),
    )


def _feedback_to_data(feedback) -> FeedbackData:
    """将 Feedback 转换为 FeedbackData"""
    if feedback is None:
        return None
    return FeedbackData(
        content=feedback.content,
        feedback_type=feedback.feedback_type.value if hasattr(feedback.feedback_type, 'value') else str(feedback.feedback_type),
        is_correct=feedback.is_correct,
        guidance=feedback.guidance,
    )


# =============================================================================
# Interview Endpoints
# =============================================================================

@interview_router.post("/start")
async def start_interview(request: StartInterviewRequest) -> StartInterviewResponse:
    """
    开始面试

    Args:
        request: 开始面试请求，包含简历ID、会话ID、模式配置

    Returns:
        StartInterviewResponse: 包含会话ID和第一个问题
    """
    try:
        # 创建面试服务
        service = _create_service_from_request(request)

        # 开始面试
        question = await service.start_interview()

        return StartInterviewResponse(
            session_id=request.session_id,
            status="active",
            first_question=_question_to_data(question, service.state.current_question_id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@interview_router.get("/question")
async def get_question(
    session_id: str = Query(..., description="会话ID")
) -> EventSourceResponse:
    """
    获取当前问题 - SSE 流式输出

    支持流式推送：
    - question 事件: 新问题
    - 追问事件: followup 类型
    - feedback 事件: 即时点评

    Args:
        session_id: 会话ID

    Returns:
        EventSourceResponse: SSE 流式响应
    """
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # 获取面试服务状态
            from src.tools.memory_tools import get_session_memory, SessionStateManager

            session_manager = SessionStateManager()
            context = await session_manager.load_interview_state(session_id)

            if not context:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Session not found"}),
                }
                return

            # 创建服务实例（用于生成问题）
            service = InterviewService(
                session_id=session_id,
                resume_id=context.resume_id,
                knowledge_base_id=context.knowledge_base_id,
                interview_mode=context.interview_mode,
                feedback_mode=context.feedback_mode,
                error_threshold=context.error_threshold,
            )
            service.context = context

            # 获取当前问题
            question = await service.get_current_question()

            if question:
                yield {
                    "event": "question",
                    "data": json.dumps({
                        "question_id": service.state.current_question_id,
                        "series": question.series,
                        "number": question.number,
                        "content": question.content,
                        "question_type": question.question_type.value if hasattr(question.question_type, 'value') else str(question.question_type),
                    }),
                }

                # 检查是否有待发送的反馈（RECORDED 模式）
                if context.pending_feedbacks:
                    for pf in context.pending_feedbacks:
                        yield {
                            "event": "feedback",
                            "data": json.dumps({
                                "question_id": pf.get("question_id"),
                                "deviation": pf.get("deviation"),
                                "is_correct": pf.get("is_correct"),
                            }),
                        }
                    # 清空待发送反馈
                    context.pending_feedbacks = []
                    await session_manager.save_interview_state(session_id, context)

            yield {
                "event": "end",
                "data": json.dumps({"status": "ready"}),
            }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@interview_router.post("/answer")
async def submit_answer(request: SubmitAnswerRequest) -> QAResponse:
    """
    提交回答

    Args:
        request: 提交回答请求

    Returns:
        QAResponse: 包含反馈和下一问题
    """
    try:
        # 获取面试服务
        from src.tools.memory_tools import SessionStateManager

        session_manager = SessionStateManager()
        context = await session_manager.load_interview_state(request.session_id)

        if not context:
            raise HTTPException(status_code=404, detail="Session not found")

        # 创建服务实例
        service = InterviewService(
            session_id=request.session_id,
            resume_id=context.resume_id,
            knowledge_base_id=context.knowledge_base_id,
            interview_mode=context.interview_mode,
            feedback_mode=context.feedback_mode,
            error_threshold=context.error_threshold,
        )
        service.context = context

        # 加载状态
        if context.current_question_id:
            from src.agent.state import Question
            service.state = type('State', (), {
                'current_question': Question(
                    content="",
                    question_type=QuestionType.INITIAL,
                    series=context.current_series,
                    number=len(context.answers) + 1,
                ),
                'current_question_id': context.current_question_id,
                'current_series': context.current_series,
                'answers': {},
                'followup_depth': context.followup_depth,
                'followup_chain': context.followup_chain,
                'error_count': context.error_count,
                'max_followup_depth': 3,
                'series_history': {},
            })()

        # 提交回答
        response = await service.submit_answer(
            user_answer=request.user_answer,
            question_id=request.question_id,
        )

        # 保存更新后的状态
        await session_manager.save_interview_state(request.session_id, service.context)

        return QAResponse(
            question_id=request.question_id,
            question_content=response.question.content if response.question else "",
            feedback=_feedback_to_data(response.feedback),
            next_question_id=response.next_question.question_id if response.next_question and hasattr(response.next_question, 'question_id') else None,
            next_question_content=response.next_question.content if response.next_question else None,
            should_continue=response.should_continue,
            interview_status=response.interview_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")


@interview_router.post("/end")
async def end_interview(
    session_id: str = Query(..., description="会话ID")
) -> InterviewResult:
    """
    结束面试

    Args:
        session_id: 会话ID

    Returns:
        InterviewResult: 面试结果和最终反馈
    """
    try:
        # 获取面试服务
        from src.tools.memory_tools import SessionStateManager

        session_manager = SessionStateManager()
        context = await session_manager.load_interview_state(session_id)

        if not context:
            return InterviewResult(
                session_id=session_id,
                status="no_active_interview",
                total_questions=0,
                total_series=0,
                final_feedback={},
            )

        # 创建服务实例
        service = InterviewService(
            session_id=session_id,
            resume_id=context.resume_id,
            knowledge_base_id=context.knowledge_base_id,
            interview_mode=context.interview_mode,
            feedback_mode=context.feedback_mode,
            error_threshold=context.error_threshold,
        )
        service.context = context

        # 结束面试
        result = await service.end_interview()

        return InterviewResult(
            session_id=session_id,
            status=result.get("status", "completed"),
            total_questions=result.get("total_questions", 0),
            total_series=result.get("total_series", 0),
            final_feedback=result.get("final_feedback", {}),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end interview: {str(e)}")
