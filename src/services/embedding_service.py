"""
Embedding Service for AI Interview Agent

提供文本嵌入和相似度计算功能
"""

from typing import Optional
import numpy as np

from langchain_community.embeddings import DashScopeEmbeddings

from src.config import get_embedding_config


# 全局嵌入实例（延迟初始化）
_embedding_instance: Optional[DashScopeEmbeddings] = None


def _get_embeddings() -> DashScopeEmbeddings:
    """获取或创建 DashScope 嵌入实例"""
    global _embedding_instance
    if _embedding_instance is None:
        cfg = get_embedding_config()
        _embedding_instance = DashScopeEmbeddings(
            model=cfg.model,
            dashscope_api_key=cfg.api_key,
        )
    return _embedding_instance


async def _get_embedding_langchain(texts: list[str]) -> list[list[float]]:
    """
    使用 LangChain DashScopeEmbeddings 获取嵌入

    Args:
        texts: 文本列表

    Returns:
        embedding 向量列表
    """
    embeddings = _get_embeddings()
    # DashScopeEmbeddings.embed_documents 是同步方法
    return await embeddings.aembed_documents(texts)


async def compute_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度

    Args:
        text1: 文本1
        text2: 文本2

    Returns:
        相似度分数 (0.0 - 1.0)
    """
    embeddings = await _get_embedding_langchain([text1, text2])

    if len(embeddings) != 2:
        return 0.0

    vec1 = np.array(embeddings[0])
    vec2 = np.array(embeddings[1])

    # 计算余弦相似度
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


async def compute_similarities(text: str, text_list: list[str]) -> list[tuple[str, float]]:
    """
    计算一个文本与列表中所有文本的相似度

    Args:
        text: 查询文本
        text_list: 目标文本列表

    Returns:
        按相似度降序排列的列表，每个元素为 (文本, 相似度)
    """
    if not text_list:
        return []

    all_texts = [text] + text_list
    embeddings = await _get_embedding_langchain(all_texts)

    query_embedding = np.array(embeddings[0])
    target_embeddings = [np.array(e) for e in embeddings[1:]]

    # 计算每个目标文本与查询文本的相似度
    similarities = []
    for i, target_emb in enumerate(target_embeddings):
        dot_product = np.dot(query_embedding, target_emb)
        norm1 = np.linalg.norm(query_embedding)
        norm2 = np.linalg.norm(target_emb)

        if norm1 == 0 or norm2 == 0:
            similarities.append((text_list[i], 0.0))
        else:
            similarity = dot_product / (norm1 * norm2)
            similarities.append((text_list[i], float(similarity)))

    # 按相似度降序排列
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities


async def get_text_embedding(text: str) -> list[float]:
    """
    获取文本的 embedding 向量

    Args:
        text: 输入文本

    Returns:
        embedding 向量
    """
    embeddings = await _get_embedding_langchain([text])
    return embeddings[0] if embeddings else []
