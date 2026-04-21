"""
Interview API Endpoints - FastAPI Route Handlers

面试相关 API 端点：
- POST /interview/start - 开始面试
- GET /interview/question - 获取当前问题（SSE 流式）
- POST /interview/answer - 提交回答（追问SSE流式）
- POST /interview/end - 结束面试
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator
from dataclasses import replace

from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request
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
    SnapshotRequest,
    SnapshotResponse,
)
from src.domain.enums import InterviewMode, FeedbackMode, QuestionType, FeedbackType
from src.domain.models import Question, Answer, Feedback
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


async def _yield_sse_events(event_stream) -> AsyncGenerator[dict, None]:
    """将服务层事件转换为 SSE 格式"""
    async for event in event_stream:
        yield {
            "event": event["type"],
            "data": json.dumps(event["data"], ensure_ascii=False),
        }


def _yield_pending_feedbacks(pending_feedbacks: list) -> list[dict]:
    """将待发送的反馈列表转换为 SSE 事件列表"""
    events = []
    for pf in pending_feedbacks:
        events.append({
            "event": "feedback",
            "data": json.dumps({
                "question_id": pf.get("question_id"),
                "deviation": pf.get("deviation"),
                "is_correct": pf.get("is_correct"),
                "feedback_content": pf.get("feedback_content"),
                "feedback_type": pf.get("feedback_type", "comment"),
                "guidance": pf.get("guidance"),
            }, ensure_ascii=False),
        })
    return events


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
    request: Request,
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
    import uuid
    from src.core.lifespan_manager import get_connection_tracker

    tracker = get_connection_tracker()
    connection_id = str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            from src.infrastructure.session_store import SessionStateManager

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
                from src.agent.state import InterviewState
                from src.domain.models import Question, Answer
                answers_dict = {}
                for ans in context.answers:
                    if 'question_id' in ans and 'answer' in ans:
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
                    max_followup_depth=context.max_followup_depth,
                    series_history={},
                    interview_mode=context.interview_mode,
                    feedback_mode=context.feedback_mode,
                    error_threshold=context.error_threshold,
                )

            # 流式模式：逐 token 推送
            if stream:
                async for event in _yield_sse_events(service._generate_next_question_stream()):
                    yield event
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
                for event in _yield_pending_feedbacks(context.pending_feedbacks):
                    yield event
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
        finally:
            # 确保连接被注销
            tracker.unregister(connection_id)

    # 注册连接（如果服务器正在关闭，会抛出异常）
    if tracker.is_shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down")

    tracker.register(connection_id, {
        "path": "/interview/question",
        "session_id": session_id,
        "client": request.client.host if request.client else "unknown",
    })

    return EventSourceResponse(event_generator())


@interview_router.post("/answer")
async def submit_answer(
    http_request: Request,
    request: SubmitAnswerRequest,
) -> EventSourceResponse:
    """
    提交回答 - SSE流式输出追问

    Args:
        request: 提交回答请求

    Returns:
        EventSourceResponse: SSE流式响应，包含追问的打字机效果
    """
    import logging
    logger = logging.getLogger(__name__)

    import uuid
    from src.core.lifespan_manager import get_connection_tracker

    tracker = get_connection_tracker()
    connection_id = str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # 获取面试服务
            from src.infrastructure.session_store import SessionStateManager

            session_manager = SessionStateManager()
            context = await session_manager.load_interview_state(request.session_id)

            if not context:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Session not found"}),
                }
                return

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

            logger.info(f"[submit_answer] loaded resume_context len={len(context.resume_context)}")

            # 加载状态
            if context.current_question_id:
                from src.agent.state import InterviewState
                from src.domain.models import Question, Answer
                # 从 context.answers 恢复 dict 格式的回答记录
                answers_dict = {}
                for ans in context.answers:
                    if 'question_id' in ans and 'answer' in ans:
                        answers_dict[ans['question_id']] = Answer(
                            question_id=ans['question_id'],
                            content=ans['answer'],
                            deviation_score=ans.get('deviation', 0.0),
                        )

                # 查找当前问题的内容
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
                    max_followup_depth=context.max_followup_depth,
                    series_history={},
                    interview_mode=context.interview_mode,
                    feedback_mode=context.feedback_mode,
                    error_threshold=context.error_threshold,
                )

            # 评估回答（同步，毫秒级）
            eval_result = await service._evaluate_answer(request.question_id, request.user_answer)
            deviation_score = eval_result["deviation_score"]
            is_correct = eval_result["is_correct"]
            logger.info(f"[submit_answer] evaluation complete, deviation={deviation_score}")

            # RECORDED模式：记录评估结果
            # REALTIME模式：生成反馈
            feedback = None
            if service.feedback_mode == FeedbackMode.REALTIME:
                try:
                    feedback = await service._generate_feedback(request.question_id, request.user_answer, deviation_score)
                    service.context.pending_feedbacks.append({
                        "question_id": request.question_id,
                        "deviation": deviation_score,
                        "is_correct": is_correct,
                        "feedback_content": feedback.content,
                        "feedback_type": feedback.feedback_type.value if feedback.feedback_type else "comment",
                        "guidance": feedback.guidance,
                    })
                except Exception as e:
                    logger.error(f"[submit_answer] feedback generation failed: {e}")
            else:
                service.context.pending_feedbacks.append({
                    "question_id": request.question_id,
                    "deviation": deviation_score,
                    "is_correct": is_correct,
                })

            # 记录回答
            answer = Answer(
                question_id=request.question_id,
                content=request.user_answer,
                deviation_score=deviation_score,
            )
            current_answers = dict(service.state.answers)
            current_answers[request.question_id] = answer
            new_error_count = service.state.error_count + 1 if not is_correct else 0

            service.state = replace(
                service.state,
                answers=current_answers,
                error_count=new_error_count
            )

            question_content = service.state.current_question.content if service.state.current_question else ""
            service.context.answers.append({
                "question_id": request.question_id,
                "question_content": question_content,
                "answer": request.user_answer,
                "deviation": deviation_score,
                "series": service.state.current_series,
            })
            service.context.error_count = new_error_count

            # 检查是否需要提醒（REMINDER）
            if new_error_count >= service.error_threshold:
                reminder_content = f"注意：您在该系列的连续答错次数已达到 {service.error_threshold} 次，建议复习相关知识点后再试。"
                if feedback:
                    feedback = replace(
                        feedback,
                        content=reminder_content,
                        guidance=f"您已连续答错 {service.error_threshold} 次，建议回顾一下该知识点的相关内容。",
                        feedback_type=FeedbackType.REMINDER,
                        is_correct=False,
                    )
                else:
                    feedback = Feedback(
                        question_id=request.question_id,
                        content=reminder_content,
                        is_correct=False,
                        guidance="建议复习相关知识点后再继续。",
                        feedback_type=FeedbackType.REMINDER,
                    )

            # 先发送评估结果
            yield {
                "event": "evaluation",
                "data": json.dumps({
                    "deviation_score": deviation_score,
                    "is_correct": is_correct,
                    "error_count": new_error_count,
                }),
            }

            # 发送待发送的反馈（RECORDED/REALTIME 模式）
            if service.context.pending_feedbacks:
                for event in _yield_pending_feedbacks(service.context.pending_feedbacks):
                    yield event
                service.context.pending_feedbacks = []

            # 判断是否继续
            should_continue = service._should_continue()

            if not should_continue:
                # 面试结束
                yield {
                    "event": "end",
                    "data": json.dumps({
                        "status": "completed",
                        "should_continue": False,
                    }),
                }
                await session_manager.save_interview_state(request.session_id, service.context)
                return

            # 检查是否需要追问
            current_q = service.state.current_question
            if service._should_ask_followup(deviation_score):
                async for event in _yield_sse_events(service._generate_followup_question_stream(
                    current_question=current_q,
                    user_answer=request.user_answer,
                    deviation_score=deviation_score,
                )):
                    yield event
            else:
                if service._is_series_complete():
                    await service._switch_to_next_series()
                async for event in _yield_sse_events(service._generate_next_question_stream()):
                    yield event

            # 发送结束信号
            yield {
                "event": "end",
                "data": json.dumps({
                    "status": "ready",
                    "should_continue": True,
                }),
            }

            # 保存状态
            await session_manager.save_interview_state(request.session_id, service.context)

        except Exception as e:
            logger.error(f"[submit_answer] exception: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }
        finally:
            # 确保连接被注销
            tracker.unregister(connection_id)

    # 注册连接（如果服务器正在关闭，会抛出异常）
    if tracker.is_shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down")

    tracker.register(connection_id, {
        "path": "/interview/answer",
        "session_id": request.session_id,
        "client": http_request.client.host if http_request.client else "unknown",
    })

    return EventSourceResponse(event_generator())


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
        from src.infrastructure.session_store import SessionStateManager

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


# =============================================================================
# Context Catch Endpoints
# =============================================================================

@interview_router.post("/snapshot")
async def create_snapshot(request: SnapshotRequest) -> SnapshotResponse:
    """
    创建上下文快照（用户主动触发）

    Args:
        request: 快照请求，包含会话ID和触发方式

    Returns:
        SnapshotResponse: 包含快照版本和时间戳
    """
    try:
        from src.infrastructure.session_store import SessionStateManager
        from src.core.context_catch import ContextCatchEngine

        session_manager = SessionStateManager()
        context = await session_manager.load_interview_state(request.session_id)

        if not context:
            raise HTTPException(status_code=404, detail="Session not found")

        engine = ContextCatchEngine()
        snapshot = await engine.compress(context, trigger=request.trigger)

        return SnapshotResponse(
            session_id=snapshot.session_id,
            version=snapshot.version,
            timestamp=snapshot.timestamp,
            compressed_summary={
                "progress": {
                    "current_series": snapshot.progress.current_series,
                    "current_phase": snapshot.progress.current_phase,
                    "responsibilities": list(snapshot.progress.responsibilities),
                },
                "evaluation": {
                    "series_scores": snapshot.evaluation.series_scores,
                    "error_count": snapshot.evaluation.error_count,
                },
                "insights": {
                    "covered_technologies": snapshot.insights.covered_technologies,
                    "weak_areas": snapshot.insights.weak_areas,
                    "error_patterns": snapshot.insights.error_patterns,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")


@interview_router.get("/snapshot/{session_id}")
async def get_snapshot(
    session_id: str,
    mode: str = Query("full", description="恢复模式: full/key_points"),
) -> SnapshotResponse:
    """
    获取/恢复上下文快照

    Args:
        session_id: 会话ID
        mode: 恢复模式 (full=完整恢复, key_points=从关键点重新开始)

    Returns:
        SnapshotResponse: 快照信息
    """
    try:
        from src.core.context_catch import ContextCatchEngine

        engine = ContextCatchEngine()
        context = await engine.restore(session_id, mode=mode)

        if not context:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        # 获取最新快照版本
        from src.db.context_snapshot import ContextSnapshot
        from src.db.database import get_db_session

        get_db = get_db_session()
        version = 1
        timestamp = datetime.now()
        compressed_summary = {}

        async for db_session in get_db():
            stmt = (
                ContextSnapshot.__table__.select()
                .where(ContextSnapshot.session_id == session_id)
                .order_by(ContextSnapshot.version.desc())
                .limit(1)
            )
            result = await db_session.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                version = row.version
                timestamp = row.timestamp
                compressed_summary = row.compressed_summary
            break

        return SnapshotResponse(
            session_id=session_id,
            version=version,
            timestamp=timestamp,
            compressed_summary=compressed_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get snapshot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {str(e)}")
