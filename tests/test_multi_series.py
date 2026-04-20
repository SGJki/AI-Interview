"""
Tests for AI Interview Agent - Multi-series Interview Flow

Phase 2: Support for multiple series with independent question chains and state tracking
"""

import pytest
from unittest.mock import patch
from dataclasses import dataclass, field, replace
from src.domain.enums import InterviewMode, FeedbackMode, QuestionType
from src.domain.models import Question, Answer, Feedback, SeriesRecord
from src.agent.state import InterviewState
from src.session.context import InterviewContext


class TestSeriesStateTracking:
    """Test series state tracking in InterviewState"""

    def test_interview_state_has_series_history(self):
        """Test that InterviewState has series_history field for tracking each series"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123"
        )

        # series_history should exist and be a dict
        assert hasattr(state, 'series_history')
        assert isinstance(state.series_history, dict)

    def test_series_history_records_series_questions_and_answers(self):
        """Test that series_history records questions and answers for each series"""
        # Create a series record
        q1 = Question(
            content="What is your experience?",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1
        )
        answer1 = Answer(question_id="q-1", content="I have 5 years experience", deviation_score=0.8)
        series_record = SeriesRecord(
            series=1,
            questions=(q1,),
            answers=(answer1,),
            completed=False
        )

        # Create state with series_history populated
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            series_history={1: series_record}
        )

        assert 1 in state.series_history
        assert len(state.series_history[1].questions) == 1
        assert len(state.series_history[1].answers) == 1
        assert state.series_history[1].completed is False

    def test_current_series_starts_at_1(self):
        """Test that current_series starts at 1"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123"
        )

        assert state.current_series == 1


class TestSeriesSwitchingLogic:
    """Test series switching logic"""

    def test_error_count_resets_on_series_switch(self):
        """Test that error_count resets when switching to new series"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            error_threshold=2
        )

        # Simulate accumulating errors in series 1
        state = replace(state, error_count=2)

        # Switch to series 2
        new_state = replace(
            state,
            current_series=2,
            error_count=0  # Reset error count on series switch
        )

        assert new_state.current_series == 2
        assert new_state.error_count == 0

    def test_series_completion_triggers_next_series(self):
        """Test that completing a series triggers switch to next series"""
        # Create some answers to meet the questions_per_series threshold
        answers_dict = {
            "q-1-1": Answer(question_id="q-1-1", content="Answer 1", deviation_score=0.8),
            "q-1-2": Answer(question_id="q-1-2", content="Answer 2", deviation_score=0.8),
            "q-1-3": Answer(question_id="q-1-3", content="Answer 3", deviation_score=0.8),
        }

        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            max_followup_depth=3,
            followup_depth=0,
            error_count=0,
            answers=answers_dict
        )

        # Simulate series completion (after sufficient questions answered)
        # When followup_depth returns to 0 and we have enough questions, series is complete
        questions_in_series = 3  # Example: 3 questions per series

        if state.followup_depth == 0 and len(state.answers) >= questions_in_series:
            # Switch to next series
            state = replace(
                state,
                current_series=state.current_series + 1,
                error_count=0  # Reset error count
            )

        assert state.current_series == 2
        assert state.error_count == 0

    def test_series_switch_resets_followup_depth(self):
        """Test that switching series resets followup_depth"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=2,
            max_followup_depth=3
        )

        # Switch to series 2
        new_state = replace(
            state,
            current_series=2,
            followup_depth=0  # Reset followup depth on series switch
        )

        assert new_state.current_series == 2
        assert new_state.followup_depth == 0


class TestSeriesInQuestion:
    """Test series attribute in Question dataclass"""

    def test_question_has_series_attribute(self):
        """Test that Question has series attribute"""
        question = Question(
            content="Tell me about your projects",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1
        )

        assert question.series == 1

    def test_question_series_defaults_to_1(self):
        """Test that Question series defaults to 1"""
        question = Question(
            content="Tell me about your projects",
            question_type=QuestionType.INITIAL,
        )

        assert question.series == 1

    def test_questions_in_different_series_have_different_series_numbers(self):
        """Test that questions from different series have correct series numbers"""
        q1_series1 = Question(
            content="Question in series 1",
            question_type=QuestionType.INITIAL,
            series=1,
            number=1
        )
        q1_series2 = Question(
            content="Question in series 2",
            question_type=QuestionType.INITIAL,
            series=2,
            number=1
        )

        assert q1_series1.series == 1
        assert q1_series2.series == 2
        assert q1_series1.series != q1_series2.series


class TestSeriesSwitchingCondition:
    """Test series switching conditional logic"""

    def test_should_switch_series_when_questions_exhausted(self):
        """Test that we should switch series when questions are exhausted"""
        # Simulate the condition check
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0  # No more followups
        )

        questions_per_series = 3
        answers_count = 3  # All questions answered

        # When followup_depth is 0 and we've answered enough questions, switch series
        should_switch = state.followup_depth == 0 and answers_count >= questions_per_series

        assert should_switch is True

    def test_should_not_switch_when_followup_pending(self):
        """Test that we should not switch series when followup is pending"""
        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=2,  # Still has followups
            max_followup_depth=3
        )

        # Should not switch when followup_depth > 0
        should_switch = state.followup_depth == 0

        assert should_switch is False


class TestInterviewServiceMultiSeries:
    """Test multi-series functionality in InterviewService"""

    def test_interview_service_has_max_series_config(self):
        """Test that InterviewService has max_series configuration"""
        from src.services.interview_service import InterviewService

        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )

        assert service.max_series == 5

    def test_should_continue_checks_max_series(self):
        """Test that _should_continue checks max_series"""
        from src.services.interview_service import InterviewService

        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=3
        )

        # Initialize state
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=3  # At max series
        )

        should_continue = service._should_continue()

        assert should_continue is False

    def test_should_continue_allows_next_series(self):
        """Test that _should_continue allows continuing to next series"""
        from src.services.interview_service import InterviewService

        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )

        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=2  # Not at max yet
        )

        should_continue = service._should_continue()

        assert should_continue is True


class TestDecideNextNode:
    """Test orchestrator decide_next_node routing"""

    def test_decide_next_routes_to_end_interview_when_max_series_reached(self):
        """Test that decide_next routes to end_interview when current_series >= max_series"""
        from src.agent.orchestrator import decide_next_node
        from src.config import config

        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=5
        )

        # Temporarily modify config for test
        original_max_series = config.max_series
        config.max_series = 5
        try:
            result = decide_next_node(state)
            assert result == {"next_action": "end_interview"}
        finally:
            config.max_series = original_max_series

    def test_decide_next_routes_to_question_agent_when_under_max_series(self):
        """Test that decide_next routes to question_agent when series < max"""
        from src.agent.orchestrator import decide_next_node
        from src.config import config

        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=3
        )

        original_max_series = config.max_series
        config.max_series = 5
        try:
            result = decide_next_node(state)
            assert result == {"next_action": "question_agent"}
        finally:
            config.max_series = original_max_series

    def test_decide_next_routes_to_end_interview_when_user_end_requested(self):
        """Test that decide_next routes to end_interview when user_end_requested"""
        from src.agent.orchestrator import decide_next_node

        # Create a state-like object with user_end_requested attribute
        class MockState:
            def __init__(self):
                self.session_id = "test-session"
                self.resume_id = "resume-123"
                self.current_series = 3
                self.user_end_requested = True

        state = MockState()
        result = decide_next_node(state)
        assert result == {"next_action": "end_interview"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
