"""
LLM Service for AI Interview Agent

提供面试相关任务的 LLM 服务：问题生成、回答评估、反馈生成、追问生成
"""

import json
from typing import Optional

from src.llm.client import invoke_llm, invoke_llm_stream
from src.llm.prompts import (
    QUESTION_GENERATION_PROMPT,
    ANSWER_EVALUATION_PROMPT,
    FEEDBACK_GENERATION_PROMPT,
    FOLLOWUP_QUESTION_PROMPT,
    INTERVIEW_SYSTEM_PROMPT,
    RESUME_EXTRACTION_PROMPT,
)
from src.services.embedding_service import compute_similarity
from src.agent.state import Feedback, FeedbackType, Question, QuestionType


class InterviewLLMService:
    """
    面试 LLM 服务

    封装所有面试相关的 LLM 调用
    """

    def __init__(self, resume_info: str = ""):
        """
        初始化面试 LLM 服务

        Args:
            resume_info: 候选人简历信息
        """
        self.resume_info = resume_info or "无简历信息"
        self.conversation_history: list[dict] = []

    async def generate_question(
        self,
        series_num: int = 1,
        question_num: int = 1,
        interview_mode: str = "free",
        topic_area: str = "技术能力",
        knowledge_context: str = "",
        responsibility_context: str = "",
    ) -> Question:
        """
        生成面试问题

        Args:
            series_num: 系列编号
            question_num: 问题序号
            interview_mode: 面试模式 (free/training)
            topic_area: 主题领域
            knowledge_context: 知识库上下文
            responsibility_context: 当前职责上下文（针对性提问用）

        Returns:
            生成的 Question 对象
        """
        prompt = QUESTION_GENERATION_PROMPT.format(
            resume_info=self.resume_info,
            series_num=series_num,
            question_num=question_num,
            interview_mode=interview_mode,
            topic_area=topic_area,
            knowledge_context=knowledge_context or "无相关上下文",
            responsibility_context=responsibility_context or "",
        )

        try:
            question_content = await invoke_llm(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.7,
                include_reasoning=True,  # 返回思考过程便于调试
            )
            question_content = question_content.strip()

            # 确保问题不为空
            if not question_content:
                question_content = f"请介绍一下你最近做的项目，以及在其中承担的角色？"

        except Exception as e:
            # LLM 调用失败时使用回退
            question_content = f"请介绍一下你最近做的项目，以及在其中承担的角色？"

        return Question(
            content=question_content,
            question_type=QuestionType.INITIAL,
            series=series_num,
            number=question_num,
            parent_question_id=None,
        )

    async def generate_question_stream(
        self,
        series_num: int = 1,
        question_num: int = 1,
        interview_mode: str = "free",
        topic_area: str = "技术能力",
        knowledge_context: str = "",
        responsibility_context: str = "",
    ):
        """
        生成面试问题（流式）

        Args:
            series_num: 系列编号
            question_num: 问题序号
            interview_mode: 面试模式 (free/training)
            topic_area: 主题领域
            knowledge_context: 知识库上下文
            responsibility_context: 当前职责上下文（针对性提问用）

        Yields:
            问题的每个 token
        """
        prompt = QUESTION_GENERATION_PROMPT.format(
            resume_info=self.resume_info,
            series_num=series_num,
            question_num=question_num,
            interview_mode=interview_mode,
            topic_area=topic_area,
            knowledge_context=knowledge_context or "无相关上下文",
            responsibility_context=responsibility_context or "",
        )

        try:
            async for token in invoke_llm_stream(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.7,
            ):
                yield token
        except Exception:
            yield "请介绍一下你最近做的项目，以及在其中承担的角色？"

    async def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        standard_answer: Optional[str] = None,
    ) -> dict:
        """
        评估用户回答

        Args:
            question: 问题内容
            user_answer: 用户回答
            standard_answer: 标准回答（可选）

        Returns:
            评估结果字典，包含 deviation_score, is_correct, key_points, suggestions
        """
        prompt = ANSWER_EVALUATION_PROMPT.format(
            question=question,
            user_answer=user_answer,
            standard_answer=standard_answer or "无标准回答",
        )

        try:
            result_text = await invoke_llm(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.3,  # 低温度保证一致性
            )

            # 解析 JSON 结果
            result = json.loads(result_text)

            # 同时计算 embedding 相似度作为参考
            if standard_answer:
                similarity = await compute_similarity(user_answer, standard_answer)
                # 综合分数：LLM 判断 70% + 相似度 30%
                embedding_score = similarity
                final_score = result.get("deviation_score", embedding_score) * 0.7 + embedding_score * 0.3
                result["deviation_score"] = final_score
                result["is_correct"] = final_score >= 0.6

            return result

        except json.JSONDecodeError:
            # JSON 解析失败，使用 embedding 相似度
            if standard_answer:
                similarity = await compute_similarity(user_answer, standard_answer)
                return {
                    "deviation_score": similarity,
                    "is_correct": similarity >= 0.6,
                    "key_points": ["评估服务暂时无法分析，请参考相似度分数"],
                    "suggestions": ["建议进一步完善回答"],
                }
            else:
                # 无标准回答时，使用简单规则
                return {
                    "deviation_score": 0.5,
                    "is_correct": True,
                    "key_points": ["暂时无法评估"],
                    "suggestions": ["请详细描述你的经验"],
                }
        except Exception as e:
            # 其他错误
            return {
                "deviation_score": 0.5,
                "is_correct": True,
                "key_points": [f"评估出错: {str(e)}"],
                "suggestions": ["请详细描述你的经验"],
            }

    async def generate_feedback(
        self,
        question: str,
        user_answer: str,
        deviation_score: float,
        is_correct: bool,
    ) -> Feedback:
        """
        生成反馈

        Args:
            question: 问题内容
            user_answer: 用户回答
            deviation_score: 偏差分数
            is_correct: 是否正确

        Returns:
            生成的 Feedback 对象
        """
        prompt = FEEDBACK_GENERATION_PROMPT.format(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
        )

        try:
            feedback_content = await invoke_llm(
                system_prompt="你是一个友善的AI面试官，给出建设性的反馈。",
                user_prompt=prompt,
                temperature=0.7,
                include_reasoning=True,  # 返回思考过程便于调试
            )
            feedback_content = feedback_content.strip()

        except Exception:
            # LLM 调用失败时使用回退
            if deviation_score < 0.3:
                feedback_content = "回答有一定偏差，建议从技术原理角度重新理解这个问题。"
            elif deviation_score < 0.6:
                feedback_content = "回答方向正确，但可以更深入一些，能否举一个具体的例子？"
            else:
                feedback_content = "回答得很好！继续深入。"

        # 确定反馈类型
        if deviation_score < 0.3:
            feedback_type = FeedbackType.CORRECTION
            guidance = "建议回顾相关技术原理，结合项目经验深入理解。"
        elif deviation_score < 0.6:
            feedback_type = FeedbackType.GUIDANCE
            guidance = "请尝试从项目实践角度更详细地说明。"
        else:
            feedback_type = FeedbackType.COMMENT
            guidance = None

        return Feedback(
            question_id="",
            content=feedback_content,
            is_correct=is_correct,
            guidance=guidance,
            feedback_type=feedback_type,
        )

    async def generate_followup_question(
        self,
        original_question: Question,
        user_answer: str,
        followup_direction: str = "",
        conversation_history: str = "",
    ) -> Question:
        """
        生成追问

        Args:
            original_question: 原始问题
            user_answer: 用户回答
            followup_direction: 追问方向提示
            conversation_history: 对话历史上下文

        Returns:
            生成的追问
        """
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            original_question=original_question.content,
            user_answer=user_answer,
            followup_direction=followup_direction or "深入技术细节和实践经验",
            conversation_history=conversation_history or "无历史对话",
        )

        try:
            followup_content = await invoke_llm(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.7,
                include_reasoning=True,  # 返回思考过程便于调试
            )
            followup_content = followup_content.strip()

            if not followup_content:
                followup_content = "能否详细说说在这个项目中遇到的具体挑战？"

        except Exception:
            followup_content = "能否详细说说在这个项目中遇到的具体挑战？"

        return Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=original_question.series,
            number=original_question.number + 1,
            parent_question_id=original_question.question_id if hasattr(original_question, 'question_id') else None,
        )

    async def generate_followup_question_stream(
        self,
        original_question: Question,
        user_answer: str,
        followup_direction: str = "",
        conversation_history: str = "",
    ):
        """
        生成追问（流式）

        Args:
            original_question: 原始问题
            user_answer: 用户回答
            followup_direction: 追问方向提示
            conversation_history: 对话历史上下文

        Yields:
            追问的每个 token
        """
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            original_question=original_question.content,
            user_answer=user_answer,
            followup_direction=followup_direction or "深入技术细节和实践经验",
            conversation_history=conversation_history or "无历史对话",
        )

        try:
            async for token in invoke_llm_stream(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.7,
            ):
                yield token
        except Exception:
            yield "能否详细说说在这个项目中遇到的具体挑战？"

    def add_to_history(self, role: str, content: str):
        """
        添加对话历史

        Args:
            role: 角色 (user/assistant/system)
            content: 内容
        """
        self.conversation_history.append({"role": role, "content": content})

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    async def extract_resume_info(self, resume_content: str) -> dict:
        """
        提取简历信息

        Args:
            resume_content: 简历文本

        Returns:
            解析后的简历结构: {skills: [], projects: [], experience: []}
        """
        prompt = RESUME_EXTRACTION_PROMPT.format(
            resume_content=resume_content,
        )

        try:
            result = await invoke_llm(
                system_prompt="你是一个专业的简历解析专家。",
                user_prompt=prompt,
                temperature=0.3,
            )

            return json.loads(result)
        except json.JSONDecodeError:
            return {"skills": [], "projects": [], "experience": []}
        except Exception:
            return {"skills": [], "projects": [], "experience": []}
