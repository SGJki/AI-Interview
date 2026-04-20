# AI-Interview 企业知识库集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将企业知识库检索集成到面试流程的评估与反馈环节，实现 EvaluateAgent 和 FeedbackAgent 调用企业知识库 API

**Architecture:** 在评估/反馈阶段统一查询企业知识库，查询结果缓存到 InterviewState 供多个方法复用，避免重复查询

**Tech Stack:** Python async/httpx, InterviewState dataclass, Enterprise KB REST API

---

## 文件变更概览

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `src/agent/state.py` | 修改 | 新增 enterprise KB 相关字段 |
| `src/tools/enterprise_knowledge.py` | 创建 | 企业知识库检索客户端 |
| `src/agent/evaluate_agent.py` | 修改 | 集成企业知识库评估 |
| `src/agent/feedback_agent.py` | 修改 | 集成企业知识库反馈生成 |
| `tests/test_enterprise_knowledge.py` | 创建 | 企业知识库检索单元测试 |
| `tests/test_evaluate_agent.py` | 修改 | 更新评估 Agent 测试 |
| `tests/test_feedback_agent.py` | 修改 | 更新反馈 Agent 测试 |

---

## Task 1: InterviewState 新增字段

**Files:**
- Modify: `src/agent/state.py:1-83`

**Tasks:**

- [ ] **Step 1: Read current state.py**

```bash
cat src/agent/state.py | head -90
```

- [ ] **Step 2: Add enterprise KB fields to InterviewState**

在 `src/agent/state.py` 的 `InterviewState` 类中添加新字段：

```python
# 在 phase 字段后添加

# Enterprise KB 相关字段
enterprise_docs: list = field(default_factory=list)  # 当前问题相关的企业知识文档
enterprise_docs_retrieved: bool = False  # 是否已查询过企业知识库
current_module: Optional[str] = None  # 当前问题所属 module
current_skill_point: Optional[str] = None  # 当前问题关联的 skill_point
identified_modules: list[str] = field(default_factory=list)  # 简历中识别的所有 module
```

- [ ] **Step 3: Run import check**

```bash
uv run python -c "from src.agent.state import InterviewState; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/agent/state.py
git commit -m "feat(state): add enterprise KB fields to InterviewState"
```

---

## Task 2: 创建企业知识库检索客户端

**Files:**
- Create: `src/tools/enterprise_knowledge.py`
- Test: `tests/test_enterprise_knowledge.py`

**Tasks:**

- [ ] **Step 1: Write failing test**

创建 `tests/test_enterprise_knowledge.py`:

```python
"""Tests for Enterprise Knowledge retrieval client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.enterprise_knowledge import (
    retrieve_enterprise_knowledge,
    ensure_enterprise_docs,
    EnterpriseKnowledgeError,
)


class TestRetrieveEnterpriseKnowledge:
    """Test retrieve_enterprise_knowledge function."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        with patch('src.tools.enterprise_knowledge.get_enterprise_kb_client') as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    @pytest.mark.asyncio
    async def test_retrieve_by_module(self, mock_httpx_client):
        """Test retrieval by module."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {
                    "content": "Token management best practices...",
                    "metadata": {"module": "用户认证", "skill_points": ["Token管理"]},
                    "score": 0.95
                }
            ],
            "total": 1
        }
        mock_httpx_client.post.return_value = mock_response

        docs = await retrieve_enterprise_knowledge(module="用户认证", top_k=3)

        assert len(docs) == 1
        assert docs[0]["content"] == "Token management best practices..."
        assert docs[0]["metadata"]["module"] == "用户认证"

    @pytest.mark.asyncio
    async def test_retrieve_by_skill_point(self, mock_httpx_client):
        """Test retrieval by skill_point."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {"content": "Redis caching strategies...", "metadata": {}, "score": 0.9}
            ],
            "total": 1
        }
        mock_httpx_client.post.return_value = mock_response

        docs = await retrieve_enterprise_knowledge(skill_point="Redis缓存", top_k=3)

        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_module_priority(self, mock_httpx_client):
        """Test module is used when both module and skill_point provided."""
        # This tests that module takes priority
        ...

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_httpx_client):
        """Test timeout returns empty list."""
        import httpx
        mock_httpx_client.post.side_effect = httpx.TimeoutException("timeout")

        docs = await retrieve_enterprise_knowledge(module="用户认证")

        assert docs == []


class TestEnsureEnterpriseDocs:
    """Test ensure_enterprise_docs helper."""

    @pytest.mark.asyncio
    async def test_returns_cached_docs(self):
        """Test returns cached docs if already retrieved."""
        from src.agent.state import InterviewState
        from langchain_core.documents import Document

        cached_docs = [Document(page_content="cached", metadata={})]
        state = InterviewState(
            session_id="test",
            resume_id="r1",
            enterprise_docs=cached_docs,
            enterprise_docs_retrieved=True
        )

        docs = await ensure_enterprise_docs(state)

        assert docs == cached_docs

    @pytest.mark.asyncio
    async def test_queries_when_not_retrieved(self):
        """Test queries when not yet retrieved."""
        ...
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_enterprise_knowledge.py -v 2>&1 | head -30
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

创建 `src/tools/enterprise_knowledge.py`:

```python
"""Enterprise Knowledge Base retrieval client."""
import logging
from typing import Optional

import httpx
from langchain_core.documents import Document

from src.agent.state import InterviewState

logger = logging.getLogger(__name__)

# Enterprise KB API configuration
ENTERPRISE_KB_BASE_URL = "http://localhost:8080"
ENTERPRISE_KB_TIMEOUT = 10  # seconds


class EnterpriseKnowledgeError(Exception):
    """Error when retrieving from enterprise knowledge base."""
    pass


def get_enterprise_kb_client() -> httpx.AsyncClient:
    """Get HTTP client for enterprise KB API."""
    return httpx.AsyncClient(
        base_url=ENTERPRISE_KB_BASE_URL,
        timeout=ENTERPRISE_KB_TIMEOUT,
    )


async def retrieve_enterprise_knowledge(
    module: Optional[str] = None,
    skill_point: Optional[str] = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve enterprise knowledge documents.

    Args:
        module: Module name (priority if provided)
        skill_point: Skill point (fallback)
        top_k: Number of results to return

    Returns:
        List of document dicts with content, metadata, score
    """
    if not module and not skill_point:
        return []

    try:
        async with get_enterprise_kb_client() as client:
            # Priority: module > skill_point
            if module:
                response = await client.post(
                    "/retrieve/by-module",
                    json={"module": module, "top_k": top_k}
                )
            else:
                response = await client.post(
                    "/retrieve/by-skill",
                    json={"skill_point": skill_point, "top_k": top_k}
                )

            response.raise_for_status()
            data = response.json()

            return data.get("documents", [])

    except httpx.TimeoutException:
        logger.warning("Enterprise KB timeout, proceeding without it")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"Enterprise KB returned {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Enterprise KB error: {e}")
        return []


async def ensure_enterprise_docs(state: InterviewState) -> list[dict]:
    """
    Ensure enterprise docs are retrieved and cached in state.

    Args:
        state: InterviewState

    Returns:
        List of enterprise knowledge documents
    """
    if state.enterprise_docs_retrieved:
        return state.enterprise_docs

    docs = await retrieve_enterprise_knowledge(
        module=state.current_module,
        skill_point=state.current_skill_point,
        top_k=3,
    )

    state.enterprise_docs = docs
    state.enterprise_docs_retrieved = True

    return docs
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_enterprise_knowledge.py -v 2>&1 | tail -30
```

Expected: PASS (or most pass)

- [ ] **Step 5: Commit**

```bash
git add src/tools/enterprise_knowledge.py tests/test_enterprise_knowledge.py
git commit -m "feat(enterprise): add enterprise KB retrieval client"
```

---

## Task 3: EvaluateAgent 集成企业知识库

**Files:**
- Modify: `src/agent/evaluate_agent.py`
- Modify: `tests/test_evaluate_agent.py`

**Tasks:**

- [ ] **Step 1: Write failing test for evaluate_with_standard integration**

在 `tests/test_evaluate_agent.py` 中添加测试：

```python
@pytest.mark.asyncio
async def test_evaluate_with_standard_uses_enterprise_kb():
    """Test evaluate_with_standard retrieves and uses enterprise KB."""
    from src.agent.evaluate_agent import evaluate_with_standard
    from src.tools.enterprise_knowledge import ensure_enterprise_docs
    from unittest.mock import patch

    state = InterviewState(
        session_id="test",
        resume_id="r1",
        current_module="用户认证",
        current_skill_point="Token管理",
        enterprise_docs=[],
        enterprise_docs_retrieved=False,
    )
    state.current_question = Question(
        content="请谈谈Token管理的经验",
        question_type=QuestionType.INITIAL,
        series=1,
        number=1,
    )
    state.answers = {}
    state.evaluation_results = {}

    mock_docs = [
        {"content": "Token best practice...", "metadata": {}, "score": 0.9}
    ]

    with patch('src.agent.evaluate_agent.ensure_enterprise_docs') as mock_ensure:
        mock_ensure.return_value = mock_docs

        result = await evaluate_with_standard(state)

    assert "answers" in result
    # Should have called ensure_enterprise_docs
    mock_ensure.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_evaluate_agent.py::test_evaluate_with_standard_uses_enterprise_kb -v 2>&1 | tail -20
```

Expected: FAIL

- [ ] **Step 3: Update evaluate_agent.py**

修改 `src/agent/evaluate_agent.py`:

1. 添加导入：
```python
from src.tools.enterprise_knowledge import ensure_enterprise_docs
```

2. 修改 `evaluate_with_standard` 函数：
```python
@async_retryable(max_attempts=3)
async def evaluate_with_standard(state: InterviewState) -> dict:
    """使用标准答案评估用户回答（企业知识库作为参考）"""

    # 确保企业知识库文档已查询
    docs = await ensure_enterprise_docs(state)

    # ... existing code ...

    # 构建评估提示词时传入 docs
    # (调用 llm_service.evaluate_answer 时传入 docs 作为参考)
```

3. 添加辅助方法 `_build_evaluation_prompt_with_similarity`:
```python
def _build_evaluation_prompt_with_similarity(
    question: str,
    user_answer: str,
    enterprise_docs: list[dict],
    similarity_score: float,
) -> str:
    """构建含相似度分数和企业知识的评估提示词"""
    prompt = f"""你是一个面试评估专家。请根据以下信息评估候选人的回答。

## 问题
{question}

## 候选人回答
{user_answer}

## 回答与参考答案的相似度
{similarity_score:.2%}

## 企业最佳实践参考答案
"""
    for i, doc in enumerate(enterprise_docs, 1):
        prompt += f"\n{i}. {doc['content']}\n"

    prompt += """
请结合相似度分数和参考答案，从以下几个方面评估：
1. 回答的正确性
2. 回答的完整性
3. 与企业最佳实践的差距
"""
    return prompt
```

4. 修改 `evaluate_without_standard` 类似处理

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_evaluate_agent.py -v 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
git add src/agent/evaluate_agent.py tests/test_evaluate_agent.py
git commit -m "feat(evaluate): integrate enterprise KB into evaluation"
```

---

## Task 4: FeedbackAgent 集成企业知识库

**Files:**
- Modify: `src/agent/feedback_agent.py`
- Modify: `tests/test_feedback_agent.py`

**Tasks:**

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_generate_correction_uses_cached_enterprise_docs():
    """Test generate_correction uses cached enterprise docs from state."""
    from src.agent.feedback_agent import generate_correction
    from unittest.mock import patch

    state = InterviewState(
        session_id="test",
        resume_id="r1",
        enterprise_docs=[{"content": "best practice", "metadata": {}}],
        enterprise_docs_retrieved=True,
    )
    # ... setup question and answer ...
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Update feedback_agent.py**

1. 添加导入：
```python
from src.tools.enterprise_knowledge import ensure_enterprise_docs
```

2. 修改三个方法使用 `state.enterprise_docs` 而不是独立查询：
```python
async def generate_correction(state: InterviewState) -> dict:
    """生成纠正反馈（使用 state.enterprise_docs）"""

    # 使用已缓存的企业知识库文档
    enterprise_docs = state.enterprise_docs

    # 构建提示词时传入 enterprise_docs
    ...
```

3. 添加反馈生成辅助方法：
```python
def _build_correction_prompt(
    question: str,
    user_answer: str,
    enterprise_docs: list[dict],
    evaluation: dict,
) -> str:
    ...

def _build_guidance_prompt(
    question: str,
    user_answer: str,
    enterprise_docs: list[dict],
    skill_point: str,
) -> str:
    ...

def _build_comment_prompt(
    question: str,
    user_answer: str,
    enterprise_docs: list[dict],
) -> str:
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_feedback_agent.py -v 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
git add src/agent/feedback_agent.py tests/test_feedback_agent.py
git commit -m "feat(feedback): integrate enterprise KB into feedback generation"
```

---

## Task 5: 添加 skill_point 提取辅助函数

**Files:**
- Modify: `src/agent/evaluate_agent.py`
- Create: `src/agent/helpers.py` (可选)

**Tasks:**

- [ ] **Step 1: Write _extract_skill_point function**

在 `src/agent/evaluate_agent.py` 末尾添加：

```python
def _extract_skill_point(question_content: str) -> str | None:
    """
    从问题内容中提取 skill_point。

    基于关键词匹配。
    """
    skill_keywords = [
        "Python", "Java", "Go", "Rust", "JavaScript", "TypeScript",
        "Redis", "MySQL", "PostgreSQL", "MongoDB",
        "Docker", "Kubernetes", "Git",
        "缓存", "队列", "微服务", "数据库", "架构",
        "认证", "授权", "Token", "OAuth",
    ]

    for keyword in skill_keywords:
        if keyword in question_content:
            return keyword

    return None
```

- [ ] **Step 2: Write test**

```python
def test_extract_skill_point():
    from src.agent.evaluate_agent import _extract_skill_point

    assert _extract_skill_point("请谈谈Python编程的经验") == "Python"
    assert _extract_skill_point("Redis缓存优化方法") == "Redis"
    assert _extract_skill_point("如何设计系统架构") is None
```

- [ ] **Step 3: Run test**

```bash
uv run pytest tests/test_evaluate_agent.py::test_extract_skill_point -v
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/evaluate_agent.py
git commit -m "feat(evaluate): add skill_point extraction helper"
```

---

## Task 6: 集成测试验证

**Files:**
- Create: `tests/integration/test_enterprise_kb_integration.py`

**Tasks:**

- [ ] **Step 1: Write integration test**

```python
"""Integration test for enterprise KB in interview flow."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.state import InterviewState
from src.agent.evaluate_agent import evaluate_with_standard
from src.agent.feedback_agent import generate_correction

@pytest.mark.asyncio
async def test_evaluate_and_feedback_share_same_enterprise_docs():
    """Test that evaluate and feedback use the same cached enterprise docs."""
    state = InterviewState(
        session_id="test",
        resume_id="r1",
        current_module="用户认证",
        current_skill_point="Token管理",
        enterprise_docs=[],
        enterprise_docs_retrieved=False,
    )
    state.current_question = Question(...)
    state.answers = {}
    state.evaluation_results = {}

    mock_docs = [{"content": "Token best practice...", "metadata": {}, "score": 0.9}]

    with patch('src.tools.enterprise_knowledge.retrieve_enterprise_knowledge') as mock_retrieve:
        mock_retrieve.return_value = mock_docs

        # First call should query
        docs1 = await ensure_enterprise_docs(state)
        assert mock_retrieve.call_count == 1

        # Second call should use cache
        docs2 = await ensure_enterprise_docs(state)
        assert mock_retrieve.call_count == 1  # No new call

        assert docs1 == docs2 == mock_docs
```

- [ ] **Step 2: Run integration test**

```bash
uv run pytest tests/integration/test_enterprise_kb_integration.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_enterprise_kb_integration.py
git commit -m "test(integration): add enterprise KB integration test"
```

---

## 实现顺序

1. **Task 1**: InterviewState 新增字段
2. **Task 2**: 企业知识库检索客户端
3. **Task 3**: EvaluateAgent 集成
4. **Task 4**: FeedbackAgent 集成
5. **Task 5**: skill_point 提取辅助函数
6. **Task 6**: 集成测试验证

---

## 注意事项

1. **企业 KB API 尚未部署** - 当前实现使用 mock，待 enterprise-kb 项目完成部署后可切换
2. **向后兼容** - 如果企业 KB 不可用，流程应正常降级（返回空列表）
3. **状态清理** - 每个问题结束后应清理 `enterprise_docs_retrieved` 标志
