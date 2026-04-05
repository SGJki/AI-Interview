"""
Training Skill Selector Service for AI Interview Agent

专项训练-技能点选择：支持按技术栈、项目模块、自定义关键词选择训练点
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.services.resume_parser import ResumeInfo


class TrainingDimension(str, Enum):
    """训练维度枚举"""
    TECH_STACK = "tech_stack"  # 技术栈
    PROJECT_MODULE = "project_module"  # 项目模块
    CUSTOM = "custom"  # 自定义关键词


@dataclass(frozen=True)
class SkillPointSelection:
    """技能点选择结果"""
    skill_point: str  # 技能点名称
    dimension: TrainingDimension  # 选择维度
    related_projects: list[str]  # 相关的项目列表
    knowledge_available: bool  # 知识库中是否可用


class TrainingSkillSelector:
    """
    训练技能点选择器

    支持三种选择模式：
    - TECH_STACK: 按技术栈选择（如 Python、FastAPI、Redis）
    - PROJECT_MODULE: 按项目模块选择（如 电商系统、后台管理系统）
    - CUSTOM: 自定义关键词选择
    """

    def __init__(self, resume_info: ResumeInfo, knowledge_base: list[str]):
        """
        初始化技能点选择器

        Args:
            resume_info: 简历信息
            knowledge_base: 知识库列表
        """
        self.resume_info = resume_info
        self.knowledge_base = knowledge_base

    def select_skill_point(
        self, dimension: TrainingDimension, value: str
    ) -> SkillPointSelection:
        """
        选择技能点

        Args:
            dimension: 选择维度
            value: 技能点值（技术栈名称/项目模块名称/自定义关键词）

        Returns:
            技能点选择结果
        """
        if dimension == TrainingDimension.TECH_STACK:
            return self._select_tech_stack(value)
        elif dimension == TrainingDimension.PROJECT_MODULE:
            return self._select_project_module(value)
        elif dimension == TrainingDimension.CUSTOM:
            return self._select_custom(value)
        else:
            return SkillPointSelection(
                skill_point=value,
                dimension=dimension,
                related_projects=[],
                knowledge_available=False,
            )

    def validate_skill_point(self, skill_point: str) -> bool:
        """
        验证技能点是否在知识库中存在

        支持部分匹配：如果技能点是某个知识库条目的子串，则认为存在

        Args:
            skill_point: 技能点名称

        Returns:
            是否存在
        """
        return any(
            skill_point in kb_item for kb_item in self.knowledge_base
        )

    def get_available_skill_points(self, dimension: TrainingDimension) -> list[str]:
        """
        获取可选的技能点列表

        Args:
            dimension: 选择维度

        Returns:
            可选的技能点列表
        """
        if dimension == TrainingDimension.TECH_STACK:
            return self._get_tech_stack_points()
        elif dimension == TrainingDimension.PROJECT_MODULE:
            return self._get_project_module_points()
        elif dimension == TrainingDimension.CUSTOM:
            return self._get_custom_points()
        else:
            return []

    def _select_tech_stack(self, tech: str) -> SkillPointSelection:
        """选择技术栈维度的技能点"""
        related_projects = self._find_projects_by_technology(tech)
        knowledge_available = self.validate_skill_point(tech)

        return SkillPointSelection(
            skill_point=tech,
            dimension=TrainingDimension.TECH_STACK,
            related_projects=related_projects,
            knowledge_available=knowledge_available,
        )

    def _select_project_module(self, project_name: str) -> SkillPointSelection:
        """选择项目模块维度的技能点"""
        # 检查项目是否存在
        project_exists = any(p.name == project_name for p in self.resume_info.projects)
        knowledge_available = self.validate_skill_point(project_name)

        return SkillPointSelection(
            skill_point=project_name,
            dimension=TrainingDimension.PROJECT_MODULE,
            related_projects=[project_name] if project_exists else [],
            knowledge_available=knowledge_available,
        )

    def _select_custom(self, keyword: str) -> SkillPointSelection:
        """选择自定义维度的技能点"""
        knowledge_available = self.validate_skill_point(keyword)

        return SkillPointSelection(
            skill_point=keyword,
            dimension=TrainingDimension.CUSTOM,
            related_projects=[],
            knowledge_available=knowledge_available,
        )

    def _get_tech_stack_points(self) -> list[str]:
        """获取所有可选的技术栈技能点"""
        return list(self.resume_info.skills)

    def _get_project_module_points(self) -> list[str]:
        """获取所有可选的项目模块技能点"""
        return [p.name for p in self.resume_info.projects]

    def _get_custom_points(self) -> list[str]:
        """获取所有可选的自定义技能点"""
        return list(self.knowledge_base)

    def _find_projects_by_technology(self, technology: str) -> list[str]:
        """
        查找使用特定技术的项目

        Args:
            technology: 技术名称

        Returns:
            使用该技术的项目名称列表
        """
        project_names = []
        for project in self.resume_info.projects:
            if technology in project.technologies:
                project_names.append(project.name)
        return project_names
