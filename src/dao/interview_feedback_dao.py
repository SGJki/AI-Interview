"""
InterviewFeedback DAO - Data Access Object for interview_feedback table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import InterviewFeedback


class InterviewFeedbackDAO:
    """
    Data Access Object for InterviewFeedback operations.

    Provides async CRUD operations for the interview_feedback table.

    Example:
        async with db.get_session() as session:
            dao = InterviewFeedbackDAO(session)
            feedback = InterviewFeedback(
                session_id=interview_session_id,
                overall_score=0.85,
                strengths=["Good communication"],
                weaknesses=["Needs more practice"],
                suggestions=["Keep practicing"]
            )
            await dao.save(feedback)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize InterviewFeedbackDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, feedback: InterviewFeedback) -> InterviewFeedback:
        """
        Save interview feedback to database.

        Args:
            feedback: InterviewFeedback model instance

        Returns:
            Saved feedback with generated ID
        """
        self.session.add(feedback)
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback

    async def find_by_id(self, feedback_id: UUID) -> Optional[InterviewFeedback]:
        """
        Find interview feedback by ID.

        Args:
            feedback_id: InterviewFeedback UUID

        Returns:
            InterviewFeedback if found, None otherwise
        """
        result = await self.session.execute(
            select(InterviewFeedback).where(InterviewFeedback.id == feedback_id)
        )
        return result.scalar_one_or_none()

    async def find_by_session_id(self, session_id: UUID) -> list[InterviewFeedback]:
        """
        Find all feedback entries for an interview session.

        Args:
            session_id: InterviewSession UUID

        Returns:
            List of feedback entries
        """
        result = await self.session.execute(
            select(InterviewFeedback).where(InterviewFeedback.session_id == session_id)
        )
        return list(result.scalars().all())

    async def find_latest_by_session_id(
        self,
        session_id: UUID,
    ) -> Optional[InterviewFeedback]:
        """
        Find latest feedback for an interview session.

        Args:
            session_id: InterviewSession UUID

        Returns:
            Latest InterviewFeedback if found, None otherwise
        """
        result = await self.session.execute(
            select(InterviewFeedback)
            .where(InterviewFeedback.session_id == session_id)
            .order_by(InterviewFeedback.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InterviewFeedback]:
        """
        Find all interview feedback entries with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of feedback entries
        """
        result = await self.session.execute(
            select(InterviewFeedback).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, feedback_id: UUID) -> bool:
        """
        Delete interview feedback by ID.

        Args:
            feedback_id: InterviewFeedback UUID

        Returns:
            True if deleted, False if not found
        """
        feedback = await self.find_by_id(feedback_id)
        if feedback:
            await self.session.delete(feedback)
            await self.session.flush()
            return True
        return False

    async def update(self, feedback: InterviewFeedback) -> InterviewFeedback:
        """
        Update interview feedback.

        Args:
            feedback: InterviewFeedback model instance (must have existing ID)

        Returns:
            Updated feedback
        """
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback
