# Phase 1: ReviewAgent LLM判断 + 结束持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 ReviewAgent 的 LLM 判断功能，完善面试结束时的持久化流程

**Architecture:** 新建 `src/agent/prompts.py` 管理 ReviewAgent prompt；ReviewAgent 的两个 checker 函数改为异步 LLM 调用；orchestrator 新增 `end_interview_node` 处理 PostgreSQL 写入和 Redis 清理。

**Tech Stack:** Python, LangGraph, SQLAlchemy, Redis

---

## File Structure

```
src/
├── agent/
│   ├── prompts.py              # NEW: ReviewAgent prompt templates
│   ├── review_agent.py        # MODIFY: add async LLM checkers
│   └── orchestrator.py        # MODIFY: add end_interview_node
tests/
├── test_review_agent.py       # MODIFY: add LLM checker tests
```

---

## Task 1: Create prompts.py with ReviewAgent templates

**Files:**
- Create: `src/agent/prompts.py`

```python
"""
Agent Prompt Templates

ReviewAgent 使用的 prompt 模板
"""

# =============================================================================
# ReviewAgent Prompts
# =============================================================================

REVIEW_EVALUATION_BASED_ON_QA = """判断以下评估是否基于实际的问答内容：

问题: {question}
回答: {user_answer}
评估: {evaluation}

评估是否基于问答内容而非外部信息？只回答 YES 或 NO。"""

REVIEW_STANDARD_ANSWER_FIT = """判断以下标准答案是否与问题相关：

问题: {question}
标准答案: {standard_answer}

标准答案是否适合作为该问题的参考？只回答 YES 或 NO。"""
```

- [ ] **Step 1: Create src/agent/prompts.py**

Create the file with the content above.

- [ ] **Step 2: Verify file exists**

Run: `ls src/agent/prompts.py`

- [ ] **Step 3: Commit**

```bash
git add src/agent/prompts.py
git commit -m "feat(agent): add prompts.py with ReviewAgent templates"
```

---

## Task 2: Implement LLM-based _check_evaluation_based_on_qa

**Files:**
- Modify: `src/agent/review_agent.py:67-78`

Current code (line 67-70):
```python
def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否基于问答内容"""
    # TODO: 实现 LLM 调用判断
    return True
```

New code:
```python
async def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """使用 LLM 判断评估是否基于问答内容"""
    from src.agent.prompts import REVIEW_EVALUATION_BASED_ON_QA
    llm = get_llm_service()
    prompt = REVIEW_EVALUATION_BASED_ON_QA.format(
        question=question,
        user_answer=user_answer,
        evaluation=evaluation,
    )
    result = await llm.invoke_llm(prompt=prompt)
    return "YES" in result.upper()
```

- [ ] **Step 1: Write failing test**

Add to `tests/test_review_agent.py`:

```python
@pytest.mark.asyncio
async def test_check_evaluation_based_on_qa_llm_true():
    """测试 LLM 判断评估基于 QA 返回 YES"""
    with patch('src.agent.review_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.invoke_llm = AsyncMock(return_value="YES, the evaluation is based on Q&A")
        mock.return_value = service

        result = await _check_evaluation_based_on_qa(
            question="What is Redis?",
            user_answer="Redis is an in-memory database",
            evaluation={"deviation_score": 0.8}
        )
        assert result is True
```

Run: `uv run pytest tests/test_review_agent.py::test_check_evaluation_based_on_qa_llm_true -v`
Expected: PASS (or FAIL if function not async yet)

- [ ] **Step 2: Update function to async with LLM call**

Modify `review_agent.py` lines 67-70 to the new async code.

- [ ] **Step 3: Run test to verify**

Run: `uv run pytest tests/test_review_agent.py::test_check_evaluation_based_on_qa_llm_true -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agent/review_agent.py tests/test_review_agent.py
git commit -m "feat(review): implement LLM-based evaluation check"
```

---

## Task 3: Implement similarity-based _check_standard_answer_fit

**Files:**
- Modify: `src/agent/review_agent.py:79-82`

Current code (line 79-82):
```python
def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str | None) -> bool:
    """检查标准答案与问题是否契合"""
    # TODO: 实现语义相似度检查
    return True
```

New code:
```python
async def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str | None) -> bool:
    """使用语义相似度检查标准答案与问题是否契合"""
    if not standard_answer:
        return True
    from src.services.embedding_service import compute_similarity
    score = await compute_similarity(question, standard_answer)
    return score > 0.7
```

- [ ] **Step 1: Write failing test**

Add to `tests/test_review_agent.py`:

```python
@pytest.mark.asyncio
async def test_check_standard_answer_fit_below_threshold():
    """测试语义相似度低于阈值返回 False"""
    with patch('src.agent.review_agent.compute_similarity', new_callable=AsyncMock) as mock:
        mock.return_value = 0.5  # below 0.7 threshold

        result = await _check_standard_answer_fit(
            question="What is Redis?",
            evaluation={},
            standard_answer="Redis is a caching system"
        )
        assert result is False

@pytest.mark.asyncio
async def test_check_standard_answer_fit_above_threshold():
    """测试语义相似度高于阈值返回 True"""
    with patch('src.agent.review_agent.compute_similarity', new_callable=AsyncMock) as mock:
        mock.return_value = 0.8  # above 0.7 threshold

        result = await _check_standard_answer_fit(
            question="What is Redis?",
            evaluation={},
            standard_answer="Redis is an in-memory database for caching"
        )
        assert result is True

@pytest.mark.asyncio
async def test_check_standard_answer_fit_no_standard_answer():
    """测试无标准答案时返回 True"""
    result = await _check_standard_answer_fit(
        question="What is Redis?",
        evaluation={},
        standard_answer=None
    )
    assert result is True
```

Run: `uv run pytest tests/test_review_agent.py::test_check_standard_answer_fit -v`
Expected: FAIL with "compute_similarity not found"

- [ ] **Step 2: Update function with similarity check**

Modify `review_agent.py` lines 79-82 to the new code.

Add import at top of file:
```python
from src.services.embedding_service import compute_similarity
```

- [ ] **Step 3: Run test to verify**

Run: `uv run pytest tests/test_review_agent.py::test_check_standard_answer_fit -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agent/review_agent.py tests/test_review_agent.py
git commit -m "feat(review): implement semantic similarity check for standard answer fit"
```

---

## Task 4: Add end_interview_node to orchestrator

**Files:**
- Modify: `src/agent/orchestrator.py`

New node function to add:

```python
async def end_interview_node(state: InterviewState) -> dict:
    """结束面试：写入 PostgreSQL + 清理 Redis"""
    from src.tools.memory_tools import clear_session_memory
    from src.dao.interview_session_dao import InterviewSessionDAO
    from src.db.database import get_session

    # 1. 写入 PostgreSQL
    session_data = {
        "session_id": state.session_id,
        "resume_id": state.resume_id,
        "status": "completed",
        "answers_count": len(state.answers),
        "feedbacks_count": len(state.feedbacks),
    }
    async with get_session() as session:
        dao = InterviewSessionDAO(session)
        await dao.update_status(state.session_id, "completed")

    # 2. 清理 Redis
    await clear_session_memory(state.session_id)

    return {"phase": "completed"}
```

- [ ] **Step 1: Add end_interview_node function**

Add the function above to `orchestrator.py` before `create_orchestrator_graph()`.

- [ ] **Step 2: Add node to graph**

In `create_orchestrator_graph()`, add:
```python
graph.add_node("end_interview", end_interview_node)
```

- [ ] **Step 3: Update routing**

Modify `decide_next` to return `{"next_action": "end_interview"}` when ending.

Add edge:
```python
graph.add_edge("end_interview", END)
```

- [ ] **Step 4: Verify imports work**

Run: `uv run python -c "from src.agent.orchestrator import end_interview_node; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/agent/orchestrator.py
git commit -m "feat(orchestrator): add end_interview_node for persistence"
```

---

## Task 5: Update decision routing

**Files:**
- Modify: `src/agent/orchestrator.py`

Current routing in `decide_next_node` returns `"final_feedback"` for end conditions. Update to return `{"next_action": "end_interview"}`.

- [ ] **Step 1: Update decide_next to route to end_interview**

Modify the return in `decide_next_node`:
```python
if state.current_series >= config.max_series:
    return {"next_action": "end_interview"}
# ... other end conditions
```

- [ ] **Step 2: Update conditional edges**

In `create_orchestrator_graph()`, update:
```python
"final_feedback": "end_interview",
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_orchestrator.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/agent/orchestrator.py
git commit -m "fix(orchestrator): route end conditions to end_interview_node"
```

---

## Task 6: Run full test suite

- [ ] **Step 1: Run all agent tests**

Run: `uv run pytest tests/test_review_agent.py tests/test_orchestrator.py tests/integration/ -v`

- [ ] **Step 2: Verify 625+ tests pass**

Expected: All tests pass

- [ ] **Step 3: Final commit if all pass**

```bash
git add -A
git commit -m "feat: Phase 1 complete - ReviewAgent LLM judgment + end interview persistence"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All 4 spec requirements have tasks
- [ ] Placeholder scan: No TBD/TODO in implementation code
- [ ] Type consistency: Function signatures match across tasks
- [ ] Test coverage: Tests for LLM checker, similarity checker, end_interview
