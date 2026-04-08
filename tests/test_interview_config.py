"""Tests for interview configuration module."""
import pytest
from src.config.interview_config import InterviewConfig, config


class TestInterviewConfig:
    """Test cases for InterviewConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        cfg = InterviewConfig()

        assert cfg.is_production is False
        assert cfg.max_followup_depth == 3
        assert cfg.Retry_Max == 3
        assert cfg.deviation_threshold == 0.8
        assert cfg.max_series == 5
        assert cfg.error_threshold == 2

    def test_feedback_thresholds_default(self):
        """Test default feedback thresholds are set in __post_init__."""
        cfg = InterviewConfig()

        assert cfg.feedback_thresholds is not None
        assert cfg.feedback_thresholds["correction"] == 0.3
        assert cfg.feedback_thresholds["guidance"] == 0.6

    def test_custom_feedback_thresholds(self):
        """Test custom feedback thresholds."""
        custom_thresholds = {"correction": 0.2, "guidance": 0.5}
        cfg = InterviewConfig(feedback_thresholds=custom_thresholds)

        assert cfg.feedback_thresholds["correction"] == 0.2
        assert cfg.feedback_thresholds["guidance"] == 0.5

    def test_get_feedback_type_correction(self):
        """Test get_feedback_type returns 'correction' for low deviation."""
        cfg = InterviewConfig()

        result = cfg.get_feedback_type(0.1)
        assert result == "correction"

    def test_get_feedback_type_guidance(self):
        """Test get_feedback_type returns 'guidance' for medium deviation."""
        cfg = InterviewConfig()

        result = cfg.get_feedback_type(0.4)
        assert result == "guidance"

    def test_get_feedback_type_comment(self):
        """Test get_feedback_type returns 'comment' for high deviation."""
        cfg = InterviewConfig()

        result = cfg.get_feedback_type(0.7)
        assert result == "comment"

    def test_feedback_type_boundary_correction(self):
        """Test boundary: deviation equal to correction threshold returns guidance."""
        cfg = InterviewConfig()

        # At correction threshold (0.3), should return guidance (not correction)
        result = cfg.get_feedback_type(0.3)
        assert result == "guidance"

    def test_feedback_type_boundary_guidance(self):
        """Test boundary: deviation at guidance threshold returns comment."""
        cfg = InterviewConfig()

        # At guidance threshold (0.6), should return comment
        result = cfg.get_feedback_type(0.6)
        assert result == "comment"

    def test_is_production_flag(self):
        """Test is_production flag."""
        cfg_prod = InterviewConfig(is_production=True)
        cfg_dev = InterviewConfig(is_production=False)

        assert cfg_prod.is_production is True
        assert cfg_dev.is_production is False

    def test_global_config_instance(self):
        """Test that global config instance is available."""
        assert config is not None
        assert isinstance(config, InterviewConfig)
        assert config.max_followup_depth == 3


class TestInterviewConfigEdgeCases:
    """Edge case tests for InterviewConfig."""

    def test_zero_deviation(self):
        """Test deviation score of zero."""
        cfg = InterviewConfig()
        assert cfg.get_feedback_type(0.0) == "correction"

    def test_negative_deviation(self):
        """Test negative deviation score."""
        cfg = InterviewConfig()
        assert cfg.get_feedback_type(-0.1) == "correction"

    def test_deviation_above_one(self):
        """Test deviation score above 1."""
        cfg = InterviewConfig()
        assert cfg.get_feedback_type(1.5) == "comment"
