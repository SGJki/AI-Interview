"""
RAG (Retrieval-Augmented Generation) Tools for AI Interview Agent

使用 LangChain 实现 RAG 检索功能
"""

from typing import Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import os


# =============================================================================
# Vector Store Configuration
# =============================================================================

def get_embeddings():
    """
    获取 embedding 模型

    TODO: 使用智谱 GLM 的 embedding 接口
    目前使用 OpenAI 兼容接口
    """
    # TODO: 替换为智谱 GLM embedding
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.zhipuai.cn/v1")

    return OpenAIEmbeddings(
        api_key=api_key,
        base_url=base_url,
        model="embedding-2"
    )


def get_vectorstore(persist_directory: str = "./data/vectorstore") -> Chroma:
    """
    获取向量数据库实例

    Args:
        persist_directory: 向量数据库持久化路径

    Returns:
        Chroma 实例
    """
    embeddings = get_embeddings()

    return Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )


# =============================================================================
# Retrieval Tools
# =============================================================================

async def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    filter_metadata: Optional[dict] = None
) -> list[Document]:
    """
    检索知识库

    Args:
        query: 检索查询
        top_k: 返回数量
        filter_metadata: 元数据过滤条件

    Returns:
        检索到的文档列表
    """
    if not query.strip():
        return []

    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": top_k,
            "filter": filter_metadata,
        }
    )

    return await retriever.ainvoke(query)


async def retrieve_similar_questions(
    question: str,
    top_k: int = 3
) -> list[Document]:
    """
    检索相似问题

    用于 RAG 问答历史匹配

    Args:
        question: 当前问题
        top_k: 返回数量

    Returns:
        相似问题列表
    """
    if not question.strip():
        return []

    vectorstore = get_vectorstore()

    # 检索时过滤类型为 question 的文档
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": top_k,
            "filter": {"type": "question"},
        }
    )

    return await retriever.ainvoke(question)


async def retrieve_standard_answer(
    question: str,
    top_k: int = 1
) -> Optional[Document]:
    """
    检索标准回答

    Args:
        question: 当前问题
        top_k: 返回数量

    Returns:
        标准回答文档，如果无匹配返回 None
    """
    if not question.strip():
        return None

    vectorstore = get_vectorstore()

    # 使用相似度阈值
    results = await vectorstore.asimilarity_search_with_score(
        question,
        k=top_k,
        filter={"type": "answer"}
    )

    if not results:
        return None

    # 只返回高相似度结果（阈值 0.7）
    best_result, score = results[0]
    if score < 0.7:
        return None

    return best_result


async def retrieve_by_skill_point(
    skill_point: str,
    top_k: int = 5
) -> list[Document]:
    """
    按技能点检索知识

    用于专项训练模式

    Args:
        skill_point: 技能点名称（如 "Redis"、"分布式缓存"）
        top_k: 返回数量

    Returns:
        相关知识文档列表
    """
    if not skill_point.strip():
        return []

    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": top_k,
            "filter": {"skill_point": skill_point},
        }
    )

    return await retriever.ainvoke(skill_point)


# =============================================================================
# Document Addition
# =============================================================================

async def add_to_knowledge_base(
    content: str,
    metadata: dict,
    persist_directory: str = "./data/vectorstore"
) -> None:
    """
    添加文档到知识库

    Args:
        content: 文档内容
        metadata: 元数据（包含 type, skill_point 等）
        persist_directory: 向量数据库路径
    """
    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )

    document = Document(
        page_content=content,
        metadata=metadata,
    )

    vectorstore.add_documents([document])


# =============================================================================
# RAG Tools Class (for LangChain Tool Calling)
# =============================================================================

class RAGTools:
    """
    RAG 工具类

    用于 LangChain Agent 的工具定义
    """

    name = "retrieve_knowledge"
    description = """
    从知识库中检索相关信息。

    Args:
        query: 检索查询字符串
        top_k: 返回结果数量，默认为 5

    Returns:
        相关文档列表
    """

    @staticmethod
    async def invoke(query: str, top_k: int = 5) -> list[Document]:
        return await retrieve_knowledge(query, top_k)


class SimilarQuestionRetriever:
    """相似问题检索工具"""

    name = "retrieve_similar_questions"
    description = """
    从历史面试中检索相似问题及其回答。

    Args:
        question: 当前面试问题
        top_k: 返回数量，默认为 3

    Returns:
        相似问题列表
    """

    @staticmethod
    async def invoke(question: str, top_k: int = 3) -> list[Document]:
        return await retrieve_similar_questions(question, top_k)


class StandardAnswerRetriever:
    """标准回答检索工具"""

    name = "retrieve_standard_answer"
    description = """
    根据问题检索标准回答。

    Args:
        question: 当前面试问题

    Returns:
        标准回答内容，如果无匹配返回 None
    """

    @staticmethod
    async def invoke(question: str) -> Optional[Document]:
        return await retrieve_standard_answer(question)
