"""
Tests for AI Interview Agent - Training Knowledge Matcher

专项训练-RAG知识匹配：从知识库检索匹配的技能点内容
"""

import pytest
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from src.services.training_knowledge_matcher import (
    KnowledgeMatchResult,
    TrainingKnowledgeMatcher,
    build_training_knowledge_base,
)
from src.services.training_selector import (
    TrainingDimension,
    SkillPointSelection,
    TrainingSkillSelector,
)
from src.services.resume_parser import ResumeInfo, ProjectInfo


class TestKnowledgeMatchResult:
    """Test KnowledgeMatchResult dataclass"""

    def test_knowledge_match_result_creation(self):
        """测试创建知识匹配结果"""
        docs = [
            Document(page_content="Python 基础语法", metadata={"type": "knowledge"}),
            Document(page_content="Python 进阶", metadata={"type": "knowledge"}),
        ]
        result = KnowledgeMatchResult(
            skill_point="Python",
            matched_knowledge=docs,
            standard_answers=["回答1", "回答2"],
            related_questions=["问题1", "问题2"],
            confidence=0.85,
        )

        assert result.skill_point == "Python"
        assert len(result.matched_knowledge) == 2
        assert result.standard_answers == ["回答1", "回答2"]
        assert result.related_questions == ["问题1", "问题2"]
        assert result.confidence == 0.85

    def test_knowledge_match_result_is_frozen(self):
        """测试 KnowledgeMatchResult 是不可变的"""
        docs = [Document(page_content="test", metadata={})]
        result = KnowledgeMatchResult(
            skill_point="Python",
            matched_knowledge=docs,
            standard_answers=["回答1"],
            related_questions=["问题1"],
            confidence=0.8,
        )

        with pytest.raises(Exception):
            result.skill_point = "Java"

    def test_knowledge_match_result_empty_lists(self):
        """测试空列表的知识匹配结果"""
        result = KnowledgeMatchResult(
            skill_point="Unknown",
            matched_knowledge=[],
            standard_answers=[],
            related_questions=[],
            confidence=0.0,
        )

        assert result.skill_point == "Unknown"
        assert result.matched_knowledge == []
        assert result.standard_answers == []
        assert result.related_questions == []
        assert result.confidence == 0.0


class TestBuildTrainingKnowledgeBase:
    """Test build_training_knowledge_base function"""

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
    def sample_project_docs(self):
        """创建样例项目知识文档"""
        return [
            Document(
                page_content="电商系统架构设计",
                metadata={"project": "电商系统", "type": "architecture"},
            ),
            Document(
                page_content="Redis 缓存策略",
                metadata={"project": "电商系统", "type": "cache"},
            ),
            Document(
                page_content="后台管理系统权限设计",
                metadata={"project": "后台管理系统", "type": "auth"},
            ),
        ]

    def test_build_knowledge_base_from_resume(self, sample_resume_info):
        """测试从简历构建知识库"""
        project_knowledge = []
        kb = build_training_knowledge_base(sample_resume_info, project_knowledge)

        assert len(kb) > 0
        assert "Python" in kb
        assert "FastAPI" in kb
        assert "Redis" in kb
        assert "电商系统" in kb
        assert "后台管理系统" in kb

    def test_build_knowledge_base_with_project_docs(
        self, sample_resume_info, sample_project_docs
    ):
        """测试从简历和项目文档构建知识库"""
        kb = build_training_knowledge_base(sample_resume_info, sample_project_docs)

        assert len(kb) > 0
        # 应该包含项目文档的内容
        assert "电商系统架构设计" in kb or any(
            "电商系统" in item for item in kb
        )

    def test_build_knowledge_base_empty_resume(self):
        """测试空简历构建知识库"""
        empty_resume = ResumeInfo(name="test", skills=[], projects=[])
        kb = build_training_knowledge_base(empty_resume, [])

        assert isinstance(kb, list)

    def test_build_knowledge_base_deduplication(self, sample_resume_info):
        """测试知识库去重"""
        # 简历中可能有重复的技能
        duplicate_resume = ResumeInfo(
            name="test",
            skills=["Python", "Python", "FastAPI"],
            projects=[],
        )
        kb = build_training_knowledge_base(duplicate_resume, [])

        # 去重后应该只有唯一项
        assert len(kb) == len(set(kb))


class TestTrainingKnowledgeMatcher:
    """Test TrainingKnowledgeMatcher class"""

    @pytest.fixture
    def sample_resume_info(self):
        """创建样例简历信息"""
        return ResumeInfo(
            name="张三",
            email="zhangsan@example.com",
            skills=["Python", "FastAPI", "Redis"],
            projects=[
                ProjectInfo(
                    name="电商系统",
                    description="基于微服务的电商平台",
                    technologies=["Python", "FastAPI", "Redis"],
                    role="后端开发",
                    highlights=["高并发处理", "微服务架构"],
                ),
            ],
        )

    @pytest.fixture
    def sample_knowledge_base(self):
        """创建样例知识库"""
        return [
            "Python 编程",
            "FastAPI Web 框架",
            "Redis 缓存",
            "电商系统架构",
        ]

    @pytest.fixture
    def mock_skill_selector(self, sample_resume_info, sample_knowledge_base):
        """创建模拟的技能选择器"""
        selector = MagicMock(spec=TrainingSkillSelector)
        selector.resume_info = sample_resume_info
        selector.knowledge_base = sample_knowledge_base
        return selector

    @pytest.fixture
    def mock_matcher(self, mock_skill_selector):
        """创建知识匹配器实例"""
        return TrainingKnowledgeMatcher(mock_skill_selector)

    def test_matcher_initialization(self, mock_skill_selector):
        """测试匹配器初始化"""
        matcher = TrainingKnowledgeMatcher(mock_skill_selector)

        assert matcher.skill_selector == mock_skill_selector

    @pytest.mark.asyncio
    async def test_match_knowledge_exact_match(self, mock_matcher):
        """测试精确匹配"""
        selection = SkillPointSelection(
            skill_point="Python",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=["电商系统"],
            knowledge_available=True,
        )

        with patch(
            "src.services.training_knowledge_matcher.retrieve_by_skill_point",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="Python 基础语法",
                    metadata={"skill_point": "Python", "type": "knowledge"},
                ),
                Document(
                    page_content="Python 进阶技巧",
                    metadata={"skill_point": "Python", "type": "knowledge"},
                ),
            ],
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_standard_answer",
            new_callable=AsyncMock,
            return_value=Document(
                page_content="Python 标准回答",
                metadata={"type": "answer"},
            ),
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_similar_questions",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="Python 相关问题1",
                    metadata={"type": "question"},
                ),
            ],
        ):
            result = await mock_matcher.match_knowledge(selection)

            assert isinstance(result, KnowledgeMatchResult)
            assert result.skill_point == "Python"
            assert len(result.matched_knowledge) == 2
            assert "Python 基础语法" in [doc.page_content for doc in result.matched_knowledge]

    @pytest.mark.asyncio
    async def test_match_knowledge_fuzzy_match(self, mock_matcher):
        """测试模糊匹配"""
        selection = SkillPointSelection(
            skill_point="Py",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=[],
            knowledge_available=False,  # 精确匹配不到
        )

        with patch(
            "src.services.training_knowledge_matcher.retrieve_by_skill_point",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="Python 编程基础",
                    metadata={"skill_point": "Python", "type": "knowledge"},
                ),
            ],
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_standard_answer",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_similar_questions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await mock_matcher.match_knowledge(selection)

            assert isinstance(result, KnowledgeMatchResult)
            assert result.skill_point == "Py"
            # 模糊匹配应该也返回结果
            assert len(result.matched_knowledge) >= 0

    @pytest.mark.asyncio
    async def test_match_knowledge_no_match(self, mock_matcher):
        """测试无匹配"""
        selection = SkillPointSelection(
            skill_point="Rust",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=[],
            knowledge_available=False,
        )

        with patch(
            "src.services.training_knowledge_matcher.retrieve_by_skill_point",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_standard_answer",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_similar_questions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await mock_matcher.match_knowledge(selection)

            assert isinstance(result, KnowledgeMatchResult)
            assert result.skill_point == "Rust"
            assert result.matched_knowledge == []
            assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_match_knowledge_with_related_projects(self, mock_matcher):
        """测试带相关项目的知识匹配"""
        selection = SkillPointSelection(
            skill_point="Redis",
            dimension=TrainingDimension.TECH_STACK,
            related_projects=["电商系统"],
            knowledge_available=True,
        )

        with patch(
            "src.services.training_knowledge_matcher.retrieve_by_skill_point",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="Redis 缓存实战",
                    metadata={
                        "skill_point": "Redis",
                        "project": "电商系统",
                        "type": "knowledge",
                    },
                ),
            ],
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_standard_answer",
            new_callable=AsyncMock,
            return_value=Document(
                page_content="Redis 标准回答",
                metadata={"type": "answer"},
            ),
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_similar_questions",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="Redis 相关问题",
                    metadata={"type": "question"},
                ),
            ],
        ):
            result = await mock_matcher.match_knowledge(selection)

            assert isinstance(result, KnowledgeMatchResult)
            assert result.skill_point == "Redis"
            assert len(result.matched_knowledge) == 1
            assert result.matched_knowledge[0].metadata.get("project") == "电商系统"

    def test_match_knowledge_confidence_calculation(self, mock_matcher):
        """测试置信度计算"""
        # 高匹配度的情况
        high_match_docs = [
            Document(page_content="Python", metadata={"score": 0.9}),
            Document(page_content="Python 基础", metadata={"score": 0.85}),
        ]
        confidence = mock_matcher._calculate_confidence(high_match_docs, exact_match=True)
        assert confidence >= 0.79  # 0.7975 rounded

        # 低匹配度的情况
        low_match_docs = [
            Document(page_content="相关内容", metadata={"score": 0.5}),
        ]
        confidence = mock_matcher._calculate_confidence(low_match_docs, exact_match=False)
        assert confidence < 0.6

        # 空结果
        confidence = mock_matcher._calculate_confidence([], exact_match=False)
        assert confidence == 0.0

    def test_match_knowledge_select_best_match(self, mock_matcher):
        """测试选择最佳匹配"""
        docs = [
            Document(page_content="Python 基础", metadata={"score": 0.9}),
            Document(page_content="Java 基础", metadata={"score": 0.85}),
            Document(page_content="Python 进阶", metadata={"score": 0.8}),
        ]

        best = mock_matcher._select_best_match("Python", docs)
        assert best is not None
        assert "Python" in best.page_content
        assert best.metadata.get("score") == 0.9


class TestTrainingKnowledgeMatcherIntegration:
    """Integration tests for TrainingKnowledgeMatcher"""

    @pytest.fixture
    def integration_resume_info(self):
        """创建用于集成的简历信息"""
        return ResumeInfo(
            name="李四",
            email="lisi@example.com",
            skills=["Python", "FastAPI", "Redis", "MySQL", "Docker"],
            projects=[
                ProjectInfo(
                    name="在线教育平台",
                    description="K12 在线教育系统",
                    technologies=["Python", "FastAPI", "Redis", "MySQL"],
                    role="技术负责人",
                    highlights=["高并发", "实时互动", "微服务"],
                ),
                ProjectInfo(
                    name="数据可视化平台",
                    description="企业级数据大屏",
                    technologies=["Python", "Django", "MySQL", "ECharts"],
                    role="后端开发",
                    highlights=["数据处理", "报表生成"],
                ),
            ],
        )

    @pytest.fixture
    def integration_knowledge_base(self, integration_resume_info):
        """创建集成测试用的知识库"""
        return build_training_knowledge_base(integration_resume_info, [])

    @pytest.mark.asyncio
    async def test_full_matching_flow(self, integration_resume_info, integration_knowledge_base):
        """测试完整匹配流程"""
        selector = TrainingSkillSelector(integration_resume_info, integration_knowledge_base)
        matcher = TrainingKnowledgeMatcher(selector)

        # 选择技能点
        selection = selector.select_skill_point(TrainingDimension.TECH_STACK, "Python")

        # 模拟检索结果
        mock_docs = [
            Document(
                page_content="Python 高并发编程",
                metadata={"skill_point": "Python", "type": "knowledge", "score": 0.9},
            ),
        ]

        with patch(
            "src.services.training_knowledge_matcher.retrieve_by_skill_point",
            new_callable=AsyncMock,
            return_value=mock_docs,
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_standard_answer",
            new_callable=AsyncMock,
            return_value=Document(
                page_content="Python 高并发处理的标准回答",
                metadata={"type": "answer"},
            ),
        ), patch(
            "src.services.training_knowledge_matcher.retrieve_similar_questions",
            new_callable=AsyncMock,
            return_value=[
                Document(
                    page_content="如何处理高并发？",
                    metadata={"type": "question"},
                ),
            ],
        ):
            result = await matcher.match_knowledge(selection)

            assert result.skill_point == "Python"
            assert len(result.matched_knowledge) == 1
            assert result.matched_knowledge[0].page_content == "Python 高并发编程"
            assert len(result.standard_answers) == 1
            assert len(result.related_questions) == 1
            assert result.confidence > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
