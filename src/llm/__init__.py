"""
LLM Module for AI Interview Agent

提供 LLM 客户端封装和提示词模板
"""

from src.llm.client import get_llm_client, get_chat_model
from src.llm.prompts import (
    QUESTION_GENERATION_PROMPT,
    ANSWER_EVALUATION_PROMPT,
    FEEDBACK_GENERATION_PROMPT,
    FOLLOWUP_QUESTION_PROMPT,
)

__all__ = [
    "get_llm_client",
    "get_chat_model",
    "QUESTION_GENERATION_PROMPT",
    "ANSWER_EVALUATION_PROMPT",
    "FEEDBACK_GENERATION_PROMPT",
    "FOLLOWUP_QUESTION_PROMPT",
]
