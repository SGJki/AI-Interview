"""
Responsibility Storage Service

负责将简历中的个人职责存储到知识库（PostgreSQL + Chroma）
"""

from typing import Optional
from uuid import UUID

from langchain_core.documents import Document

from src.db.database import get_db_session
from src.db.models import KnowledgeBase, Project
from src.dao.knowledge_base_dao import KnowledgeBaseDAO
from src.dao.project_dao import ProjectDAO
from src.tools.rag_tools import get_vectorstore


class ResponsibilityStorageService:
    """职责存储服务"""

    @staticmethod
    async def save_responsibilities_from_project(
        project_id: UUID,
        responsibilities: list[str],
        resume_id: Optional[UUID] = None,
    ) -> list[KnowledgeBase]:
        """
        将项目职责保存到知识库（PostgreSQL + Chroma）

        Args:
            project_id: 项目ID
            responsibilities: 职责列表
            resume_id: 简历ID（用于 Chroma 元数据）

        Returns:
            保存的知识库条目列表
        """
        saved_entries = []

        # 如果没有提供 resume_id，从 project 查找
        if not resume_id:
            async for session in get_db_session():
                project_dao = ProjectDAO(session)
                project = await project_dao.find_by_uuid(project_id)
                if project:
                    resume_id = project.resume_id  # resume_id is already BIGINT
                break

        # 获取 project_id (BIGINT) 用于保存
        project_id_int = None
        async for session in get_db_session():
            project_dao = ProjectDAO(session)
            project = await project_dao.find_by_uuid(project_id)
            if project:
                project_id_int = project.id  # BIGINT
            break

        if not project_id_int:
            logger.error(f"Project not found: {project_id}")
            return saved_entries

        async for session in get_db_session():
            dao = KnowledgeBaseDAO(session)

            for idx, resp_text in enumerate(responsibilities):
                kb = KnowledgeBase(
                    project_id=project_id_int,  # BIGINT
                    type="responsibility",
                    content=resp_text,
                    responsibility_id=idx,
                    responsibility_text=resp_text,
                    skill_point=f"responsibility_{idx}",
                )
                await dao.save(kb)
                saved_entries.append(kb)

            break  # get_db_session returns async generator

        # 同时添加到 Chroma 向量数据库
        if resume_id and responsibilities:
            try:
                vectorstore = get_vectorstore()
                docs = []
                for idx, resp_text in enumerate(responsibilities):
                    doc = Document(
                        page_content=resp_text,
                        metadata={
                            "type": "responsibility",
                            "resume_id": str(resume_id),
                            "responsibility_id": idx,
                        }
                    )
                    docs.append(doc)
                if docs:
                    vectorstore.add_documents(docs)
            except Exception as e:
                # Chroma 存储失败不影响主流程，仅记录日志
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[ResponsibilityStorageService] Failed to add to Chroma: {e}")

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
        获取简历的所有职责文本列表（从 PostgreSQL 查询）

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

    @staticmethod
    async def get_responsibilities_by_resume_from_chroma(resume_id: str, top_k: int = 50) -> list[str]:
        """
        从 Chroma 向量库获取简历的职责列表

        Args:
            resume_id: 简历ID
            top_k: 返回数量

        Returns:
            职责文本列表
        """
        try:
            from src.tools.rag_tools import retrieve_knowledge

            # 从 Chroma 检索所有相关文档
            docs = await retrieve_knowledge(
                query="个人职责 工作内容 项目责任",
                top_k=top_k,
                filter_metadata={"resume_id": resume_id}
            )

            # 过滤职责类型的文档
            responsibilities = []
            seen = set()
            for doc in docs:
                doc_type = doc.metadata.get("type", "")
                if doc_type == "responsibility":
                    content = doc.page_content.strip()
                    if content and content not in seen:
                        seen.add(content)
                        responsibilities.append(content)

            return responsibilities
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[get_responsibilities_by_resume_from_chroma] Failed: {e}")
            # 回退到 PostgreSQL 查询
            return await ResponsibilityStorageService.get_responsibilities_by_resume(resume_id)
