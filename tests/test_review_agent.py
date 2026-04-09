"""
Tests for ReviewAgent - Review evaluation with 3-instance voting
"""

import pytest
from dataclasses import replace
from src.agent.review_agent import (
    review_evaluation,
    _check_evaluation_reasonableness,
    _check_evaluation_based_on_qa,
    _check_standard_answer_fit,
    create_review_agent_graph,
    review_agent_graph,
)
from src.agent.state import InterviewState, Answer, Question, QuestionType


class TestReviewAgentGraph:
    """Test ReviewAgent subgraph structure"""

    def test_graph_exists(self):
        """Test that the compiled graph exists"""
        assert review_agent_graph is not None

    def test_create_graph(self):
        """Test creating a new review agent graph"""
        graph = create_review_agent_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test graph contains the expected nodes"""
        graph = create_review_agent_graph()
        nodes = graph.nodes
        expected_nodes = ["review_evaluation"]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_graph_entry_point(self):
        """Test graph entry point is set to review_evaluation"""
        graph = create_review_agent_graph()
        assert "review_evaluation" in graph.nodes

    def test_graph_is_compiled(self):
        """Test that the graph returned from create_review_agent_graph is already compiled"""
        graph = create_review_agent_graph()
        assert hasattr(graph, "invoke")


class TestReviewAgentFunctions:
    """Test ReviewAgent function signatures"""

    def test_review_evaluation_is_async(self):
        """Test that review_evaluation is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(review_evaluation)

    def test_check_evaluation_reasonableness_is_function(self):
        """Test that _check_evaluation_reasonableness is a regular function"""
        import asyncio
        assert not asyncio.iscoroutinefunction(_check_evaluation_reasonableness)

    def test_check_evaluation_based_on_qa_is_async_function(self):
        """Test that _check_evaluation_based_on_qa is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(_check_evaluation_based_on_qa)

    def test_check_standard_answer_fit_is_async_function(self):
        """Test that _check_standard_answer_fit is an async function"""
        import asyncio
        assert asyncio.iscoroutinefunction(_check_standard_answer_fit)


class TestCheckEvaluationReasonableness:
    """Test _check_evaluation_reasonableness function"""

    def test_valid_score_0(self):
        """Test evaluation with deviation_score of 0"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": 0.0}
        )
        assert result is True

    def test_valid_score_05(self):
        """Test evaluation with deviation_score of 0.5"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": 0.5}
        )
        assert result is True

    def test_valid_score_1(self):
        """Test evaluation with deviation_score of 1.0"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": 1.0}
        )
        assert result is True

    def test_invalid_score_negative(self):
        """Test evaluation with negative deviation_score"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": -0.1}
        )
        assert result is False

    def test_invalid_score_above_1(self):
        """Test evaluation with deviation_score above 1"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": 1.5}
        )
        assert result is False

    def test_missing_deviation_score_defaults_to_valid(self):
        """Test evaluation with missing deviation_score defaults to 0.5"""
        result = _check_evaluation_reasonableness(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {}
        )
        assert result is True


class TestCheckEvaluationBasedOnQa:
    """Test _check_evaluation_based_on_qa function"""

    @pytest.mark.asyncio
    async def test_returns_true_with_yes_response(self):
        """Test that _check_evaluation_based_on_qa returns True when LLM returns YES"""
        from unittest.mock import AsyncMock, patch

        with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock:
            mock.return_value = "YES, the evaluation is based on Q&A"

            result = await _check_evaluation_based_on_qa(
                "什么是 Redis?",
                "Redis 是内存数据库",
                {"deviation_score": 0.8}
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_with_no_response(self):
        """Test that _check_evaluation_based_on_qa returns False when LLM returns NO"""
        from unittest.mock import AsyncMock, patch

        with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock:
            mock.return_value = "NO, the evaluation is not based on Q&A"

            result = await _check_evaluation_based_on_qa(
                "什么是 Redis?",
                "Redis 是内存数据库",
                {"deviation_score": 0.8}
            )
            assert result is False


@pytest.mark.asyncio
async def test_check_evaluation_based_on_qa_llm_true():
    """测试 LLM 判断评估基于 QA 返回 YES"""
    from unittest.mock import AsyncMock, patch

    # Patch the invoke_llm function in the review_agent module where it's imported
    with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock:
        mock.return_value = "YES, the evaluation is based on Q&A"

        result = await _check_evaluation_based_on_qa(
            question="What is Redis?",
            user_answer="Redis is an in-memory database",
            evaluation={"deviation_score": 0.8}
        )
        assert result is True
        mock.assert_awaited_once()
        # Verify the prompt was formatted correctly
        call_args = mock.call_args
        assert "what is redis" in call_args.kwargs["user_prompt"].lower()


class TestCheckStandardAnswerFit:
    """Test _check_standard_answer_fit function"""

    @pytest.mark.asyncio
    async def test_returns_true_todo_implementation(self):
        """Test that _check_standard_answer_fit returns True when similarity is high"""
        from unittest.mock import AsyncMock, patch

        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock:
            mock.return_value = 0.9  # high similarity
            result = await _check_standard_answer_fit(
                "什么是 Redis?",
                {"deviation_score": 0.8},
                "Redis 是一个内存数据库"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_with_empty_standard_answer(self):
        """Test with empty standard answer"""
        result = await _check_standard_answer_fit(
            "什么是 Redis?",
            {"deviation_score": 0.8},
            ""
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_standard_answer_fit_below_threshold(self):
        """测试语义相似度低于阈值返回 False"""
        from unittest.mock import AsyncMock, patch

        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock:
            mock.return_value = 0.5  # below 0.7 threshold

            result = await _check_standard_answer_fit(
                question="What is Redis?",
                evaluation={},
                standard_answer="Redis is a caching system"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_standard_answer_fit_above_threshold(self):
        """测试语义相似度高于阈值返回 True"""
        from unittest.mock import AsyncMock, patch

        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock:
            mock.return_value = 0.8  # above 0.7 threshold

            result = await _check_standard_answer_fit(
                question="What is Redis?",
                evaluation={},
                standard_answer="Redis is an in-memory database for caching"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_check_standard_answer_fit_no_standard_answer(self):
        """测试无标准答案时返回 True"""
        result = await _check_standard_answer_fit(
            question="What is Redis?",
            evaluation={},
            standard_answer=None
        )
        assert result is True


@pytest.mark.asyncio
async def test_review_evaluation_pass():
    """测试审查通过 - 所有投票器通过"""
    from unittest.mock import AsyncMock, patch

    state = InterviewState(session_id="test", resume_id="r1")
    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=0.8)},
        evaluation_results={"q_test": evaluation_result},
        mastered_questions={"q_test": {"standard_answer": "使用 Redis 缓存"}},
        current_question=None
    )

    # Mock both invoke_llm and compute_similarity
    with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "YES"
        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock_sim:
            mock_sim.return_value = 0.9  # high similarity
            result = await review_evaluation(state)

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result
    # With deviation 0.8 (valid range), voter 1 passes
    # Voter 0 (LLM) returns YES, voter 2 (similarity) returns True with high similarity
    # At least 2 votes needed to pass, so this should pass
    assert result["review_passed"] is True
    assert len(result["review_failures"]) == 0


@pytest.mark.asyncio
async def test_review_evaluation_fail_invalid_score():
    """测试审查失败 - 评估分数无效"""
    from unittest.mock import AsyncMock, patch

    state = InterviewState(session_id="test", resume_id="r1")
    evaluation_result = {
        "deviation_score": 1.5,  # Invalid: > 1
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=1.5)},
        evaluation_results={"q_test": evaluation_result},
        mastered_questions={"q_test": {"standard_answer": "使用 Redis 缓存"}},
        current_question=None
    )

    # Mock the LLM call to return YES (voter 0 passes) and similarity (voter 2 passes)
    with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "YES"
        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock_sim:
            mock_sim.return_value = 0.9
            result = await review_evaluation(state)

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result
    # Voter 1 (_check_evaluation_reasonableness) should fail due to invalid score
    # Voter 0 (LLM check) passes with YES
    # Voter 2 (standard answer fit) passes
    # 2 out of 3 passed, so overall should pass
    assert result["review_passed"] is True


@pytest.mark.asyncio
async def test_review_evaluation_no_standard_answer():
    """测试审查无标准答案"""
    state = InterviewState(session_id="test", resume_id="r1")
    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=0.8)},
        evaluation_results={"q_test": evaluation_result},
        current_question=None
    )

    result = await review_evaluation(state)

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result


@pytest.mark.asyncio
async def test_review_evaluation_with_current_question():
    """测试审查使用当前问题内容"""
    from unittest.mock import AsyncMock, patch

    current_question = Question(
        content="请介绍一下 Redis",
        question_type=QuestionType.INITIAL,
        series=1,
        number=1
    )
    state = InterviewState(session_id="test", resume_id="r1")
    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答正确"],
        "suggestions": [],
    }
    state = replace(state,
        current_question_id="q_test",
        current_question=current_question,
        answers={"q_test": Answer(question_id="q_test", content="Redis 是内存数据库", deviation_score=0.8)},
        evaluation_results={"q_test": evaluation_result},
        mastered_questions={"q_test": {"standard_answer": "Redis 是一个内存数据库"}},
    )

    # Mock both invoke_llm and compute_similarity
    with patch('src.agent.review_agent.invoke_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "YES"
        with patch('src.services.embedding_service.compute_similarity', new_callable=AsyncMock) as mock_sim:
            mock_sim.return_value = 0.9
            result = await review_evaluation(state)

    assert "review_passed" in result
    assert result["review_passed"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
