"""
QAHistory DAO - Data Access Object for qa_history table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import QAHistory


class QAHistoryDAO:
    """
    Data Access Object for QAHistory operations.

    Provides async CRUD operations for the qa_history table.

    Example:
        async with db.get_session() as session:
            dao = QAHistoryDAO(session)
            qa = QAHistory(
                session_id=interview_session_id,
                series=1,
                question_number=1,
                question="What is Python?",
                user_answer="A programming language",
                deviation_score=0.8
            )
            await dao.save(qa)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize QAHistoryDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, qa_history: QAHistory) -> QAHistory:
        """
        Save Q&A history entry to database.

        Args:
            qa_history: QAHistory model instance

        Returns:
            Saved entry with generated ID
        """
        self.session.add(qa_history)
        await self.session.flush()
        await self.session.refresh(qa_history)
        return qa_history

    async def find_by_id(self, qa_id: int) -> Optional[QAHistory]:
        """
        Find Q&A history entry by BIGINT ID.

        Args:
            qa_id: QAHistory BIGINT ID

        Returns:
            QAHistory entry if found, None otherwise
        """
        result = await self.session.execute(
            select(QAHistory).where(QAHistory.id == qa_id)
        )
        return result.scalar_one_or_none()

    async def find_by_session_id(self, session_id: int) -> list[QAHistory]:
        """
        Find all Q&A history entries for an interview session.

        Args:
            session_id: InterviewSession BIGINT ID

        Returns:
            List of Q&A history entries
        """
        result = await self.session.execute(
            select(QAHistory)
            .where(QAHistory.session_id == session_id)
            .order_by(QAHistory.series, QAHistory.question_number)
        )
        return list(result.scalars().all())

    async def find_by_series(
        self,
        session_id: int,
        series: int,
    ) -> list[QAHistory]:
        """
        Find all Q&A history entries for a specific series.

        Args:
            session_id: InterviewSession BIGINT ID
            series: Series number

        Returns:
            List of Q&A history entries
        """
        result = await self.session.execute(
            select(QAHistory)
            .where(
                QAHistory.session_id == session_id,
                QAHistory.series == series,
            )
            .order_by(QAHistory.question_number)
        )
        return list(result.scalars().all())

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QAHistory]:
        """
        Find all Q&A history entries with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Q&A history entries
        """
        result = await self.session.execute(
            select(QAHistory).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, qa_id: int) -> bool:
        """
        Delete Q&A history entry by BIGINT ID.

        Args:
            qa_id: QAHistory BIGINT ID

        Returns:
            True if deleted, False if not found
        """
        qa = await self.find_by_id(qa_id)
        if qa:
            await self.session.delete(qa)
            await self.session.flush()
            return True
        return False

    async def update(self, qa_history: QAHistory) -> QAHistory:
        """
        Update Q&A history entry.

        Args:
            qa_history: QAHistory model instance (must have existing ID)

        Returns:
            Updated entry
        """
        await self.session.flush()
        await self.session.refresh(qa_history)
        return qa_history

    async def save_batch(self, qa_entries: list[QAHistory]) -> list[QAHistory]:
        """
        Save multiple Q&A history entries.

        Args:
            qa_entries: List of QAHistory model instances

        Returns:
            List of saved entries
        """
        for qa in qa_entries:
            self.session.add(qa)
        await self.session.flush()
        for qa in qa_entries:
            await self.session.refresh(qa)
        return qa_entries
