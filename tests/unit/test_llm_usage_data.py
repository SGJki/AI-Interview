import pytest
from src.llm.usage import LLMUsage, LLMResponse, PromptTokensDetails

def test_llm_response_holds_content_and_usage():
    details = PromptTokensDetails(cached_tokens=800)
    usage = LLMUsage(prompt_tokens=1000, completion_tokens=200, prompt_tokens_details=details)
    response = LLMResponse(content="test", usage=usage)
    assert response.content == "test"
    assert response.usage.prompt_tokens_details.cached_tokens == 800
