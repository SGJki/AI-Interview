# Final Feedback Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement final feedback aggregation for `OrchestratorAdapter.end_interview()` and add tests for `validate_cache_with_llm`.

**Architecture:** Reuse `FinalFeedback` dataclass from `src/session/snapshot.py`. Adapt aggregation logic from `InterviewService._generate_final_feedback()` (line ~1125 in `src/services/interview_service.py`).

**Tech Stack:** Python dataclasses, unittest.mock

---

## File Map

| File | Responsibility |
|------|----------------|
| `src/services/orchestrator_adapter.py` | Add aggregation functions, update `end_interview()` |
| `src/session/snapshot.py` | Already has `FinalFeedback` dataclass (import from here) |
| `tests/unit/test_orchestrator_adapter.py` | Add tests for aggregation logic |
| `tests/unit/test_prompt_cache.py` | Add tests for `validate_cache_with_llm` |

---

## Data Structures Reference

### Evaluation Result (from `evaluation_results` dict)
```python
{
    "deviation_score": float,  # 0-1, 1=完全匹配
    "is_correct": bool,
    "key_points": list[str],
    "suggestions": list[str],
}
```

### Answer (from `answers` dict)
```python
Answer(
    question_id: str,
    content: str,
    deviation_score: float,  # 0-1
)
```

### FinalFeedback (already exists in snapshot.py)
```python
FinalFeedback(
    overall_score: float,          # 0-1
    series_scores: dict[int, float],
    strengths: list[str],
    weaknesses: list[str],
    suggestions: list[str],
)
```

---

## Task 1: Create Aggregation Helper Functions

**Files:**
- Modify: `src/services/orchestrator_adapter.py`
- Create: `tests/unit/test_orchestrator_adapter.py` (new file)

- [ ] **Step 1: Write failing tests for aggregation functions**

Create new test file `tests/unit/test_orchestrator_adapter.py` with content:

```python
"""
Unit tests for OrchestratorAdapter
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.orchestrator_adapter import OrchestratorAdapter


class TestFinalFeedbackAggregation:
    """Tests for final feedback aggregation logic."""

    def test_aggregate_series_score_single_evaluation(self):
    """Tests for final feedback aggregation logic."""

    def test_aggregate_series_score_single_evaluation(self):
        """Test series score with single evaluation."""
        from src.services.orchestrator_adapter import aggregate_series_score
        evaluations = [
            {"deviation_score": 0.8, "is_correct": True},
        ]
        result = aggregate_series_score(evaluations)
        assert result == 0.8

    def test_aggregate_series_score_multiple_evaluations(self):
        """Test series score with multiple evaluations."""
        from src.services.orchestrator_adapter import aggregate_series_score
        evaluations = [
            {"deviation_score": 0.9, "is_correct": True},
            {"deviation_score": 0.7, "is_correct": True},
            {"deviation_score": 0.5, "is_correct": False},
        ]
        result = aggregate_series_score(evaluations)
        assert result == pytest.approx(0.7)

    def test_aggregate_series_score_empty(self):
        """Test series score with empty evaluations returns 0.0."""
        from src.services.orchestrator_adapter import aggregate_series_score
        result = aggregate_series_score([])
        assert result == 0.0

    def test_aggregate_overall_score_basic(self):
        """Test overall score calculation."""
        from src.services.orchestrator_adapter import aggregate_overall_score
        series_scores = {1: 0.8, 2: 0.7, 3: 0.9}
        result = aggregate_overall_score(series_scores)
        assert result == pytest.approx(0.8)  # Average

    def test_aggregate_overall_score_empty(self):
        """Test overall score with no series returns 0.0."""
        from src.services.orchestrator_adapter import aggregate_overall_score
        result = aggregate_overall_score({})
        assert result == 0.0

    def test_extract_strengths_from_high_scores(self):
        """Test extracting strengths from high-scoring evaluations."""
        from src.services.orchestrator_adapter import extract_strengths
        evaluations = [
            {"deviation_score": 0.9, "is_correct": True, "key_points": ["技术深度好"]},
            {"deviation_score": 0.8, "is_correct": True, "key_points": ["表达清晰"]},
        ]
        feedbacks = []
        result = extract_strengths(evaluations, feedbacks)
        assert len(result) > 0

    def test_extract_weaknesses_from_low_scores(self):
        """Test extracting weaknesses from low-scoring evaluations."""
        from src.services.orchestrator_adapter import extract_weaknesses
        evaluations = [
            {"deviation_score": 0.3, "is_correct": False, "key_points": ["不够深入"]},
            {"deviation_score": 0.2, "is_correct": False, "key_points": ["缺乏细节"]},
        ]
        feedbacks = []
        result = extract_weaknesses(evaluations, feedbacks)
        assert len(result) > 0

    def test_generate_suggestions_low_score(self):
        """Test suggestions generated for low overall score."""
        from src.services.orchestrator_adapter import generate_suggestions
        weaknesses = ["有 2 个问题回答不够深入，需要加强"]
        overall_score = 0.4
        result = generate_suggestions(weaknesses, overall_score)
        assert len(result) > 0
```

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::TestFinalFeedbackAggregation -v`
Expected: FAIL with "module 'src.services.orchestrator_adapter' has no attribute 'aggregate_series_score'"

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::TestFinalFeedbackAggregation -v`
Expected: FAIL

- [ ] **Step 3: Implement aggregation functions**

Add to end of `src/services/orchestrator_adapter.py`:

```python
def aggregate_series_score(evaluations: list[dict]) -> float:
    """
    Calculate average score for a series.

    Args:
        evaluations: List of evaluation result dicts with deviation_score

    Returns:
        Average deviation score (0-1), or 0.0 if empty
    """
    if not evaluations:
        return 0.0
    scores = [e.get("deviation_score", 0.0) for e in evaluations]
    return sum(scores) / len(scores)


def aggregate_overall_score(series_scores: dict[int, float]) -> float:
    """
    Calculate overall score from series scores.

    Args:
        series_scores: Dict mapping series number to score

    Returns:
        Average score across series, or 0.0 if empty
    """
    if not series_scores:
        return 0.0
    return sum(series_scores.values()) / len(series_scores)


def extract_strengths(evaluations: list[dict], feedbacks: list[dict]) -> list[str]:
    """
    Extract strengths from evaluations and feedbacks.

    Args:
        evaluations: List of evaluation result dicts
        feedbacks: List of feedback dicts

    Returns:
        List of strength strings
    """
    strengths = []
    # High score evaluations (deviation >= 0.8)
    high_scores = [e for e in evaluations if e.get("deviation_score", 0) >= 0.8]
    if len(high_scores) >= 2:
        strengths.append(f"整体表现良好，在 {len(high_scores)} 个问题中回答准确")
    elif high_scores:
        strengths.append("部分问题回答准确")

    # Collect key points from high scores
    for e in high_scores:
        key_points = e.get("key_points", [])
        strengths.extend(key_points[:2])  # Add up to 2 key points

    return strengths if strengths else ["暂无明显优点"]


def extract_weaknesses(evaluations: list[dict], feedbacks: list[dict]) -> list[str]:
    """
    Extract weaknesses from evaluations and feedbacks.

    Args:
        evaluations: List of evaluation result dicts
        feedbacks: List of feedback dicts

    Returns:
        List of weakness strings
    """
    weaknesses = []
    # Low score evaluations (deviation < 0.4)
    low_scores = [e for e in evaluations if e.get("deviation_score", 0) < 0.4]
    if low_scores:
        weaknesses.append(f"有 {len(low_scores)} 个问题回答不够深入，需要加强")

    # Incorrect answers
    incorrect = [e for e in evaluations if not e.get("is_correct", True)]
    if len(incorrect) >= 2:
        weaknesses.append(f"有 {len(incorrect)} 个问题回答错误")

    return weaknesses if weaknesses else ["暂无明显缺点"]


def generate_suggestions(weaknesses: list[str], overall_score: float) -> list[str]:
    """
    Generate suggestions based on weaknesses and overall score.

    Args:
        weaknesses: List of weakness strings
        overall_score: Overall deviation score (0-1)

    Returns:
        List of suggestion strings
    """
    suggestions = list(weaknesses)  # Start with weaknesses

    # Add score-based suggestion
    if overall_score >= 0.8:
        suggestions.append("整体表现优秀，建议挑战更深入的问题")
    elif overall_score >= 0.6:
        suggestions.append("基础扎实，可加强技术细节的理解")
    elif overall_score >= 0.4:
        suggestions.append("需要加强核心知识点的掌握")
    else:
        suggestions.append("建议系统复习相关技术知识")

    return suggestions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::TestFinalFeedbackAggregation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/orchestrator_adapter.py tests/unit/test_orchestrator_adapter.py
git commit -m "feat(orchestrator): add final feedback aggregation functions"
```

---

## Task 2: Integrate Aggregation into end_interview()

**Files:**
- Modify: `src/services/orchestrator_adapter.py:172-209`

- [ ] **Step 1: Write failing test for end_interview final_feedback**

Add to `tests/unit/test_orchestrator_adapter.py`:

```python
@pytest.mark.asyncio
async def test_end_interview_generates_real_final_feedback():
    """Test end_interview generates aggregated final feedback instead of placeholder."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.services.orchestrator_adapter import OrchestratorAdapter
    from dataclasses import replace
    from src.agent.state import InterviewState
    from src.domain.enums import InterviewMode, QuestionType
    from src.domain.models import Question, Answer

    adapter = OrchestratorAdapter(
        session_id="test-session",
        resume_id="resume-123",
    )

    # Create mock state with evaluation results
    mock_state = replace(
        InterviewState(session_id="test-session", resume_id="resume-123"),
        answers={
            "q1": Answer(question_id="q1", content="回答1", deviation_score=0.8),
            "q2": Answer(question_id="q2", content="回答2", deviation_score=0.6),
        },
        evaluation_results={
            "q1": {"deviation_score": 0.8, "is_correct": True, "key_points": ["技术深度好"]},
            "q2": {"deviation_score": 0.6, "is_correct": True, "key_points": ["基本准确"]},
        },
        feedbacks={},
        series_history={},
        current_series=1,
    )

    adapter.state = mock_state

    # Mock graph.ainvoke to avoid actual execution
    with patch.object(adapter, 'graph') as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=mock_state)
        result = await adapter.end_interview()

    # Verify final_feedback is not the hardcoded placeholder
    final_feedback = result["final_feedback"]
    assert final_feedback["overall_score"] != 0.8 or final_feedback["strengths"] != ["表达清晰", "技术深度好"]
    # Should be based on actual evaluation results
    assert "overall_score" in final_feedback
    assert "series_scores" in final_feedback
```

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::test_end_interview_generates_real_final_feedback -v`
Expected: FAIL (placeholder values still used)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::test_end_interview_generates_real_final_feedback -v`
Expected: FAIL

- [ ] **Step 3: Update end_interview() to use aggregation functions**

Replace lines 194-201 in `src/services/orchestrator_adapter.py`:

```python
        # 计算统计
        total_questions = len(self.state.answers)
        total_series = self.state.current_series

        # 生成最终反馈
        final_feedback = self._generate_final_feedback()
```

Add new method to `OrchestratorAdapter` class:

```python
    def _generate_final_feedback(self) -> dict:
        """
        Generate final feedback from evaluation results.

        Returns:
            dict with overall_score, series_scores, strengths, weaknesses, suggestions
        """
        from src.session.snapshot import FinalFeedback

        if not self.state.evaluation_results:
            return {
                "overall_score": 0.0,
                "series_scores": {},
                "strengths": ["暂无评估数据"],
                "weaknesses": ["暂无评估数据"],
                "suggestions": ["暂无建议"],
            }

        # Get evaluations
        evaluations = list(self.state.evaluation_results.values())

        # Calculate series scores
        # For simplicity, group all evaluations under current_series
        # A more sophisticated approach would parse question_id to determine series
        series_scores = {}
        if evaluations:
            series_avg = aggregate_series_score(evaluations)
            series_scores = {self.state.current_series: series_avg}

        # Calculate overall score
        overall_score = aggregate_overall_score(series_scores)

        # Extract strengths and weaknesses
        feedbacks = list(self.state.feedbacks.values())
        strengths = extract_strengths(evaluations, feedbacks)
        weaknesses = extract_weaknesses(evaluations, feedbacks)

        # Generate suggestions
        suggestions = generate_suggestions(weaknesses, overall_score)

        return {
            "overall_score": round(overall_score, 2),
            "series_scores": {k: round(v, 2) for k, v in series_scores.items()},
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py::test_end_interview_generates_real_final_feedback -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/orchestrator_adapter.py tests/unit/test_orchestrator_adapter.py
git commit -m "feat(orchestrator): integrate aggregation into end_interview()"
```

---

## Task 3: Add Tests for validate_cache_with_llm

**Files:**
- Modify: `tests/unit/test_prompt_cache.py` (add TestValidateCacheWithLLM class)

- [ ] **Step 1: Write failing tests for validate_cache_with_llm**

Add the following class to `tests/unit/test_prompt_cache.py` (append to end of file):

```python
class TestValidateCacheWithLLM:
    """Tests for validate_cache_with_llm method."""

    @pytest.fixture
    def cache(self):
        """Create PromptCache instance."""
        return PromptCache()

    @pytest.fixture
    def mock_llm_response_cached(self):
        """Mock LLM response with cached_tokens > 0."""
        from src.llm.usage import LLMResponse, PromptTokensDetails, LLMUsage

        return LLMResponse(
            content="缓存验证响应",
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                prompt_tokens_details=PromptTokensDetails(cached_tokens=80)
            )
        )

    @pytest.fixture
    def mock_llm_response_not_cached(self):
        """Mock LLM response with cached_tokens = 0."""
        from src.llm.usage import LLMResponse, PromptTokensDetails, LLMUsage

        return LLMResponse(
            content="非缓存响应",
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                prompt_tokens_details=PromptTokensDetails(cached_tokens=0)
            )
        )

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_cached(self, cache, mock_llm_response_cached):
        """Test validate_cache_with_llm when cache hits."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_cached

            state = await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1", "职责2"],
                system_prompt="测试系统提示词",
                test_prompt="测试提示词",
            )

            assert state.is_valid is True
            assert state.last_cached_tokens == 80
            assert state.hit_count >= 0

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_not_cached(self, cache, mock_llm_response_not_cached):
        """Test validate_cache_with_llm when cache misses."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_not_cached

            state = await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1", "职责2"],
                system_prompt="测试系统提示词",
                test_prompt="测试提示词",
            )

            assert state.is_valid is False
            assert state.last_cached_tokens == 0

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_exception(self, cache):
        """Test validate_cache_with_llm handles exceptions."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("LLM 调用失败")

            with pytest.raises(Exception, match="LLM 调用失败"):
                await cache.validate_cache_with_llm(
                    session_id="session-123",
                    resume_id="resume-456",
                    responsibilities=["职责1"],
                    system_prompt="测试系统提示词",
                )

    @pytest.mark.asyncio
    async def test_validate_cache_with_llm_records_state(self, cache, mock_llm_response_cached):
        """Test validate_cache_with_llm records state to cache store."""
        with patch('src.llm.client.invoke_llm_with_usage', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_llm_response_cached

            await cache.validate_cache_with_llm(
                session_id="session-123",
                resume_id="resume-456",
                responsibilities=["职责1"],
                system_prompt="测试",
            )

            # Verify state was recorded
            recorded_state = await cache.get_cache_state("session-123")
            assert recorded_state is not None
            assert recorded_state.cache_key is not None
```

Run: `uv run pytest tests/unit/test_prompt_cache.py::TestValidateCacheWithLLM -v`
Expected: FAIL with "nothing found to test"

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_prompt_cache.py::TestValidateCacheWithLLM -v`
Expected: FAIL

- [ ] **Step 3: Verify imports are correct**

Check that `LLMResponse`, `PromptTokensDetails`, `Usage` exist in `src.llm.usage`:

```python
from src.llm.usage import LLMResponse, PromptTokensDetails, Usage
```

Run: `uv run python -c "from src.llm.usage import LLMResponse, PromptTokensDetails, Usage; print('OK')"`
Expected: OK

- [ ] **Step 4: Run tests again**

Run: `uv run pytest tests/unit/test_prompt_cache.py::TestValidateCacheWithLLM -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_prompt_cache.py
git commit -m "test(prompt_cache): add validate_cache_with_llm tests"
```

---

## Task 4: Final Verification

- [ ] **Step 1: Run all tests**

Run: `uv run pytest tests/unit/test_orchestrator_adapter.py tests/unit/test_prompt_cache.py -v`

- [ ] **Step 2: Run linting**

Run: `uv run ruff check src/services/orchestrator_adapter.py src/core/prompt_cache.py`

- [ ] **Step 3: Final test run**

Run: `uv run pytest tests/ --tb=no -q`
