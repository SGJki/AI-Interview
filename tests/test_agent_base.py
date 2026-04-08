"""
Tests for AI Interview Agent - Base Classes
"""

import pytest
import asyncio
from src.agent.base import (
    AgentPhase,
    AgentResult,
    ReviewVoter,
    create_review_voters,
)


class TestAgentPhase:
    """Test AgentPhase enum"""

    def test_agent_phase_values(self):
        """Test AgentPhase enum values"""
        assert AgentPhase.IDLE == "idle"
        assert AgentPhase.RUNNING == "running"
        assert AgentPhase.WAITING_REVIEW == "waiting_review"
        assert AgentPhase.COMPLETED == "completed"
        assert AgentPhase.FAILED == "failed"

    def test_agent_phase_is_string_enum(self):
        """Test AgentPhase is a string enum"""
        assert isinstance(AgentPhase.IDLE, str)
        assert isinstance(AgentPhase.RUNNING, str)


class TestAgentResult:
    """Test AgentResult dataclass"""

    def test_create_success_result(self):
        """Test creating a successful result"""
        result = AgentResult(success=True, data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.retry_count == 0

    def test_create_failure_result(self):
        """Test creating a failure result"""
        result = AgentResult(success=False, error="Something went wrong", retry_count=2)

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.retry_count == 2
        assert result.data is None

    def test_agent_result_defaults(self):
        """Test AgentResult default values"""
        result = AgentResult(success=False)

        assert result.success is False
        assert result.data is None
        assert result.error is None
        assert result.retry_count == 0

    def test_agent_result_mutable(self):
        """Test AgentResult is mutable"""
        result = AgentResult(success=False)
        result.retry_count = 1
        result.data = {"updated": True}

        assert result.retry_count == 1
        assert result.data == {"updated": True}


class TestReviewVoter:
    """Test ReviewVoter class"""

    @pytest.mark.asyncio
    async def test_vote_all_pass(self):
        """Test voting when all voters pass"""
        async def voter1(c):
            return True
        async def voter2(c):
            return True
        async def voter3(c):
            return True

        voters = [voter1, voter2, voter3]
        review_voter = ReviewVoter(voters)

        passed, failures = await review_voter.vote({"content": "test"})

        assert passed is True
        assert failures == []

    @pytest.mark.asyncio
    async def test_vote_exactly_two_pass(self):
        """Test voting when exactly two voters pass"""
        async def voter1(c):
            return True
        async def voter2(c):
            return True
        async def voter3(c):
            return False

        voters = [voter1, voter2, voter3]
        review_voter = ReviewVoter(voters)

        passed, failures = await review_voter.vote({"content": "test"})

        assert passed is True
        assert failures == []

    @pytest.mark.asyncio
    async def test_vote_only_one_passes(self):
        """Test voting when only one voter passes"""
        async def voter1(c):
            return True
        async def voter2(c):
            return False
        async def voter3(c):
            return False

        voters = [voter1, voter2, voter3]
        review_voter = ReviewVoter(voters)

        passed, failures = await review_voter.vote({"content": "test"})

        assert passed is False
        assert len(failures) == 2
        assert "Voter 1 failed" in failures
        assert "Voter 2 failed" in failures

    @pytest.mark.asyncio
    async def test_vote_all_fail(self):
        """Test voting when all voters fail"""
        async def voter1(c):
            return False
        async def voter2(c):
            return False
        async def voter3(c):
            return False

        voters = [voter1, voter2, voter3]
        review_voter = ReviewVoter(voters)

        passed, failures = await review_voter.vote({"content": "test"})

        assert passed is False
        assert len(failures) == 3
        assert "Voter 0 failed" in failures
        assert "Voter 1 failed" in failures
        assert "Voter 2 failed" in failures

    @pytest.mark.asyncio
    async def test_vote_with_exception(self):
        """Test voting when a voter raises an exception"""
        async def voter1(c):
            return True

        async def voter2(c):
            raise Exception("Vote failed")

        async def voter3(c):
            return False

        voters = [voter1, voter2, voter3]
        review_voter = ReviewVoter(voters)

        passed, failures = await review_voter.vote({"content": "test"})

        assert passed is False
        assert len(failures) == 2

    @pytest.mark.asyncio
    async def test_vote_receives_content(self):
        """Test that voters receive the content dict"""
        received_content = None

        async def set_received(c):
            nonlocal received_content
            received_content = c
            return c.get("expected_key") == "expected_value"

        async def voter2(c):
            return True

        async def voter3(c):
            return True

        voters = [set_received, voter2, voter3]
        review_voter = ReviewVoter(voters)
        test_content = {"expected_key": "expected_value", "other": "data"}

        await review_voter.vote(test_content)

        assert received_content == test_content


class TestCreateReviewVoters:
    """Test create_review_voters factory function"""

    def test_create_review_voters_empty(self):
        """Test creating ReviewVoter with empty list"""
        voter = create_review_voters([])

        assert isinstance(voter, ReviewVoter)
        assert voter.voters == []

    def test_create_review_voters_with_functions(self):
        """Test creating ReviewVoter with check functions"""
        async def check_fn1(c):
            return True
        async def check_fn2(c):
            return True

        voter = create_review_voters([check_fn1, check_fn2])

        assert isinstance(voter, ReviewVoter)
        assert len(voter.voters) == 2

    @pytest.mark.asyncio
    async def test_create_review_voters_returns_functional_voter(self):
        """Test that the created ReviewVoter is functional"""
        async def check_fn1(c):
            return True
        async def check_fn2(c):
            return True
        async def check_fn3(c):
            return True

        check_fns = [check_fn1, check_fn2, check_fn3]
        voter = create_review_voters(check_fns)

        passed, failures = await voter.vote({})

        assert passed is True
        assert failures == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
