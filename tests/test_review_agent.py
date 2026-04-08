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

    def test_check_evaluation_based_on_qa_is_function(self):
        """Test that _check_evaluation_based_on_qa is a regular function"""
        import asyncio
        assert not asyncio.iscoroutinefunction(_check_evaluation_based_on_qa)

    def test_check_standard_answer_fit_is_function(self):
        """Test that _check_standard_answer_fit is a regular function"""
        import asyncio
        assert not asyncio.iscoroutinefunction(_check_standard_answer_fit)


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

    def test_returns_true_todo_implementation(self):
        """Test that _check_evaluation_based_on_qa returns True (TODO implementation)"""
        result = _check_evaluation_based_on_qa(
            "什么是 Redis?",
            "Redis 是内存数据库",
            {"deviation_score": 0.8}
        )
        assert result is True


class TestCheckStandardAnswerFit:
    """Test _check_standard_answer_fit function"""

    def test_returns_true_todo_implementation(self):
        """Test that _check_standard_answer_fit returns True (TODO implementation)"""
        result = _check_standard_answer_fit(
            "什么是 Redis?",
            {"deviation_score": 0.8},
            "Redis 是一个内存数据库"
        )
        assert result is True

    def test_with_empty_standard_answer(self):
        """Test with empty standard answer"""
        result = _check_standard_answer_fit(
            "什么是 Redis?",
            {"deviation_score": 0.8},
            ""
        )
        assert result is True


@pytest.mark.asyncio
async def test_review_evaluation_pass():
    """测试审查通过 - 所有投票器通过"""
    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=0.8)},
        current_question=None
    )

    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }

    result = await review_evaluation(state, evaluation_result, standard_answer="使用 Redis 缓存")

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result
    # With deviation 0.8 (valid range), voter 1 passes
    # Voters 0 and 2 return True (TODO implementations)
    # At least 2 votes needed to pass, so this should pass
    assert result["review_passed"] is True
    assert len(result["review_failures"]) == 0


@pytest.mark.asyncio
async def test_review_evaluation_fail_invalid_score():
    """测试审查失败 - 评估分数无效"""
    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=1.5)},
        current_question=None
    )

    evaluation_result = {
        "deviation_score": 1.5,  # Invalid: > 1
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }

    result = await review_evaluation(state, evaluation_result, standard_answer="使用 Redis 缓存")

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result
    # Voter 1 (_check_evaluation_reasonableness) should fail due to invalid score
    # Voters 0 and 2 return True (TODO implementations)
    # 2 out of 3 passed, so overall should pass
    assert result["review_passed"] is True


@pytest.mark.asyncio
async def test_review_evaluation_no_standard_answer():
    """测试审查无标准答案"""
    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question_id="q_test",
        answers={"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=0.8)},
        current_question=None
    )

    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }

    result = await review_evaluation(state, evaluation_result, standard_answer=None)

    assert "review_passed" in result
    assert "review_failures" in result
    assert "failure_reasons" in result


@pytest.mark.asyncio
async def test_review_evaluation_with_current_question():
    """测试审查使用当前问题内容"""
    current_question = Question(
        content="请介绍一下 Redis",
        question_type=QuestionType.INITIAL,
        series=1,
        number=1
    )
    state = InterviewState(session_id="test", resume_id="r1")
    state = replace(state,
        current_question_id="q_test",
        current_question=current_question,
        answers={"q_test": Answer(question_id="q_test", content="Redis 是内存数据库", deviation_score=0.8)}
    )

    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答正确"],
        "suggestions": [],
    }

    result = await review_evaluation(state, evaluation_result, standard_answer="Redis 是一个内存数据库")

    assert "review_passed" in result
    assert result["review_passed"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
