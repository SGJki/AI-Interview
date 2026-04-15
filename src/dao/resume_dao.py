"""
Resume DAO - Data Access Object for resumes table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Resume


class ResumeDAO:
    """
    Data Access Object for Resume operations.

    Provides async CRUD operations for the resumes table.

    Example:
        async with db.get_session() as session:
            dao = ResumeDAO(session)
            resume = Resume(user_id=user_id, file_path="/path/to/resume.pdf")
            await dao.save(resume)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize ResumeDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, resume: Resume) -> Resume:
        """
        Save resume to database.

        Args:
            resume: Resume model instance

        Returns:
            Saved resume with generated ID
        """
        self.session.add(resume)
        await self.session.flush()
        await self.session.refresh(resume)
        return resume

    async def find_by_id(self, resume_id: int) -> Optional[Resume]:
        """
        Find resume by BIGINT ID.

        Args:
            resume_id: Resume BIGINT ID

        Returns:
            Resume if found, None otherwise
        """
        result = await self.session.execute(
            select(Resume).where(Resume.id == resume_id)
        )
        return result.scalar_one_or_none()

    async def find_by_uuid(self, resume_uuid: UUID) -> Optional[Resume]:
        """
        Find resume by UUID.

        Args:
            resume_uuid: Resume UUID

        Returns:
            Resume if found, None otherwise
        """
        result = await self.session.execute(
            select(Resume).where(Resume.uuid == resume_uuid)
        )
        return result.scalar_one_or_none()

    async def find_by_user_id(self, user_id: int) -> list[Resume]:
        """
        Find all resumes for a user.

        Args:
            user_id: User BIGINT ID

        Returns:
            List of resumes
        """
        result = await self.session.execute(
            select(Resume).where(Resume.user_id == user_id)
        )
        return list(result.scalars().all())

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[Resume]:
        """
        Find all resumes with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of resumes
        """
        result = await self.session.execute(
            select(Resume).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, resume_id: int) -> bool:
        """
        Delete resume by BIGINT ID.

        Args:
            resume_id: Resume BIGINT ID

        Returns:
            True if deleted, False if not found
        """
        resume = await self.find_by_id(resume_id)
        if resume:
            await self.session.delete(resume)
            await self.session.flush()
            return True
        return False

    async def update(self, resume: Resume) -> Resume:
        """
        Update resume.

        Args:
            resume: Resume model instance (must have existing ID)

        Returns:
            Updated resume
        """
        await self.session.flush()
        await self.session.refresh(resume)
        return resume
