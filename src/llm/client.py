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
    import json
    import re
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_chat_model(temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    content = response.content

    # 提取思考过程
    thinking_content = ""
    thinking_match = re.search(r'<think>([\s\S]*?)?</think>', content)
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
