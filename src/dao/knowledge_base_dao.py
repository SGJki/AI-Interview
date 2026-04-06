"""
KnowledgeBase DAO - Data Access Object for knowledge_base table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import KnowledgeBase, Project


class KnowledgeBaseDAO:
    """
    Data Access Object for KnowledgeBase operations.

    Provides async CRUD operations for the knowledge_base table.

    Example:
        async with db.get_session() as session:
            dao = KnowledgeBaseDAO(session)
            kb = KnowledgeBase(
                project_id=project_id,
                type="skill",
                skill_point="Python",
                content="Python is a programming language..."
            )
            await dao.save(kb)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize KnowledgeBaseDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """
        Save knowledge base entry to database.

        Args:
            knowledge_base: KnowledgeBase model instance

        Returns:
            Saved entry with generated ID
        """
        self.session.add(knowledge_base)
        await self.session.flush()
        await self.session.refresh(knowledge_base)
        return knowledge_base

    async def find_by_id(self, kb_id: UUID) -> Optional[KnowledgeBase]:
        """
        Find knowledge base entry by ID.

        Args:
            kb_id: KnowledgeBase UUID

        Returns:
            KnowledgeBase entry if found, None otherwise
        """
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def find_by_project_id(self, project_id: UUID) -> list[KnowledgeBase]:
        """
        Find all knowledge base entries for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of knowledge base entries
        """
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.project_id == project_id)
        )
        return list(result.scalars().all())

    async def find_by_skill_point(self, skill_point: str) -> list[KnowledgeBase]:
        """
        Find all knowledge base entries for a skill point.

        Args:
            skill_point: Skill point name

        Returns:
            List of knowledge base entries
        """
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.skill_point == skill_point)
        )
        return list(result.scalars().all())

    async def find_by_type(self, kb_type: str) -> list[KnowledgeBase]:
        """
        Find all knowledge base entries of a specific type.

        Args:
            kb_type: Entry type (e.g., 'skill', 'experience')

        Returns:
            List of knowledge base entries
        """
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.type == kb_type)
        )
        return list(result.scalars().all())

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[KnowledgeBase]:
        """
        Find all knowledge base entries with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of knowledge base entries
        """
        result = await self.session.execute(
            select(KnowledgeBase).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, kb_id: UUID) -> bool:
        """
        Delete knowledge base entry by ID.

        Args:
            kb_id: KnowledgeBase UUID

        Returns:
            True if deleted, False if not found
        """
        kb = await self.find_by_id(kb_id)
        if kb:
            await self.session.delete(kb)
            await self.session.flush()
            return True
        return False

    async def update(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """
        Update knowledge base entry.

        Args:
            knowledge_base: KnowledgeBase model instance (must have existing ID)

        Returns:
            Updated entry
        """
        await self.session.flush()
        await self.session.refresh(knowledge_base)
        return knowledge_base

    async def find_by_responsibility_id(self, responsibility_id: int) -> list[KnowledgeBase]:
        """
        Find all knowledge base entries for a specific responsibility.

        Args:
            responsibility_id: Responsibility index

        Returns:
            List of knowledge base entries for the responsibility
        """
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.responsibility_id == responsibility_id)
        )
        return list(result.scalars().all())

    async def find_responsibilities_by_resume(self, resume_id: UUID) -> list[KnowledgeBase]:
        """
        Find all responsibility-type KB entries for a resume.

        Args:
            resume_id: Resume UUID

        Returns:
            List of responsibility knowledge base entries
        """
        # Join with Project to filter by resume_id
        result = await self.session.execute(
            select(KnowledgeBase)
            .join(Project, KnowledgeBase.project_id == Project.id)
            .where(
                and_(
                    Project.resume_id == resume_id,
                    KnowledgeBase.type == "responsibility"
                )
            )
            .order_by(KnowledgeBase.responsibility_id)
        )
        return list(result.scalars().all())

    async def find_questions_by_session(self, session_id: str) -> list[KnowledgeBase]:
        """
        Find all question-type KB entries for a session (for question deduplication).

        Args:
            session_id: Session ID to filter by

        Returns:
            List of question knowledge base entries for the session
        """
        result = await self.session.execute(
            select(KnowledgeBase)
            .where(
                and_(
                    KnowledgeBase.session_id == session_id,
                    KnowledgeBase.question_id.isnot(None)
                )
            )
            .order_by(KnowledgeBase.created_at)
        )
        return list(result.scalars().all())

    async def save_question(
        self,
        project_id: UUID,
        question_id: str,
        session_id: str,
        content: str,
        responsibility_id: Optional[int] = None,
        responsibility_text: Optional[str] = None,
    ) -> KnowledgeBase:
        """
        Save a generated question to the knowledge base (for deduplication tracking).

        Args:
            project_id: Project UUID
            question_id: Unique question identifier
            session_id: Session ID
            content: Question text content
            responsibility_id: Optional responsibility index
            responsibility_text: Optional responsibility text

        Returns:
            Saved knowledge base entry
        """
        kb = KnowledgeBase(
            project_id=project_id,
            type="question",
            question_id=question_id,
            session_id=session_id,
            content=content,
            responsibility_id=responsibility_id,
            responsibility_text=responsibility_text,
        )
        return await self.save(kb)
