"""
SQLAlchemy Models for PostgreSQL Database Schema

Includes:
- User: Multi-tenant user support (reserved)
- Resume: Resume parsing results
- Project: Project experiences from resume
- KnowledgeBase: RAG knowledge entries with vector embeddings
- InterviewSession: Interview session tracking
- QAHistory: Question and answer history
- InterviewFeedback: Final interview feedback
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class InterviewMode(str, Enum):
    """面试模式"""

    FREE = "free"
    TRAINING = "training"


class SessionStatus(str, Enum):
    """会话状态"""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    """
    用户表（预留多租户）

    Attributes:
        id: Primary key (UUID)
        name: User display name
        email: Unique email address
        created_at: Account creation timestamp
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Resume(Base):
    """
    简历表

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to users table
        file_path: Path to uploaded resume file
        parsed_content: JSONB field for parsed resume data
        created_at: Creation timestamp
    """

    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parsed_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="resume",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, user_id={self.user_id})>"


class Project(Base):
    """
    项目表

    Attributes:
        id: Primary key (UUID)
        resume_id: Foreign key to resumes table
        name: Project name
        repo_path: Repository path or URL
        description: Project description
        created_at: Creation timestamp
    """

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    resume_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    repo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="projects")
    knowledge_base_entries: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


class KnowledgeBase(Base):
    """
    知识库表

    Stores RAG knowledge entries with optional vector embeddings.
    The embedding_id references a pgvector embedding if pgvector is enabled.

    Attributes:
        id: Primary key (UUID)
        project_id: Foreign key to projects table
        type: Entry type (e.g., 'skill', 'experience')
        skill_point: Skill point name
        content: Text content
        embedding_id: Reference to pgvector embedding (optional)
        created_at: Creation timestamp
    """

    __tablename__ = "knowledge_base"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    skill_point: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # pgvector reference
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="knowledge_base_entries")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_knowledge_base_project_id", "project_id"),
        Index("ix_knowledge_base_skill_point", "skill_point"),
        Index("ix_knowledge_base_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, skill_point={self.skill_point})>"


class InterviewSession(Base):
    """
    面试会话表

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to users table
        resume_id: Foreign key to resumes table
        mode: Interview mode (free/training)
        feedback_mode: Feedback mode (realtime/recorded)
        status: Session status (active/completed/cancelled)
        started_at: Session start timestamp
        ended_at: Session end timestamp (nullable)
    """

    __tablename__ = "interview_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(50), default=InterviewMode.FREE.value)
    feedback_mode: Mapped[str] = mapped_column(String(50), default="recorded")
    status: Mapped[str] = mapped_column(
        String(50),
        default=SessionStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interview_sessions")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="interview_sessions")
    qa_history: Mapped[list["QAHistory"]] = relationship(
        "QAHistory",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    interview_feedback: Mapped[list["InterviewFeedback"]] = relationship(
        "InterviewFeedback",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_interview_sessions_user_id", "user_id"),
        Index("ix_interview_sessions_resume_id", "resume_id"),
        Index("ix_interview_sessions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, status={self.status})>"


class QAHistory(Base):
    """
    Q&A 历史表

    Stores individual question-answer pairs during an interview session.

    Attributes:
        id: Primary key (UUID)
        session_id: Foreign key to interview_sessions table
        series: Series number (interview series)
        question_number: Question number within the series
        question: Question text
        user_answer: User's answer text
        standard_answer: Standard/correct answer (optional)
        feedback: Feedback for the answer (optional)
        deviation_score: Score indicating deviation from standard (0-1)
        created_at: Creation timestamp
    """

    __tablename__ = "qa_history"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    series: Mapped[int] = mapped_column(Integer, default=1)
    question_number: Mapped[int] = mapped_column(Integer, default=1)
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    standard_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deviation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="qa_history",
    )

    # Indexes
    __table_args__ = (
        Index("ix_qa_history_session_id", "session_id"),
        Index("ix_qa_history_series", "series"),
    )

    def __repr__(self) -> str:
        return f"<QAHistory(id={self.id}, series={self.series}, q_num={self.question_number})>"


class InterviewFeedback(Base):
    """
    面试反馈表

    Stores final interview feedback and evaluation.

    Attributes:
        id: Primary key (UUID)
        session_id: Foreign key to interview_sessions table
        overall_score: Overall interview score (0-1)
        strengths: JSONB array of strengths
        weaknesses: JSONB array of weaknesses
        suggestions: JSONB array of suggestions
        created_at: Creation timestamp
    """

    __tablename__ = "interview_feedback"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strengths: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    suggestions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="interview_feedback",
    )

    # Indexes
    __table_args__ = (Index("ix_interview_feedback_session_id", "session_id"),)

    def __repr__(self) -> str:
        return f"<InterviewFeedback(id={self.id}, score={self.overall_score})>"
