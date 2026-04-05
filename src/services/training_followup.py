"""
Training Followup Expander Service for AI Interview Agent - Phase 4

专项训练-展开追问逻辑：根据技能点展开递进式追问

功能：
- 递进式追问生成
- 追问层级 (Level 1-4)
- 追问模板管理
- 追问流程控制
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

from src.agent.state import Question, QuestionType
from src.services.training_knowledge_matcher import (
    KnowledgeMatchResult,
    TrainingKnowledgeMatcher,
)
from src.services.training_selector import SkillPointSelection, TrainingDimension


# =============================================================================
# Enums
# =============================================================================


class FollowupLevel(IntEnum):
    """
    追问层级

    Attributes:
        LEVEL_1: 基础概念 - 考察基本定义和概念理解
        LEVEL_2: 实现细节 - 考察具体实现和方法
        LEVEL_3: 深度理解 - 考察原理分析和为什么
        LEVEL_4: 扩展应用 - 考察实际应用和场景
    """
    LEVEL_1 = 1  # 基础概念
    LEVEL_2 = 2  # 实现细节
    LEVEL_3 = 3  # 深度理解
    LEVEL_4 = 4  # 扩展应用


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class FollowupTemplate:
    """
    追问模板

    Attributes:
        level: 追问层级
        question_template: 问题模板，支持 {skill_point} 占位符
        scoring_criteria: 评分标准
        expected_keywords: 期望的关键词列表
        depth_bonus: 深度奖励分数
    """
    level: FollowupLevel
    question_template: str
    scoring_criteria: str
    expected_keywords: list[str]
    depth_bonus: float


# =============================================================================
# Template Definitions
# =============================================================================


# Level 1 模板：基础概念
LEVEL_1_TEMPLATES = {
    "default": FollowupTemplate(
        level=FollowupLevel.LEVEL_1,
        question_template="请解释一下 {skill_point} 的基本概念",
        scoring_criteria="是否准确描述 {skill_point} 的基本定义和核心特点",
        expected_keywords=["定义", "概念", "特点", "是什么"],
        depth_bonus=0.1,
    ),
}

# Level 2 模板：实现细节
LEVEL_2_TEMPLATES = {
    "default": FollowupTemplate(
        level=FollowupLevel.LEVEL_2,
        question_template="{skill_point} 在项目中是如何实现的？",
        scoring_criteria="是否清楚描述 {skill_point} 的实现方式和关键步骤",
        expected_keywords=["如何", "实现", "步骤", "方法"],
        depth_bonus=0.2,
    ),
}

# Level 3 模板：深度理解
LEVEL_3_TEMPLATES = {
    "default": FollowupTemplate(
        level=FollowupLevel.LEVEL_3,
        question_template="为什么选择 {skill_point}？它的原理是什么？",
        scoring_criteria="是否理解 {skill_point} 的底层原理和设计原因",
        expected_keywords=["为什么", "原理", "原因", "底层"],
        depth_bonus=0.3,
    ),
}

# Level 4 模板：扩展应用
LEVEL_4_TEMPLATES = {
    "default": FollowupTemplate(
        level=FollowupLevel.LEVEL_4,
        question_template="{skill_point} 在实际工作中有哪些应用场景？",
        scoring_criteria="是否能举出 {skill_point} 的实际应用案例和扩展场景",
        expected_keywords=["应用", "场景", "案例", "实践"],
        depth_bonus=0.4,
    ),
}


# =============================================================================
# Training Followup Expander
# =============================================================================


class TrainingFollowupExpander:
    """
    训练追问扩展器

    根据技能点知识生成递进式追问，支持多层级递进

    Attributes:
        knowledge_matcher: 知识匹配器实例
        max_followup_depth: 最大追问深度，默认为 3
    """

    def __init__(
        self,
        knowledge_matcher: TrainingKnowledgeMatcher,
        max_followup_depth: int = 3,
    ):
        """
        初始化追问扩展器

        Args:
            knowledge_matcher: 知识匹配器实例
            max_followup_depth: 最大追问深度，默认为 3
        """
        self.knowledge_matcher = knowledge_matcher
        self.max_followup_depth = max_followup_depth

    def generate_followup(
        self,
        skill_point: str,
        current_depth: int,
        previous_answer: str,
    ) -> Question:
        """
        生成递进式追问

        Args:
            skill_point: 技能点名称
            current_depth: 当前追问深度
            previous_answer: 用户之前的回答

        Returns:
            生成的追问问题

        Raises:
            ValueError: 当面试状态未初始化时
        """
        # 达到最大深度时返回空问题
        if current_depth >= self.max_followup_depth:
            return Question(
                content="",
                question_type=QuestionType.FOLLOWUP,
                series=1,
                number=current_depth + 1,
            )

        # 负深度当作 0 处理
        if current_depth < 0:
            current_depth = 0

        # 获取对应的追问层级
        level = self._depth_to_level(current_depth)

        # 获取追问模板
        template = self.get_followup_template(skill_point, level)

        # 生成追问内容
        followup_content = self._generate_followup_content(
            skill_point=skill_point,
            template=template,
            previous_answer=previous_answer,
        )

        return Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=1,
            number=current_depth + 1,
        )

    def get_followup_template(
        self,
        skill_point: str,
        level: FollowupLevel,
    ) -> FollowupTemplate:
        """
        获取追问模板

        Args:
            skill_point: 技能点名称
            level: 追问层级

        Returns:
            追问模板
        """
        # 根据层级选择模板字典
        if level == FollowupLevel.LEVEL_1:
            template_dict = LEVEL_1_TEMPLATES
        elif level == FollowupLevel.LEVEL_2:
            template_dict = LEVEL_2_TEMPLATES
        elif level == FollowupLevel.LEVEL_3:
            template_dict = LEVEL_3_TEMPLATES
        elif level == FollowupLevel.LEVEL_4:
            template_dict = LEVEL_4_TEMPLATES
        else:
            # 默认使用 Level 1 模板
            template_dict = LEVEL_1_TEMPLATES

        # 获取模板（目前使用 default）
        template = template_dict.get("default", LEVEL_1_TEMPLATES["default"])

        # 替换技能点占位符
        question_with_skill = template.question_template.format(skill_point=skill_point)
        criteria_with_skill = template.scoring_criteria.format(skill_point=skill_point)

        return FollowupTemplate(
            level=template.level,
            question_template=question_with_skill,
            scoring_criteria=criteria_with_skill,
            expected_keywords=template.expected_keywords,
            depth_bonus=template.depth_bonus,
        )

    def _depth_to_level(self, depth: int) -> FollowupLevel:
        """
        将深度转换为层级

        Args:
            depth: 追问深度

        Returns:
            对应的追问层级
        """
        if depth < 0:
            return FollowupLevel.LEVEL_1
        elif depth == 0:
            return FollowupLevel.LEVEL_1
        elif depth == 1:
            return FollowupLevel.LEVEL_2
        elif depth == 2:
            return FollowupLevel.LEVEL_3
        else:
            return FollowupLevel.LEVEL_4

    async def _get_knowledge_result(
        self,
        skill_point: str,
    ) -> Optional[KnowledgeMatchResult]:
        """
        获取知识匹配结果

        Args:
            skill_point: 技能点名称

        Returns:
            知识匹配结果
        """
        try:
            selection = SkillPointSelection(
                skill_point=skill_point,
                dimension=TrainingDimension.TECH_STACK,
                related_projects=[],
                knowledge_available=True,
            )
            result = await self.knowledge_matcher.match_knowledge(selection)
            return result
        except Exception:
            return None

    def _generate_followup_content(
        self,
        skill_point: str,
        template: FollowupTemplate,
        previous_answer: str,
    ) -> str:
        """
        生成追问内容

        Args:
            skill_point: 技能点名称
            template: 追问模板
            previous_answer: 用户之前的回答

        Returns:
            生成的追问内容
        """
        # 使用模板生成基础内容
        content = template.question_template

        return content


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FollowupLevel",
    "FollowupTemplate",
    "TrainingFollowupExpander",
]
