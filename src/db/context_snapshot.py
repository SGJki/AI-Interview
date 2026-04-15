"""
Context Catch Snapshot ORM Model

SQLAlchemy model for context_snapshots table.
Stores compressed context snapshots for session recovery (disaster recovery).
"""

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class ContextSnapshot(Base):
    """
    Context Catch 快照版本表

    Attributes:
        id: 主键
        session_id: 会话ID
        version: 版本号，每次压缩递增
        timestamp: 快照时间戳
        compressed_summary: 压缩后的摘要（JSONB）
        created_at: 创建时间
    """

    __tablename__ = "context_snapshots"
    __table_args__ = (
        Index("idx_context_snapshots_session_version", "session_id", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    compressed_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
