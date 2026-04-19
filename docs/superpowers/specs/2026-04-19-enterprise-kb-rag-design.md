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

### 5.2 构建脚本逻辑

```python
# scripts/build_index.py
async def build_index(source_dir: Path):
    # 1. 扫描所有 .md 文件
    documents = list(source_dir.glob("**/*.md"))

    # 2. 解析 front-matter 和内容
    parsed_docs = []
    for doc in documents:
        content = doc.read_text()
        metadata = parse_front_matter(content)
        body = extract_body(content)
        parsed_docs.append({
            "content": body,
            "metadata": metadata
        })

    # 3. 生成向量嵌入
    embeddings = embed_texts([d["content"] for d in parsed_docs])

    # 4. 存入 pgvector
    await store_in_pgvector(parsed_docs, embeddings)

    # 5. 更新索引元数据
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

    async def retrieve_by_skill(
        self,
        skill_point: str,
        top_k: int = 5
    ) -> list[Document]:
        # 1. BM25 关键词检索
        sparse_results = await self.sparse.aretrieve(skill_point, top_k * 2)

        # 2. 向量语义检索
        dense_results = await self.dense.aretrieve(skill_point, top_k * 2)

        # 3. RRF 融合 (Reciprocal Rank Fusion)
        fused = self.fusion.combine(sparse_results, dense_results)

        return fused[:top_k]

    async def retrieve_by_module(
        self,
        module: str,
        top_k: int = 5
    ) -> list[Document]:
        # 直接按 module 字段过滤 + 语义检索
        return await self.dense.aretrieve(module, top_k)
```

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
