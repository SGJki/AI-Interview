---
name: 向量存储
description: RAG 向量存储操作
version: 1.0.0
agent: knowledge
triggers:
  - action: store_vector
---

# 向量存储

## 存储流程

```
职责文本
    ↓
Embedding 模型
    ↓
向量 (1536 维)
    ↓
向量数据库 (Chroma/pgvector)
    ↓
Metadata (resume_id, type, index)
```

## 存储格式

```python
# 存储到 Chroma
document = Document(
    page_content=responsibility_text,
    metadata={
        "type": "responsibility",
        "resume_id": resume_id,
        "responsibility_id": idx,
        "project_id": project_id,
    }
)
vectorstore.add_documents([document])

# 存储到 pgvector (PostgreSQL)
kb = KnowledgeBase(
    project_id=project_id_int,
    type="responsibility",
    content=responsibility_text,
    embedding_id=embedding_id,
)
```

## 检索流程

```python
async def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    filter_metadata: dict = None
) -> list[Document]:
    """检索相关知识"""

    # 1. 查询向量
    results = vectorstore.similarity_search(
        query=query,
        k=top_k,
        filter=filter_metadata,
    )

    return results
```

## 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| top_k | 5 | 返回前 k 个结果 |
| threshold | 0.7 | 相似度阈值 |
| filter_metadata | None | 元数据过滤条件 |

## 元数据过滤

```python
# 按 resume_id 过滤
{"resume_id": "xxx"}

# 按 type 过滤
{"type": "responsibility"}

# 组合过滤
{
    "resume_id": "xxx",
    "type": {"$in": ["responsibility", "project"]}
}
```

## 双存储策略

同时存储到 Chroma 和 PostgreSQL：

| 存储 | 用途 | 优势 |
|------|------|------|
| Chroma | 向量检索 (RAG) | 语义相似度搜索 |
| PostgreSQL | 持久化/关联查询 | 事务支持、复杂查询 |
