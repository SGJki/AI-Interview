"""Interview orchestration configuration."""
from dataclasses import dataclass
from typing import Literal


@dataclass
class InterviewConfig:
    # Review storage strategy
    is_production: bool = False

    # Flow parameters
    max_followup_depth: int = 3
    Retry_Max: int = 3
    deviation_threshold: float = 0.8
    max_series: int = 5
    error_threshold: int = 2

    # Feedback thresholds
    feedback_thresholds: dict = None

    def __post_init__(self):
        if self.feedback_thresholds is None:
            self.feedback_thresholds = {
                "correction": 0.3,
                "guidance": 0.6
            }

    def get_feedback_type(self, deviation_score: float) -> Literal["correction", "guidance", "comment"]:
        if deviation_score < self.feedback_thresholds["correction"]:
            return "correction"
        elif deviation_score < self.feedback_thresholds["guidance"]:
            return "guidance"
        return "comment"


# Global config instance
config = InterviewConfig()
