"""
LLM Client for AI Interview Agent

基于 LangChain 的 ChatOpenAI 客户端，支持 OpenAI 兼容 API（如 GLM）
"""

from typing import Optional, AsyncGenerator
from langchain_openai import ChatOpenAI

from src.config import get_llm_config


# 全局 LLM 客户端缓存
_llm_client: Optional[ChatOpenAI] = None


def get_llm_client() -> ChatOpenAI:
    """
    获取 LLM 客户端（单例）

    配置来自 config/config.toml [tool.ai-interview.llm]

    Returns:
        ChatOpenAI 实例
    """
    global _llm_client

    if _llm_client is None:
        from src.config import get_llm_config as get_cfg

        cfg = get_cfg()
        _llm_client = ChatOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )

    return _llm_client


def get_chat_model(
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """
    获取配置不同的 Chat model 实例

    Args:
        temperature: 采样温度
        max_tokens: 最大 token 数

    Returns:
        ChatOpenAI 实例
    """
    from src.config import get_llm_config as get_cfg

    cfg = get_cfg()

    return ChatOpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        model=cfg.model,
        max_tokens=max_tokens or cfg.max_tokens,
        temperature=temperature,
    )


def _process_llm_response_content(content: str, include_reasoning: bool = False) -> str:
    """
    处理 LLM 响应内容，提取思考标签和干净内容

    Args:
        content: 原始 LLM 响应内容
        include_reasoning: 是否在返回内容中包含思考过程

    Returns:
        处理后的内容。如果 include_reasoning=True，返回格式为：
        "【思考过程】\n{thinking}\n【回答】\n{answer}"
    """
    import re
    import json

    # 提取思考标签内容
    thinking_content = ""
    thinking_match = re.search(r'<think>([\s\S]*?)</think>', content)
    if thinking_match:
        thinking_content = thinking_match.group(0)
    thinking_match2 = re.search(r'<thinking>([\s\S]*?)</thinking>', content)
    if thinking_match2:
        thinking_content = thinking_match2.group(0)

    # 提取"最终输出生成"之后的内容（如果存在）
    if "最终输出生成" in content:
        content = content.split("最终输出生成")[-1].strip()

    # 去除思考标签得到干净内容
    clean_content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    clean_content = re.sub(r'<thinking>[\s\S]*?</thinking>', '', clean_content)

    # 如果内容不是干净的 JSON，尝试提取 JSON 部分
    clean_content = clean_content.strip()
    if not clean_content.startswith("{"):
        # 尝试找到第一个 { 并提取 JSON
        try:
            decoder = json.JSONDecoder()
            first_brace = clean_content.find("{")
            if first_brace >= 0:
                json_content = clean_content[first_brace:]
                decoded, end_idx = decoder.raw_decode(json_content)
                clean_content = json.dumps(decoded, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass  # 保持原内容

    # 根据参数决定返回内容
    if include_reasoning and thinking_content:
        return f"【思考过程】\n{thinking_content}\n\n【回答】\n{clean_content}"
    else:
        return clean_content


async def invoke_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    include_reasoning: bool = False,
) -> str:
    """
    调用 LLM 生成文本

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        temperature: 采样温度
        include_reasoning: 是否在返回内容中包含思考过程

    Returns:
        LLM 生成的文本。如果 include_reasoning=True，返回格式为：
        "【思考过程】\n{thinking}\n【回答】\n{answer}"
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_chat_model(temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    return _process_llm_response_content(response.content, include_reasoning)


async def invoke_llm_with_history(
    messages: list[dict],
    temperature: float = 0.7,
) -> str:
    """
    调用 LLM（带对话历史）

    Args:
        messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
        temperature: 采样温度

    Returns:
        LLM 生成的文本
    """
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    llm = get_chat_model(temperature=temperature)

    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))

    response = await llm.ainvoke(langchain_messages)
    content = response.content

    # 去除 <thinking>...</thinking> 或 <think>...</think> 推理标签
    content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    content = re.sub(r'<thinking>[\s\S]*?</thinking>', '', content)

    return content


async def invoke_llm_stream(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
):
    """
    调用 LLM 生成文本（流式）

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        temperature: 采样温度

    Yields:
        LLM 生成的每个 token
    """
    import re
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_chat_model(temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # 使用 astream 获取流式响应，逐 token yield
    chunk_count = 0
    async for chunk in llm.astream(messages):
        chunk_count += 1
        content = chunk.content
        if content:
            # 不去除思考标签，让思考内容也流式输出
            yield content

    # 如果只有1个chunk，说明API可能不支持流式返回完整内容
    if chunk_count <= 1:
        # 这种情况可能API不支持流式，返回空让调用方知道
        pass


async def invoke_llm_with_usage(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    include_reasoning: bool = False,
) -> LLMResponse:
    """
    调用 LLM 生成文本，并返回使用量信息

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        temperature: 采样温度
        include_reasoning: 是否在返回内容中包含思考过程

    Returns:
        LLMResponse，含生成文本和 usage（prompt_tokens, completion_tokens, cached_tokens）
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.llm.usage import LLMUsage, LLMResponse, PromptTokensDetails

    llm = get_chat_model(temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)

    # 使用 helper 处理内容
    final_content = _process_llm_response_content(response.content, include_reasoning)

    # 提取 usage 信息
    usage_metadata = getattr(response, "usage_metadata", None)
    prompt_tokens = 0
    completion_tokens = 0
    cached_tokens = 0

    if usage_metadata:
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        prompt_tokens = input_tokens if input_tokens else 0
        completion_tokens = output_tokens if output_tokens else 0

        response_metadata = getattr(response, "response_metadata", {})
        cached_tokens = response_metadata.get("cache_tokens", 0) or response_metadata.get("cached_tokens", 0) or 0

    usage = LLMUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=PromptTokensDetails(cached_tokens=cached_tokens),
    )

    return LLMResponse(content=final_content, usage=usage)
