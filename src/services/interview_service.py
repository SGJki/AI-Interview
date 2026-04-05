"""
Interview Service for AI Interview Agent

面试服务：整合 Agent、工具和状态管理
"""

from typing import Optional
from dataclasses import dataclass, replace

from src.agent.state import (
    InterviewState,
    InterviewContext,
    InterviewMode,
    FeedbackMode,
    FeedbackType,
    FollowupStrategy,
    Question,
    QuestionType,
    Answer,
    Feedback,
    SeriesRecord,
    FinalFeedback,
)
from src.agent.graph import (
    interview_graph_with_checkpointer,
    generate_question,
    evaluate_answer,
    generate_feedback,
)
from src.tools.memory_tools import (
    save_to_session_memory,
    get_session_memory,
    clear_session_memory,
    cache_next_series_question,
    get_cached_next_question,
)
from src.tools.rag_tools import (
    retrieve_knowledge,
    retrieve_standard_answer,
    retrieve_by_skill_point,
)


# =============================================================================
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

        # 保存到 Redis
        await save_to_session_memory(self.session_id, self.context)

        # 生成第一个问题
        question = await self._generate_next_question()

        return question

    async def submit_answer(self, user_answer: str, question_id: str) -> QAResponse:
        """
        提交回答

        Args:
            user_answer: 用户回答
            question_id: 问题ID

        Returns:
            问答响应
        """
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
            feedback = await self._generate_feedback(question_id, user_answer, deviation_score)
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

        # 更新 context
        self.context.answers.append({
            "question_id": question_id,
            "answer": user_answer,
            "deviation": deviation_score,
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

        # 检查是否需要切换到下一个系列
        if self._is_series_complete():
            await self._switch_to_next_series()

        # 判断是否继续
        should_continue = self._should_continue()
        next_question = None

        if should_continue:
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

        # TODO: 写入 PostgreSQL

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
        """加载知识库"""
        # TODO: 从 RAG 加载知识库到 context
        pass

    async def _generate_next_question(self) -> Question:
        """
        生成下一个问题

        Returns:
            下一个问题
        """
        # 检查是否有预生成的问题
        cached_q = await get_cached_next_question(
            self.session_id,
            self.state.current_series
        )

        if cached_q:
            # 使用预生成的问题
            question = Question(
                content=cached_q,
                question_type=QuestionType.INITIAL,
                series=self.state.current_series,
                number=len(self.state.answers) + 1,
            )
        else:
            # 动态生成
            # TODO: 使用 LLM 生成问题
            question = Question(
                content=f"[模拟问题 {self.state.current_series}-{len(self.state.answers) + 1}] 请介绍你的项目经验",
                question_type=QuestionType.INITIAL,
                series=self.state.current_series,
                number=len(self.state.answers) + 1,
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
            # TODO: 检查知识库是否有相关内容
            pass

        return question

    async def _evaluate_answer(
        self,
        question_id: str,
        user_answer: str
    ) -> dict:
        """
        评估回答

        Returns:
            评估结果字典
        """
        # TODO: 使用 embedding 计算相似度
        # TODO: 使用 LLM 判断回答质量

        # 模拟评估
        deviation_score = 0.8  # 默认 80% 相似度
        is_correct = deviation_score >= 0.6

        return {
            "deviation_score": deviation_score,
            "is_correct": is_correct,
        }

    async def _generate_feedback(
        self,
        question_id: str,
        user_answer: str,
        deviation_score: float
    ) -> Feedback:
        """
        生成反馈

        根据 deviation_score 生成不同类型的实时反馈:
        - deviation_score < 0.3: CORRECTION (直接给出正确答案)
        - deviation_score < 0.6: GUIDANCE (提示性追问)
        - deviation_score >= 0.6: COMMENT (正面点评)

        Returns:
            反馈内容
        """
        is_correct = deviation_score >= 0.6
        feedback_content = ""
        guidance = None
        feedback_type = FeedbackType.COMMENT

        if deviation_score < 0.3:
            # CORRECTION: 偏离方向，直接给出正确答案
            feedback_type = FeedbackType.CORRECTION
            feedback_content = "回答偏离了主要方向。标准答案是..."
            guidance = "请注意理解题目的核心要求，从头梳理思路。"
        elif deviation_score < 0.6:
            # GUIDANCE: 部分正确，提示性追问引导
            feedback_type = FeedbackType.GUIDANCE
            feedback_content = "你提到的方向有一定道理，能否进一步说明..."
            guidance = "请尝试从另一个角度思考这个问题？"
        else:
            # COMMENT: 基本正确，正面点评
            feedback_type = FeedbackType.COMMENT
            feedback_content = "很好，你的理解基本正确，继续深入。"

        return Feedback(
            question_id=question_id,
            content=feedback_content,
            is_correct=is_correct,
            guidance=guidance,
            feedback_type=feedback_type,
        )

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

    async def _switch_to_next_series(self) -> None:
        """
        切换到下一个系列

        记录当前系列到历史记录，重置错误计数
        """
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

        # TODO: 调用 LLM 生成问题
        # 目前使用模拟实现
        generated_question = f"[预生成问题 系列{next_series}-1] 关于{self._get_next_topic()}"

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
            # 返回一个空的 Question 占位（实际不会使用）
            return Question(
                content="",
                question_type=QuestionType.FOLLOWUP,
                series=current_question.series,
                number=current_question.number + 1,
                parent_question_id=None,
            )

        # 获取追问主题
        topic = self._get_followup_topic(current_question)

        # 生成追问内容（基于偏差程度和主题）
        if deviation_score < 0.3:
            # 极低偏差：直接纠错，不生成追问内容
            followup_content = f"让我来纠正一下这个概念..."
        elif deviation_score < 0.6:
            # 中等偏差：生成提示性追问
            followup_num = self.state.followup_depth + 1
            followup_content = f"关于{topic}，能否详细说说你在项目中是如何实践的？"
        else:
            # 高偏差：深入追问
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
        self.state = replace(
            self.state,
            followup_depth=self.state.followup_depth + 1,
            followup_chain=new_followup_chain,
        )

        # 更新 context
        if self.context:
            self.context.followup_depth = self.state.followup_depth
            self.context.followup_chain = new_followup_chain

        return Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=current_question.series,
            number=current_question.number + self.state.followup_depth,
            parent_question_id=current_question.question_type,
        )


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
