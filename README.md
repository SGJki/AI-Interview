# AI Interview Agent

基于 LangGraph + LangChain 的智能 AI 模拟面试官 Agent，支持多系列面试、实时点评、流式输出和专项训练功能。

## 项目概述

AI Interview Agent 能够：

- **智能提问**: 根据简历信息生成多系列面试问题
- **深度理解**: 解析项目源代码，作为面试回答标准
- **实时反馈**: 支持实时点评和全程记录两种反馈模式
- **追问引导**: 基于偏差检测的智能追问引导机制
- **专项训练**: 针对特定技能点进行深入训练

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Agent 框架 | LangGraph + LangChain | 多状态、多阶段 Agent |
| 大模型 | Qwen3-Max (通义千问) | OpenAI API 兼容 |
| 向量数据库 | PostgreSQL + pgvector | RAG 检索 |
| 关系数据库 | PostgreSQL | 主数据存储 |
| 缓存 | Redis | 短中期记忆、会话管理 |
| API 框架 | FastAPI | 高性能 API + SSE 流式 |
| 测试 | pytest + pytest-asyncio | 300+ 测试用例 |

## 快速开始

### 1. 安装依赖

```bash
# 激活 uv 虚拟环境
.venv\Scripts\activate

# 使用 uv 运行
uv run python main.py
```

### 2. 启动服务

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. 运行测试

```bash
uv run pytest tests/ -v
```

## 项目架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Spring App / Postman)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                     │
│  /interview/*  /train/*  /knowledge/*  /rag/*             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  InterviewService  TrainingService  KnowledgeService       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer (LangGraph)                  │
│  State → Nodes (load_context, generate_question, etc.)    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Memory Layer                            │
│  LangGraph State │ Redis │ PostgreSQL + pgvector           │
└─────────────────────────────────────────────────────────────┘
```

### 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                   长期记忆 (RAG + PostgreSQL)              │
│  RAG 向量库 ←→ PostgreSQL (Q&A 历史, 元数据)               │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 写入
                              │
┌─────────────────────────────────────────────────────────────┐
│                   短中期记忆 (Redis)                        │
│  interview:{session_id}:state  → 整个面试 Q&A             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 合并写入
                              │
┌─────────────────────────────────────────────────────────────┐
│                   短期记忆 (LangGraph State)                │
│  → 当前追问链状态（当前问题、追问深度、引导标记）            │
└─────────────────────────────────────────────────────────────┘
```

### 三层知识体系

| 层级 | 内容来源 | 存储方式 |
|------|---------|---------|
| **模块级知识** | 源代码按模块解析 | pgvector |
| **项目级理解** | README、架构图、工作流 | pgvector |
| **企业级知识** | 技术最佳实践、行业标准 | pgvector |

## 核心模块

### Agent (src/agent/)

| 文件 | 说明 |
|------|------|
| `state.py` | InterviewState, Question, Answer, Feedback 数据结构 |
| `graph.py` | LangGraph 定义，包含 8 个节点 |

**LangGraph 节点:**

- `load_context` - 加载简历和 RAG 知识
- `generate_question` - 生成问题
- `evaluate_answer` - 评估回答偏差度
- `generate_feedback` - 生成反馈
- `generate_followup` - 生成追问
- `check_series_complete` - 检查系列是否完成
- `switch_series` - 切换系列
- `end_interview` - 结束面试

### RAG 工具 (src/tools/)

| 文件 | 说明 |
|------|------|
| `rag_tools.py` | 知识检索、相似问题检索、标准答案检索 |
| `rag_enhancements.py` | MultiVectorRetriever, HybridRetriever, Reranker |
| `enterprise_knowledge.py` | 企业级知识动态检索 |
| `memory_tools.py` | SessionStateManager, SessionHealthMonitor |
| `code_tools.py` | 源代码解析工具 |

**融合算法:**

- RRF (Reciprocal Rank Fusion)
- DRR (Distribution-Based Rank Fusion)
- SBERT (Sentence BERT Cross-Encoder)

### 服务层 (src/services/)

| 文件 | 说明 |
|------|------|
| `interview_service.py` | 核心面试逻辑 |
| `resume_parser.py` | 简历解析 |
| `training_selector.py` | 技能点选择 |
| `training_knowledge_matcher.py` | RAG 知识匹配 |
| `training_followup.py` | 训练追问扩展 |

### 数据库 (src/db/)

| 文件 | 说明 |
|------|------|
| `models.py` | SQLAlchemy 异步模型 |
| `database.py` | 数据库连接管理 |
| `vector_store.py` | pgvector 向量存储 |

### DAO 层 (src/dao/)

- `user_dao.py` - 用户操作
- `resume_dao.py` - 简历操作
- `project_dao.py` - 项目操作
- `knowledge_base_dao.py` - 知识库操作
- `interview_session_dao.py` - 面试会话
- `qa_history_dao.py` - Q&A 历史
- `interview_feedback_dao.py` - 反馈记录

### API 层 (src/api/)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/interview/start` | POST | 开始面试 |
| `/interview/question` | GET | SSE 流式获取问题 |
| `/interview/answer` | POST | 提交回答 |
| `/interview/end` | POST | 结束面试 |
| `/train/start` | POST | 开始专项训练 |
| `/train/answer` | POST | 提交训练回答 |
| `/train/end` | POST | 结束训练 |
| `/knowledge/query` | POST | RAG 查询 |
| `/knowledge/build` | POST | 构建知识库 |
| `/health` | GET | 健康检查 |

## 数据模型

### 面试状态

```python
InterviewState:
  - session_id: 会话ID
  - current_series: 当前系列号
  - current_question: 当前问题
  - followup_depth: 追问深度
  - answers: 回答记录
  - feedbacks: 反馈记录
  - interview_mode: 面试模式
  - feedback_mode: 反馈模式
```

### 反馈类型

| 类型 | 说明 | 触发条件 |
|------|------|---------|
| `comment` | 正面点评 | 正确且有深度 |
| `correction` | 直接纠错 | 高偏差 (>0.7) |
| `guidance` | 引导追问 | 中等偏差 (0.3-0.7) |
| `reminder` | 错题提醒 | 连续答错 >= 阈值 |

## 面试流程

```
用户开始面试
      │
      ▼
┌─────────────────┐
│ 加载简历 + RAG  │
│ 知识库          │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ 生成系列1-Q1    │
└─────────────────┘
      │
      ▼
 ┌─────────────────┐
 │   用户回答      │
 └─────────────────┘
      │
      ├─▶ 实时点评 ─▶ 偏差检测 ─▶ 追问/引导/给答案
      │
      └─▶ 全程记录 ─▶ 直接记录
              │
              ▼
 ┌─────────────────┐
 │ 系列间预生成缓存│
 └─────────────────┘
      │
      ▼
 ┌─────────────────┐
 │ 所有系列完成    │
 │ 输出最终反馈    │
 └─────────────────┘
```

## 配置

所有配置统一管理在 `config/config.toml` 的 `[tool.ai-interview]` 下：

```toml
[tool.ai-interview.redis]
host = "localhost"
port = 6379
db = 0
password = ""

[tool.ai-interview.database]
url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
pool_size = 10

[tool.ai-interview.llm]
api_key = "your_api_key"
base_url = "https://xplt.sdu.edu.cn:4000"
model = "Ali-dashscope/Qwen3-Max"
max_tokens = 2048
temperature = 0.7

[tool.ai-interview.embedding]
api_key = "your_embedding_key"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "text-embedding-v3"

[tool.ai-interview.vector]
persist_directory = "./data/vectorstore"
collection_name = "ai_interview_knowledge"

[tool.ai-interview.server]
host = "0.0.0.0"
port = 8000
reload = true
workers = 1

[tool.ai-interview.interview]
default_max_series = 5
default_error_threshold = 2
max_followup_depth = 3
session_ttl = 86400

[tool.ai-interview.rag]
top_k = 5
reranker_top_k = 10
similarity_threshold = 0.7
```

### PostgreSQL 初始化

```bash
# 创建数据库
CREATE DATABASE ai_interview;

# 启用 pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_interview_flow.py -v

# 查看覆盖率
uv run pytest --cov=src --cov-report=term-missing
```

**测试统计:**

- 总计: 300+ 测试用例
- 覆盖: Agent, RAG, API, 数据库, 服务层

## 项目结构

```
ai-interview/
├── main.py                  # FastAPI 入口
├── pyproject.toml           # 项目配置
├── CLAUDE.md               # Claude 项目说明
├── README.md               # 本文档
├── docs/
│   └── API_docs.md         # API 文档
├── migrations/
│   └── 001_initial_schema.sql  # 数据库迁移
├── src/
│   ├── agent/              # LangGraph Agent
│   ├── api/                # FastAPI 路由
│   ├── dao/                # 数据访问层
│   ├── db/                 # 数据库
│   ├── services/           # 业务服务
│   └── tools/             # 工具函数
└── tests/                  # 测试用例
    ├── test_agent_*.py
    ├── test_api_*.py
    ├── test_rag_*.py
    └── ...
```

## API 使用示例

### JavaScript

```javascript
// 1. 开始面试
const startRes = await fetch('/interview/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    resume_id: 'resume-123',
    session_id: 'session-456',
    interview_mode: 'free',
    feedback_mode: 'recorded'
  })
});
const { first_question } = await startRes.json();

// 2. SSE 流式获取问题
const eventSource = new EventSource(`/interview/question?session_id=session-456`);
eventSource.addEventListener('question', (e) => {
  const q = JSON.parse(e.data);
  console.log(`Q${q.series}.${q.number}: ${q.content}`);
});

// 3. 提交回答
await fetch('/interview/answer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'session-456',
    question_id: first_question.question_id,
    user_answer: '我的回答是...'
  })
});

// 4. 结束面试
const endRes = await fetch('/interview/end?session_id=session-456', {
  method: 'POST'
});
const result = await endRes.json();
console.log('Final Feedback:', result.final_feedback);
```

### cURL

```bash
# 开始面试
curl -X POST http://localhost:8000/interview/start \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"r1","session_id":"s1","interview_mode":"free","feedback_mode":"recorded"}'

# 提交回答
curl -X POST http://localhost:8000/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","question_id":"q1","user_answer":"我的回答"}'

# 结束面试
curl -X POST "http://localhost:8000/interview/end?session_id=s1"
```

## 后续开发

- [ ] 添加认证机制
- [ ] 添加 WebSocket 支持
- [ ] 集成 Spring Boot 应用
- [ ] 多租户支持
- [ ] 前端界面优化

## License

MIT
