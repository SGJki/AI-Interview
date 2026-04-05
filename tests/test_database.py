"""
Tests for PostgreSQL Database Layer - DAO, Models, Vector Store
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseManager:
    """Test DatabaseManager class"""

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization"""
        from src.db.database import DatabaseManager

        db_url = "postgresql+asyncpg://user:pass@localhost/testdb"
        db_manager = DatabaseManager(db_url)

        assert db_manager.database_url == db_url
        assert db_manager.engine is not None
        assert db_manager.session_factory is not None

    def test_database_manager_get_session(self):
        """Test getting async session"""
        import asyncio
        from src.db.database import DatabaseManager

        db_url = "postgresql+asyncpg://user:pass@localhost/testdb"
        db_manager = DatabaseManager(db_url)

        # Get a session (even if mock)
        session_gen = db_manager.get_session()
        assert session_gen is not None

        # Test that it's a generator/async context manager
        import inspect
        assert inspect.isasyncgenfunction(db_manager.get_session) or hasattr(session_gen, '__aenter__')


class TestDatabaseModels:
    """Test SQLAlchemy models"""

    def test_user_model_creation(self):
        """Test User model can be instantiated"""
        from src.db.models import User

        user = User(
            id=uuid4(),
            name="Test User",
            email="test@example.com"
        )

        assert user.name == "Test User"
        assert user.email == "test@example.com"
        # Note: created_at is set by SQLAlchemy default on persist, not on instantiation

    def test_resume_model_creation(self):
        """Test Resume model can be instantiated"""
        from src.db.models import Resume

        user_id = uuid4()
        resume = Resume(
            id=uuid4(),
            user_id=user_id,
            file_path="/path/to/resume.pdf",
            parsed_content={"skills": ["Python", "Go"]}
        )

        assert resume.user_id == user_id
        assert resume.file_path == "/path/to/resume.pdf"
        assert resume.parsed_content["skills"] == ["Python", "Go"]

    def test_project_model_creation(self):
        """Test Project model can be instantiated"""
        from src.db.models import Project

        resume_id = uuid4()
        project = Project(
            id=uuid4(),
            resume_id=resume_id,
            name="Test Project",
            repo_path="/path/to/repo",
            description="A test project"
        )

        assert project.resume_id == resume_id
        assert project.name == "Test Project"

    def test_knowledge_base_model_creation(self):
        """Test KnowledgeBase model can be instantiated"""
        from src.db.models import KnowledgeBase

        project_id = uuid4()
        kb = KnowledgeBase(
            id=uuid4(),
            project_id=project_id,
            type="skill",
            skill_point="Python",
            content="Python is a programming language..."
        )

        assert project_id == kb.project_id
        assert kb.skill_point == "Python"

    def test_interview_session_model_creation(self):
        """Test InterviewSession model can be instantiated"""
        from src.db.models import InterviewSession, InterviewMode, SessionStatus

        user_id = uuid4()
        resume_id = uuid4()
        session = InterviewSession(
            id=uuid4(),
            user_id=user_id,
            resume_id=resume_id,
            mode=InterviewMode.FREE,
            feedback_mode="recorded",
            status=SessionStatus.ACTIVE
        )

        assert session.user_id == user_id
        assert session.resume_id == resume_id

    def test_qa_history_model_creation(self):
        """Test QAHistory model can be instantiated"""
        from src.db.models import QAHistory

        session_id = uuid4()
        qa = QAHistory(
            id=uuid4(),
            session_id=session_id,
            series=1,
            question_number=1,
            question="What is Python?",
            user_answer="Python is a programming language",
            standard_answer="Python is a high-level programming language",
            feedback="Good answer",
            deviation_score=0.8
        )

        assert qa.session_id == session_id
        assert qa.series == 1
        assert qa.deviation_score == 0.8

    def test_interview_feedback_model_creation(self):
        """Test InterviewFeedback model can be instantiated"""
        from src.db.models import InterviewFeedback

        session_id = uuid4()
        feedback = InterviewFeedback(
            id=uuid4(),
            session_id=session_id,
            overall_score=0.85,
            strengths=["Good communication", "Technical depth"],
            weaknesses=["Needs more practice"],
            suggestions=["Keep practicing"]
        )

        assert feedback.session_id == session_id
        assert feedback.overall_score == 0.85


class TestUserDAO:
    """Test UserDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    def test_user_dao_create(self, mock_session):
        """Test UserDAO create operation"""
        from src.dao.user_dao import UserDAO

        dao = UserDAO(mock_session)
        assert dao.session == mock_session

    @pytest.mark.asyncio
    async def test_user_dao_save(self, mock_session):
        """Test UserDAO save operation"""
        from src.dao.user_dao import UserDAO
        from src.db.models import User

        # Setup mock to return the user on commit
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: None))

        dao = UserDAO(mock_session)
        user = User(
            name="Test User",
            email="test@example.com"
        )

        # The save should work without errors
        result = await dao.save(user)
        assert result is not None


class TestResumeDAO:
    """Test ResumeDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_resume_dao_create(self, mock_session):
        """Test ResumeDAO create operation"""
        from src.dao.resume_dao import ResumeDAO

        dao = ResumeDAO(mock_session)
        assert dao.session == mock_session


class TestProjectDAO:
    """Test ProjectDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_project_dao_create(self, mock_session):
        """Test ProjectDAO create operation"""
        from src.dao.project_dao import ProjectDAO

        dao = ProjectDAO(mock_session)
        assert dao.session == mock_session


class TestKnowledgeBaseDAO:
    """Test KnowledgeBaseDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_knowledge_base_dao_create(self, mock_session):
        """Test KnowledgeBaseDAO create operation"""
        from src.dao.knowledge_base_dao import KnowledgeBaseDAO

        dao = KnowledgeBaseDAO(mock_session)
        assert dao.session == mock_session


class TestInterviewSessionDAO:
    """Test InterviewSessionDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_interview_session_dao_create(self, mock_session):
        """Test InterviewSessionDAO create operation"""
        from src.dao.interview_session_dao import InterviewSessionDAO

        dao = InterviewSessionDAO(mock_session)
        assert dao.session == mock_session


class TestQAHistoryDAO:
    """Test QAHistoryDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_qa_history_dao_create(self, mock_session):
        """Test QAHistoryDAO create operation"""
        from src.dao.qa_history_dao import QAHistoryDAO

        dao = QAHistoryDAO(mock_session)
        assert dao.session == mock_session


class TestInterviewFeedbackDAO:
    """Test InterviewFeedbackDAO operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session"""
        session = AsyncMock()
        return session

    def test_interview_feedback_dao_create(self, mock_session):
        """Test InterviewFeedbackDAO create operation"""
        from src.dao.interview_feedback_dao import InterviewFeedbackDAO

        dao = InterviewFeedbackDAO(mock_session)
        assert dao.session == mock_session


class TestVectorStore:
    """Test VectorStore for pgvector integration"""

    def test_vector_store_initialization(self):
        """Test VectorStore initialization"""
        from src.db.vector_store import VectorStore

        # Mock embedding function
        mock_embed = MagicMock(return_value=[0.1] * 1536)
        store = VectorStore(mock_embed, dimensions=1536)

        assert store.dimensions == 1536
        assert store._embed_fn is not None

    def test_vector_store_embed_text(self):
        """Test VectorStore embed_text method"""
        from src.db.vector_store import VectorStore

        # Create mock embedding function - returns list of embeddings
        # Each embedding is a list of floats
        mock_embed = MagicMock(return_value=[[0.1] * 1536])
        store = VectorStore(mock_embed, dimensions=1536)

        text = "This is a test text"
        result = store.embed_text(text)

        assert isinstance(result, list)
        assert len(result) == 1536
        mock_embed.assert_called_once_with([text])

    def test_vector_store_embed_texts(self):
        """Test VectorStore embed_texts batch method"""
        from src.db.vector_store import VectorStore

        # Mock returns list of embeddings (one per text input)
        mock_embed = MagicMock(return_value=[[0.1] * 1536, [0.1] * 1536, [0.1] * 1536])
        store = VectorStore(mock_embed, dimensions=1536)

        texts = ["Text 1", "Text 2", "Text 3"]
        results = store.embed_texts(texts)

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(len(r) == 1536 for r in results)

    def test_vector_store_similarity(self):
        """Test VectorStore cosine_similarity method"""
        from src.db.vector_store import VectorStore
        import numpy as np

        mock_embed = MagicMock(return_value=[0.1] * 1536)
        store = VectorStore(mock_embed, dimensions=1536)

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]

        # Same vectors should have similarity 1.0
        sim_same = store.cosine_similarity(vec1, vec2)
        assert np.isclose(sim_same, 1.0)

        # Orthogonal vectors should have similarity 0.0
        sim_orth = store.cosine_similarity(vec1, vec3)
        assert np.isclose(sim_orth, 0.0)

    def test_vector_store_find_similar(self):
        """Test VectorStore find_similar method"""
        from src.db.vector_store import VectorStore
        import numpy as np

        # Create mock embedding function that returns predictable vectors
        def mock_embed_fn(texts):
            # Simple embedding: first char hash determines direction
            embeddings = []
            for t in texts:
                vec = np.zeros(10)
                vec[hash(t[0]) % 10] = 1.0
                embeddings.append(vec.tolist())
            return embeddings

        store = VectorStore(mock_embed_fn, dimensions=10)

        # Add some documents
        doc_ids = []
        doc_ids.append(store.add_text("Apple fruit"))
        doc_ids.append(store.add_text("Banana fruit"))
        doc_ids.append(store.add_text("Carrot vegetable"))

        # Find similar - should work
        results = store.find_similar("Apple", top_k=2)
        assert len(results) <= 2

    def test_vector_store_add_text(self):
        """Test VectorStore add_text method"""
        from src.db.vector_store import VectorStore

        mock_embed = MagicMock(return_value=[0.1] * 1536)
        store = VectorStore(mock_embed, dimensions=1536)

        doc_id = store.add_text("Test document", metadata={"source": "test"})
        assert doc_id is not None
        assert store.document_count == 1

    def test_vector_store_delete_document(self):
        """Test VectorStore delete_document method"""
        from src.db.vector_store import VectorStore

        mock_embed = MagicMock(return_value=[0.1] * 1536)
        store = VectorStore(mock_embed, dimensions=1536)

        doc_id = store.add_text("Test document")
        assert store.document_count == 1

        store.delete_document(doc_id)
        assert store.document_count == 0

    def test_vector_store_get_document(self):
        """Test VectorStore get_document method"""
        from src.db.vector_store import VectorStore

        mock_embed = MagicMock(return_value=[0.1] * 1536)
        store = VectorStore(mock_embed, dimensions=1536)

        doc_id = store.add_text("Test document", metadata={"key": "value"})
        doc = store.get_document(doc_id)

        assert doc is not None
        assert doc["text"] == "Test document"
        assert doc["metadata"]["key"] == "value"


class TestVectorSearch:
    """Test vector search functionality"""

    def test_vector_search_basic(self):
        """Test basic vector search"""
        from src.db.vector_store import VectorStore
        import numpy as np

        def mock_embed_fn(texts):
            # Return simple deterministic embeddings
            embeddings = []
            for t in texts:
                vec = np.zeros(5)
                if "apple" in t.lower():
                    vec[0] = 1.0
                elif "banana" in t.lower():
                    vec[1] = 1.0
                else:
                    vec[2] = 1.0
                embeddings.append(vec.tolist())
            return embeddings

        store = VectorStore(mock_embed_fn, dimensions=5)

        store.add_text("I love apples")
        store.add_text("I love bananas")
        store.add_text("I love cars")

        results = store.find_similar("apple", top_k=1)
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])