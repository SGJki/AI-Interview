"""
Tests for KnowledgeBaseService

Complete coverage for knowledge_base_service.py (0% -> target 80%+)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.documents import Document

from src.services.knowledge_base_service import KnowledgeBaseService


class TestKnowledgeBaseServiceInit:
    """Test KnowledgeBaseService initialization"""

    def test_init_with_default_directory(self):
        """Test initialization with default persist_directory"""
        service = KnowledgeBaseService()
        assert service.persist_directory == "./data/vectorstore"

    def test_init_with_custom_directory(self):
        """Test initialization with custom persist_directory"""
        service = KnowledgeBaseService(persist_directory="/custom/path")
        assert service.persist_directory == "/custom/path"


class TestBuildFromResume:
    """Test build_from_resume method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_build_from_resume_success(self, service):
        """Test successful resume knowledge base building"""
        resume_content = """
        Name: John Doe
        Skills: Python, JavaScript, React
        Experience:
          - Company: TechCorp
            Position: Senior Developer
            Highlights: Built microservices architecture
        Projects:
          - Name: E-commerce Platform
            Technologies: Python, Django, PostgreSQL
            Highlights: Handled 10k+ concurrent users
        """

        mock_result_text = '''{
            "skills": ["Python", "JavaScript", "React"],
            "projects": [
                {
                    "name": "E-commerce Platform",
                    "description": "Built with Django",
                    "technologies": ["Python", "Django", "PostgreSQL"],
                    "highlights": ["Handled 10k+ users"]
                }
            ],
            "experience": [
                {
                    "company": "TechCorp",
                    "position": "Senior Developer",
                    "duration": "2020-2024",
                    "highlights": ["Built microservices"]
                }
            ]
        }'''

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock()
            result = await service.build_from_resume(resume_content, "resume-123")

        assert result["status"] == "success"
        assert result["resume_id"] == "resume-123"
        assert result["skills_count"] == 3
        assert result["projects_count"] == 1
        assert result["experience_count"] == 1
        assert result["documents_added"] == 4  # 1 raw + 1 skills + 1 projects + 1 experience

    @pytest.mark.asyncio
    async def test_build_from_resume_json_decode_error(self, service):
        """Test handling of JSON decode error"""
        resume_content = "Invalid resume content"

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value="not valid json{{{"):

            result = await service.build_from_resume(resume_content, "resume-123")

        assert result["status"] == "error"
        assert "简历解析失败" in result["error"]

    @pytest.mark.asyncio
    async def test_build_from_resume_with_no_skills(self, service):
        """Test building with no skills in resume"""
        resume_content = "Minimal resume"

        mock_result_text = '{"skills": [], "projects": [], "experience": []}'

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock()
            result = await service.build_from_resume(resume_content, "resume-456")

        assert result["status"] == "success"
        assert result["skills_count"] == 0
        assert result["documents_added"] == 1  # Only raw resume

    @pytest.mark.asyncio
    async def test_build_from_resume_with_multiple_projects(self, service):
        """Test building with multiple projects"""
        resume_content = "Resume with projects"

        mock_result_text = '''{
            "skills": ["Python"],
            "projects": [
                {"name": "Project1", "description": "D1", "technologies": ["T1"], "highlights": ["H1"]},
                {"name": "Project2", "description": "D2", "technologies": ["T2"], "highlights": ["H2"]}
            ],
            "experience": []
        }'''

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock()
            result = await service.build_from_resume(resume_content, "resume-789")

        assert result["status"] == "success"
        assert result["projects_count"] == 2
        assert result["documents_added"] == 4  # raw + skills + 2 projects

    @pytest.mark.asyncio
    async def test_build_from_resume_general_exception(self, service):
        """Test handling of general exception"""
        resume_content = "Resume content"

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   side_effect=Exception("LLM error")):

            result = await service.build_from_resume(resume_content, "resume-123")

        assert result["status"] == "error"
        assert "知识库构建失败" in result["error"]


class TestBuildPresetQuestionBank:
    """Test build_preset_question_bank method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_build_preset_question_bank_success(self, service):
        """Test successful preset question bank building"""
        mock_questions = '["问题1", "问题2", "问题3"]'

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_questions), \
             patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.build_preset_question_bank()

        assert result["status"] == "success"
        assert result["category_count"] == 8
        assert result["questions_added"] > 0

    @pytest.mark.asyncio
    async def test_build_preset_question_bank_partial_failure(self, service):
        """Test handles partial failures gracefully"""
        call_count = [0]

        async def mock_invoke(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return '["问题1", "问题2"]'
            raise Exception("LLM error")

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   side_effect=mock_invoke), \
             patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.build_preset_question_bank()

        # Should still return success with partial results
        assert result["status"] == "success"
        assert result["questions_added"] > 0


class TestBuildStandardAnswerKb:
    """Test build_standard_answer_kb method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_build_standard_answer_kb_success(self, service):
        """Test successful standard answer knowledge base building"""
        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.build_standard_answer_kb()

        assert result["status"] == "success"
        assert result["qa_pairs_added"] == 3

    @pytest.mark.asyncio
    async def test_build_standard_answer_kb_handles_errors(self, service):
        """Test handles errors gracefully"""
        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock,
                   side_effect=Exception("DB error")):

            result = await service.build_standard_answer_kb()

        # Should continue despite errors
        assert result["status"] == "success"


class TestBuildSkillPointKb:
    """Test build_skill_point_kb method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_build_skill_point_kb_success(self, service):
        """Test successful skill point knowledge base building"""
        skill_points = ["Python编程", "数据库设计", "微服务架构"]

        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.build_skill_point_kb(skill_points)

        assert result["status"] == "success"
        assert result["skill_points_added"] == 3

    @pytest.mark.asyncio
    async def test_build_skill_point_kb_empty_list(self, service):
        """Test with empty skill points list"""
        result = await service.build_skill_point_kb([])

        assert result["status"] == "success"
        assert result["skill_points_added"] == 0

    @pytest.mark.asyncio
    async def test_build_skill_point_kb_handles_errors(self, service):
        """Test handles errors gracefully"""
        skill_points = ["Python", "JavaScript"]

        async def mock_add(*args, **kwargs):
            if "Python" in str(args):
                raise Exception("Add error")
            return None

        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock,
                   side_effect=mock_add):

            result = await service.build_skill_point_kb(skill_points)

        # Should continue despite errors
        assert result["status"] == "success"


class TestAddDocument:
    """Test add_document method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_add_document_success(self, service):
        """Test successful document addition"""
        metadata = {"type": "test", "source": "unit_test"}

        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.add_document(
                content="Test document content",
                metadata=metadata,
            )

        assert result["status"] == "success"
        assert "Test document" in result["content"]

    @pytest.mark.asyncio
    async def test_add_document_error(self, service):
        """Test document addition error handling"""
        with patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock,
                   side_effect=Exception("Vectorstore error")):

            result = await service.add_document(
                content="Test content",
                metadata={},
            )

        assert result["status"] == "error"
        assert "Vectorstore error" in result["error"]


class TestBuildAll:
    """Test build_all method"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_build_all_success(self, service):
        """Test successful build all"""
        with patch.object(service, 'build_preset_question_bank', new_callable=AsyncMock,
                          return_value={"status": "success", "questions_added": 10}), \
             patch.object(service, 'build_standard_answer_kb', new_callable=AsyncMock,
                          return_value={"status": "success", "qa_pairs_added": 3}):

            result = await service.build_all()

        assert "question_bank" in result
        assert "standard_answers" in result


class TestDocumentMetadata:
    """Test document metadata structure"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_raw_resume_document_metadata(self, service):
        """Test raw resume document has correct metadata"""
        resume_content = "Test resume"

        mock_result_text = '{"skills": [], "projects": [], "experience": []}'

        captured_docs = []

        def capture_add(documents):
            captured_docs.extend(documents)

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock(side_effect=capture_add)
            await service.build_from_resume(resume_content, "resume-123")

        # First document should be raw resume
        raw_doc = captured_docs[0]
        assert raw_doc.metadata["type"] == "raw_resume"
        assert raw_doc.metadata["resume_id"] == "resume-123"

    @pytest.mark.asyncio
    async def test_skills_document_metadata(self, service):
        """Test skills document has correct metadata"""
        resume_content = "Test resume"

        mock_result_text = '{"skills": ["Python", "JavaScript"], "projects": [], "experience": []}'

        captured_docs = []

        def capture_add(documents):
            captured_docs.extend(documents)

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock(side_effect=capture_add)
            await service.build_from_resume(resume_content, "resume-123")

        # Find skills document
        skill_doc = next((d for d in captured_docs if d.metadata.get("type") == "skills"), None)
        assert skill_doc is not None
        assert skill_doc.metadata["resume_id"] == "resume-123"

    @pytest.mark.asyncio
    async def test_project_document_metadata(self, service):
        """Test project document has correct metadata"""
        resume_content = "Test resume"

        mock_result_text = '''{
            "skills": [],
            "projects": [{"name": "Proj1", "description": "D1", "technologies": ["T1"], "highlights": ["H1"]}],
            "experience": []
        }'''

        captured_docs = []

        def capture_add(documents):
            captured_docs.extend(documents)

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock(side_effect=capture_add)
            await service.build_from_resume(resume_content, "resume-123")

        # Find project document
        project_doc = next((d for d in captured_docs if d.metadata.get("type") == "project"), None)
        assert project_doc is not None
        assert project_doc.metadata["resume_id"] == "resume-123"

    @pytest.mark.asyncio
    async def test_experience_document_metadata(self, service):
        """Test experience document has correct metadata"""
        resume_content = "Test resume"

        mock_result_text = '''{
            "skills": [],
            "projects": [],
            "experience": [{"company": "Corp", "position": "Dev", "duration": "2020-2024", "highlights": ["H1"]}]
        }'''

        captured_docs = []

        def capture_add(documents):
            captured_docs.extend(documents)

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock(side_effect=capture_add)
            await service.build_from_resume(resume_content, "resume-123")

        # Find experience document
        exp_doc = next((d for d in captured_docs if d.metadata.get("type") == "experience"), None)
        assert exp_doc is not None
        assert exp_doc.metadata["resume_id"] == "resume-123"


class TestQuestionBankSkillCategories:
    """Test question bank builds for all skill categories"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_all_skill_categories_processed(self, service):
        """Test all 8 skill categories are processed"""
        call_count = [0]

        async def mock_invoke(*args, **kwargs):
            call_count[0] += 1
            return '["问题1"]'

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   side_effect=mock_invoke), \
             patch('src.services.knowledge_base_service.add_to_knowledge_base', new_callable=AsyncMock):

            result = await service.build_preset_question_bank()

        # Should have called LLM for each skill category
        assert call_count[0] == 8
        assert result["category_count"] == 8


class TestBuildFromResumeEdgeCases:
    """Test edge cases for build_from_resume"""

    @pytest.fixture
    def service(self):
        return KnowledgeBaseService(persist_directory="./test_vectorstore")

    @pytest.mark.asyncio
    async def test_handles_missing_project_fields(self, service):
        """Test handles missing optional project fields"""
        resume_content = "Resume"

        mock_result_text = '''{
            "skills": [],
            "projects": [{"name": "Proj1"}],
            "experience": []
        }'''

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock()
            result = await service.build_from_resume(resume_content, "resume-123")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handles_missing_experience_fields(self, service):
        """Test handles missing optional experience fields"""
        resume_content = "Resume"

        mock_result_text = '''{
            "skills": [],
            "projects": [],
            "experience": [{"company": "Corp"}]
        }'''

        with patch('src.services.knowledge_base_service.invoke_llm', new_callable=AsyncMock,
                   return_value=mock_result_text), \
             patch('src.services.knowledge_base_service.get_vectorstore') as mock_vs:

            mock_vs.return_value.add_documents = MagicMock()
            result = await service.build_from_resume(resume_content, "resume-123")

        assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
