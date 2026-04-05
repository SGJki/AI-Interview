"""
Tests for AI Interview Agent - Training Skill Selector

专项训练-技能点选择：支持按技术栈、项目模块、自定义关键词选择训练点
"""

import pytest
from dataclasses import dataclass, field
from enum import Enum

from src.services.training_selector import (
    TrainingDimension,
    SkillPointSelection,
    TrainingSkillSelector,
)
from src.services.resume_parser import ResumeInfo, ProjectInfo


class TestTrainingDimension:
    """Test TrainingDimension enum"""

    def test_training_dimension_values(self):
        """测试 TrainingDimension 枚举值"""
        assert TrainingDimension.TECH_STACK.value == "tech_stack"
        assert TrainingDimension.PROJECT_MODULE.value == "project_module"
        assert TrainingDimension.CUSTOM.value == "custom"

    def test_training_dimension_is_string_enum(self):
        """测试 TrainingDimension 是字符串枚举"""
        assert isinstance(TrainingDimension.TECH_STACK, str)
        assert TrainingDimension.TECH_STACK == "tech_stack"


class TestSkillPointSelection:
    """Test SkillPointSelection dataclass"""

    def test_skill_point_selection_creation(self):
        """测试创建技能点选择结果"""
        selection = SkillPointSelection(
            skill_point="Python",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=["电商系统", "后台服务"],
            knowledge_available=True,
        )

        assert selection.skill_point == "Python"
        assert selection.dimension == TrainingDimension.TECH_STACK
        assert selection.related_projects == ["电商系统", "后台服务"]
        assert selection.knowledge_available is True

    def test_skill_point_selection_is_frozen(self):
        """测试 SkillPointSelection 是不可变的"""
        selection = SkillPointSelection(
            skill_point="Python",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=["电商系统"],
            knowledge_available=True,
        )

        with pytest.raises(Exception):
            selection.skill_point = "Java"


class TestTrainingSkillSelector:
    """Test TrainingSkillSelector class"""

    @pytest.fixture
    def sample_resume_info(self):
        """创建样例简历信息"""
        return ResumeInfo(
            name="张三",
            email="zhangsan@example.com",
            skills=["Python", "FastAPI", "Redis", "Docker", "MySQL"],
            skill_categories={
                "programming_languages": ["Python"],
                "frameworks": ["FastAPI"],
                "databases": ["Redis", "MySQL"],
                "tools": ["Docker"],
            },
            projects=[
                ProjectInfo(
                    name="电商系统",
                    description="基于微服务的电商平台",
                    technologies=["Python", "FastAPI", "Redis", "MySQL"],
                    role="后端开发",
                    highlights=["高并发处理", "微服务架构"],
                ),
                ProjectInfo(
                    name="后台管理系统",
                    description="企业内部管理系统",
                    technologies=["Python", "Django", "MySQL"],
                    role="全栈开发",
                    highlights=["RBAC权限管理", "前后端分离"],
                ),
            ],
        )

    @pytest.fixture
    def sample_knowledge_base(self):
        """创建样例知识库"""
        return [
            "Python 编程基础",
            "FastAPI Web 框架",
            "Redis 缓存实战",
            "MySQL 数据库设计",
            "Docker 容器化",
            "微服务架构设计",
            "电商系统架构",
            "RESTful API 设计",
        ]

    @pytest.fixture
    def selector(self, sample_resume_info, sample_knowledge_base):
        """创建技能选择器实例"""
        return TrainingSkillSelector(sample_resume_info, sample_knowledge_base)

    def test_selector_initialization(self, sample_resume_info, sample_knowledge_base):
        """测试选择器初始化"""
        selector = TrainingSkillSelector(sample_resume_info, sample_knowledge_base)

        assert selector.resume_info == sample_resume_info
        assert selector.knowledge_base == sample_knowledge_base

    def test_get_available_skill_points_tech_stack(self, selector):
        """测试获取技术栈可选技能点"""
        skill_points = selector.get_available_skill_points(TrainingDimension.TECH_STACK)

        assert "Python" in skill_points
        assert "FastAPI" in skill_points
        assert "Redis" in skill_points
        assert "MySQL" in skill_points
        assert "Docker" in skill_points

    def test_get_available_skill_points_project_module(self, selector):
        """测试获取项目模块可选技能点"""
        skill_points = selector.get_available_skill_points(TrainingDimension.PROJECT_MODULE)

        assert "电商系统" in skill_points
        assert "后台管理系统" in skill_points

    def test_get_available_skill_points_custom(self, selector):
        """测试获取自定义可选技能点"""
        skill_points = selector.get_available_skill_points(TrainingDimension.CUSTOM)

        # 自定义模式应返回知识库中的所有内容
        assert len(skill_points) > 0

    def test_validate_skill_point_exists_in_knowledge(self, selector):
        """测试验证技能点存在于知识库"""
        assert selector.validate_skill_point("Python") is True
        assert selector.validate_skill_point("FastAPI") is True
        assert selector.validate_skill_point("Redis") is True

    def test_validate_skill_point_not_in_knowledge(self, selector):
        """测试验证技能点不存在于知识库"""
        assert selector.validate_skill_point("Rust") is False
        assert selector.validate_skill_point("Kubernetes") is False

    def test_select_skill_point_tech_stack(self, selector):
        """测试选择技术栈维度的技能点"""
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Python")

        assert selection.skill_point == "Python"
        assert selection.dimension == TrainingDimension.TECH_STACK
        assert "电商系统" in selection.related_projects
        assert selection.knowledge_available is True

    def test_select_skill_point_project_module(self, selector):
        """测试选择项目模块维度的技能点"""
        selection = selector.select_skill_point(TrainingDimension.PROJECT_MODULE, "电商系统")

        assert selection.skill_point == "电商系统"
        assert selection.dimension == TrainingDimension.PROJECT_MODULE
        assert selection.related_projects == ["电商系统"]
        assert selection.knowledge_available is True

    def test_select_skill_point_custom(self, selector):
        """测试选择自定义维度的技能点"""
        selection = selector.select_skill_point(TrainingDimension.CUSTOM, "微服务架构设计")

        assert selection.skill_point == "微服务架构设计"
        assert selection.dimension == TrainingDimension.CUSTOM
        assert selection.related_projects == []
        assert selection.knowledge_available is True

    def test_select_skill_point_not_in_knowledge_base(self, selector):
        """测试选择知识库中不存在的技能点"""
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Rust")

        assert selection.skill_point == "Rust"
        assert selection.dimension == TrainingDimension.TECH_STACK
        assert selection.knowledge_available is False

    def test_select_skill_point_invalid_dimension(self, selector):
        """测试无效维度时的选择"""
        # 使用一个不在项目中的技能
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Go")

        assert selection.dimension == TrainingDimension.TECH_STACK
        assert selection.knowledge_available is False

    def test_related_projects_for_tech_stack(self, selector):
        """测试获取技能点相关的项目"""
        # Python 在电商系统和后台管理系统中都使用了
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Python")

        assert "电商系统" in selection.related_projects
        assert "后台管理系统" in selection.related_projects

    def test_related_projects_for_specific_tech(self, selector):
        """测试特定技术只在某些项目中使用"""
        # Redis 只在电商系统中使用
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Redis")

        assert "电商系统" in selection.related_projects
        assert "后台管理系统" not in selection.related_projects


class TestTrainingSkillSelectorEdgeCases:
    """Test TrainingSkillSelector edge cases"""

    @pytest.fixture
    def empty_resume_info(self):
        """创建空简历信息"""
        return ResumeInfo(
            name="李四",
            skills=[],
            projects=[],
        )

    @pytest.fixture
    def empty_knowledge_base(self):
        """创建空知识库"""
        return []

    def test_selector_with_empty_resume(self, empty_resume_info, empty_knowledge_base):
        """测试空简历信息"""
        selector = TrainingSkillSelector(empty_resume_info, empty_knowledge_base)

        skill_points = selector.get_available_skill_points(TrainingDimension.TECH_STACK)
        assert skill_points == []

        skill_points = selector.get_available_skill_points(TrainingDimension.PROJECT_MODULE)
        assert skill_points == []

    def test_selector_with_empty_knowledge_base(self):
        """测试空知识库"""
        resume = ResumeInfo(
            name="王五",
            skills=["Python"],
            projects=[ProjectInfo(name="测试项目", description="测试", technologies=["Python"])],
        )
        knowledge_base = []

        selector = TrainingSkillSelector(resume, knowledge_base)

        assert selector.validate_skill_point("Python") is False

        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Python")
        assert selection.knowledge_available is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
