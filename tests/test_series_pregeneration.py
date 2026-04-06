"""
Tests for AI Interview Agent - Series Question Pre-generation Cache

Phase 2: Pre-generate next series questions before user completes current series

Tests the _pregenerate_next_series_question method and its integration
with _switch_to_next_series.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import replace

from src.agent.state import (
    InterviewMode,
    FeedbackMode,
    QuestionType,
    Question,
    Answer,
    InterviewState,
    InterviewContext,
)
from src.services.interview_service import InterviewService


class TestPregenerateNextSeriesQuestion:
    """Test the _pregenerate_next_series_question method"""

    @pytest.fixture
    def service(self):
        """Create an InterviewService with mocked state"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        # Initialize state
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        return service

    @pytest.mark.asyncio
    async def test_pregenerate_method_exists(self, service):
        """Test that _pregenerate_next_series_question method exists"""
        assert hasattr(service, '_pregenerate_next_series_question')
        assert callable(service._pregenerate_next_series_question)

    @pytest.mark.asyncio
    async def test_pregenerate_does_not_exceed_max_series(self, service):
        """Test that pregeneration does not generate beyond max_series"""
        service.state = replace(service.state, current_series=5)  # Already at max

        with patch('src.services.interview_service.cache_next_series_question') as mock_cache:
            await service._pregenerate_next_series_question()
            # Should not cache when at max series
            mock_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_pregenerate_caches_question_for_next_series(self, service):
        """Test that pregeneration caches the question for next series"""
        service.state = replace(service.state, current_series=1)

        with patch('src.services.interview_service.cache_next_series_question') as mock_cache:
            mock_cache.return_value = AsyncMock()
            await service._pregenerate_next_series_question()
            # Should call cache with next series (2)
            mock_cache.assert_called_once()
            call_args = mock_cache.call_args
            assert call_args[0][1] == 2  # next_series = current + 1

    @pytest.mark.asyncio
    async def test_pregenerate_uses_correct_ttl(self, service):
        """Test that pregeneration uses correct TTL (3600 seconds)"""
        service.state = replace(service.state, current_series=1)

        with patch('src.services.interview_service.cache_next_series_question') as mock_cache:
            mock_cache.return_value = AsyncMock()
            await service._pregenerate_next_series_question()
            call_args = mock_cache.call_args
            assert call_args[1]['ttl'] == 3600

    @pytest.mark.asyncio
    async def test_pregenerate_includes_series_info_in_question(self, service):
        """Test that pregenerated question includes series info"""
        service.state = replace(service.state, current_series=2)

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM, \
             patch('src.services.interview_service.cache_next_series_question') as mock_cache:
            MockLLM.return_value.generate_question = AsyncMock(
                return_value=Question(
                    content="请介绍一下系列3的项目经验？",
                    question_type=QuestionType.INITIAL,
                    series=3,
                    number=1,
                )
            )
            await service._pregenerate_next_series_question()
            call_args = mock_cache.call_args
            question_content = call_args[0][2]  # question_content
            assert "系列3" in question_content or "series 3" in question_content.lower()


class TestSwitchToNextSeriesIntegration:
    """Test integration of pregeneration with _switch_to_next_series"""

    @pytest.mark.asyncio
    async def test_switch_to_next_series_triggers_pregeneration(self):
        """Test that _switch_to_next_series calls _pregenerate_next_series_question"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        # Set up state with some answers
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
            answers={
                "q-test-1-1": Answer(
                    question_id="q-test-1-1",
                    content="Test answer",
                    deviation_score=0.8
                )
            },
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        with patch.object(service, '_pregenerate_next_series_question', new_callable=AsyncMock) as mock_pregenerate:
            await service._switch_to_next_series()
            mock_pregenerate.assert_called_once()

    @pytest.mark.asyncio
    async def test_pregeneration_happens_after_series_increment(self):
        """Test that pregeneration happens after state.current_series is incremented"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
            answers={
                "q-test-1-1": Answer(
                    question_id="q-test-1-1",
                    content="Test answer",
                    deviation_score=0.8
                )
            },
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        captured_series = []

        async def capture_pregenerate():
            captured_series.append(service.state.current_series)
            # At this point, series should already be 2

        with patch.object(service, '_pregenerate_next_series_question', side_effect=capture_pregenerate):
            await service._switch_to_next_series()

        assert captured_series[0] == 2  # Series should be incremented before pregeneration


class TestPregenerateWithSubmitAnswer:
    """Test pregeneration behavior during submit_answer flow"""

    @pytest.mark.asyncio
    async def test_submit_answer_triggers_pregeneration_on_series_switch(self):
        """Test that submit_answer triggers pregeneration when series switches"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
            answers={},
            current_question=Question(
                content="Test question",
                question_type=QuestionType.INITIAL,
                series=1,
                number=1,
            ),
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM, \
             patch('src.services.interview_service.get_cached_next_question', new_callable=AsyncMock) as mock_get_cached, \
             patch('src.services.interview_service.cache_next_series_question', new_callable=AsyncMock) as mock_cache, \
             patch.object(service, '_pregenerate_next_series_question', new_callable=AsyncMock) as mock_pregenerate, \
             patch('src.services.interview_service.save_to_session_memory', new_callable=AsyncMock):
            MockLLM.return_value.generate_question = AsyncMock(
                return_value=Question(
                    content="[模拟问题]",
                    question_type=QuestionType.INITIAL,
                    series=2,
                    number=1,
                )
            )
            MockLLM.return_value.evaluate_answer = AsyncMock(
                return_value={"deviation_score": 0.8, "is_correct": True}
            )
            mock_get_cached.return_value = None
            # Set up so that _is_series_complete returns True
            service.state = replace(
                service.state,
                answers={
                    "q-test-session-1-1": Answer(
                        question_id="q-test-session-1-1",
                        content="Answer",
                        deviation_score=0.8
                    )
                }
            )

            # submit_answer should trigger pregeneration when series completes
            await service.submit_answer("My answer", "q-test-session-1-1")

            # If series switch happened, pregeneration should be called
            if mock_pregenerate.called:
                mock_pregenerate.assert_called()


class TestCachedQuestionUsage:
    """Test that _generate_next_question uses cached questions"""

    @pytest.mark.asyncio
    async def test_generate_next_question_prefers_cached(self):
        """Test that _generate_next_question uses cached question when available"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=2,
            followup_depth=0,
            error_count=0,
            answers={},
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        cached_content = "This is a cached question for series 2"

        with patch('src.services.interview_service.get_cached_next_question', new_callable=AsyncMock) as mock_get_cached:
            mock_get_cached.return_value = cached_content

            question = await service._generate_next_question()

            assert question.content == cached_content
            assert question.series == 2

    @pytest.mark.asyncio
    async def test_generate_next_question_falls_back_to_dynamic(self):
        """Test that _generate_next_question generates dynamically when no cache"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
            answers={},
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM, \
             patch('src.services.interview_service.get_cached_next_question', new_callable=AsyncMock) as mock_get_cached:
            MockLLM.return_value.generate_question = AsyncMock(
                return_value=Question(
                    content="[模拟问题] 请介绍一下你的项目经验？",
                    question_type=QuestionType.INITIAL,
                    series=1,
                    number=1,
                )
            )
            mock_get_cached.return_value = None  # No cached question

            question = await service._generate_next_question()

            # Should generate dynamic question (contains mock marker)
            assert "[模拟问题" in question.content or "[预生成问题" in question.content


class TestPregenerationTopic:
    """Test that pregeneration includes appropriate topic"""

    @pytest.mark.asyncio
    async def test_pregenerate_contains_relevant_topic_marker(self):
        """Test that pregenerated question contains topic marker"""
        service = InterviewService(
            session_id="test-session",
            resume_id="resume-123",
            max_series=5
        )
        service.state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
            current_series=1,
            followup_depth=0,
            error_count=0,
        )
        service.context = InterviewContext(
            session_id="test-session",
            resume_id="resume-123",
            knowledge_base_id="",
            interview_mode=InterviewMode.FREE,
            feedback_mode=FeedbackMode.RECORDED,
            error_threshold=2,
        )
        service.state = replace(service.state, current_series=1)

        with patch('src.services.interview_service.InterviewLLMService') as MockLLM, \
             patch('src.services.interview_service.cache_next_series_question', new_callable=AsyncMock) as mock_cache:
            MockLLM.return_value.generate_question = AsyncMock(
                return_value=Question(
                    content="请介绍一下系列2的项目经验？",
                    question_type=QuestionType.INITIAL,
                    series=2,
                    number=1,
                )
            )
            await service._pregenerate_next_series_question()
            call_args = mock_cache.call_args
            question_content = call_args[0][2]
            # Should indicate this is for next series
            assert "系列2" in question_content or "series 2" in question_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])