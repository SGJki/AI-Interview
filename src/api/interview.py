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

    # resume_id 和 knowledge_base_id 相同（简历构建后）
    resume_id = request.resume_id or request.session_id
    knowledge_base_id = request.knowledge_base_id or resume_id

    return InterviewService(
        session_id=request.session_id,
        resume_id=resume_id,
        knowledge_base_id=knowledge_base_id,
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
    session_id: str = Query(..., description="会话ID"),
    stream: bool = Query(False, description="是否流式输出"),
) -> EventSourceResponse:
    """
    获取当前问题 - SSE 流式输出

    支持流式推送：
    - stream=true: token 事件逐 token 推送（打字机效果）
    - stream=false: 返回完整问题（非流式）

    Args:
        session_id: 会话ID
        stream: 是否启用流式输出

    Returns:
        EventSourceResponse: SSE 流式响应
    """
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            from src.tools.memory_tools import SessionStateManager

            session_manager = SessionStateManager()
            context = await session_manager.load_interview_state(session_id)

            if not context:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Session not found"}),
                }
                return

            service = InterviewService(
                session_id=session_id,
                resume_id=context.resume_id,
                knowledge_base_id=context.knowledge_base_id,
                interview_mode=context.interview_mode,
                feedback_mode=context.feedback_mode,
                error_threshold=context.error_threshold,
            )
            service.context = context

            # 初始化 service.state（如果没有的话）
            if service.state is None:
                from src.agent.state import InterviewState, Question
                answers_dict = {}
                for ans in context.answers:
                    if 'question_id' in ans and 'answer' in ans:
                        from src.agent.state import Answer
                        answers_dict[ans['question_id']] = Answer(
                            question_id=ans['question_id'],
                            content=ans['answer'],
                            deviation_score=ans.get('deviation', 0.0),
                        )
                service.state = InterviewState(
                    session_id=session_id,
                    resume_id=context.resume_id,
                    current_series=context.current_series,
                    current_question=Question(
                        content="",
                        question_type=QuestionType.INITIAL,
                        series=context.current_series,
                        number=len(context.answers) + 1,
                    ),
                    current_question_id=context.current_question_id,
                    answers=answers_dict,
                    followup_depth=context.followup_depth,
                    followup_chain=context.followup_chain or [],
                    error_count=context.error_count,
                    max_followup_depth=3,
                    series_history={},
                    interview_mode=context.interview_mode,
                    feedback_mode=context.feedback_mode,
                    error_threshold=context.error_threshold,
                )

            # 流式模式：逐 token 推送
            if stream:
                async for event in service._generate_next_question_stream():
                    event_type = event["type"]
                    if event_type == "question_start":
                        yield {
                            "event": "question_start",
                            "data": json.dumps(event["data"]),
                        }
                    elif event_type == "token":
                        yield {
                            "event": "token",
                            "data": json.dumps(event["data"]),
                        }
                    elif event_type == "question_end":
                        yield {
                            "event": "question_end",
                            "data": json.dumps(event["data"]),
                        }
            else:
                # 非流式模式：直接返回完整问题
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

            # 检查待发送的反馈（RECORDED/REALTIME 模式）
            if context.pending_feedbacks:
                for pf in context.pending_feedbacks:
                    yield {
                        "event": "feedback",
                        "data": json.dumps({
                            "question_id": pf.get("question_id"),
                            "deviation": pf.get("deviation"),
                            "is_correct": pf.get("is_correct"),
                            "feedback_content": pf.get("feedback_content"),
                            "feedback_type": pf.get("feedback_type", "comment"),
                            "guidance": pf.get("guidance"),
                        }),
                    }
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

        # DEBUG: 检查 resume_context 是否正确加载
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[submit_answer] loaded resume_context len={len(context.resume_context)}, context.resume_id={context.resume_id}")

        # 加载状态
        if context.current_question_id:
            from src.agent.state import InterviewState, Question
            # 从 context.answers 恢复 dict 格式的回答记录
            answers_dict = {}
            for ans in context.answers:
                if 'question_id' in ans and 'answer' in ans:
                    from src.agent.state import Answer
                    answers_dict[ans['question_id']] = Answer(
                        question_id=ans['question_id'],
                        content=ans['answer'],
                        deviation_score=ans.get('deviation', 0.0),
                    )

            # 查找当前问题的内容（从 question_contents 或 context.answers）
            question_content = context.question_contents.get(context.current_question_id, "")
            if not question_content:
                for ans in context.answers:
                    if ans.get('question_id') == context.current_question_id:
                        question_content = ans.get('question_content', '')
                        break

            service.state = InterviewState(
                session_id=request.session_id,
                resume_id=context.resume_id,
                current_series=context.current_series,
                current_question=Question(
                    content=question_content,
                    question_type=QuestionType.INITIAL,
                    series=context.current_series,
                    number=len(context.answers) + 1,
                ),
                current_question_id=context.current_question_id,
                answers=answers_dict,
                followup_depth=context.followup_depth,
                followup_chain=context.followup_chain or [],
                error_count=context.error_count,
                max_followup_depth=3,
                series_history={},
                interview_mode=context.interview_mode,
                feedback_mode=context.feedback_mode,
                error_threshold=context.error_threshold,
            )

        # 提交回答
        try:
            response = await service.submit_answer(
                user_answer=request.user_answer,
                question_id=request.question_id,
            )
        except Exception as e:
            logger.error(f"[submit_answer] exception: {e}", exc_info=True)
            raise

        # DEBUG: 检查 submit_answer 后 resume_context
        logger.info(f"[submit_answer] after submit_answer resume_context len={len(service.context.resume_context)}")

        # 保存更新后的状态
        await session_manager.save_interview_state(request.session_id, service.context)

        # DEBUG: 检查保存前 resume_context
        logger.info(f"[submit_answer] before save resume_context len={len(service.context.resume_context)}")

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

        # 处理 final_feedback（可能是 FinalFeedback 对象或 dict）
        final_feedback = result.get("final_feedback", {})
        if hasattr(final_feedback, '__dict__'):
            # FinalFeedback 对象转换为 dict
            final_feedback = {
                "overall_score": final_feedback.overall_score,
                "series_scores": final_feedback.series_scores,
                "strengths": final_feedback.strengths,
                "weaknesses": final_feedback.weaknesses,
                "suggestions": final_feedback.suggestions,
            }

        return InterviewResult(
            session_id=session_id,
            status=result.get("status", "completed"),
            total_questions=result.get("total_questions", 0),
            total_series=result.get("total_series", 0),
            final_feedback=final_feedback,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end interview: {str(e)}")
