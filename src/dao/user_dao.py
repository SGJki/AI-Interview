"""
User DAO - Data Access Object for users table
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User


class UserDAO:
    """
    Data Access Object for User operations.

    Provides async CRUD operations for the users table.

    Example:
        async with db.get_session() as session:
            dao = UserDAO(session)
            user = User(name="John", email="john@example.com")
            await dao.save(user)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize UserDAO.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, user: User) -> User:
        """
        Save user to database.

        Args:
            user: User model instance

        Returns:
            Saved user with generated ID
        """
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def find_by_id(self, user_id: int) -> Optional[User]:
        """
        Find user by BIGINT ID.

        Args:
            user_id: User BIGINT ID

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_uuid(self, user_uuid: UUID) -> Optional[User]:
        """
        Find user by UUID.

        Args:
            user_uuid: User UUID

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.uuid == user_uuid)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """
        Find all users with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of users
        """
        result = await self.session.execute(
            select(User).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, user_id: int) -> bool:
        """
        Delete user by BIGINT ID.

        Args:
            user_id: User BIGINT ID

        Returns:
            True if deleted, False if not found
        """
        user = await self.find_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.flush()
            return True
        return False

    async def update(self, user: User) -> User:
        """
        Update user.

        Args:
            user: User model instance (must have existing ID)

        Returns:
            Updated user
        """
        await self.session.flush()
        await self.session.refresh(user)
        return user
