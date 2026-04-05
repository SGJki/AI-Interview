"""
Project DAO - Data Access Object for projects table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Project


class ProjectDAO:
    """
    Data Access Object for Project operations.

    Provides async CRUD operations for the projects table.

    Example:
        async with db.get_session() as session:
            dao = ProjectDAO(session)
            project = Project(resume_id=resume_id, name="My Project")
            await dao.save(project)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize ProjectDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, project: Project) -> Project:
        """
        Save project to database.

        Args:
            project: Project model instance

        Returns:
            Saved project with generated ID
        """
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def find_by_id(self, project_id: UUID) -> Optional[Project]:
        """
        Find project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project if found, None otherwise
        """
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def find_by_resume_id(self, resume_id: UUID) -> list[Project]:
        """
        Find all projects for a resume.

        Args:
            resume_id: Resume UUID

        Returns:
            List of projects
        """
        result = await self.session.execute(
            select(Project).where(Project.resume_id == resume_id)
        )
        return list(result.scalars().all())

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """
        Find all projects with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of projects
        """
        result = await self.session.execute(
            select(Project).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, project_id: UUID) -> bool:
        """
        Delete project by ID.

        Args:
            project_id: Project UUID

        Returns:
            True if deleted, False if not found
        """
        project = await self.find_by_id(project_id)
        if project:
            await self.session.delete(project)
            await self.session.flush()
            return True
        return False

    async def update(self, project: Project) -> Project:
        """
        Update project.

        Args:
            project: Project model instance (must have existing ID)

        Returns:
            Updated project
        """
        await self.session.flush()
        await self.session.refresh(project)
        return project
