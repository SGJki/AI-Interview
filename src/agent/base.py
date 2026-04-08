"""Base classes for all agents."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class AgentPhase(str, Enum):
    """Agent execution phase."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    data: dict = None
    error: str = None
    retry_count: int = 0


class ReviewVoter:
    """3-instance voting mechanism for reviews."""

    def __init__(self, voters: list[Callable[[dict], bool]]):
        self.voters = voters

    async def vote(self, content: dict) -> tuple[bool, list[str]]:
        """
        Run voting and return (passed, failures).
        At least 2 votes needed to pass.
        """
        results = []
        for voter in self.voters:
            try:
                if asyncio.iscoroutinefunction(voter):
                    results.append(await voter(content))
                else:
                    results.append(voter(content))
            except Exception as e:
                results.append(False)

        passed_count = sum(results)
        passed = passed_count >= 2

        failures = []
        if not passed:
            for i, r in enumerate(results):
                if not r:
                    failures.append(f"Voter {i} failed")

        return passed, failures


def create_review_voters(check_functions: list[Callable[[dict], bool]]) -> ReviewVoter:
    """Factory to create ReviewVoter with check functions."""
    return ReviewVoter(check_functions)
