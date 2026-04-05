"""
Training API Endpoints - FastAPI Route Handlers

专项训练相关 API 端点：
- POST /train/start - 开始专项训练
- POST /train/answer - 提交训练回答
- POST /train/end - 结束训练
"""

from fastapi import APIRouter, HTTPException, Query

from src.api.routers import training_router
from src.api.models import (
    StartTrainingRequest,
    SubmitAnswerRequest,
    TrainingResult,
    QAResponse,
    FeedbackData,
)
from src.agent.state import InterviewMode, FeedbackMode
from src.services.interview_service import InterviewService


@training_router.post("/start")
async def start_training(request: StartTrainingRequest) -> dict:
    """
    开始专项训练

    Args:
        request: 开始训练请求，包含简历ID、技能点等

    Returns:
        dict: 训练会话信息
    """
    try:
        service = InterviewService(
            session_id=request.session_id,
            resume_id=request.resume_id,
            knowledge_base_id=request.knowledge_base_id,
            interview_mode=InterviewMode.TRAINING,
            feedback_mode=FeedbackMode.RECORDED,
            max_series=3,
        )

        # 开始面试（训练模式）
        question = await service.start_interview()

        return {
            "session_id": request.session_id,
            "status": "active",
            "skill_point": request.skill_point,
            "first_question": {
                "question_id": service.state.current_question_id,
                "series": question.series,
                "number": question.number,
                "content": question.content,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@training_router.post("/answer")
async def submit_training_answer(request: SubmitAnswerRequest) -> QAResponse:
    """
    提交训练回答

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
            feedback=FeedbackData(
                content=response.feedback.content if response.feedback else "",
                feedback_type=response.feedback.feedback_type.value if response.feedback and hasattr(response.feedback, 'feedback_type') else "comment",
                is_correct=response.feedback.is_correct if response.feedback else True,
                guidance=response.feedback.guidance if response.feedback else None,
            ) if response.feedback else None,
            next_question_id=None,
            next_question_content=response.next_question.content if response.next_question else None,
            should_continue=response.should_continue,
            interview_status=response.interview_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit training answer: {str(e)}")


@training_router.post("/end")
async def end_training(
    session_id: str = Query(..., description="会话ID")
) -> TrainingResult:
    """
    结束专项训练

    Args:
        session_id: 会话ID

    Returns:
        TrainingResult: 训练结果
    """
    try:
        from src.tools.memory_tools import SessionStateManager

        session_manager = SessionStateManager()
        context = await session_manager.load_interview_state(session_id)

        if not context:
            return TrainingResult(
                session_id=session_id,
                status="no_active_session",
                skill_point="",
                questions_answered=0,
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

        return TrainingResult(
            session_id=session_id,
            status="completed",
            skill_point=context.knowledge_base_id or "",
            questions_answered=len(context.answers),
            final_feedback=result.get("final_feedback", {}),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end training: {str(e)}")
