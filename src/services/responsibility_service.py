"""
Responsibility Storage Service

负责将简历中的个人职责存储到知识库
"""

from typing import Optional
from uuid import UUID

from src.db.database import get_db_session
from src.db.models import KnowledgeBase, Project
from src.dao.knowledge_base_dao import KnowledgeBaseDAO


class ResponsibilityStorageService:
    """职责存储服务"""

    @staticmethod
    async def save_responsibilities_from_project(
        project_id: UUID,
        responsibilities: list[str],
    ) -> list[KnowledgeBase]:
        """
        将项目职责保存到知识库

        Args:
            project_id: 项目ID
            responsibilities: 职责列表

        Returns:
            保存的知识库条目列表
        """
        saved_entries = []

        async for session in get_db_session():
            dao = KnowledgeBaseDAO(session)

            for idx, resp_text in enumerate(responsibilities):
                kb = KnowledgeBase(
                    project_id=project_id,
                    type="responsibility",
                    content=resp_text,
                    responsibility_id=idx,
                    responsibility_text=resp_text,
                    skill_point=f"responsibility_{idx}",
                )
                await dao.save(kb)
                saved_entries.append(kb)

            break  # get_db_session returns async generator

        return saved_entries

    @staticmethod
    async def save_responsibilities_from_resume(
        resume_id: UUID,
        projects_with_responsibilities: list[tuple[UUID, list[str]]],
    ) -> dict[UUID, list[KnowledgeBase]]:
        """
        从简历的所有项目保存职责到知识库

        Args:
            resume_id: 简历ID
            projects_with_responsibilities: [(project_id, responsibilities), ...]

        Returns:
            {project_id: [KnowledgeBase entries]} 映射
        """
        results = {}

        for project_id, responsibilities in projects_with_responsibilities:
            if responsibilities:
                saved = await ResponsibilityStorageService.save_responsibilities_from_project(
                    project_id=project_id,
                    responsibilities=responsibilities,
                )
                results[project_id] = saved

        return results

    @staticmethod
    async def get_responsibilities_by_resume(resume_id: UUID) -> list[str]:
        """
        获取简历的所有职责文本列表

        Args:
            resume_id: 简历ID

        Returns:
            职责文本列表
        """
        responsibilities = []

        async for session in get_db_session():
            dao = KnowledgeBaseDAO(session)
            entries = await dao.find_responsibilities_by_resume(resume_id)

            for entry in entries:
                if entry.responsibility_text:
                    responsibilities.append(entry.responsibility_text)

            break

        return responsibilities
