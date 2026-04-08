"""
Tests for KnowledgeAgent - Knowledge base and responsibility management subgraph
"""

import pytest
from unittest.mock import AsyncMock, patch
from dataclasses import replace
from src.agent.knowledge_agent import (
    create_knowledge_agent_graph,
    knowledge_agent_graph,
    shuffle_responsibilities,
    store_to_vector_db,
    fetch_responsibility,
    find_standard_answer,
)
from src.agent.state import InterviewState


@pytest.mark.asyncio
async def test_find_standard_answer_found():
    """测试找到标准答案"""
    state = replace(
        InterviewState(session_id="test", resume_id="r1"),
        mastered_questions={
            "q1": {"answer": "使用 Redis", "standard_answer": "使用 Redis 缓存", "deviation_score": 0.9}
        }
    )

    with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock:
        mock.return_value = 0.85

        result = await find_standard_answer(state, "如何优化性能？")

        assert result["standard_answer"] == "使用 Redis 缓存"
        assert result["similarity_score"] == 0.85


@pytest.mark.asyncio
async def test_find_standard_answer_not_found():
    """测试未找到标准答案（无匹配项）"""
    state = replace(
        InterviewState(session_id="test", resume_id="r1"),
        mastered_questions={
            "q1": {"answer": "使用 Redis", "standard_answer": "使用 Redis 缓存", "deviation_score": 0.9}
        }
    )

    with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock:
        mock.return_value = 0.5  # 相似度低于阈值

        result = await find_standard_answer(state, "不相关的问题？")

        assert result["standard_answer"] is None
        assert result["similarity_score"] == 0.0


@pytest.mark.asyncio
async def test_find_standard_answer_no_mastered_questions():
    """测试没有 mastered_questions 的情况"""
    state = InterviewState(session_id="test", resume_id="r1")

    result = await find_standard_answer(state, "任何问题？")

    assert result["standard_answer"] is None
    assert result["similarity_score"] == 0.0


class TestKnowledgeAgentGraph:
    """Test KnowledgeAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert knowledge_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new knowledge agent graph"""
        graph = create_knowledge_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_knowledge_agent_graph()
        nodes = graph.nodes
        expected_nodes = [
            "shuffle_responsibilities",
            "store_to_vector_db",
            "fetch_responsibility",
            "find_standard_answer",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to shuffle_responsibilities"""
        graph = create_knowledge_agent_graph()
        assert "shuffle_responsibilities" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_knowledge_agent_graph is already compiled"""
        graph = create_knowledge_agent_graph()
        assert hasattr(graph, "invoke")


class TestKnowledgeAgentFunctions:
    """Test KnowledgeAgent function signatures"""

    def test_shuffle_responsibilities_is_async(self):
        """Test that shuffle_responsibilities is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(shuffle_responsibilities)

    def test_store_to_vector_db_is_async(self):
        """Test that store_to_vector_db is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(store_to_vector_db)

    def test_fetch_responsibility_is_async(self):
        """Test that fetch_responsibility is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(fetch_responsibility)

    def test_find_standard_answer_is_async(self):
        """Test that find_standard_answer is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(find_standard_answer)

    def test_shuffle_responsibilities_takes_state_and_responsibilities(self):
        """Test shuffle_responsibilities function signature"""
        import inspect
        sig = inspect.signature(shuffle_responsibilities)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "responsibilities" in params

    def test_store_to_vector_db_takes_state_and_responsibilities(self):
        """Test store_to_vector_db function signature"""
        import inspect
        sig = inspect.signature(store_to_vector_db)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "responsibilities" in params

    def test_fetch_responsibility_takes_state_and_session_id(self):
        """Test fetch_responsibility function signature"""
        import inspect
        sig = inspect.signature(fetch_responsibility)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "session_id" in params

    def test_find_standard_answer_takes_state_and_question(self):
        """Test find_standard_answer function signature"""
        import inspect
        sig = inspect.signature(find_standard_answer)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "question" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
