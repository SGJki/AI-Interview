"""
Unit tests for ContextCatchEngine
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.context_catch import ContextCatchEngine, _snapshot_key, _version_key
from src.session.context import InterviewContext
from src.domain.enums import InterviewMode, FeedbackMode
from src.session.snapshot import (
    ProgressSnapshot,
    EvaluationSnapshot,
    InsightSummary,
    ContextSnapshotData,
)


@pytest.fixture
def engine():
    return ContextCatchEngine()


@pytest.fixture
def mock_state():
    return InterviewContext(
        session_id="test-session-123",
        resume_id="resume-456",
        knowledge_base_id="kb-789",
        current_series=2,
        phase="followup",
        answers=[
            {"question": "Python 装饰器是什么？", "deviation": 0.9, "series": 1},
            {"question": "Redis 持久化机制？", "deviation": 0.7, "series": 1},
            {"question": "分布式一致性？", "deviation": 0.6, "series": 2},
        ],
        feedbacks=[
            {"question_id": "q1", "is_correct": True},
            {"question_id": "q2", "is_correct": False},
        ],
        error_count=1,
        responsibilities=("后端开发", "微服务架构"),
    )


class TestExtractProgress:
    """Test _extract_progress method"""

    def test_extract_progress_basic(self, engine, mock_state):
        progress = engine._extract_progress(mock_state, ProgressSnapshot)
        assert progress.current_series == 2
        assert progress.current_phase == "followup"
        assert progress.responsibilities == ("后端开发", "微服务架构")

    def test_extract_progress_question_index(self, engine, mock_state):
        progress = engine._extract_progress(mock_state, ProgressSnapshot)
        # 3 answers + 1 = 4
        assert progress.current_question_index == 4

    def test_extract_progress_followup_chain(self, engine, mock_state):
        mock_state.followup_chain = ["q1", "q2"]
        progress = engine._extract_progress(mock_state, ProgressSnapshot)
        assert progress.followup_chain == ["q1", "q2"]


class TestExtractEvaluation:
    """Test _extract_evaluation method"""

    def test_extract_evaluation_series_scores(self, engine, mock_state):
        evaluation = engine._extract_evaluation(mock_state, EvaluationSnapshot)
        assert 1 in evaluation.series_scores
        assert 2 in evaluation.series_scores
        # Series 1: (0.9 + 0.7) / 2 = 0.8
        assert evaluation.series_scores[1] == pytest.approx(0.8)
        # Series 2: 0.6 / 1 = 0.6
        assert evaluation.series_scores[2] == pytest.approx(0.6)

    def test_extract_evaluation_error_count(self, engine, mock_state):
        evaluation = engine._extract_evaluation(mock_state, EvaluationSnapshot)
        assert evaluation.error_count == 1

    def test_extract_evaluation_empty_answers(self, engine):
        state = InterviewContext(
            session_id="empty-session",
            resume_id="resume",
            knowledge_base_id="kb",
            current_series=1,
            phase="init",
            answers=[],
        )
        evaluation = engine._extract_evaluation(state, EvaluationSnapshot)
        assert evaluation.series_scores == {}


class TestRedisKeyFunctions:
    """Test Redis key generation functions"""

    def test_snapshot_key(self):
        key = _snapshot_key("session-123")
        assert key == "context_catch:session-123:snapshot"

    def test_version_key(self):
        key = _version_key("session-123")
        assert key == "context_catch:session-123:version"


class TestCompress:
    """Test compress method"""

    @pytest.mark.asyncio
    async def test_compress_generates_snapshot(self, engine, mock_state):
        mock_redis_instance = MagicMock()
        mock_redis_instance.incr = AsyncMock(return_value=1)
        mock_redis_instance.setex = AsyncMock()

        engine._redis = mock_redis_instance

        with patch.object(engine, "_generate_insights", new_callable=AsyncMock) as mock_insights:
            mock_insights.return_value = InsightSummary(
                covered_technologies=["Python", "Redis"],
                weak_areas=["分布式系统"],
                error_patterns=[],
                followup_triggers=[],
                interview_continuity_note="面试进行中",
            )

            with patch.object(engine, "save_checkpoint", new_callable=AsyncMock):
                snapshot = await engine.compress(mock_state, trigger="manual")

                assert snapshot.session_id == "test-session-123"
                assert snapshot.version == 1
                assert snapshot.progress.current_series == 2
                assert snapshot.evaluation.series_scores[1] == pytest.approx(0.8)
                assert "Python" in snapshot.insights.covered_technologies
                mock_redis_instance.setex.assert_called_once()


class TestRestore:
    """Test restore method"""

    @pytest.mark.asyncio
    async def test_restore_full_mode(self, engine):
        mock_snapshot = ContextSnapshotData(
            session_id="test-session",
            version=1,
            timestamp=datetime.now(),
            progress=ProgressSnapshot(
                current_series=2,
                current_phase="followup",
                responsibilities=("后端开发",),
            ),
            evaluation=EvaluationSnapshot(error_count=1),
            insights=InsightSummary(),
        )

        with patch.object(engine, "_load_from_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_snapshot

            context = await engine.restore("test-session", mode="full")
            assert context is not None
            assert context.current_series == 2
            assert context.phase == "followup"
            assert context.error_count == 1

    @pytest.mark.asyncio
    async def test_restore_key_points_mode(self, engine):
        mock_snapshot = ContextSnapshotData(
            session_id="test-session",
            version=1,
            timestamp=datetime.now(),
            progress=ProgressSnapshot(
                current_series=2,
                current_phase="followup",
                responsibilities=("后端开发",),
            ),
            evaluation=EvaluationSnapshot(error_count=3),
            insights=InsightSummary(),
        )

        with patch.object(engine, "_load_from_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_snapshot

            context = await engine.restore("test-session", mode="key_points")
            assert context is not None
            assert context.current_series == 2
            assert context.phase == "initial"  # 重置
            assert context.error_count == 0  # 重置

    @pytest.mark.asyncio
    async def test_restore_fallback_to_pg(self, engine):
        with patch.object(engine, "_load_from_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = None  # Redis 未命中

            mock_snapshot = ContextSnapshotData(
                session_id="test-session",
                version=1,
                timestamp=datetime.now(),
                progress=ProgressSnapshot(current_series=1),
                evaluation=EvaluationSnapshot(),
                insights=InsightSummary(),
            )

            with patch.object(engine, "load_from_pg", new_callable=AsyncMock) as mock_pg:
                mock_pg.return_value = mock_snapshot

                with patch.object(engine, "_save_to_redis", new_callable=AsyncMock) as mock_save:
                    context = await engine.restore("test-session", mode="full")
                    assert context is not None
                    mock_save.assert_called_once()  # 回填 Redis

    @pytest.mark.asyncio
    async def test_restore_session_not_found(self, engine):
        with patch.object(engine, "_load_from_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = None

            with patch.object(engine, "load_from_pg", new_callable=AsyncMock) as mock_pg:
                mock_pg.return_value = None

                context = await engine.restore("non-existent-session", mode="full")
                assert context is None


class TestSummarizeAnswers:
    """Test answer summarization"""

    def test_summarize_answers_empty(self, engine):
        result = engine._summarize_answers([])
        assert result == "暂无回答"

    def test_summarize_answers_multiple(self, engine, mock_state):
        result = engine._summarize_answers(mock_state.answers)
        assert "Q1:" in result or "Q-2:" in result
        assert "装饰器" in result or "Redis" in result


class TestSummarizeFeedbacks:
    """Test feedback summarization"""

    def test_summarize_feedbacks_empty(self, engine):
        result = engine._summarize_feedbacks([])
        assert result == "暂无反馈"

    def test_summarize_feedbacks_multiple(self, engine, mock_state):
        result = engine._summarize_feedbacks(mock_state.feedbacks)
        assert "✓" in result or "✗" in result
