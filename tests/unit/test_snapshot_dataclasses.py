"""
Unit tests for Context Catch Snapshot dataclasses
"""

import pytest
from datetime import datetime
from src.agent.state import (
    ProgressSnapshot,
    EvaluationSnapshot,
    InsightSummary,
    ContextSnapshotData,
)


def test_progress_snapshot():
    """Test ProgressSnapshot dataclass creation"""
    progress = ProgressSnapshot(
        current_series=2,
        current_question_index=3,
        current_phase="followup",
        responsibilities=("后端开发", "微服务"),
    )
    assert progress.current_series == 2
    assert progress.current_question_index == 3
    assert progress.current_phase == "followup"
    assert progress.responsibilities == ("后端开发", "微服务")


def test_progress_snapshot_defaults():
    """Test ProgressSnapshot default values"""
    progress = ProgressSnapshot()
    assert progress.current_series == 1
    assert progress.current_question_index == 1
    assert progress.current_phase == "init"
    assert progress.series_history == {}
    assert progress.followup_chain == []
    assert progress.responsibilities == ()


def test_evaluation_snapshot():
    """Test EvaluationSnapshot dataclass creation"""
    evaluation = EvaluationSnapshot(
        series_scores={1: 0.85, 2: 0.72},
        error_count=1,
        mastered_questions={"q1": {"answer": "ok"}},
        asked_logical_questions={"q1", "q2"},
    )
    assert evaluation.series_scores[1] == 0.85
    assert evaluation.series_scores[2] == 0.72
    assert evaluation.error_count == 1
    assert "q1" in evaluation.asked_logical_questions


def test_evaluation_snapshot_defaults():
    """Test EvaluationSnapshot default values"""
    evaluation = EvaluationSnapshot()
    assert evaluation.series_scores == {}
    assert evaluation.error_count == 0
    assert evaluation.error_threshold == 2
    assert evaluation.mastered_questions == {}
    assert evaluation.asked_logical_questions == set()


def test_insight_summary():
    """Test InsightSummary dataclass creation"""
    insights = InsightSummary(
        covered_technologies=["Python", "Redis"],
        weak_areas=["分布式系统"],
        error_patterns=["混淆一致性级别"],
        followup_triggers=["回答不完整"],
        interview_continuity_note="面试进行中",
    )
    assert "Python" in insights.covered_technologies
    assert "Redis" in insights.covered_technologies
    assert insights.weak_areas == ["分布式系统"]
    assert insights.error_patterns == ["混淆一致性级别"]
    assert insights.interview_continuity_note == "面试进行中"


def test_insight_summary_defaults():
    """Test InsightSummary default values"""
    insights = InsightSummary()
    assert insights.covered_technologies == []
    assert insights.weak_areas == []
    assert insights.error_patterns == []
    assert insights.followup_triggers == []
    assert insights.interview_continuity_note == ""


def test_context_snapshot_data():
    """Test ContextSnapshotData dataclass composition"""
    snapshot = ContextSnapshotData(
        session_id="sess-123",
        version=1,
        timestamp=datetime.now(),
        progress=ProgressSnapshot(current_series=1, current_phase="initial"),
        evaluation=EvaluationSnapshot(error_count=0),
        insights=InsightSummary(covered_technologies=["Python"]),
    )
    assert snapshot.session_id == "sess-123"
    assert snapshot.version == 1
    assert snapshot.progress.current_series == 1
    assert snapshot.evaluation.error_count == 0
    assert "Python" in snapshot.insights.covered_technologies


def test_context_snapshot_data_immutable():
    """Test that ContextSnapshotData is immutable (frozen=True)"""
    snapshot = ContextSnapshotData(
        session_id="sess-123",
        version=1,
        timestamp=datetime.now(),
        progress=ProgressSnapshot(),
        evaluation=EvaluationSnapshot(),
        insights=InsightSummary(),
    )
    with pytest.raises(AttributeError):
        snapshot.session_id = "changed"
