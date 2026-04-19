"""
LLM Service for AI Interview Agent

提供面试相关任务的 LLM 服务：问题生成、回答评估、反馈生成、追问生成
"""

import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

from src.llm.client import invoke_llm, invoke_llm_stream
from src.llm.prompts import (
    QUESTION_GENERATION_PROMPT,
    ANSWER_EVALUATION_PROMPT,
    FEEDBACK_GENERATION_PROMPT,
    FOLLOWUP_QUESTION_PROMPT,
    INTERVIEW_SYSTEM_PROMPT,
    RESUME_EXTRACTION_PROMPT,
)
from src.services.embedding_service import compute_similarity, compute_similarities
from src.domain.enums import FeedbackType, QuestionType
from src.domain.models import Question, Feedback

# Scoring constants
LLM_SCORE_WEIGHT = 0.7
EMBEDDING_SCORE_WEIGHT = 0.3
CORRECTNESS_THRESHOLD = 0.6


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
        enterprise_docs: Optional[list[dict]] = None,
    ) -> dict:
        """
        评估用户回答

        Args:
            question: 问题内容
            user_answer: 用户回答
            standard_answer: 标准回答（可选）
            enterprise_docs: 企业知识库文档列表（可选）

        Returns:
            评估结果字典，包含 deviation_score, is_correct, key_points, suggestions
        """
        # 根据是否有企业文档选择不同的提示词构建方式
        if enterprise_docs:
            # 计算与最相关企业文档的相似度
            doc_contents = [doc.get("content", "") for doc in enterprise_docs]
            similarities = await compute_similarities(user_answer, doc_contents)
            best_similarity = similarities[0][1] if similarities else 0.0

            prompt = self._build_evaluation_prompt_with_similarity(
                question=question,
                user_answer=user_answer,
                enterprise_docs=enterprise_docs,
                similarity_score=best_similarity,
            )
        else:
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

            # 综合分数：LLM 判断 + 相似度
            if enterprise_docs:
                # 有企业文档时，使用 LLM 判断 70% + 相似度 30%
                embedding_score = best_similarity
                llm_deviation = result.get("deviation_score", 0.5)
                final_score = llm_deviation * LLM_SCORE_WEIGHT + embedding_score * EMBEDDING_SCORE_WEIGHT
                result["deviation_score"] = final_score
                result["is_correct"] = final_score >= CORRECTNESS_THRESHOLD
            elif standard_answer:
                # 有标准答案时，计算与标准答案的相似度
                similarity = await compute_similarity(user_answer, standard_answer)
                embedding_score = similarity
                llm_deviation = result.get("deviation_score", 0.5)
                final_score = llm_deviation * LLM_SCORE_WEIGHT + embedding_score * EMBEDDING_SCORE_WEIGHT
                result["deviation_score"] = final_score
                result["is_correct"] = final_score >= CORRECTNESS_THRESHOLD

            return result

        except json.JSONDecodeError:
            # JSON 解析失败，使用 embedding 相似度
            if enterprise_docs:
                return {
                    "deviation_score": best_similarity,
                    "is_correct": best_similarity >= CORRECTNESS_THRESHOLD,
                    "key_points": ["评估服务暂时无法分析，请参考相似度分数"],
                    "suggestions": ["建议进一步完善回答"],
                }
            elif standard_answer:
                similarity = await compute_similarity(user_answer, standard_answer)
                return {
                    "deviation_score": similarity,
                    "is_correct": similarity >= CORRECTNESS_THRESHOLD,
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

    def _build_evaluation_prompt_with_similarity(
        self,
        question: str,
        user_answer: str,
        enterprise_docs: list[dict],
        similarity_score: float,
    ) -> str:
        """构建含相似度分数和企业知识的评估提示词"""
        prompt = f"""Role: AI面试评估专家
## Profile
language: 中文
description: 我是一名专业的AI面试评估专家，专注于客观、准确地评估技术岗位候选人的回答。我基于预定的评估维度，将候选人回答与标准答案进行对比，并提供结构化、建设性的反馈，旨在帮助面试官高效决策，并为候选人提供成长建议。
background: 我源自知名科技公司的面试官团队，积累了丰富的技术面试与人才评估经验。
personality: 专业、严谨、客观、富有洞察力、具备同理心和帮助精神。
expertise: 人工智能、软件开发、系统设计、行为面试、结构化评估。
target_audience: HR招聘专员、技术面试官、希望提升面试表现的求职者。
## Skills
### 核心评估技能

技术准确性评估: 快速识别回答中的技术概念、术语、方法论是否正确。
深度理解分析: 判断候选人是对知识点死记硬背，还是能触类旁通、阐释原理与权衡。
实践经验鉴别: 从回答中提取具体案例、量化结果，区分真实项目经验与泛泛而谈。
表达逻辑解构: 分析回答的条理性、层次感，以及论点与论据之间的支撑关系。
量化评分能力: 将多维度的定性评估转化为精确的数值分数和判断。
### 辅助沟通技能

反馈信息结构化: 将评估结果组织成清晰的要点、优点和改进建议。
建设性沟通: 以鼓励和改进为导向，而非单纯的批判，提供可操作的提升路径。
多源信息整合: 能同时处理问题、候选人回答、标准答案等多重输入，进行综合判断。
流程标准化执行: 严格遵循预设的工作流程与输出格式，确保评估的一致性与可重复性。
## Rules
### 基本原则：

客观中立: 评估必须基于提供的内容和既定维度，避免个人主观偏见或先入为主的印象。
聚焦问题: 评估严格围绕"候选人的回答"与"标准答案"的对比展开，不臆测候选人未提及的信息。
维度驱动: 所有分析和结论必须明确对应到"技术准确性"、"深度理解"、"实践经验"、"表达清晰度"四个维度。
证据说话: 指出优点或问题时，必须引用回答中的具体词句作为依据。
### 行为准则：

提供建设性反馈: "suggestions"应具体、可行，指向如何改进答案，而非空洞批评。
平衡评估视角: 在指出问题的同时，也应识别并肯定回答中的亮点（若有）。
尊重候选人的努力: 评估语言应专业、礼貌，即使对错误答案也应保持尊重。
优先使用标准答案: 当提供标准答案时，以其为主要参照基准；若无，则基于行业共识和最佳实践进行评估。
### 限制条件：

不超出评估范围: 不评估与给定问题和四个维度无关的内容，如候选人的语法细微错误（除非严重影响理解）。
不进行绝对判断: 避免使用"极其糟糕"、"完美无缺"等极端词汇，评估应是相对和描述性的。
不创造信息: 当候选人回答模糊或缺失信息时，按"未提及"处理，不替候选人补充或美化。
严守输出格式: 必须且只能以指定的JSON格式输出，不得添加任何额外的解释、评论或格式化标记（如json）。
## Workflows
目标: 对候选人的回答进行全面、公正的评估，并生成结构化反馈报告。
步骤 1: 信息接收与解析 – 清晰理解question（面试问题）、user_answer（候选人回答）及可选的standard_answer（标准答案）的内容。
步骤 2: 多维度对比分析 – 严格依据四个评估维度，逐条分析候选人回答。与标准答案（若有）进行比对，或基于专业知识判断其有效性、深度和清晰度。
步骤 3: 综合评分与判断 – 基于分析，计算deviation_score（综合偏离度/优秀度，0.0-1.0），并做出is_correct的基本正确性判断。提炼关键的优点与问题点形成key_points，并构思具体的improvement_suggestions。
步骤 4: 格式化输出 – 严格按照OutputFormat的要求，将评估结果封装成纯净的JSON对象输出。
预期结果: 一份客观、量化、具有行动指导意义的JSON格式评估报告，帮助用户快速把握候选人回答的质量与改进方向。
## OutputFormat
### 输出格式类型：

format: json (纯JSON文本)
structure: 必须包含且仅包含以下四个顶级键：deviation_score, is_correct, key_points, suggestions。值类型分别为数字、布尔值、字符串数组、字符串数组。
style: 专业、简洁、无冗余。键名使用蛇形命名法（snake_case）。
special_requirements: 输出必须是可直接被程序解析的有效JSON字符串，不包含任何额外的文本、标记或说明。
### 格式规范：

indentation: 为提升人类可读性，生成时建议使用2个空格进行缩进。
sections: JSON对象本身即为一个完整的整体，不额外分节。
highlighting: 不应用任何格式高亮，输出为纯文本。
### 验证规则：

validation: 输出的JSON必须能通过标准JSON解析器的校验。
constraints: deviation_score必须是0到1之间（含）的浮点数；key_points和suggestions数组中的每个元素应为非空字符串。
error_handling: 若输入信息严重缺失（如缺少面试问题或用户回答），则在JSON中通过suggestions字段说明输入不完整，而非抛出非JSON错误。
### 示例说明：

示例1：优秀回答

标题: 深度理解且表达清晰的回答
格式类型: JSON
说明: 候选人回答高度符合标准，展现了深入的理解。
示例内容: | {{ "deviation_score": 0.95, "is_correct": true, "key_points": ["准确阐述了RESTful API的核心原则（如无状态性、资源导向）", "对比了REST与GraphQL的适用场景，体现了深度思考", "用'项目X中通过清晰URI设计降低了客户端耦合'佐证了实践经验"], "suggestions": ["可以考虑补充说明HATEOAS（超媒体作为应用状态引擎）概念，以展现更完整的知识体系。"] }}
示例2：存在偏差的回答

标题: 技术概念存在混淆的回答
格式类型: JSON
说明: 候选人回答部分正确，但在关键概念上存在偏差。
示例内容: | {{ "deviation_score": 0.6, "is_correct": false, "key_points": ["正确提到了索引可以加快查询速度", "混淆了'聚簇索引'和'非聚簇索引'的关键区别（如物理存储顺序）", "未提及不当使用索引可能带来的写性能开销"], "suggestions": ["建议深入理解聚簇索引与非聚簇索引在数据物理组织方式上的根本不同。", "在讨论优化时，可补充说明索引的维护成本，以体现权衡思维。"] }}
## Initialization
作为AI面试评估专家，你必须遵守上述Rules，按照Workflows执行任务，并按照OutputFormat输出。现在，请开始评估以下面试回答：

问题
question: {question}

候选人的回答
user_answer: {user_answer}

回答与参考答案的相似度
{similarity_score:.2%}

企业最佳实践参考答案
"""
        for i, doc in enumerate(enterprise_docs, 1):
            prompt += f"\n{i}. {doc.get('content', '')}\n"

        prompt += """
请结合相似度分数和参考答案，从以下几个方面评估：
1. 回答的正确性
2. 回答的完整性
3. 与企业最佳实践的差距
"""
        return prompt

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

            parsed = json.loads(result)

            # Validate structure
            if not isinstance(parsed, dict):
                logger.warning("LLM returned non-dict: %s", type(parsed))
                return {"skills": [], "projects": [], "experience": []}

            return {
                "skills": parsed.get("skills", []),
                "projects": parsed.get("projects", []),
                "experience": parsed.get("experience", []),
            }
        except json.JSONDecodeError as e:
            logger.error("JSON decode error in extract_resume_info: %s", e)
            return {"skills": [], "projects": [], "experience": []}
        except Exception as e:
            logger.error("Error in extract_resume_info: %s", e)
            return {"skills": [], "projects": [], "experience": []}
