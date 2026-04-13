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
