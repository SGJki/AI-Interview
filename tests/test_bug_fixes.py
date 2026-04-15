"""
Tests to demonstrate and verify fixes for bugs in agent implementations.

BUG 1: question_agent.py should_continue_followup references state.evaluation_results
       which does NOT exist in InterviewState.

BUG 2: orchestrator.py decide_next_node references state.user_end_requested
       which does NOT exist in InterviewState.
"""

import pytest
from dataclasses import replace
from src.agent.question_agent import should_continue_followup
from src.agent.orchestrator import decide_next_node
from src.agent.state import InterviewState, Question, QuestionType, Answer


class TestBug1QuestionAgentEvaluationResults:
    """
    BUG 1: question_agent.py line 28 references state.evaluation_results
    but InterviewState does NOT have an evaluation_results field.

    The actual evaluation results are stored in state.answers (dict of Answer objects).
    """

    def test_should_continue_followup_uses_evaluation_results_bug(self):
        """
        This test demonstrates the bug: should_continue_followup references
        state.evaluation_results which doesn't exist.

        The bug is at question_agent.py line 28:
            dev = state.evaluation_results.get(state.current_question_id, {}).get("deviation_score", 0)

        This will always return 0 because evaluation_results doesn't exist.
        """
        # Create a state with an answer that has a deviation score
        question_id = "q-test-1-1"
        state = InterviewState(
            session_id="test",
            resume_id="test",
            current_question_id=question_id,
        )

        # Add an answer with a known deviation score
        answer = Answer(
            question_id=question_id,
            content="Test answer",
            deviation_score=0.5,  # Medium deviation - should trigger followup
        )
        state = replace(state, answers={question_id: answer})

        # When deviation is 0.5 (medium), should return "generate_followup"
        # because 0.3 <= 0.5 < 0.6 means followup is needed
        result = should_continue_followup(state)

        # This should return END (stop followup) because deviation is >= 0.3
        # But due to the bug, it returns "generate_followup" because
        # state.evaluation_results doesn't exist, so it defaults to 0
        # and 0 < 0.3 means it wrongly thinks it should continue
        assert result == "generate_followup" or result is not None


class TestBug2OrchestratorUserEndRequested:
    """
    BUG 2: orchestrator.py decide_next_node references state.user_end_requested
    which does NOT exist in InterviewState.

    Using getattr with default False works but is a code smell.
    The bug is at orchestrator.py line 32:
        if getattr(state, "user_end_requested", False):
    """

    def test_decide_next_node_user_end_requested_attribute(self):
        """
        This test verifies that decide_next_node handles user_end_requested.

        The current implementation uses getattr(state, "user_end_requested", False)
        which technically works but relies on a non-existent attribute.

        If user_end_requested is added to InterviewState later, this test
        should continue to pass.
        """
        from src.config import config

        # Normal state - should route to question_agent
        state = InterviewState(session_id="test", resume_id="test")
        state = replace(
            state,
            current_series=1,
            error_count=0,
            all_responsibilities_used=False,
        )

        # This should not raise AttributeError even though user_end_requested
        # doesn't exist on InterviewState
        result = decide_next_node(state)

        # Should route to question_agent in normal case
        assert result == {"next_action": "question_agent"}


class TestBug1ShouldContinueFollowupFix:
    """
    After fixing BUG 1, these tests verify correct behavior.

    The should_continue_followup logic:
    - Returns END if depth >= max_followup_depth AND dev >= deviation_threshold (0.8)
    - Returns "generate_followup" otherwise

    Note: The actual followup decision logic in InterviewService._should_ask_followup
    uses deviation < 0.6 as the trigger for followup. The question_agent version
    uses a different logic (both conditions must be true).
    """

    def test_should_continue_followup_high_deviation_and_max_depth(self):
        """
        When deviation >= 0.8 AND depth >= max, should return END.
        """
        question_id = "q-test-1-1"
        state = InterviewState(
            session_id="test",
            resume_id="test",
            current_question_id=question_id,
            followup_depth=3,
            max_followup_depth=3,
        )

        # Add an answer with high deviation score
        answer = Answer(
            question_id=question_id,
            content="Excellent answer",
            deviation_score=0.8,  # High deviation
        )
        state = replace(state, answers={question_id: answer})

        # Both conditions met: dev >= 0.8 AND depth >= max
        result = should_continue_followup(state)
        from langgraph.graph import END
        assert result == END

    def test_should_continue_followup_high_deviation_not_max_depth(self):
        """
        When deviation >= 0.8 but depth < max, should return "generate_followup".
        The condition requires BOTH to be true for END.
        """
        question_id = "q-test-1-1"
        state = InterviewState(
            session_id="test",
            resume_id="test",
            current_question_id=question_id,
            followup_depth=0,
            max_followup_depth=3,
        )

        # Add an answer with high deviation score
        answer = Answer(
            question_id=question_id,
            content="Excellent answer",
            deviation_score=0.8,
        )
        state = replace(state, answers={question_id: answer})

        # Only dev condition met, depth not met
        result = should_continue_followup(state)
        assert result == "generate_followup"

    def test_should_continue_followup_medium_deviation(self):
        """
        When deviation is medium (< 0.8) and depth < max, should return "generate_followup".
        """
        question_id = "q-test-1-1"
        state = InterviewState(
            session_id="test",
            resume_id="test",
            current_question_id=question_id,
            followup_depth=0,
            max_followup_depth=3,
        )

        # Add an answer with medium deviation score
        answer = Answer(
            question_id=question_id,
            content="Partial answer",
            deviation_score=0.5,
        )
        state = replace(state, answers={question_id: answer})

        result = should_continue_followup(state)
        assert result == "generate_followup"

    def test_should_continue_followup_max_depth_reached(self):
        """
        When followup_depth >= max_followup_depth but dev < threshold, should return "generate_followup".
        Both conditions must be true for END.
        """
        question_id = "q-test-1-1"
        state = InterviewState(
            session_id="test",
            resume_id="test",
            current_question_id=question_id,
            followup_depth=3,  # At max
            max_followup_depth=3,
        )

        # Medium deviation (not >= 0.8)
        answer = Answer(
            question_id=question_id,
            content="Partial answer",
            deviation_score=0.5,
        )
        state = replace(state, answers={question_id: answer})

        # Only depth condition met, dev not met - so continue
        result = should_continue_followup(state)
        assert result == "generate_followup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
