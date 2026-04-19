# 企业知识库 RAG 系统设计

**日期**: 2026-04-19
**类型**: 独立项目
**目的**: 为公司内部各项目提供统一的企业级知识检索服务

---

## 1. 项目概述

企业知识库 RAG 系统是一个独立的项目（`enterprise-kb`），通过 Git Hook 自动从 Markdown 文档构建索引，提供标准化的 REST API 供其他项目查询企业级最佳实践和技术规范。

---

## 2. 核心架构

```
enterprise-kb/
├── enterprise-kb/              # Markdown 源文档
│   ├── 用户认证模块.md
│   ├── 订单处理模块.md
│   └── ...
├── src/enterprise_kb/
│   ├── __init__.py
│   ├── api.py                 # FastAPI 服务
│   ├── retriever.py           # 检索逻辑 (HybridRetriever)
│   ├── indexer.py             # 索引构建
│   └── models.py              # 数据模型
├── pgvector/                  # 向量数据 (SQLite/文件)
├── pyproject.toml
└── uv.lock
```

---

## 3. 文档格式规范

### 3.1 Markdown 文档结构

```markdown
---
skill_points:
  - 用户登录
  - Token管理
  - SSO单点登录
module: 用户认证
score_points:
  - 基本: 是否理解登录流程原理
  - 进阶: 能否说明 Token 过期处理
  - 高级: 是否有安全意识（敏感信息处理）
---
# 用户认证模块

## 功能规范

### 1. 登录流程
...

### 2. Token 管理
...

## 评分要点

### 基础级
- 正确描述登录流程
- 理解 Session vs Token 区别

### 进阶级
- 说明 Token 过期处理机制
- 描述 Refresh Token 用途

### 高级
- 安全意识：密码加密存储
- 防御能力：SQL注入防护、XSS防护
```

### 3.2 Front-matter 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `skill_points` | list[str] | 关联的技能点列表 |
| `module` | str | 所属模块名（唯一） |
| `score_points` | list[str] | 评分要点 |

---

## 4. API 接口设计

### 4.1 按技能点检索

```bash
POST /retrieve/by-skill
Content-Type: application/json

{
  "skill_point": "Redis缓存",
  "top_k": 5
}

# Response
{
  "documents": [
    {
      "content": "...",
      "metadata": {
        "module": "缓存系统",
        "skill_points": ["Redis", "缓存"],
        "score_points": ["基础: ...", "进阶: ..."],
        "source": "缓存系统模块.md"
      },
      "score": 0.95
    }
  ],
  "total": 1
}
```

### 4.2 按模块检索

```bash
POST /retrieve/by-module
Content-Type: application/json

{
  "module": "用户认证",
  "top_k": 5
}

# Response
{
  "documents": [
    {
      "content": "...",
      "metadata": {
        "module": "用户认证",
        "skill_points": ["用户登录", "Token管理"],
        "score_points": ["基础: ...", "进阶: ..."],
        "source": "用户认证模块.md"
      },
      "score": 0.98
    }
  ],
  "skill_points": ["用户登录", "Token管理", "SSO单点登录"],
  "total": 1
}
```

### 4.3 健康检查

```bash
GET /health

# Response
{
  "status": "healthy",
  "indexed_modules": 15,
  "indexed_documents": 48
}
```

---

## 5. 索引构建流程

### 5.1 Git Hook 触发

```bash
# .git/hooks/post-commit 或 pre-push
#!/bin/bash
uv run python scripts/build_index.py --source ./enterprise-kb/
```

### 5.2 分块策略 (Chunking)

采用 **按 Markdown 标题层级分块**，保持语义完整性：

```python
def chunk_by_headings(content: str, source: str, metadata: dict) -> list[Chunk]:
    """
    按 Markdown 标题层级（## / ###）切分文档
    
    Args:
        content: Markdown 原始内容
        source: 文档来源文件名
        metadata: front-matter 解析的元数据
    
    Returns:
        Chunk 列表，每个 chunk 包含：
        - content: 块文本内容
        - level: 标题层级 (1=#, 2=##, 3=###)
        - parent_heading: 父标题路径
        - chunk_index: 块序号
    """
    chunks = []
    lines = content.split('\n')
    
    current_section = ""
    current_level = 0
    parent_headings = []
    
    for line in lines:
        if line.startswith('### '):
            # 保存前一个 chunk
            if current_section.strip():
                chunks.append(create_chunk(current_section, current_level, parent_headings, metadata))
            
            # 更新标题路径
            parent_headings.append(line[4:])
            current_level = 3
            current_section = line + "\n"
            
        elif line.startswith('## '):
            if current_section.strip():
                chunks.append(create_chunk(current_section, current_level, parent_headings, metadata))
            
            parent_headings = [line[3:]]
            current_level = 2
            current_section = line + "\n"
            
        else:
            current_section += line + "\n"
    
    # 保存最后一个 chunk
    if current_section.strip():
        chunks.append(create_chunk(current_section, current_level, parent_headings, metadata))
    
    return chunks
```

**Chunk 元数据结构**：

```python
@dataclass
class Chunk:
    content: str              # 块文本内容
    chunk_index: int           # 块序号
    level: int                # 标题层级 (1, 2, 3)
    parent_heading: str       # 父标题（如 "2. Token 管理"）
    heading_path: str          # 完整路径（如 "功能规范 > 2. Token 管理"）
    source: str               # 来源文档名
    module: str               # 模块名（继承自 front-matter）
    skill_points: list[str]   # 关联技能点（继承自 front-matter）
    embedding: list[float]    # 块级向量
```

### 5.3 构建脚本逻辑

```python
# scripts/build_index.py
async def build_index(source_dir: Path):
    # 1. 扫描所有 .md 文件
    documents = list(source_dir.glob("**/*.md"))

    # 2. 解析 front-matter
    parsed_docs = []
    for doc in documents:
        content = doc.read_text()
        fm = parse_front_matter(content)
        chunks = chunk_by_headings(content, doc.name, fm)
        
        for chunk in chunks:
            parsed_docs.append({
                "content": chunk.content,
                "metadata": {
                    "source": chunk.source,
                    "module": chunk.module,
                    "skill_points": chunk.skill_points,
                    "heading_path": chunk.heading_path,
                    "level": chunk.level,
                },
                "embedding": embed_text(chunk.content)
            })

    # 3. 批量存入 pgvector
    await store_in_pgvector(parsed_docs)

    # 4. 更新索引元数据
    await update_index_meta(len(parsed_docs))
```

---

## 6. 模块识别机制

### 6.1 预定义模块描述

每个模块对应一段描述文本，用于向量嵌入匹配：

```python
MODULE_DESCRIPTIONS = {
    "用户认证": "用户登录、注册、Token管理、SSO单点登录、会话管理...",
    "订单处理": "订单创建、订单查询、订单取消、订单状态流转...",
    "支付系统": "支付网关、支付回调、退款处理、账务对账...",
    # ...
}
```

### 6.2 最近邻匹配

```python
async def identify_module(responsibility_text: str) -> str | None:
    # 1. 嵌入职责文本
    embedding = embed_text(responsibility_text)

    # 2. 与所有模块描述向量计算相似度
    scores = {}
    for module, desc_embedding in module_embeddings.items():
        scores[module] = cosine_similarity(embedding, desc_embedding)

    # 3. 返回最相似的模块（阈值 0.7）
    best_match = max(scores.items(), key=lambda x: x[1])
    if best_match[1] >= 0.7:
        return best_match[0]
    return None
```

---

## 7. 检索实现

### 7.1 HybridRetriever 融合

```python
# src/enterprise_kb/retriever.py
class EnterpriseKBRetriever:
    def __init__(self):
        self.sparse = BM25SparseRetriever(...)
        self.dense = VectorRetriever(...)
        self.fusion = WeightedRRF(fusion_resolver)
        self.reranker = CrossEncoderReranker(...)

    async def retrieve_by_skill(
        self,
        skill_point: str,
        top_k: int = 5
    ) -> list[Document]:
        # 1. Query Expansion - 扩展 skill_point
        expanded_queries = self._expand_query(skill_point)

        # 2. BM25 关键词检索 (使用扩展查询)
        sparse_results = []
        for query in expanded_queries:
            results = await self.sparse.aretrieve(query, top_k * 2)
            sparse_results.extend(results)

        # 3. 向量语义检索 (使用扩展查询)
        dense_results = []
        for query in expanded_queries:
            results = await self.dense.aretrieve(query, top_k * 2)
            dense_results.extend(results)

        # 4. RRF 融合 (Reciprocal Rank Fusion)
        fused = self.fusion.combine(sparse_results, dense_results)

        # 5. Cross-encoder Reranking
        reranked = await self.reranker.rerank(skill_point, fused[:top_k * 3])

        return reranked[:top_k]

    async def retrieve_by_module(
        self,
        module: str,
        top_k: int = 5
    ) -> list[Document]:
        # 按 module 字段过滤 + 语义检索 + Reranking
        results = await self.dense.aretrieve(module, top_k * 3)
        reranked = await self.reranker.rerank(module, results)
        return reranked[:top_k]
```

### 7.2 Query Expansion

将 skill_point 扩展为多个同义词/相关查询，提高召回率：

```python
# Query Expansion 实现
SKILL_POINT_SYNONYMS = {
    "Redis缓存": ["Redis", "缓存", "Redis缓存", "分布式缓存", "缓存策略"],
    "用户登录": ["登录", "用户认证", "Authentication", "登录验证"],
    "Token管理": ["Token", "JWT", "AccessToken", "RefreshToken", "令牌"],
    "微服务": ["微服务", "Microservice", "服务拆分", "分布式架构"],
    # ...
}

def expand_query(query: str) -> list[str]:
    """扩展查询为多个同义词查询"""
    # 精确匹配优先
    expanded = [query]

    # 查找同义词
    for key, synonyms in SKILL_POINT_SYNONYMS.items():
        if query in synonyms or query == key:
            expanded.extend(synonyms)
            break

    # 去重
    return list(set(expanded))
```

### 7.3 RRF 融合 (Reciprocal Rank Fusion)

```python
def reciprocal_rank_fusion(
    sparse_results: list[tuple[Document, float]],
    dense_results: list[tuple[Document, float]],
    k: int = 60
) -> list[tuple[Document, float]]:
    """
    RRF 融合算法
    
    RRF_score(d) = Σ 1/(k + rank_i(d))
    
    Args:
        sparse_results: BM25 结果 (doc, score)
        dense_results: 向量结果 (doc, score)
        k: 融合参数 (通常 60)
    """
    rrf_scores = defaultdict(float)

    # BM25 结果计分
    for rank, (doc, _) in enumerate(sparse_results):
        rrf_scores[doc.page_content] += 1 / (k + rank + 1)

    # 向量结果计分
    for rank, (doc, _) in enumerate(dense_results):
        rrf_scores[doc.page_content] += 1 / (k + rank + 1)

    # 按 RRF 分数排序
    sorted_docs = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [(doc, score) for doc, score in sorted_docs]
```

### 7.4 Cross-encoder Reranking

用 Cross-encoder 模型对融合结果重排，提高精确率：

```python
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    async def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int = 5
    ) -> list[Document]:
        if not documents:
            return []

        # 构造 query-document pairs
        pairs = [(query, doc.page_content) for doc in documents]

        # 获取 Cross-encoder 分数
        scores = self.model.predict(pairs)

        # 按分数排序
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, _ in doc_scores[:top_k]]
```

### 7.5 API 响应格式

```json
// POST /retrieve/by-module 或 /retrieve/by-skill
{
  "documents": [
    {
      "content": "Token 是服务端生成的用户身份标识...",
      "metadata": {
        "module": "用户认证",
        "skill_points": ["Token管理", "用户登录"],
        "score_points": ["基础: 理解 Token 用途"],
        "source": "用户认证模块.md",
        "heading_path": "功能规范 > 2. Token 管理",
        "level": 3
      },
      "score": 0.92
    }
  ],
  "total": 1
}
```

注意：`skill_points` 不再作为顶层字段返回，而是保留在 `metadata` 中。

---

## 8. 部署架构

### 8.1 常驻服务

```bash
# 启动命令
uv run enterprise-kb serve --host 0.0.0.0 --port 8080

# 环境变量
ENTERPRISE_KB_PGVECTOR_URL=postgresql://...
ENTERPRISE_KB_INDEX_DIR=./pgvector
LOG_LEVEL=INFO
```

### 8.2 Docker 支持 (可选)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "enterprise-kb", "serve", "--port", "8080"]
```

---

## 9. 消费者调用示例

```python
import httpx

async def get_enterprise_knowledge(skill_point: str, module: str | None = None):
    # 优先按 module 检索
    if module:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8080/retrieve/by-module",
                json={"module": module, "top_k": 5}
            )
            if resp.status_code == 200 and resp.json()["documents"]:
                return resp.json()["documents"]

    # Fallback 按 skill_point 检索
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8080/retrieve/by-skill",
            json={"skill_point": skill_point, "top_k": 5}
        )
        return resp.json()["documents"]
```

---

## 10. 待集成事项

- [ ] 创建独立 enterprise-kb repo
- [ ] 实现 FastAPI 服务骨架
- [ ] 实现 Markdown 解析器 (front-matter)
- [ ] 实现 HybridRetriever 检索
- [ ] 实现 pgvector 存储
- [ ] 实现 Git Hook 构建脚本
- [ ] 编写示例文档
- [ ] 部署常驻服务
