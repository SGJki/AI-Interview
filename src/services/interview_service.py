"""
Interview Service for AI Interview Agent

面试服务：整合 Agent、工具和状态管理
"""

import logging
import random
import time
from typing import Optional
from dataclasses import dataclass, replace

logger = logging.getLogger(__name__)

from src.agent.state import InterviewState
from src.session.context import InterviewContext
from src.domain.enums import (
    InterviewMode,
    FeedbackMode,
    FeedbackType,
    FollowupStrategy,
    QuestionType,
)
from src.domain.models import (
    Question,
    Answer,
    Feedback,
    SeriesRecord,
)
from src.session.snapshot import FinalFeedback
from src.infrastructure.session_store import (
    save_to_session_memory,
    clear_session_memory,
    cache_next_series_question,
    get_cached_next_question,
)
from src.tools.rag_tools import (
    retrieve_knowledge,
    retrieve_standard_answer,
    retrieve_by_skill_point,
)
from src.services.llm_service import InterviewLLMService
from src.services.embedding_service import compute_similarity, compute_similarities

# Constants
DEFAULT_QUESTION_DEDUP_THRESHOLD = 0.85  # 相似度阈值，超过此值认为问题重复# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class QARequest:
    """问答请求"""
    session_id: str
    user_answer: str
    question_id: str


@dataclass
class QAResponse:
    """问答响应"""
    question: Question
    feedback: Optional[Feedback]
    next_question: Optional[Question]
    should_continue: bool
    interview_status: str


@dataclass
class InterviewConfig:
    """面试配置"""
    session_id: str
    resume_id: str
    knowledge_base_id: str

    # 模式配置
    interview_mode: InterviewMode = InterviewMode.FREE
    feedback_mode: FeedbackMode = FeedbackMode.RECORDED
    max_series: int = 5
    error_threshold: int = 2

    # 专项训练配置
    training_skill_point: Optional[str] = None


# =============================================================================
# Interview Service
# =============================================================================

class InterviewService:
    """
    面试服务

    整合所有组件，提供完整的面试功能
    """

    def __init__(
        self,
        session_id: str,
        resume_id: str,
        knowledge_base_id: str = None,
        interview_mode: InterviewMode = InterviewMode.FREE,
        feedback_mode: FeedbackMode = FeedbackMode.RECORDED,
        max_series: int = 5,
        error_threshold: int = 2,
    ):
        """
        初始化面试服务

        Args:
            session_id: 会话ID
            resume_id: 简历ID
            knowledge_base_id: 知识库ID
            interview_mode: 面试模式
            feedback_mode: 反馈模式
            max_series: 最大系列数
            error_threshold: 连续答错阈值
        """
        self.session_id = session_id
        self.resume_id = resume_id
        self.knowledge_base_id = knowledge_base_id or ""

        self.interview_mode = interview_mode
        self.feedback_mode = feedback_mode
        self.max_series = max_series
        self.error_threshold = error_threshold

        # 当前状态
        self.state: Optional[InterviewState] = None
        self.context: Optional[InterviewContext] = None

    async def start_interview(self) -> Question:
        """
        开始面试

        Returns:
            第一个问题
        """
        # 创建初始状态
        self.state = InterviewState(
            session_id=self.session_id,
            resume_id=self.resume_id,
            interview_mode=self.interview_mode,
            feedback_mode=self.feedback_mode,
            error_threshold=self.error_threshold,
        )

        # 创建上下文
        self.context = InterviewContext(
            session_id=self.session_id,
            resume_id=self.resume_id,
            knowledge_base_id=self.knowledge_base_id,
            interview_mode=self.interview_mode,
            feedback_mode=self.feedback_mode,
            error_threshold=self.error_threshold,
        )

        # 加载知识库（如有）
        if self.knowledge_base_id:
            await self._load_knowledge_base()

        # 加载职责列表（用于针对性提问）
        await self._load_responsibilities()

        # 生成第一个问题
        question = await self._generate_next_question()

        # 保存到 Redis（问题生成后）
        await save_to_session_memory(self.session_id, self.context)

        return question

    async def restore_interview(self) -> tuple[Question, bool]:
        """
        恢复面试会话

        使用 RecoveryManager 协调 ContextCatch 和 PromptCache 进行会话恢复。
        如果缓存有效，恢复速度快；如果缓存失效或无缓存，降级恢复。

        Returns:
            tuple[Question, bool]: (第一个问题, 是否降级恢复)
            - 问题: 恢复后的当前问题
            - 是否降级: True=降级恢复(缓存无效)，False=正常恢复(缓存有效)

        Raises:
            ValueError: 如果会话不存在
        """
        from src.core.recovery_manager import RecoveryManager

        manager = RecoveryManager()

        try:
            result = await manager.recover_session(self.session_id)
        except ValueError:
            # 会话不存在，降级到 start_interview
            logger.info(f"Session {self.session_id} not found, starting fresh")
            question = await self.start_interview()
            return question, True

        if result.degraded:
            logger.info(f"Session {self.session_id} recovered in degraded mode: {result.degraded_reason}")
        else:
            logger.info(f"Session {self.session_id} recovered with cache hit rate: {result.cache_hit_rate:.2%}")

        # 恢复状态和上下文
        self.state = result.snapshot
        self.context = InterviewContext(
            session_id=self.session_id,
            resume_id=self.resume_id,
            knowledge_base_id=self.knowledge_base_id,
            interview_mode=self.interview_mode,
            feedback_mode=self.feedback_mode,
            error_threshold=self.error_threshold,
        )

        # 降级恢复时从快照补充关键状态
        if result.degraded:
            if hasattr(result.snapshot, 'current_series'):
                self.state.current_series = result.snapshot.current_series
            if hasattr(result.snapshot, 'error_count'):
                self.state.error_count = result.snapshot.error_count

        # 加载知识库（如有）
        if self.knowledge_base_id:
            await self._load_knowledge_base()

        # 生成当前问题
        question = await self._generate_next_question()

        # 保存到 Redis
        await save_to_session_memory(self.session_id, self.context)

        return question, result.degraded

    async def submit_answer(self, user_answer: str, question_id: str) -> QAResponse:
        """
        提交回答

        Args:
            user_answer: 用户回答
            question_id: 问题ID

        Returns:
            问答响应
        """
        logger.info(f"[submit_answer] START resume_context len={len(self.context.resume_context)}, context id={id(self.context)}")

        if not self.state or not self.context:
            raise ValueError("面试未开始")

        # 评估回答
        eval_result = await self._evaluate_answer(question_id, user_answer)
        deviation_score = eval_result["deviation_score"]
        is_correct = eval_result["is_correct"]

        # RECORDED 模式：只记录评估结果，不生成即时反馈
        # REALTIME 模式：立即生成反馈
        feedback = None
        if self.feedback_mode == FeedbackMode.REALTIME:
            logger.info(f"[submit_answer] REALTIME mode, generating feedback...")
            try:
                feedback = await self._generate_feedback(question_id, user_answer, deviation_score)
                logger.info(f"[submit_answer] feedback generated: {feedback.content[:50]}...")
                # 存储反馈到 pending_feedbacks 用于 SSE 推送
                self.context.pending_feedbacks.append({
                    "question_id": question_id,
                    "deviation": deviation_score,
                    "is_correct": is_correct,
                    "feedback_content": feedback.content,
                    "feedback_type": feedback.feedback_type.value if feedback.feedback_type else "comment",
                    "guidance": feedback.guidance,
                })
            except Exception as e:
                logger.error(f"[submit_answer] feedback generation failed: {e}", exc_info=True)
                raise
        else:
            # RECORDED 模式：将评估结果存入 pending_feedbacks
            self.context.pending_feedbacks.append({
                "question_id": question_id,
                "deviation": deviation_score,
                "is_correct": is_correct,
            })

        # 记录回答
        answer = Answer(
            question_id=question_id,
            content=user_answer,
            deviation_score=deviation_score,
        )

        # 使用 replace 创建新状态（frozen dataclass）
        current_answers = dict(self.state.answers)
        current_answers[question_id] = answer

        # 计算新的错误计数
        new_error_count = self.state.error_count + 1 if not is_correct else 0

        # 更新状态（使用 replace 保持 frozen dataclass 不可变性）
        self.state = replace(
            self.state,
            answers=current_answers,
            error_count=new_error_count
        )

        # 更新 context - 保存问题内容以便后续追问时使用
        question_content = self.state.current_question.content if self.state.current_question else ""
        self.context.answers.append({
            "question_id": question_id,
            "question_content": question_content,
            "answer": user_answer,
            "deviation": deviation_score,
            "series": self.state.current_series,
        })
        self.context.error_count = new_error_count

        # 检查是否需要提醒（REMINDER）
        if new_error_count >= self.error_threshold:
            # 创建 REMINDER 类型的反馈
            reminder_content = f"注意：您在该系列的连续答错次数已达到 {self.error_threshold} 次，建议复习相关知识点后再试。"
            if feedback:
                # 使用 replace 创建新的 Feedback（保持 frozen dataclass 不可变性）
                feedback = replace(
                    feedback,
                    content=reminder_content,
                    guidance=f"您已连续答错 {self.error_threshold} 次，建议回顾一下该知识点的相关内容。",
                    feedback_type=FeedbackType.REMINDER,
                    is_correct=False,
                )
            else:
                # 没有反馈时创建纯提醒
                feedback = Feedback(
                    question_id=question_id,
                    content=reminder_content,
                    is_correct=False,
                    guidance="建议复习相关知识点后再继续。",
                    feedback_type=FeedbackType.REMINDER,
                )

        # 判断是否继续
        should_continue = self._should_continue()
        next_question = None

        if should_continue:
            # 检查是否需要追问（基于偏差分数）
            # 追问条件：0.3 <= deviation < 0.6 且未达到最大追问深度
            if self._should_ask_followup(deviation_score):
                # 生成追问（基于用户回答）
                current_q = self.state.current_question
                next_question = await self._generate_followup_question(
                    current_question=current_q,
                    user_answer=user_answer,
                    deviation_score=deviation_score,
                )
            else:
                # 生成下一个新问题前，先检查是否需要切换系列
                if self._is_series_complete():
                    await self._switch_to_next_series()
                next_question = await self._generate_next_question()

        # 更新记忆
        await save_to_session_memory(self.session_id, self.context)

        return QAResponse(
            question=self.state.current_question,
            feedback=feedback,
            next_question=next_question,
            should_continue=should_continue,
            interview_status="active" if should_continue else "completed",
        )

    async def end_interview(self) -> dict:
        """
        结束面试

        Returns:
            面试总结，包含最终反馈
        """
        if not self.context:
            return {"status": "no_active_interview"}

        # 生成最终反馈（RECORDED 模式）
        final_feedback = await self.generate_final_feedback()

        # 清空 pending_feedbacks
        self.context.pending_feedbacks = []

        # 清理 Redis 记忆
        await clear_session_memory(self.session_id)

        # 写入 PostgreSQL
        await self._persist_to_postgresql(final_feedback)

        return {
            "status": "completed",
            "session_id": self.session_id,
            "total_series": self.context.current_series,
            "total_questions": len(self.context.answers),
            "final_feedback": final_feedback,
        }

    async def get_current_question(self) -> Optional[Question]:
        """
        获取当前问题

        Returns:
            当前问题或 None
        """
        if self.state:
            return self.state.current_question
        return None

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _load_knowledge_base(self):
        """加载知识库

        从向量数据库加载与当前面试相关的知识上下文
        """
        if not self.context:
            return

        logger.info(f"[_load_knowledge_base] resume_id={self.resume_id}, knowledge_base_id={self.knowledge_base_id}")

        # 如果有简历ID，使用元数据过滤加载简历相关内容
        if self.resume_id:
            try:
                docs = await retrieve_knowledge(
                    query="简历 项目 经验 技术栈",
                    top_k=10,
                    filter_metadata={"resume_id": self.resume_id}
                )
                logger.info(f"[_load_knowledge_base] retrieved {len(docs)} docs for resume_id={self.resume_id}")
                if docs:
                    self.context.resume_context = "\n".join([doc.page_content for doc in docs])
                    logger.info(f"[_load_knowledge_base] set resume_context length={len(self.context.resume_context)}")
            except Exception as e:
                logger.error(f"[_load_knowledge_base] error loading resume: {e}")

        # 如果有知识库ID，加载知识库相关内容
        if self.knowledge_base_id:
            try:
                docs = await retrieve_knowledge(
                    query="面试问题 技术项目 经验",
                    top_k=10,
                    filter_metadata={"resume_id": self.knowledge_base_id}
                )
                logger.info(f"[_load_knowledge_base] retrieved {len(docs)} docs for knowledge_base_id={self.knowledge_base_id}")
                if docs:
                    self.context.knowledge_context = "\n".join([doc.page_content for doc in docs])
                    logger.info(f"[_load_knowledge_base] set knowledge_context length={len(self.context.knowledge_context)}")
            except Exception as e:
                logger.error(f"[_load_knowledge_base] error loading knowledge: {e}")

    async def _persist_to_postgresql(self, final_feedback: dict) -> None:
        """持久化面试数据到 PostgreSQL

        将面试会话、问答历史和反馈写入数据库

        迁移后版本：使用 BIGSERIAL 主键，通过 uuid 列定位

        Args:
            final_feedback: 最终反馈字典
        """
        if not self.context:
            logger.warning("[_persist_to_postgresql] No context to persist")
            return

        try:
            from src.db.database import get_database_manager
            from src.db.models import InterviewSession, QAHistory, InterviewFeedback, Resume
            from uuid import UUID, uuid4
            from sqlalchemy import select
            from datetime import datetime

            db = get_database_manager()

            # 验证 session_id 和 resume_id 是有效的 UUID 格式
            try:
                session_uuid = UUID(self.session_id) if self.session_id else None
                resume_uuid = UUID(self.resume_id) if self.resume_id else None
            except ValueError:
                logger.warning(f"[_persist_to_postgresql] Invalid UUID format, session_id={self.session_id}, resume_id={self.resume_id}")
                return

            if not session_uuid or not resume_uuid:
                logger.warning(f"[_persist_to_postgresql] Missing session_uuid or resume_uuid")
                return

            async with db.get_session() as session:
                # 1. 通过 resumes.uuid 找到 resume 的 BIGSERIAL id
                stmt_resume = select(Resume).where(Resume.uuid == resume_uuid)
                result_resume = await session.execute(stmt_resume)
                resume = result_resume.scalar_one_or_none()

                if not resume:
                    logger.warning(f"[_persist_to_postgresql] Resume not found for uuid={resume_uuid}")
                    return

                resume_id_bigint = resume.id  # BIGINT
                user_id_bigint = resume.user_id  # BIGINT

                # 2. 查找或创建面试会话
                # 先尝试通过 interview_sessions.uuid 查找现有会话
                stmt_session = select(InterviewSession).where(InterviewSession.uuid == session_uuid)
                result_session = await session.execute(stmt_session)
                interview_session = result_session.scalar_one_or_none()

                if interview_session:
                    # 更新现有会话
                    interview_session.status = "completed"
                    interview_session.ended_at = datetime.now()
                else:
                    # 创建新会话
                    interview_session = InterviewSession(
                        uuid=session_uuid,  # 存储 UUID
                        user_id=user_id_bigint,  # BIGINT
                        resume_id=resume_id_bigint,  # BIGINT
                        mode=self.context.interview_mode.value if hasattr(self.context.interview_mode, 'value') else str(self.context.interview_mode),
                        feedback_mode=self.context.feedback_mode.value if hasattr(self.context.feedback_mode, 'value') else str(self.context.feedback_mode),
                        status="completed",
                    )
                    session.add(interview_session)

                await session.flush()
                session_id_bigint = interview_session.id  # BIGINT

                # 3. 保存问答历史
                for answer_data in self.context.answers:
                    if isinstance(answer_data, dict):
                        qa_history = QAHistory(
                            session_id=session_id_bigint,  # BIGINT
                            series=answer_data.get("series", 1),
                            question_number=answer_data.get("question_number", 1),
                            question=answer_data.get("question", ""),
                            user_answer=answer_data.get("answer", ""),
                            standard_answer=answer_data.get("standard_answer"),
                            feedback=answer_data.get("feedback"),
                            deviation_score=answer_data.get("deviation", 1.0),
                        )
                        session.add(qa_history)

                # 4. 保存最终反馈
                if final_feedback:
                    feedback_record = InterviewFeedback(
                        session_id=session_id_bigint,  # BIGINT
                        overall_score=final_feedback.get("overall_score", 0.0),
                        strengths=final_feedback.get("strengths", []),
                        weaknesses=final_feedback.get("weaknesses", []),
                        suggestions=final_feedback.get("suggestions", []),
                    )
                    session.add(feedback_record)

                await session.commit()
                logger.info(f"[_persist_to_postgresql] Persisted interview data for session {self.session_id}")

        except Exception as e:
            logger.error(f"[_persist_to_postgresql] Failed to persist interview data: {e}")

    async def _load_responsibilities(self):
        """加载职责列表

        从 Chroma 向量库加载简历中的个人职责，用于针对性提问
        """
        if not self.context or not self.resume_id:
            return

        logger.info(f"[_load_responsibilities] resume_id={self.resume_id}")

        try:
            # 从 Chroma 向量库获取职责列表
            from src.services.responsibility_service import ResponsibilityStorageService
            responsibilities = await ResponsibilityStorageService.get_responsibilities_by_resume_from_chroma(
                resume_id=self.resume_id,
                top_k=50
            )
            logger.info(f"[_load_responsibilities] loaded {len(responsibilities)} responsibilities from Chroma")

            # 更新 context
            self.context.responsibilities = tuple(responsibilities)
            logger.info(f"[_load_responsibilities] set responsibilities tuple with {len(responsibilities)} items")

            # 创建系列-职责的随机映射（以时间为种子）
            if responsibilities:
                random.seed(int(time.time()))
                indices = list(range(len(responsibilities)))
                random.shuffle(indices)

                # 获取最大系列数
                max_series = getattr(self, 'max_series', 5) or 5
                series_map = {}
                for i in range(max_series):
                    # 职责数量少于系列数时用 modulo 轮换
                    series_map[i + 1] = indices[i % len(indices)]

                self.context.series_responsibility_map = series_map
                logger.info(f"[_load_responsibilities] created shuffled series_responsibility_map: {series_map}")

        except Exception as e:
            logger.error(f"[_load_responsibilities] error: {e}")

    def _get_responsibility_for_series(self, series_num: int) -> str:
        """获取指定系列对应的职责

        Args:
            series_num: 系列编号（从1开始）

        Returns:
            职责文本，如果没有职责则返回空字符串
        """
        if not self.context or not self.context.responsibilities:
            return ""

        responsibilities = self.context.responsibilities

        # 优先使用预计算的 series_responsibility_map
        if hasattr(self.context, 'series_responsibility_map') and self.context.series_responsibility_map:
            resp_idx = self.context.series_responsibility_map.get(series_num)
            if resp_idx is not None and resp_idx < len(responsibilities):
                return responsibilities[resp_idx]

        # 回退：使用 modulo 轮换职责
        resp_idx = (series_num - 1) % len(responsibilities)
        return responsibilities[resp_idx]

    def _is_valid_uuid(self, value: str) -> bool:
        """检查字符串是否为有效的 UUID 格式"""
        from uuid import UUID
        if not value:
            return False
        try:
            UUID(value)
            return True
        except ValueError:
            return False

    async def _check_question_duplication(
        self,
        question_content: str,
        threshold: float = DEFAULT_QUESTION_DEDUP_THRESHOLD,
    ) -> tuple[bool, Optional[str]]:
        """
        检查问题是否与历史问题重复（语义相似度检测）

        Args:
            question_content: 待检查的问题内容
            threshold: 相似度阈值，超过此值认为重复

        Returns:
            (is_duplicate, similar_question_id): 是否重复及相似的问题ID
        """
        # 验证 resume_id 是否为有效的 UUID 格式
        if not self._is_valid_uuid(self.resume_id):
            logger.warning(f"[_check_question_duplication] resume_id '{self.resume_id}' is not a valid UUID, skipping duplicate check")
            return False, None

        try:
            from src.db.database import get_db_session
            from src.dao.project_dao import ProjectDAO
            from src.db.models import KnowledgeBase
            from sqlalchemy import select, and_

            async for session in get_db_session():
                # 获取当前简历关联的project_id
                project_dao = ProjectDAO(session)
                projects = await project_dao.find_by_resume_id(self.resume_id)
                if not projects:
                    return False, None

                project_id = projects[0].id

                # 查找该简历历史问题（跨session）
                result = await session.execute(
                    select(KnowledgeBase)
                    .where(
                        and_(
                            KnowledgeBase.project_id == project_id,
                            KnowledgeBase.type == "question",
                            KnowledgeBase.question_id.isnot(None)
                        )
                    )
                )
                existing_questions = list(result.scalars().all())

                if not existing_questions:
                    return False, None

                # 收集所有历史问题内容和ID的映射
                text_to_qid = {}
                text_list = []
                for q in existing_questions:
                    if q.content:
                        text_list.append(q.content)
                        text_to_qid[q.content] = q.question_id

                if not text_list:
                    return False, None

                # 批量计算相似度（一次embedding调用）
                similarities = await compute_similarities(question_content, text_list)

                # 遍历相似度结果，找到最高的
                max_similarity = 0.0
                most_similar_id = None
                for text, similarity in similarities:
                    if similarity > max_similarity:
                        max_similarity = similarity
                        most_similar_id = text_to_qid.get(text)

                    if similarity >= threshold:
                        logger.info(f"[_check_question_duplication] Question similar to {most_similar_id}, similarity={similarity}")
                        return True, most_similar_id

                logger.info(f"[_check_question_duplication] max_similarity={max_similarity}, threshold={threshold}")
                break

        except Exception as e:
            # 检查是否是表不存在的错误
            error_str = str(e).lower()
            if "does not exist" in error_str or "undefinedtable" in error_str:
                logger.warning(f"[_check_question_duplication] Database tables not initialized. Run scripts/init_db.py to create tables.")
            else:
                logger.error(f"[_check_question_duplication] error: {e}")
            return False, None

    async def _save_question_to_kb(
        self,
        question_id: str,
        content: str,
        responsibility_id: Optional[int] = None,
        responsibility_text: Optional[str] = None,
    ) -> bool:
        """
        保存生成的问题到知识库（用于去重追踪）

        Args:
            question_id: 问题ID
            content: 问题内容
            responsibility_id: 职责索引
            responsibility_text: 职责文本

        Returns:
            是否保存成功
        """
        # 验证 resume_id 是否为有效的 UUID 格式
        if not self._is_valid_uuid(self.resume_id):
            logger.warning(f"[_save_question_to_kb] resume_id '{self.resume_id}' is not a valid UUID, skipping save")
            return False

        try:
            from src.db.database import get_db_session
            from src.dao.knowledge_base_dao import KnowledgeBaseDAO
            from src.dao.project_dao import ProjectDAO

            async for session in get_db_session():
                dao = KnowledgeBaseDAO(session)

                # 获取project_id
                project_dao = ProjectDAO(session)
                projects = await project_dao.find_by_resume_id(self.resume_id)
                if not projects:
                    logger.warning(f"[_save_question_to_kb] No project found for resume {self.resume_id}")
                    return False

                project_id = projects[0].id

                # 保存问题
                await dao.save_question(
                    project_id=project_id,
                    question_id=question_id,
                    session_id=self.session_id,
                    content=content,
                    responsibility_id=responsibility_id,
                    responsibility_text=responsibility_text,
                )

                logger.info(f"[_save_question_to_kb] Saved question {question_id}")
                break
            return True

        except Exception as e:
            # 检查是否是表不存在的错误
            error_str = str(e).lower()
            if "does not exist" in error_str or "undefinedtable" in error_str:
                logger.warning(f"[_save_question_to_kb] Database tables not initialized. Run scripts/init_db.py to create tables.")
            else:
                logger.error(f"[_save_question_to_kb] error: {e}")
            return False

    async def _generate_next_question(self) -> Question:
        """
        生成下一个问题

        Returns:
            下一个问题
        """
        logger.info(f"[_generate_next_question] ENTRY resume_context len={len(self.context.resume_context)}, context id={id(self.context)}")

        # 检查是否有预生成的问题
        cached_q = await get_cached_next_question(
            self.session_id,
            self.state.current_series
        )

        if cached_q:
            logger.info(f"[_generate_next_question] USING CACHED Q, resume_context len={len(self.context.resume_context)}, context id={id(self.context)}")
            # 使用预生成的问题
            question = Question(
                content=cached_q,
                question_type=QuestionType.INITIAL,
                series=self.state.current_series,
                number=len(self.state.answers) + 1,
            )
        else:
            logger.info(f"[_generate_next_question] GENERATING NEW Q, resume_context len={len(self.context.resume_context)}, context id={id(self.context)}")
            # 动态生成 - 使用 LLM
            logger.info(f"[_generate_next_question] resume_id={self.resume_id}")

            resume_info = self.context.resume_context or self.resume_id or "无简历信息"
            logger.info(f"[_generate_next_question] final resume_info len={len(resume_info)}")

            llm_service = InterviewLLMService(
                resume_info=resume_info
            )

            # 获取主题领域
            topic_area = self._get_next_topic()

            # 获取知识库上下文
            knowledge_context = ""
            if self.context.knowledge_context:
                knowledge_context = self.context.knowledge_context

            # 使用 LLM 生成问题
            question = await llm_service.generate_question(
                series_num=self.state.current_series,
                question_num=len(self.state.answers) + 1,
                interview_mode=self.interview_mode.value,
                topic_area=topic_area,
                knowledge_context=knowledge_context,
            )

        # 生成问题ID
        question_id = f"q-{self.session_id}-{self.state.current_series}-{question.number}"

        # 使用 replace 创建新状态（frozen dataclass）
        self.state = replace(
            self.state,
            current_question=question,
            current_question_id=question_id,
        )
        self.context.current_question_id = question_id

        # 如果是专项训练模式，检查知识库
        if self.interview_mode == InterviewMode.TRAINING and self.context.knowledge_base_id:
            # 检索相关技能点知识
            try:
                docs = await retrieve_by_skill_point(
                    skill_point=question.content[:20],  # 取前20字作为技能点查询
                    top_k=3
                )
                if docs:
                    self.context.current_knowledge = "\n".join([doc.page_content for doc in docs])
            except Exception:
                pass

        return question

    async def _generate_next_question_stream(self):
        """
        生成下一个问题（流式）

        Yields:
            问题的每个 token
        """
        logger.info(f"[_generate_next_question_stream] ENTRY resume_context len={len(self.context.resume_context)}")

        resume_info = self.context.resume_context or self.resume_id or "无简历信息"

        # 获取当前系列对应的职责（用于针对性提问）
        responsibility_context = self._get_responsibility_for_series(self.state.current_series)
        if responsibility_context:
            resume_info = f"{resume_info}\n\n【当前面试重点】{responsibility_context}"

        logger.info(f"[_generate_next_question_stream] responsibility_context preview: {responsibility_context[:100]}...")
        topic_area = self._get_next_topic()
        knowledge_context = self.context.knowledge_context or ""

        llm_service = InterviewLLMService(
            resume_info=resume_info
        )

        # 生成问题ID
        question_number = len(self.state.answers) + 1
        question_id = f"q-{self.session_id}-{self.state.current_series}-{question_number}"
        logger.info(f"[_generate_next_question_stream] question_id={question_id}")

        # 先发送 metadata
        yield {
            "type": "question_start",
            "data": {
                "question_id": question_id,
                "series": self.state.current_series,
                "number": question_number,
            }
        }
        logger.info(f"[_generate_next_question_stream] sent question_start event")

        # 流式生成问题，同时缓冲完整内容用于去重检查
        full_content = ""
        token_count = 0
        max_retries = 3
        dedup_threshold = DEFAULT_QUESTION_DEDUP_THRESHOLD

        for retry in range(max_retries):
            try:
                async for token in llm_service.generate_question_stream(
                    series_num=self.state.current_series,
                    question_num=question_number,
                    interview_mode=self.interview_mode.value,
                    topic_area=topic_area,
                    knowledge_context=knowledge_context,
                ):
                    token_count += 1
                    full_content += token
                    # 流式发送每个 token（与 followup 版本保持一致）
                    yield {
                        "type": "token",
                        "data": {"content": token}
                    }
                break  # 生成成功，跳出重试循环
            except Exception as e:
                logger.error(f"[_generate_next_question_stream] error: {e}")
                if retry == max_retries - 1:
                    # 所有重试都失败了，使用 fallback 内容
                    full_content = "请介绍一下你最近做的项目，以及在其中承担的角色？"
                    # 将 fallback 内容作为 token 发送
                    for char in full_content:
                        yield {
                            "type": "token",
                            "data": {"content": char}
                        }
                    # 跳出重试循环，跳过后续去重检查
                    break
                else:
                    full_content = ""  # 重试时清空
                    continue

                if retry > 0:
                    logger.info(f"[_generate_next_question_stream] retry {retry} after checking duplication")

        logger.info(f"[_generate_next_question_stream] generated content len={len(full_content)}, checking duplication...")

        # 检查问题是否重复（仅对初始问题检查）
        if self.state.followup_depth == 0:
            is_dup, similar_id = await self._check_question_duplication(full_content, dedup_threshold)
            if is_dup:
                logger.warning(f"[_generate_next_question_stream] Question duplicated with {similar_id}, requesting regeneration")
                # 问题重复，发送重试信号
                yield {
                    "type": "retry",
                    "data": {"reason": "question_duplicated", "similar_id": similar_id}
                }
                return

        logger.info(f"[_generate_next_question_stream] streaming complete, total_tokens={token_count}, full_content len={len(full_content)}")

        # 创建 Question 对象并更新 state
        question = Question(
            content=full_content,
            question_type=QuestionType.INITIAL,
            series=self.state.current_series,
            number=question_number,
            parent_question_id=None,
        )
        self.state = replace(
            self.state,
            current_question=question,
            current_question_id=question_id,
        )
        self.context.current_question_id = question_id
        # 保存问题内容到 context 以便后续 submit_answer 使用
        self.context.question_contents[question_id] = full_content
        logger.info(f"[_generate_next_question_stream] state updated with question, content len={len(full_content)}")

        # 保存到知识库（用于后续去重，仅初始问题）
        if self.state.followup_depth == 0:
            responsibility_id = self.context.series_responsibility_map.get(self.state.current_series)
            responsibility_text = self._get_responsibility_for_series(self.state.current_series)
            await self._save_question_to_kb(
                question_id=question_id,
                content=full_content,
                responsibility_id=responsibility_id,
                responsibility_text=responsibility_text,
            )

        # 发送完成信号
        yield {
            "type": "question_end",
            "data": {"question_id": question_id}
        }
        logger.info(f"[_generate_next_question_stream] sent question_end event")

    async def _evaluate_answer(
        self,
        question_id: str,
        user_answer: str
    ) -> dict:
        """
        评估回答

        使用 Embedding 相似度 + LLM 判断回答质量

        Returns:
            评估结果字典
        """
        # 获取当前问题内容
        question_content = ""
        if self.state.current_question:
            question_content = self.state.current_question.content

        # 检索标准回答（如果有）
        standard_answer = None
        try:
            doc = await retrieve_standard_answer(question_content)
            if doc:
                standard_answer = doc.page_content
        except Exception:
            pass

        # 使用 LLM 服务评估回答
        llm_service = InterviewLLMService(
            resume_info=self.context.resume_context or self.resume_id or ""
        )

        evaluation = await llm_service.evaluate_answer(
            question=question_content,
            user_answer=user_answer,
            standard_answer=standard_answer,
        )

        # 如果没有标准回答，使用 embedding 相似度作为补充
        if not standard_answer and self.context.current_knowledge:
            # 使用知识库内容作为参考计算相似度
            similarity = await compute_similarity(user_answer, self.context.current_knowledge)
            # 综合分数
            final_score = evaluation.get("deviation_score", 0.5) * 0.7 + similarity * 0.3
            evaluation["deviation_score"] = final_score
            evaluation["is_correct"] = final_score >= 0.6

        return evaluation

    async def _generate_feedback(
        self,
        question_id: str,
        user_answer: str,
        deviation_score: float
    ) -> Feedback:
        """
        生成反馈

        根据 deviation_score 使用 LLM 生成不同类型的实时反馈:
        - deviation_score < 0.3: CORRECTION (直接给出正确答案)
        - deviation_score < 0.6: GUIDANCE (提示性追问)
        - deviation_score >= 0.6: COMMENT (正面点评)

        Returns:
            反馈内容
        """
        is_correct = deviation_score >= 0.6

        # 获取当前问题内容
        question_content = ""
        if self.state.current_question:
            question_content = self.state.current_question.content

        # 使用 LLM 生成反馈
        llm_service = InterviewLLMService(
            resume_info=self.context.resume_context or self.resume_id or ""
        )

        feedback = await llm_service.generate_feedback(
            question=question_content,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
        )

        # 设置 question_id（使用 replace 保持 frozen dataclass 不可变性）
        feedback = replace(feedback, question_id=question_id)

        return feedback

    async def generate_final_feedback(self) -> FinalFeedback:
        """
        生成最终面试反馈

        适用于 RECORDED 模式，面试结束时调用
        遍历所有回答，生成整体评价

        Returns:
            FinalFeedback: 包含整体评分、各系列评分、优缺点和建议
        """
        if not self.context:
            return FinalFeedback(
                overall_score=0.0,
                series_scores={},
                strengths=[],
                weaknesses=[],
                suggestions=[],
            )

        pending_feedbacks = self.context.pending_feedbacks

        # 无回答时返回默认反馈
        if not pending_feedbacks:
            return FinalFeedback(
                overall_score=0.0,
                series_scores={},
                strengths=["暂无数据"],
                weaknesses=["暂无数据"],
                suggestions=["暂无数据"],
            )

        # 计算整体评分
        total_deviation = sum(p["deviation"] for p in pending_feedbacks)
        overall_score = total_deviation / len(pending_feedbacks)

        # 计算各系列评分
        # 优先使用 series_history，如果存在则从中提取系列评分
        series_score_avg: dict[int, float] = {}
        if self.context.series_history:
            for series_num, series_data in self.context.series_history.items():
                series_answers = series_data.get("answers", [])
                if series_answers:
                    deviations = [a.get("deviation", 0) for a in series_answers]
                    series_score_avg[series_num] = sum(deviations) / len(deviations)
        else:
            # 如果没有 series_history，从 pending_feedbacks 推断系列
            # 根据 question_id 模式 "q-{session_id}-{series}-{number}" 提取系列号
            series_map: dict[int, list[float]] = {}
            for pf in pending_feedbacks:
                qid = pf["question_id"]
                # 格式: q-{session_id}-{series}-{number}
                parts = qid.split("-")
                if len(parts) >= 3:
                    try:
                        series = int(parts[2])
                    except ValueError:
                        series = 1
                else:
                    series = 1

                if series not in series_map:
                    series_map[series] = []
                series_map[series].append(pf["deviation"])

            for series, deviations in series_map.items():
                if deviations:
                    series_score_avg[series] = sum(deviations) / len(deviations)

        # 分析优缺点
        strengths: list[str] = []
        weaknesses: list[str] = []
        suggestions: list[str] = []

        # 高分回答 (deviation >= 0.8) 识别为优点
        high_score_count = sum(1 for p in pending_feedbacks if p["deviation"] >= 0.8)
        if high_score_count > 0:
            strengths.append(f"整体表现良好，在 {high_score_count} 个问题中回答准确")

        # 低分回答 (deviation < 0.4) 识别为缺点
        low_score_count = sum(1 for p in pending_feedbacks if p["deviation"] < 0.4)
        if low_score_count > 0:
            weaknesses.append(f"有 {low_score_count} 个问题回答不够深入，需要加强")

        # 介于高低分之间的为中等
        mid_score_count = sum(1 for p in pending_feedbacks if 0.4 <= p["deviation"] < 0.8)
        if mid_score_count > 0:
            suggestions.append(f"有 {mid_score_count} 个问题可以进一步优化回答质量")

        # 根据整体评分给出建议
        if overall_score >= 0.8:
            suggestions.append("整体表现优秀，建议挑战更深入的问题")
        elif overall_score >= 0.6:
            suggestions.append("基础扎实，可加强技术细节的理解")
        elif overall_score >= 0.4:
            suggestions.append("需要加强核心知识点的掌握")
        else:
            suggestions.append("建议系统复习相关技术知识")

        return FinalFeedback(
            overall_score=overall_score,
            series_scores=series_score_avg,
            strengths=strengths if strengths else ["暂无明显优点"],
            weaknesses=weaknesses if weaknesses else ["暂无明显缺点"],
            suggestions=suggestions,
        )

    def _should_continue(self) -> bool:
        """
        判断是否继续面试

        Returns:
            是否继续
        """
        # 检查是否达到最大系列数
        if self.state.current_series >= self.max_series:
            return False

        # 检查回答数量（可选：限制总问题数）
        total_questions = len(self.state.answers)
        if total_questions >= self.max_series * 3:  # 每个系列最多3个问题
            return False

        return True

    def _is_series_complete(self) -> bool:
        """
        判断当前系列是否已完成

        当 followup_depth 回到 0 且当前系列的问题数量达到阈值时，认为系列完成

        Returns:
            当前系列是否已完成
        """
        # 追问深度必须回到 0 才算系列完成
        if self.state.followup_depth != 0:
            return False

        # 统计当前系列的问题数量
        current_series = self.state.current_series
        questions_in_current_series = [
            q for q in self.state.answers.keys()
            if q.startswith(f"q-{self.session_id}-{current_series}-")
        ]

        # 每个系列至少需要 1 个问题才认为完成
        return len(questions_in_current_series) >= 1

    async def _compress_current_series(self) -> None:
        """
        Context Catch + Prompt Cache: 压缩当前系列状态并更新缓存

        在系列切换时自动调用，使用 RecoveryManager 协调保存快照和缓存状态
        """
        try:
            from src.core.recovery_manager import RecoveryManager

            manager = RecoveryManager()

            # 1. 生成压缩快照（包含进度、评估、洞察）
            from src.core.context_catch import ContextCatchEngine
            engine = ContextCatchEngine()
            snapshot = await engine.compress(self.context, trigger="auto")

            # 2. 使用 RecoveryManager 统一保存（快照 + 缓存状态）
            await manager.save_checkpoint(self.session_id, snapshot)
        except Exception as e:
            # 压缩失败不应该阻止系列切换，记录日志继续执行
            logger.warning(f"ContextCatch compress failed: {e}")

    async def _switch_to_next_series(self) -> None:
        """
        切换到下一个系列

        记录当前系列到历史记录，重置错误计数
        """
        # Context Catch: 系列切换前自动压缩
        await self._compress_current_series()

        current_series = self.state.current_series

        # 收集当前系列的问题和回答
        series_question_ids = [
            qid for qid in self.state.answers.keys()
            if qid.startswith(f"q-{self.session_id}-{current_series}-")
        ]

        # 获取当前系列的问题（从 current_question 或 followup_chain）
        current_questions = []
        if self.state.current_question and self.state.current_question.series == current_series:
            current_questions.append(self.state.current_question)

        # 构建当前系列的记录
        series_record = SeriesRecord(
            series=current_series,
            questions=tuple(current_questions),
            answers=tuple(self.state.answers[qid] for qid in series_question_ids),
            completed=True,
        )

        # 更新 series_history
        new_series_history = dict(self.state.series_history)
        new_series_history[current_series] = series_record

        # 切换到下一个系列，重置 error_count 和 followup_depth
        self.state = replace(
            self.state,
            current_series=current_series + 1,
            error_count=0,
            followup_depth=0,
            followup_chain=[],
            series_history=new_series_history,
        )

        # 更新 context
        self.context.current_series = current_series + 1
        self.context.error_count = 0
        self.context.followup_depth = 0
        self.context.followup_chain = []

        # 切换完成后触发预生成
        await self._pregenerate_next_series_question()

    async def _pregenerate_next_series_question(self) -> None:
        """
        预生成下一系列的问题

        在当前系列完成后调用，提前生成下一系列的问题以减少延迟
        """
        next_series = self.state.current_series + 1

        # 检查是否已达最大系列数
        if next_series > self.max_series:
            return

        # 使用 LLM 生成下一个问题
        llm_service = InterviewLLMService(
            resume_info=self.context.resume_context or self.resume_id or "无简历信息"
        )

        topic_area = self._get_next_topic()

        try:
            question = await llm_service.generate_question(
                series_num=next_series,
                question_num=1,
                interview_mode=self.interview_mode.value,
                topic_area=topic_area,
                knowledge_context=self.context.knowledge_context or "",
            )
            generated_question = question.content
        except Exception:
            # LLM 调用失败时使用回退
            generated_question = f"关于{topic_area}，请介绍一下你的相关经验和理解？"

        # 存入 Redis 缓存
        await cache_next_series_question(
            self.session_id,
            next_series,
            generated_question,
            ttl=3600
        )

    def _get_next_topic(self) -> str:
        """
        获取下一个系列的主题

        根据当前系列历史确定下一个系列的主题

        Returns:
            主题描述
        """
        # 简单实现：基于系列号返回通用主题
        topic_map = {
            1: "项目经验",
            2: "技术深度",
            3: "问题解决",
            4: "团队协作",
            5: "职业发展",
        }
        return topic_map.get(self.state.current_series + 1, "综合能力")

    def _should_ask_followup(self, deviation_score: float) -> bool:
        """
        判断是否需要追问

        追问策略:
        - deviation_score < 0.3: 极低偏差，直接给出正确答案（SKIP）
        - 0.3 <= deviation_score < 0.6: 中等偏差，需要追问（IMMEDIATE）
        - deviation_score >= 0.6: 高偏差，不需要追问（SKIP）

        Args:
            deviation_score: 偏差分数 (0-1)

        Returns:
            是否需要追问
        """
        if self.state is None:
            return False

        # 达到最大追问深度时不追问
        if self.state.followup_depth >= self.state.max_followup_depth:
            return False

        # 中等偏差需要追问
        if 0.3 <= deviation_score < 0.6:
            return True

        # 其他情况不追问
        return False

    def _get_followup_topic(self, current_question: Question) -> str:
        """
        获取追问主题

        基于当前问题提取追问的主题方向

        Args:
            current_question: 当前问题

        Returns:
            追问主题描述
        """
        # 从当前问题内容中提取关键词作为追问主题
        content = current_question.content

        # 简单实现：提取问题中的关键技术词汇
        keywords = []
        if "微服务" in content or "Spring Cloud" in content:
            keywords.append("微服务")
        if "项目" in content:
            keywords.append("项目经验")
        if "架构" in content:
            keywords.append("架构设计")
        if "性能" in content:
            keywords.append("性能优化")
        if "数据库" in content or "SQL" in content:
            keywords.append("数据库")
        if "Redis" in content or "缓存" in content:
            keywords.append("缓存")
        if "并发" in content or "多线程" in content:
            keywords.append("并发")

        if keywords:
            return "、".join(keywords[:2])  # 最多返回两个关键词
        return "相关知识点"

    def _build_conversation_history(self) -> str:
        """构建对话历史上下文 - 包含当前系列的所有问答"""
        if not self.context or not self.context.answers:
            return "无历史问答"

        # 获取当前系列号
        current_series = self.state.current_series if self.state else 1

        # 筛选当前系列的所有问答
        series_answers = [
            ans for ans in self.context.answers
            if ans.get("series", 1) == current_series
        ]

        if not series_answers:
            return "无历史问答"

        # 构建系列对话历史
        history_parts = []
        for ans in series_answers:
            question_content = ans.get("question_content", "")
            answer_content = ans.get("answer", "")
            if question_content:
                history_parts.append(f"问: {question_content}\n答: {answer_content}")
            else:
                history_parts.append(f"答: {answer_content}")

        return "\n\n".join(history_parts)

    def _get_followup_direction(self, deviation_score: float) -> str:
        """根据偏差分数获取追问方向"""
        if deviation_score < 0.3:
            return "纠正错误理解，深入讲解正确概念"
        elif deviation_score < 0.6:
            return "引导深入项目细节和实践经验"
        else:
            return "鼓励继续深入，引导展示更多项目经验"

    async def _generate_followup_question(
        self,
        current_question: Question,
        user_answer: str,
        deviation_score: float
    ) -> Question:
        """
        生成追问

        基于当前问题、回答和偏差度生成追问

        Args:
            current_question: 当前问题
            user_answer: 用户回答
            deviation_score: 偏差分数 (0-1)

        Returns:
            生成的追问
        """
        if self.state is None:
            raise ValueError("面试状态未初始化")

        # 判断是否需要追问
        if not self._should_ask_followup(deviation_score):
            return Question(
                content="",
                question_type=QuestionType.FOLLOWUP,
                series=current_question.series,
                number=current_question.number + 1,
                parent_question_id=None,
            )

        # 构建对话历史上下文
        conversation_history = self._build_conversation_history()

        # 使用 LLM 生成追问
        llm_service = InterviewLLMService(
            resume_info=self.context.resume_context or "无简历信息"
        )

        try:
            followup_content = await llm_service.generate_followup_question(
                original_question=current_question,
                user_answer=user_answer,
                followup_direction=self._get_followup_direction(deviation_score),
                conversation_history=conversation_history,
            )
            followup_content = followup_content.content
        except Exception:
            # Fallback to simple follow-up if LLM fails
            topic = self._get_followup_topic(current_question)
            if deviation_score < 0.3:
                followup_content = "让我来纠正一下这个概念..."
            elif deviation_score < 0.6:
                followup_content = f"关于{topic}，能否详细说说你在项目中是如何实践的？"
            else:
                followup_content = f"你提到{topic}，能具体说说遇到了什么挑战吗？"

        # 生成追问的问题ID
        followup_question_id = f"q-{self.session_id}-{current_question.series}-{current_question.number + self.state.followup_depth + 1}"

        # 更新追问链
        new_followup_chain = list(self.state.followup_chain)
        if current_question.question_type == QuestionType.FOLLOWUP:
            # 如果当前问题是追问，追加到链
            new_followup_chain.append(followup_question_id)
        else:
            # 如果是初始问题且已有追问链，追加到链；否则创建新链
            if new_followup_chain:
                new_followup_chain.append(followup_question_id)
            else:
                new_followup_chain = [followup_question_id]

        # 更新状态
        new_followup_depth = self.state.followup_depth + 1
        self.state = replace(
            self.state,
            followup_depth=new_followup_depth,
            followup_chain=new_followup_chain,
        )

        # 更新 context
        if self.context:
            self.context.followup_depth = new_followup_depth
            self.context.followup_chain = new_followup_chain
            # 保存追问内容以便后续 submit_answer 使用
            self.context.question_contents[followup_question_id] = followup_content

        return Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=current_question.series,
            number=current_question.number + self.state.followup_depth,
            parent_question_id=self.state.current_question_id,
        )

    async def _generate_followup_question_stream(
        self,
        current_question: Question,
        user_answer: str,
        deviation_score: float
    ):
        """
        生成追问（流式）

        基于当前问题、回答和偏差度生成追问，通过SSE流式输出

        Yields:
            追问的每个 token 和元数据
        """
        logger.info(f"[_generate_followup_question_stream] ENTRY")

        if self.state is None:
            raise ValueError("面试状态未初始化")

        # 判断是否需要追问
        if not self._should_ask_followup(deviation_score):
            logger.info(f"[_generate_followup_question_stream] _should_ask_followup returned False, skipping")
            return

        # 生成追问的问题ID
        question_number = current_question.number + self.state.followup_depth + 1
        followup_question_id = f"q-{self.session_id}-{current_question.series}-{question_number}"
        logger.info(f"[_generate_followup_question_stream] followup_question_id={followup_question_id}")

        # 先发送 metadata
        yield {
            "type": "question_start",
            "data": {
                "question_id": followup_question_id,
                "series": current_question.series,
                "number": question_number,
                "question_type": "followup",
                "parent_question_id": self.state.current_question_id,
            }
        }
        logger.info(f"[_generate_followup_question_stream] sent question_start event")

        # 构建对话历史上下文
        conversation_history = self._build_conversation_history()

        # 使用 LLM 生成追问
        llm_service = InterviewLLMService(
            resume_info=self.context.resume_context or "无简历信息"
        )

        # 流式生成追问，收集完整内容
        full_content = ""
        token_count = 0
        try:
            async for token in llm_service.generate_followup_question_stream(
                original_question=current_question,
                user_answer=user_answer,
                followup_direction=self._get_followup_direction(deviation_score),
                conversation_history=conversation_history,
            ):
                token_count += 1
                full_content += token
                logger.debug(f"[_generate_followup_question_stream] token {token_count}: {token[:20]}...")
                yield {
                    "type": "token",
                    "data": {"content": token}
                }
            logger.info(f"[_generate_followup_question_stream] streaming complete, total_tokens={token_count}, full_content len={len(full_content)}")
        except Exception as e:
            logger.error(f"[_generate_followup_question_stream] error: {e}")
            topic = self._get_followup_topic(current_question)
            if deviation_score < 0.3:
                full_content = "让我来纠正一下这个概念..."
            elif deviation_score < 0.6:
                full_content = f"关于{topic}，能否详细说说你在项目中是如何实践的？"
            else:
                full_content = f"你提到{topic}，能具体说说遇到了什么挑战吗？"
            yield {
                "type": "token",
                "data": {"content": full_content}
            }

        # 更新追问链
        new_followup_chain = list(self.state.followup_chain)
        if current_question.question_type == QuestionType.FOLLOWUP:
            new_followup_chain.append(followup_question_id)
        else:
            if new_followup_chain:
                new_followup_chain.append(followup_question_id)
            else:
                new_followup_chain = [followup_question_id]

        # 创建 Question 对象并更新 state
        question = Question(
            content=full_content,
            question_type=QuestionType.FOLLOWUP,
            series=current_question.series,
            number=question_number,
            parent_question_id=self.state.current_question_id,
        )
        # 注意：replace 返回新对象，需要捕获新的 followup_depth
        new_followup_depth = self.state.followup_depth + 1
        self.state = replace(
            self.state,
            current_question=question,
            current_question_id=followup_question_id,
            followup_depth=new_followup_depth,
            followup_chain=new_followup_chain,
        )
        self.context.current_question_id = followup_question_id
        self.context.followup_depth = new_followup_depth
        self.context.followup_chain = new_followup_chain
        # 保存问题内容到 context 以便后续 submit_answer 使用
        self.context.question_contents[followup_question_id] = full_content
        logger.info(f"[_generate_followup_question_stream] state updated with followup question, followup_depth={new_followup_depth}")

        # 发送完成信号
        yield {
            "type": "question_end",
            "data": {"question_id": followup_question_id}
        }
        logger.info(f"[_generate_followup_question_stream] sent question_end event")


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_interview(
    session_id: str,
    resume_id: str,
    mode: str = "free",
    feedback_mode: str = "recorded",
) -> InterviewService:
    """
    创建面试服务

    Args:
        session_id: 会话ID
        resume_id: 简历ID
        mode: 面试模式 (free/training)
        feedback_mode: 反馈模式 (realtime/recorded)

    Returns:
        InterviewService 实例
    """
    interview_mode = InterviewMode.FREE if mode == "free" else InterviewMode.TRAINING
    feedback = FeedbackMode.REALTIME if feedback_mode == "realtime" else FeedbackMode.RECORDED

    return InterviewService(
        session_id=session_id,
        resume_id=resume_id,
        interview_mode=interview_mode,
        feedback_mode=feedback,
    )
