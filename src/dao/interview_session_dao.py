"""
InterviewSession DAO - Data Access Object for interview_sessions table
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import InterviewSession, SessionStatus


class InterviewSessionDAO:
    """
    Data Access Object for InterviewSession operations.

    Provides async CRUD operations for the interview_sessions table.

    Example:
        async with db.get_session() as session:
            dao = InterviewSessionDAO(session)
            session = InterviewSession(
                user_id=user_id,
                resume_id=resume_id,
                mode=InterviewMode.FREE
            )
            await dao.save(session)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize InterviewSessionDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, interview_session: InterviewSession) -> InterviewSession:
        """
        Save interview session to database.

        Args:
            interview_session: InterviewSession model instance

        Returns:
            Saved session with generated ID
        """
        self.session.add(interview_session)
        await self.session.flush()
        await self.session.refresh(interview_session)
        return interview_session

    async def find_by_id(self, session_id: int) -> Optional[InterviewSession]:
        """
        Find interview session by BIGINT ID.

        Args:
            session_id: InterviewSession BIGINT ID

        Returns:
            InterviewSession if found, None otherwise
        """
        result = await self.session.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def find_by_uuid(self, session_uuid: UUID) -> Optional[InterviewSession]:
        """
        Find interview session by UUID.

        Args:
            session_uuid: InterviewSession UUID

        Returns:
            InterviewSession if found, None otherwise
        """
        result = await self.session.execute(
            select(InterviewSession).where(InterviewSession.uuid == session_uuid)
        )
        return result.scalar_one_or_none()

    async def find_by_user_id(
        self,
        user_id: int,
        status: Optional[SessionStatus] = None,
    ) -> list[InterviewSession]:
        """
        Find all interview sessions for a user.

        Args:
            user_id: User BIGINT ID
            status: Optional filter by session status

        Returns:
            List of interview sessions
        """
        query = select(InterviewSession).where(InterviewSession.user_id == user_id)
        if status:
            query = query.where(InterviewSession.status == status.value)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_active_session(self, user_id: int) -> Optional[InterviewSession]:
        """
        Find active interview session for a user.

        Args:
            user_id: User BIGINT ID

        Returns:
            Active InterviewSession if found, None otherwise
        """
        result = await self.session.execute(
            select(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == SessionStatus.ACTIVE.value,
            )
            .order_by(InterviewSession.started_at.desc())
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[SessionStatus] = None,
    ) -> list[InterviewSession]:
        """
        Find all interview sessions with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Optional filter by session status

        Returns:
            List of interview sessions
        """
        query = select(InterviewSession).limit(limit).offset(offset)
        if status:
            query = query.where(InterviewSession.status == status.value)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, session_id: int) -> bool:
        """
        Delete interview session by BIGINT ID.

        Args:
            session_id: InterviewSession BIGINT ID

        Returns:
            True if deleted, False if not found
        """
        session = await self.find_by_id(session_id)
        if session:
            await self.session.delete(session)
            await self.session.flush()
            return True
        return False

    async def update(self, interview_session: InterviewSession) -> InterviewSession:
        """
        Update interview session.

        Args:
            interview_session: InterviewSession model instance (must have existing ID)

        Returns:
            Updated session
        """
        await self.session.flush()
        await self.session.refresh(interview_session)
        return interview_session

    async def end_session(self, session_id: int) -> Optional[InterviewSession]:
        """
        Mark interview session as ended.

        Args:
            session_id: InterviewSession BIGINT ID

        Returns:
            Updated session or None if not found
        """
        interview_session = await self.find_by_id(session_id)
        if interview_session:
            interview_session.status = SessionStatus.COMPLETED.value
            interview_session.ended_at = datetime.now()
            return await self.update(interview_session)
        return None

    async def cancel_session(self, session_id: int) -> Optional[InterviewSession]:
        """
        Cancel interview session.

        Args:
            session_id: InterviewSession BIGINT ID

        Returns:
            Updated session or None if not found
        """
        interview_session = await self.find_by_id(session_id)
        if interview_session:
            interview_session.status = SessionStatus.CANCELLED.value
            interview_session.ended_at = datetime.now()
            return await self.update(interview_session)
        return None
