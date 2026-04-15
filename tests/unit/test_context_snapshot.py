"""
Unit tests for ContextSnapshot ORM Model
"""

import pytest
from datetime import datetime
from src.db.context_snapshot import ContextSnapshot


def test_context_snapshot_creation():
    """Test creating a ContextSnapshot instance"""
    snapshot = ContextSnapshot(
        session_id="test-session-123",
        version=1,
        timestamp=datetime.now(),
        compressed_summary={
            "progress": {"current_series": 1},
            "evaluation": {"error_count": 0},
            "insights": {"covered_technologies": ["Python"]},
        },
    )
    assert snapshot.session_id == "test-session-123"
    assert snapshot.version == 1
    assert snapshot.compressed_summary["progress"]["current_series"] == 1


def test_context_snapshot_version_increments():
    """Test that version can be incremented"""
    snapshot = ContextSnapshot(
        session_id="test-session-456",
        version=1,
        timestamp=datetime.now(),
        compressed_summary={"progress": {}, "evaluation": {}, "insights": {}},
    )
    snapshot.version = 2
    assert snapshot.version == 2


def test_context_snapshot_compressed_summary_structure():
    """Test compressed_summary stores JSONB data correctly"""
    summary = {
        "progress": {
            "current_series": 2,
            "current_question_index": 3,
            "current_phase": "followup",
            "series_history": {},
            "followup_chain": ["q1", "q2"],
            "responsibilities": ("后端开发",),
        },
        "evaluation": {
            "series_scores": {1: 0.85, 2: 0.72},
            "error_count": 1,
            "error_threshold": 2,
            "mastered_questions": {},
            "asked_logical_questions": [],
        },
        "insights": {
            "covered_technologies": ["Python", "Redis"],
            "weak_areas": ["分布式系统"],
            "error_patterns": ["混淆一致性级别"],
            "followup_triggers": ["回答不完整"],
            "interview_continuity_note": "面试进行中",
        },
    }

    snapshot = ContextSnapshot(
        session_id="test-session-789",
        version=3,
        timestamp=datetime.now(),
        compressed_summary=summary,
    )

    assert snapshot.compressed_summary["progress"]["current_series"] == 2
    assert snapshot.compressed_summary["evaluation"]["error_count"] == 1
    assert "Python" in snapshot.compressed_summary["insights"]["covered_technologies"]
