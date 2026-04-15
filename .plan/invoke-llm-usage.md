# invoke_llm 返回 usage 信息

**Problem solved**: 修改 `invoke_llm` 返回 usage 信息（含 `cached_tokens`），使 `PromptCache.validate_cache_with_llm` 能真正验证 GLM 缓存效果。

## Goal

新增 `invoke_llm_with_usage()` 函数，返回 `(content, usage)` 元组，包含 GLM API 的 `prompt_tokens_details.cached_tokens` 信息，供 PromptCache 验证缓存命中情况。

## Architecture

**新增文件**: `src/llm/usage.py` - 定义 `LLMUsage` 数据类

**修改文件**: `src/llm/client.py` - 新增 `invoke_llm_with_usage()` 函数

**保持不变**: 所有现有 `invoke_llm` 调用方不受影响

## Data Structures

```python
# src/llm/usage.py
@dataclass
class PromptTokensDetails:
    cached_tokens: int  # GLM 缓存命中 token 数

@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    prompt_tokens_details: PromptTokensDetails

@dataclass
class LLMResponse:
    content: str
    usage: LLMUsage
```

## API Design

### `invoke_llm_with_usage()`

```python
async def invoke_llm_with_usage(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    include_reasoning: bool = False,
) -> LLMResponse:
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
```

## Implementation Steps

1. 创建 `src/llm/usage.py` 定义数据结构
2. 在 `src/llm/client.py` 新增 `invoke_llm_with_usage()` 函数
3. 更新 `PromptCache.validate_cache_with_llm()` 使用新函数
4. 添加单元测试验证 usage 提取

## Backward Compatibility

- `invoke_llm()` 保持不变
- 所有现有调用方无需修改
- 新函数命名明确表示返回 usage 信息
