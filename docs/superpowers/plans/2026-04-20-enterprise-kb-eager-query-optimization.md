# 企业知识库提前查询优化计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将企业知识库查询从 EvaluateAgent（用户回答后）提前到 QuestionAgent（问题生成时），减少用户感知延迟。同时修复 `current_module` 和 `current_skill_point` 从未被设置的 bug。

**Architecture:** 使用 LangChain `with_structured_output()` schema 约束 QuestionAgent LLM 输出，同时输出 question、module、skill_point。解析后设置到 state 并立即查询企业 KB。EvaluateAgent 直接使用已缓存的 KB 文档。

**Tech Stack:** Python, LangChain structured output (Pydantic/JSON Schema), httpx, InterviewState

---

## 问题分析

### 当前问题

1. **current_module 和 current_skill_point 从未被设置**
   - `InterviewState` 定义了这两个字段
   - 但没有任何地方设置它们
   - 导致 `ensure_enterprise_docs()` 总是使用 `module=None, skill_point=None`

2. **KB 查询延迟**
   - 当前流程：`question_agent` → `evaluate_agent`（用户回答后）→ `ensure_enterprise_docs()`
   - 用户必须等待 KB 查询完成才能看到反馈
   - 感知延迟 = LLM评估 + KB查询 + 反馈生成

### 解决方案

**核心思路：** 在 QuestionAgent 生成问题时，让 LLM 使用结构化输出同时输出 `module` 和 `skill_point`。利用这个信息：
1. 问题生成后立即设置 `state.current_module` 和 `state.current_skill_point`
2. 问题生成后立即查询企业 KB（用户思考问题时后台进行）
3. EvaluateAgent 直接使用缓存的 KB 文档，无需等待

**为什么用 Schema 而非 Prompt 约束？**
- Prompt 约束依赖 LLM "听话"，可能输出格式不稳定
- Schema 约束由 LangChain 底层强制执行，输出100%符合预期
- 支持 JSON Schema 验证，解析100%可靠

---

## 文件变更概览

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `src/domain/models.py` | 修改 | 添加 QuestionResult Pydantic 模型 |
| `src/llm/client.py` | 修改 | get_chat_model 支持 structured_output_schema 参数 |
| `src/services/llm_service.py` | 修改 | 添加 generate_question_structured 方法 |
| `src/agent/question_agent.py` | 修改 | 设置 state.current_module/skill_point 并调用 KB 查询 |
| `src/agent/evaluate_agent.py` | 修改 | 移除 ensure_enterprise_docs 调用（已缓存） |
| `tests/test_question_agent.py` | 修改 | 添加 question + module + skill_point 测试 |

---

## Task 1: 添加 QuestionResult Pydantic 模型和 LLM Service 改造

**Files:**
- Modify: `src/domain/models.py`
- Modify: `src/llm/client.py`
- Modify: `src/services/llm_service.py`

**Tasks:**

- [ ] **Step 1: 添加 QuestionResult 模型到 domain/models.py**

```python
from pydantic import BaseModel, Field

class QuestionResult(BaseModel):
    """问题生成的结构化结果"""
    question: str = Field(description="面试问题文本，≤50字符，中文问号结尾")
    module: str = Field(default="", description="所属模块名称，如'用户认证'")
    skill_point: str = Field(default="", description="关联技能点，如'Token管理'")
```

- [ ] **Step 2: 修改 get_chat_model 支持 structured output**

修改 `src/llm/client.py` 中的 `get_chat_model` 函数：

```python
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def get_chat_model(
    temperature: float = 0.7,
    structured_output_schema: Optional[Type[BaseModel]] = None,
) -> ChatOpenAI:
    """
    获取 ChatOpenAI 实例（支持结构化输出）

    Args:
        temperature: 采样温度
        structured_output_schema: Pydantic 模型类，用于结构化输出
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = ChatOpenAI(
            model=os.environ.get("LLM_MODEL", "glm-4"),
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            temperature=temperature,
        )

    if structured_output_schema:
        return _llm_client.with_structured_output(structured_output_schema)

    return _llm_client
```

- [ ] **Step 3: 添加 generate_question_structured 方法到 LLM Service**

在 `src/services/llm_service.py` 中添加：

```python
async def generate_question_structured(
    self,
    series_num: int = 1,
    question_num: int = 1,
    interview_mode: str = "free",
    topic_area: str = "技术能力",
    knowledge_context: str = "",
    responsibility_context: str = "",
) -> QuestionResult:
    """
    使用结构化输出生成面试问题

    Returns:
        QuestionResult: 包含问题内容、module 和 skill_point
    """
    from src.domain.models import QuestionResult
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = QUESTION_GENERATION_PROMPT.format(
        resume_info=self.resume_info,
        series_num=series_num,
        question_num=question_num,
        interview_mode=interview_mode,
        topic_area=topic_area,
        knowledge_context=knowledge_context or "无相关上下文",
        responsibility_context=responsibility_context or "",
    )

    # 使用结构化输出
    llm = get_chat_model(temperature=0.7, structured_output_schema=QuestionResult)

    messages = [
        SystemMessage(content="你是一个专业的AI面试官。"),
        HumanMessage(content=prompt),
    ]

    try:
        result: QuestionResult = await llm.ainvoke(messages)
        return result
    except Exception as e:
        logger.warning(f"Structured output failed: {e}, using fallback")
        return QuestionResult(
            question="请介绍一下你最近做的项目，以及在其中承担的角色？",
            module="",
            skill_point=""
        )
```

- [ ] **Step 4: 验证导入和类型正确**

```bash
uv run python -c "
from src.domain.models import QuestionResult
from src.services.llm_service import InterviewLLMService
print('Import OK')
print('QuestionResult fields:', QuestionResult.model_fields.keys())
"
```

- [ ] **Step 5: Commit**

```bash
git add src/domain/models.py src/llm/client.py src/services/llm_service.py
git commit -m "feat(llm): add structured output support for question generation"
```

---

## Task 2: 修改 QuestionAgent 设置 module/skill_point 并提前查询 KB

**Files:**
- Modify: `src/agent/question_agent.py`

**Tasks:**

- [ ] **Step 1: 修改 generate_initial 函数**

```python
async def generate_initial(
    state: InterviewState,
    resume_context: str,
    responsibility: str = "",
) -> InterviewState:
    """生成初始问题"""
    from src.services.llm_service import InterviewLLMService

    llm = get_llm_service()
    llm.resume_info = resume_context

    # 使用结构化输出生成问题
    result = await llm.generate_question_structured(
        series_num=state.current_series,
        question_num=1,
        interview_mode=state.interview_mode.value,
        topic_area="技术能力",
        knowledge_context="",
        responsibility_context=responsibility,
    )

    question = Question(
        content=result.question,
        question_type=QuestionType.INITIAL,
        series=state.current_series,
        number=1,
        parent_question_id=None,
    )

    # 设置 module 和 skill_point 到 state
    state.current_module = result.module if result.module else None
    state.current_skill_point = result.skill_point if result.skill_point else None
    state.current_question = question

    # 立即查询企业 KB（后台进行，用户思考时可以并行）
    if state.current_module or state.current_skill_point:
        asyncio.create_task(self._ensure_enterprise_docs(state))

    return state
```

- [ ] **Step 2: 添加 _ensure_enterprise_docs 辅助方法**

在 QuestionAgent 类中添加：

```python
async def _ensure_enterprise_docs(self, state: InterviewState):
    """后台查询企业 KB 并缓存到 state"""
    from src.tools.enterprise_knowledge import ensure_enterprise_docs
    try:
        await ensure_enterprise_docs(state)
    except Exception as e:
        logger.warning(f"Enterprise KB query failed: {e}")
```

- [ ] **Step 3: 修改 generate_followup 函数**

同样修改 `generate_followup` 函数。

- [ ] **Step 4: 添加 import**

确保 `question_agent.py` 顶部有：

```python
import asyncio
```

- [ ] **Step 5: 验证语法正确**

```bash
uv run python -c "from src.agent.question_agent import generate_initial, generate_followup; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add src/agent/question_agent.py
git commit -m "feat(question_agent): set module/skill_point and eagerly query enterprise KB"
```

---

## Task 3: 修改 EvaluateAgent 使用已缓存的 KB 文档

**Files:**
- Modify: `src/agent/evaluate_agent.py`

**Tasks:**

- [ ] **Step 1: 移除 ensure_enterprise_docs 调用**

修改 `evaluate_with_standard` 和 `evaluate_without_standard` 函数，移除 KB 查询调用（KB 已在 question_agent 时缓存）。

- [ ] **Step 2: Commit**

```bash
git add src/agent/evaluate_agent.py
git commit -m "refactor(evaluate): use cached enterprise KB docs instead of lazy query"
```

---

## Task 4: 更新测试

**Files:**
- Modify: `tests/test_question_agent.py`

**Tasks:**

- [ ] **Step 1: 添加 module/skill_point 测试**

```python
class TestQuestionAgentModuleSkillPoint:
    """测试 QuestionAgent 设置 module 和 skill_point"""

    @pytest.mark.asyncio
    async def test_generate_initial_sets_module_and_skill_point(self):
        """Test that generate_initial sets current_module and current_skill_point in state."""
        from src.agent.question_agent import generate_initial
        from src.agent.state import InterviewState
        from src.domain.models import QuestionResult
        from unittest.mock import patch, AsyncMock

        state = InterviewState(
            session_id="test-session",
            resume_id="resume-123",
        )

        mock_result = QuestionResult(
            question="请谈谈Token管理的经验？",
            module="用户认证",
            skill_point="Token管理"
        )

        with patch('src.agent.question_agent.get_llm_service') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate_question_structured.return_value = mock_result
            mock_get_llm.return_value = mock_llm

            result_state = await generate_initial(
                state,
                resume_context="简历内容",
                responsibility="后端开发"
            )

            assert result_state.current_module == "用户认证"
            assert result_state.current_skill_point == "Token管理"
```

- [ ] **Step 2: 验证测试通过**

```bash
uv run pytest tests/test_question_agent.py -v 2>&1 | tail -40
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_question_agent.py
git commit -m "test(question_agent): add module/skill_point and KB eager query tests"
```

---

## 实现顺序

1. **Task 1**: 添加 QuestionResult 模型 + LLM Service 改造
2. **Task 2**: 修改 QuestionAgent 设置 module/skill_point 并提前查询
3. **Task 3**: 修改 EvaluateAgent 使用缓存
4. **Task 4**: 更新测试

---

## 预期效果

**Before:**
```
用户回答 → 等待 EvaluateAgent → 等待 KB 查询 → 看到反馈
           (用户感知延迟包括 KB 查询时间)
```

**After:**
```
用户回答 → 立即看到反馈（KB 已在用户思考时查询完）
           (KB 查询与用户思考并行进行)
```

---

## 注意事项

1. **流式输出兼容**: 当前 `generate_question_stream` 方法用于实时展示问题，但结构化输出不支持流式。两种方案：
   - 方案A：非流式生成问题 → 设置 state → 流式回显给用户
   - 方案B：保留原流式方法用于展示，结构化结果仅用于 KB 查询
2. **Schema 约束优势**: 使用 `with_structured_output()` 后，LLM 输出100%符合 schema，无需 JSON 解析容错
3. **KB 查询失败处理**: 如果 KB 查询失败，`state.enterprise_docs` 为空列表，评估逻辑应正常降级