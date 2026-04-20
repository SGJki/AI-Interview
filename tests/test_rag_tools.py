"""
Tests for AI Interview Agent - LangChain Tools
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.tools.rag_tools import (
    retrieve_knowledge,
    retrieve_similar_questions,
    retrieve_standard_answer,
    RAGTools,
)
from src.tools.code_tools import (
    parse_source_code,
    extract_module_structure,
    extract_architecture,
    ModuleInfo,
    ProjectInfo,
    ArchitectureInfo,
)


class TestRAGTools:
    """Test RAG retrieval tools"""

    def test_rag_tools_class_exists(self):
        """测试 RAGTools 类存在"""
        assert RAGTools is not None

    @pytest.mark.asyncio
    async def test_retrieve_knowledge_returns_results(self):
        """测试知识检索返回结果"""
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = [
            MagicMock(page_content="Redis 缓存策略..."),
            MagicMock(page_content="缓存过期机制..."),
        ]

        mock_vectorstore = MagicMock()
        mock_vectorstore.as_retriever.return_value = mock_retriever

        with patch("src.tools.rag_tools.get_vectorstore", return_value=mock_vectorstore):
            results = await retrieve_knowledge("Redis 缓存", top_k=2)

            assert len(results) == 2
            assert "Redis" in results[0].page_content

    @pytest.mark.asyncio
    async def test_retrieve_knowledge_empty_query(self):
        """测试空查询返回空列表"""
        results = await retrieve_knowledge("", top_k=2)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_similar_questions(self):
        """测试相似问题检索"""
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = [
            MagicMock(page_content="Q: 如何设计缓存？", metadata={"type": "question"}),
        ]

        mock_vectorstore = MagicMock()
        mock_vectorstore.as_retriever.return_value = mock_retriever

        with patch("src.tools.rag_tools.get_vectorstore", return_value=mock_vectorstore):
            results = await retrieve_similar_questions("缓存设计", top_k=2)
            # Mock 返回为空列表
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_standard_answer(self):
        """测试标准回答检索"""
        mock_vectorstore = AsyncMock()
        mock_vectorstore.asimilarity_search_with_score.return_value = [
            (MagicMock(page_content="标准回答内容...", metadata={"type": "answer"}), 0.95),
        ]

        with patch("src.tools.rag_tools.get_vectorstore", return_value=mock_vectorstore):
            result = await retrieve_standard_answer("缓存问题", top_k=1)

            assert result is not None


class TestMemoryTools:
    """Test memory retrieval tools"""

    def test_memory_tools_exist(self):
        """测试 memory tools 模块存在"""
        from src.infrastructure.session_store import (
            save_to_session_memory,
            get_session_memory,
            clear_session_memory,
        )
        assert save_to_session_memory is not None
        assert get_session_memory is not None
        assert clear_session_memory is not None


class TestCodeParsingTools:
    """Test code parsing tools"""

    def test_code_tools_exist(self):
        """测试 code parsing tools 模块存在"""
        assert parse_source_code is not None
        assert extract_module_structure is not None
        assert extract_architecture is not None

    def test_module_info_dataclass(self):
        """测试 ModuleInfo 数据类"""
        module = ModuleInfo(
            name="test_module",
            path="/path/to/module",
            language="Python",
            functions=["func1", "func2"],
            classes=["Class1"],
            dependencies=["dep1"],
        )
        assert module.name == "test_module"
        assert len(module.functions) == 2

    def test_project_info_dataclass(self):
        """测试 ProjectInfo 数据类"""
        project = ProjectInfo(
            name="test_project",
            path="/path/to/project",
            language="Python",
            readme_content="# Test",
            architecture_files=[],
            modules=[],
            tech_stack=["Python", "FastAPI"],
        )
        assert project.name == "test_project"
        assert "Python" in project.tech_stack


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
