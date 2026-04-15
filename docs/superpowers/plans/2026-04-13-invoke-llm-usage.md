# invoke_llm_with_usage 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `invoke_llm_with_usage()` 函数，返回包含 `content` 和 `usage`（含 `cached_tokens`）的 `LLMResponse`，使 `PromptCache.validate_cache_with_llm` 能验证 GLM 缓存效果。

**Architecture:** 新增 `src/llm/usage.py` 定义数据结构，新增 `invoke_llm_with_usage()` 函数，现有 `invoke_llm()` 保持不变以保证向后兼容。

**Tech Stack:** Python dataclass, LangChain ChatOpenAI, pytest

---

## 文件结构

```
src/llm/
├── client.py          # 修改 - 新增 invoke_llm_with_usage()
└── usage.py          # 新建 - LLMUsage, LLMResponse 数据类

src/core/
└── prompt_cache.py    # 修改 - validate_cache_with_llm() 使用新函数

tests/unit/
└── test_llm_usage.py  # 新建 - 单元测试
```

---

## Task 1: 创建 usage.py 数据类

**Files:**
- Create: `src/llm/usage.py`
- Test: `tests/unit/test_llm_usage.py`

- [ ] **Step 1: 创建 usage.py 定义数据类**

```python
# src/llm/usage.py
"""
LLM Usage 数据类型定义
"""
from dataclasses import dataclass


@dataclass
class PromptTokensDetails:
    """Prompt Token 详情"""
    cached_tokens: int = 0  # GLM 缓存命中 token 数


@dataclass
class LLMUsage:
    """LLM API 调用使用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    prompt_tokens_details: PromptTokensDetails = None

    def __post_init__(self):
        if self.prompt_tokens_details is None:
            self.prompt_tokens_details = PromptTokensDetails()


@dataclass
class LLMResponse:
    """LLM 响应（含 usage）"""
    content: str
    usage: LLMUsage
```

- [ ] **Step 2: 运行测试验证数据结构**

Run: `pytest tests/unit/test_llm_usage.py -v`
Expected: PASS (测试文件待创建，Task 4 再创建)

---

## Task 2: 新增 invoke_llm_with_usage() 函数

**Files:**
- Modify: `src/llm/client.py:180-220`
- Test: `tests/unit/test_llm_usage.py`

- [ ] **Step 1: 在 client.py 末尾添加新函数**

```python
# src/llm/client.py (追加到文件末尾，约第 220 行)

async def invoke_llm_with_usage(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    include_reasoning: bool = False,
) -> "LLMResponse":
    """
    调用 LLM 并返回 usage 信息

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        temperature: 采样温度
        include_reasoning: 是否返回推理过程

    Returns:
        LLMResponse: 包含生成文本和 usage 信息
    """
    import re
    from langchain_core.messages import HumanMessage, SystemMessage
    from src.llm.usage import LLMResponse, LLMUsage, PromptTokensDetails

    llm = get_chat_model(temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    content = response.content

    # 提取思考标签内容
    thinking_content = ""
    thinking_match = re.search(r'<think>([\s\S]*?)</think>', content)
    if thinking_match:
        thinking_content = thinking_match.group(0)
    thinking_match2 = re.search(r'<thinking>([\s\S]*?)</thinking>', content)
    if thinking_match2:
        thinking_content = thinking_match2.group(0)

    # 提取"最终输出生成"之后的内容
    if "最终输出生成" in content:
        content = content.split("最终输出生成")[-1].strip()

    # 去除思考标签得到干净内容
    clean_content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    clean_content = re.sub(r'<thinking>[\s\S]*?</thinking>', '', clean_content)

    # 去除思考标签得到干净内容
    clean_content = clean_content.strip()
    if not clean_content.startswith("{"):
        try:
            decoder = json.JSONDecoder()
            first_brace = clean_content.find("{")
            if first_brace >= 0:
                json_content = clean_content[first_brace:]
                decoded, end_idx = decoder.raw_decode(json_content)
                clean_content = json.dumps(decoded, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # 根据参数决定返回内容
    if include_reasoning and thinking_content:
        final_content = f"【思考过程】\n{thinking_content}\n\n【回答】\n{clean_content}"
    else:
        final_content = clean_content

    # 提取 usage 信息
    # LangChain ChatOpenAI 的 response 对象包含 usage_metadata
    usage_metadata = getattr(response, "usage_metadata", None)
    prompt_tokens = 0
    completion_tokens = 0
    cached_tokens = 0

    if usage_metadata:
        # LangChain 格式: usage_metadata = {"input_tokens": ..., "output_tokens": ...}
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        prompt_tokens = input_tokens if input_tokens else 0
        completion_tokens = output_tokens if output_tokens else 0

        # 尝试从 response_metadata 中获取 cached_tokens
        response_metadata = getattr(response, "response_metadata", {})
        # GLM API 可能返回 cache_tokens 或 cached_tokens
        cached_tokens = response_metadata.get("cache_tokens", 0) or response_metadata.get("cached_tokens", 0) or 0

    usage = LLMUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=PromptTokensDetails(cached_tokens=cached_tokens),
    )

    return LLMResponse(content=final_content, usage=usage)
```

- [ ] **Step 2: 添加导入**

在 `src/llm/client.py` 文件顶部添加 `from __future__ import annotations` (如不存在)，确保类型注解字符串引用有效。

- [ ] **Step 3: 运行现有测试确保不破坏**

Run: `pytest tests/unit/test_prompt_cache.py tests/unit/test_recovery_manager.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/llm/usage.py src/llm/client.py
git commit -m "feat(llm): add invoke_llm_with_usage() returning usage info"
```

---

## Task 3: 更新 PromptCache.validate_cache_with_llm()

**Files:**
- Modify: `src/core/prompt_cache.py:188-242`
- Test: `tests/unit/test_prompt_cache.py`

- [ ] **Step 1: 更新 validate_cache_with_llm 方法**

修改 `src/core/prompt_cache.py` 中的 `validate_cache_with_llm` 方法：

```python
async def validate_cache_with_llm(
    self,
    session_id: str,
    resume_id: str,
    responsibilities: list[str],
    system_prompt: str,
    test_prompt: str = "缓存验证测试",
) -> PromptCacheState:
    """
    使用真实 LLM 调用验证缓存

    Args:
        session_id: 会话 ID
        resume_id: 简历 ID
        responsibilities: 职责列表
        system_prompt: 系统提示词
        test_prompt: 测试用提示词

    Returns:
        PromptCacheState 实例
    """
    from src.llm.client import invoke_llm_with_usage
    from src.llm.usage import LLMResponse

    cache_key_obj = CacheKey.generate(resume_id, responsibilities)

    try:
        # 调用 LLM
        response: LLMResponse = await invoke_llm_with_usage(
            system_prompt=system_prompt,
            user_prompt=test_prompt,
            temperature=0.0,
        )

        # 提取 cached_tokens
        cached_tokens = response.usage.prompt_tokens_details.cached_tokens

        state = PromptCacheState(
            cache_key=cache_key_obj.cache_key,
            responsibilities_hash=cache_key_obj.responsibilities_hash,
            is_valid=cached_tokens > 0,
            last_cached_tokens=cached_tokens,
            created_at=datetime.now().isoformat(),
        )

        await self.record_cache(session_id, state)
        return state

    except Exception as e:
        logger.error(f"LLM validation failed for session {session_id}: {e}")
        raise
```

- [ ] **Step 2: 运行测试**

Run: `pytest tests/unit/test_prompt_cache.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add src/core/prompt_cache.py
git commit -m "feat(prompt_cache): use invoke_llm_with_usage for cache validation"
```

---

## Task 4: 添加单元测试

**Files:**
- Create: `tests/unit/test_llm_usage.py`
- Modify: `tests/unit/test_prompt_cache.py` (增加集成测试)

- [ ] **Step 1: 创建 usage 数据类测试**

```python
# tests/unit/test_llm_usage.py
"""
单元测试 for LLM Usage 数据类型
"""
import pytest
from dataclasses import dataclass
from src.llm.usage import LLMUsage, LLMResponse, PromptTokensDetails


class TestPromptTokensDetails:
    """测试 PromptTokensDetails 数据类"""

    def test_creation_with_defaults(self):
        details = PromptTokensDetails()
        assert details.cached_tokens == 0

    def test_creation_with_value(self):
        details = PromptTokensDetails(cached_tokens=800)
        assert details.cached_tokens == 800


class TestLLMUsage:
    """测试 LLMUsage 数据类"""

    def test_creation_with_defaults(self):
        usage = LLMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.prompt_tokens_details.cached_tokens == 0

    def test_creation_with_values(self):
        details = PromptTokensDetails(cached_tokens=500)
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=200,
            prompt_tokens_details=details,
        )
        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 200
        assert usage.prompt_tokens_details.cached_tokens == 500


class TestLLMResponse:
    """测试 LLMResponse 数据类"""

    def test_creation(self):
        details = PromptTokensDetails(cached_tokens=800)
        usage = LLMUsage(prompt_tokens=1000, completion_tokens=200, prompt_tokens_details=details)
        response = LLMResponse(content="测试回答", usage=usage)
        assert response.content == "测试回答"
        assert response.usage.prompt_tokens_details.cached_tokens == 800
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/test_llm_usage.py -v`
Expected: PASS

- [ ] **Step 3: 添加 invoke_llm_with_usage mock 测试**

```python
# tests/unit/test_llm_usage.py (追加)

class TestInvokeLlmWithUsage:
    """测试 invoke_llm_with_usage 函数"""

    @pytest.mark.asyncio
    async def test_extracts_cached_tokens_from_response(self):
        """验证从 LangChain 响应中正确提取 cached_tokens"""
        from unittest.mock import MagicMock, AsyncMock, patch

        # Mock LangChain response
        mock_response = MagicMock()
        mock_response.content = "测试回答"
        mock_response.usage_metadata = {"input_tokens": 1000, "output_tokens": 200}
        mock_response.response_metadata = {"cache_tokens": 800}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            from src.llm.client import invoke_llm_with_usage

            result = await invoke_llm_with_usage(
                system_prompt="系统提示",
                user_prompt="用户问题",
                temperature=0.0,
            )

            assert result.content == "测试回答"
            assert result.usage.prompt_tokens == 1000
            assert result.usage.completion_tokens == 200
            assert result.usage.prompt_tokens_details.cached_tokens == 800

    @pytest.mark.asyncio
    async def test_returns_clean_content_without_thinking(self):
        """验证 include_reasoning=False 时返回干净内容"""
        from unittest.mock import MagicMock, AsyncMock, patch

        mock_response = MagicMock()
        mock_response.content = "<think>思考过程</think>这是最终回答"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        mock_response.response_metadata = {}

        with patch("src.llm.client.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            from src.llm.client import invoke_llm_with_usage

            result = await invoke_llm_with_usage(
                system_prompt="系统",
                user_prompt="问题",
                include_reasoning=False,
            )

            assert "<think>" not in result.content
            assert "这是最终回答" in result.content
```

- [ ] **Step 4: 运行所有新测试**

Run: `pytest tests/unit/test_llm_usage.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/test_llm_usage.py
git commit -m "test(llm): add unit tests for invoke_llm_with_usage"
```

---

## 实现顺序总结

1. **Task 1**: 创建 usage.py 数据类 ✅
2. **Task 2**: 新增 invoke_llm_with_usage() 函数 ✅
3. **Task 3**: 更新 PromptCache.validate_cache_with_llm() ✅
4. **Task 4**: 添加单元测试 ✅

---

## 验证命令

```bash
# 运行所有相关测试
uv run pytest tests/unit/test_llm_usage.py tests/unit/test_prompt_cache.py tests/unit/test_recovery_manager.py -v
```

## 后续优化点

1. **流式版本** - 新增 `invoke_llm_stream_with_usage()` 支持流式响应
2. **历史版本** - 新增 `invoke_llm_with_history_and_usage()` 支持对话历史
