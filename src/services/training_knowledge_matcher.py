"""
Training Knowledge Matcher Service for AI Interview Agent

专项训练-RAG知识匹配：从知识库检索匹配的技能点内容

支持多种匹配策略：
- 精确匹配：技能点名称完全一致
- 模糊匹配：技能点名称部分匹配
- 语义匹配：使用 embedding 语义相似度
"""

from dataclasses import dataclass
from typing import Optional

from langchain_core.documents import Document

from src.services.resume_parser import ResumeInfo, ProjectInfo
from src.services.training_selector import SkillPointSelection, TrainingSkillSelector
from src.tools.rag_tools import (
    retrieve_by_skill_point,
    retrieve_standard_answer,
    retrieve_similar_questions,
)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class KnowledgeMatchResult:
    """
    知识匹配结果

    Attributes:
        skill_point: 技能点名称
        matched_knowledge: 检索到的知识文档列表
        standard_answers: 标准回答列表
        related_questions: 相关问题列表
        confidence: 匹配置信度 (0.0 - 1.0)
    """
    skill_point: str
    matched_knowledge: list[Document]
    standard_answers: list[str]
    related_questions: list[str]
    confidence: float


# =============================================================================
# Knowledge Base Builder
# =============================================================================


def build_training_knowledge_base(
    resume_info: ResumeInfo,
    project_knowledge: list[Document]
) -> list[str]:
    """
    从简历和项目代码构建训练知识库

    从简历中提取：
    - 技术栈（skills）
    - 项目名称（projects）
    - 项目描述和亮点

    从项目文档中提取：
    - 项目架构相关知识
    - 技术实现细节

    Args:
        resume_info: 简历信息
        project_knowledge: 项目知识文档列表

    Returns:
        知识库字符串列表
    """
    knowledge_items: set[str] = set()

    # 添加技能
    for skill in resume_info.skills:
        if skill:
            knowledge_items.add(skill)

    # 添加项目名称
    for project in resume_info.projects:
        if project.name:
            knowledge_items.add(project.name)
        # 添加项目描述中的关键词
        if project.description:
            knowledge_items.add(project.description[:100])
        # 添加技术栈
        for tech in project.technologies:
            if tech:
                knowledge_items.add(tech)
        # 添加项目亮点
        for highlight in project.highlights:
            if highlight:
                knowledge_items.add(highlight)

    # 从项目文档中提取知识
    for doc in project_knowledge:
        content = doc.page_content
        if content:
            knowledge_items.add(content)
        # 从元数据中提取信息
        metadata = doc.metadata
        if metadata.get("project"):
            knowledge_items.add(metadata["project"])
        if metadata.get("skill_point"):
            knowledge_items.add(metadata["skill_point"])

    # 添加教育背景关键词
    for edu in resume_info.education:
        if edu.school:
            knowledge_items.add(edu.school)
        if edu.major:
            knowledge_items.add(edu.major)

    # 添加工作经历关键词
    for work in resume_info.work_experience:
        if work.company:
            knowledge_items.add(work.company)
        if work.position:
            knowledge_items.add(work.position)
        for achievement in work.achievements:
            if achievement:
                knowledge_items.add(achievement)

    # 返回去重后的列表
    return list(knowledge_items)


# =============================================================================
# Training Knowledge Matcher
# =============================================================================


class TrainingKnowledgeMatcher:
    """
    训练知识匹配器

    根据技能点从 RAG 知识库检索相关内容
    支持多库融合检索

    Attributes:
        skill_selector: 技能选择器实例
    """

    def __init__(self, skill_selector: TrainingSkillSelector):
        """
        初始化知识匹配器

        Args:
            skill_selector: 技能选择器实例
        """
        self.skill_selector = skill_selector

    async def match_knowledge(
        self,
        selection: SkillPointSelection,
        top_k: int = 5
    ) -> KnowledgeMatchResult:
        """
        匹配技能点对应的知识

        使用多策略检索：
        1. 精确匹配：直接按技能点名称检索
        2. 模糊匹配：当精确匹配无结果时，使用部分名称检索
        3. 语义匹配：使用 embedding 语义相似度检索

        Args:
            selection: 技能点选择结果
            top_k: 返回结果数量

        Returns:
            知识匹配结果
        """
        skill_point = selection.skill_point

        # 策略1：精确匹配
        exact_docs = await self._retrieve_exact_match(skill_point, top_k)

        if exact_docs and self._is_good_match(exact_docs, skill_point):
            # 精确匹配成功
            standard_answers = await self._retrieve_standard_answers(skill_point)
            related_questions = await self._retrieve_related_questions(skill_point)
            confidence = self._calculate_confidence(exact_docs, exact_match=True)

            return KnowledgeMatchResult(
                skill_point=skill_point,
                matched_knowledge=exact_docs,
                standard_answers=standard_answers,
                related_questions=related_questions,
                confidence=confidence,
            )

        # 策略2：模糊匹配
        fuzzy_docs = await self._retrieve_fuzzy_match(skill_point, top_k)

        if fuzzy_docs:
            # 模糊匹配成功
            standard_answers = await self._retrieve_standard_answers(skill_point)
            related_questions = await self._retrieve_related_questions(skill_point)
            confidence = self._calculate_confidence(fuzzy_docs, exact_match=False)

            return KnowledgeMatchResult(
                skill_point=skill_point,
                matched_knowledge=fuzzy_docs,
                standard_answers=standard_answers,
                related_questions=related_questions,
                confidence=confidence,
            )

        # 策略3：语义匹配（使用相关项目信息）
        semantic_docs = await self._retrieve_semantic_match(selection, top_k)

        if semantic_docs:
            standard_answers = await self._retrieve_standard_answers(skill_point)
            related_questions = await self._retrieve_related_questions(skill_point)
            confidence = self._calculate_confidence(semantic_docs, exact_match=False)

            return KnowledgeMatchResult(
                skill_point=skill_point,
                matched_knowledge=semantic_docs,
                standard_answers=standard_answers,
                related_questions=related_questions,
                confidence=confidence,
            )

        # 无匹配结果
        return KnowledgeMatchResult(
            skill_point=skill_point,
            matched_knowledge=[],
            standard_answers=[],
            related_questions=[],
            confidence=0.0,
        )

    async def _retrieve_exact_match(
        self,
        skill_point: str,
        top_k: int
    ) -> list[Document]:
        """
        精确匹配检索

        Args:
            skill_point: 技能点名称
            top_k: 返回数量

        Returns:
            检索到的文档列表
        """
        try:
            return await retrieve_by_skill_point(skill_point, top_k)
        except Exception:
            return []

    async def _retrieve_fuzzy_match(
        self,
        skill_point: str,
        top_k: int
    ) -> list[Document]:
        """
        模糊匹配检索

        当精确匹配无结果时，使用包含技能点名称部分字符串的检索

        Args:
            skill_point: 技能点名称
            top_k: 返回数量

        Returns:
            检索到的文档列表
        """
        try:
            # 尝试使用部分名称检索
            partial_query = f"{skill_point}"
            docs = await retrieve_by_skill_point(partial_query, top_k)

            # 过滤出包含该技能点的文档
            filtered_docs = [
                doc for doc in docs
                if skill_point.lower() in doc.page_content.lower()
                or skill_point in str(doc.metadata.get("skill_point", ""))
            ]

            return filtered_docs if filtered_docs else docs
        except Exception:
            return []

    async def _retrieve_semantic_match(
        self,
        selection: SkillPointSelection,
        top_k: int
    ) -> list[Document]:
        """
        语义匹配检索

        结合技能点和相关项目信息进行语义检索

        Args:
            selection: 技能点选择结果
            top_k: 返回数量

        Returns:
            检索到的文档列表
        """
        try:
            # 构建语义查询，结合技能点和相关项目
            query_parts = [selection.skill_point]

            for project_name in selection.related_projects:
                query_parts.append(project_name)

            semantic_query = " ".join(query_parts)
            return await retrieve_by_skill_point(semantic_query, top_k)
        except Exception:
            return []

    async def _retrieve_standard_answers(
        self,
        skill_point: str
    ) -> list[str]:
        """
        检索标准回答

        Args:
            skill_point: 技能点名称

        Returns:
            标准回答列表
        """
        try:
            doc = await retrieve_standard_answer(skill_point)
            if doc:
                return [doc.page_content]
            return []
        except Exception:
            return []

    async def _retrieve_related_questions(
        self,
        skill_point: str
    ) -> list[str]:
        """
        检索相关问题

        Args:
            skill_point: 技能点名称

        Returns:
            相关问题列表
        """
        try:
            docs = await retrieve_similar_questions(skill_point, top_k=3)
            return [doc.page_content for doc in docs]
        except Exception:
            return []

    def _is_good_match(
        self,
        docs: list[Document],
        skill_point: str
    ) -> bool:
        """
        判断匹配结果是否良好

        Args:
            docs: 检索到的文档列表
            skill_point: 技能点名称

        Returns:
            是否是良好的匹配
        """
        if not docs:
            return False

        # 检查第一个结果的相似度
        first_score = docs[0].metadata.get("score", 0.0)
        if first_score >= 0.8:
            return True

        # 检查是否有多个结果匹配
        if len(docs) >= 3:
            return True

        return False

    def _calculate_confidence(
        self,
        docs: list[Document],
        exact_match: bool
    ) -> float:
        """
        计算匹配置信度

        置信度考虑因素：
        - 文档数量
        - 相似度分数
        - 是否为精确匹配

        Args:
            docs: 检索到的文档列表
            exact_match: 是否为精确匹配

        Returns:
            置信度 (0.0 - 1.0)
        """
        if not docs:
            return 0.0

        # 基础分数
        base_score = 0.3 if exact_match else 0.2

        # 数量分数（最多 0.3）
        count_score = min(len(docs) / 10, 1.0) * 0.3

        # 相似度分数（最多 0.5）
        avg_score = sum(
            doc.metadata.get("score", 0.5) for doc in docs
        ) / len(docs)
        similarity_score = avg_score * 0.5

        total = base_score + count_score + similarity_score

        # 确保在有效范围内
        return max(0.0, min(1.0, total))

    def _select_best_match(
        self,
        skill_point: str,
        docs: list[Document]
    ) -> Optional[Document]:
        """
        从多个匹配结果中选择最佳匹配

        Args:
            skill_point: 技能点名称
            docs: 文档列表

        Returns:
            最佳匹配的文档，如果没有匹配则返回 None
        """
        if not docs:
            return None

        # 按分数排序
        sorted_docs = sorted(
            docs,
            key=lambda doc: doc.metadata.get("score", 0.0),
            reverse=True
        )

        # 返回最佳匹配
        return sorted_docs[0]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "KnowledgeMatchResult",
    "TrainingKnowledgeMatcher",
    "build_training_knowledge_base",
]
