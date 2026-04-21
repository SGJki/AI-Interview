# AI Interview Agent

基于 LangGraph + LangChain 的智能 AI 模拟面试官 Agent，支持多系列面试、实时点评、流式输出和专项训练功能。

## 项目概述

AI Interview Agent 能够：

- **智能提问**: 根据简历信息生成多系列面试问题
- **深度理解**: 解析项目源代码，作为面试回答标准
- **实时反馈**: 支持实时点评和全程记录两种反馈模式
- **追问引导**: 基于偏差检测的智能追问引导机制
- **专项训练**: 针对特定技能点进行深入训练
- **企业知识**: 企业级知识库提前查询，减少用户响应延迟

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Agent 框架 | LangGraph + LangChain | 多状态、多阶段 Agent |
| 大模型 | ChatGLM (智谱 GLM) | OpenAI API 兼容 |
| 向量数据库 | PostgreSQL + pgvector | RAG 检索 |
| 关系数据库 | PostgreSQL | 主数据存储 |
| 缓存 | Redis | 短中期记忆、会话管理 |
| API 框架 | FastAPI | 高性能 API + SSE 流式 |
| 测试 | pytest + pytest-asyncio | 733 测试用例 |

---

## Scripts

| 命令 | 说明 |
|------|------|
| `uv run python main.py` | 启动服务 |
| `uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` | 启动 FastAPI 服务 |
| `uv run pytest tests/ -v` | 运行所有测试 |
| `uv run pytest tests/ --cov=src --cov-report=term-missing` | 运行测试 + 覆盖率 |
| `uv run pytest tests/test_xxx.py -v` | 运行特定测试文件 |
| `uv run python scripts/init_db.py` | 初始化数据库 |
| `uv run ruff check src/` | 代码检查 |
| `uv run ruff format src/` | 代码格式化 |

---

## 快速开始

### 1. 环境要求

| 服务 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 15+ | 主数据存储，需要 pgvector 扩展 |
| Redis | 6+ | 会话缓存和记忆存储 |
| Python | 3.10+ | 运行环境 |

### 2. 启动依赖服务

#### 启动 PostgreSQL

```bash
# macOS (使用 Homebrew)
brew services start postgresql@15
brew services start postgresql@16

# Linux (使用 systemd)
sudo systemctl start postgresql

# Windows (使用 Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres --name postgres pgvector/pgvector:pg16
```

#### 启动 Redis

```bash
# macOS (使用 Homebrew)
brew services start redis

# Linux (使用 systemd)
sudo systemctl start redis

# Windows (使用 Docker)
docker run -d -p 6379:6379 --name redis redis:alpine
```

#### 初始化数据库（首次运行）

```bash
# 初始化数据库表和 pgvector 扩展
uv run python scripts/init_db.py
```

### 3. 安装依赖

```bash
# 激活 uv 虚拟环境
.venv\Scripts\activate

# 安装依赖（如果需要）
uv sync
```

### 4. 启动服务

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 6. 运行测试

```bash
uv run pytest tests/ -v
```

### 快速验证

服务启动后，可通过以下方式验证：

```bash
# 健康检查
curl http://localhost:8000/health

# 响应示例
{"status":"healthy","service":"ai-interview"}
```

---

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
│  InterviewService  TrainingService  KnowledgeService        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer (LangGraph)                  │
│  Main Orchestrator + 6 Agent Subgraphs                     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Memory Layer                           │
│  LangGraph State │ Redis │ PostgreSQL + pgvector           │
└─────────────────────────────────────────────────────────────┘
```

### Orchestrator Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Orchestrator Graph                               │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐
  │   init   │  (初始化: phase, current_series, followup_depth)
  └────┬─────┘
       │
       ▼
  ┌──────────────┐
  │ orchestrator │  (根据 phase 决定下一步)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ decide_next  │  (条件路由: 根据 state 决定 next_action)
  └──┬───────┬───┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► resume_agent   │ (简历解析)
     │       ├──► knowledge_agent│ (知识检索)
     │       ├──► question_agent  │ (生成问题 + 后台 KB 查询)
     │       ├──► evaluate_agent  │ (评估回答)
     │       ├──► review_agent   │ (审查评估质量)
     │       ├──► feedback_agent │ (生成反馈)
     │       └──► end_interview  │ (结束面试)
     │
     ▼
  [END]
```

### Enterprise KB Eager Query

```
用户思考期间 (后台并行)
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ QuestionAgent: generate_initial / generate_followup              │
│   1. LLM 生成问题 + module + skill_point                         │
│   2. asyncio.create_task(ensure_enterprise_docs(state))         │
│                   │                                              │
│                   └─→ /retrieve/by-module (优先)                │
│                       或 /retrieve/by-skill (fallback)           │
│                            │                                     │
│                            └─→ state.enterprise_docs             │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ EvaluateAgent: evaluate_with_standard                            │
│   - 直接读取 state.enterprise_docs (已缓存，无额外 KB 调用)       │
└──────────────────────────────────────────────────────────────────┘
```

### 三层记忆架构

| 层级 | 存储 | 说明 |
|------|------|------|
| **短期记忆** | LangGraph State | 当前问题、追问链、KB 文档 |
| **短中期记忆** | Redis | 会话 Q&A、待处理反馈 |
| **长期记忆** | PostgreSQL + pgvector | Q&A 历史、RAG 知识 |

### 三层知识体系

| 层级 | 内容来源 | 存储 | API |
|------|---------|------|-----|
| **模块级知识** | 源代码按模块解析 | pgvector | `/knowledge/query` |
| **项目级理解** | README、架构图、工作流 | pgvector | `/knowledge/query` |
| **企业级知识** | 技术最佳实践、行业标准 | Enterprise KB API | `/retrieve/by-module`, `/retrieve/by-skill` |

---

## Multi-Agent 架构

### Agent 组成

| Agent | 职责 | 核心节点 |
|-------|------|---------|
| **Main Orchestrator** | 主协调 Agent，规则驱动流程控制 | init, orchestrator, decide_next, end_interview |
| **ResumeAgent** | 简历解析与存储 | parse_resume, fetch_old_resume |
| **KnowledgeAgent** | 知识库检索与职责管理 | shuffle_responsibilities, store_to_vector_db, fetch_responsibility |
| **QuestionAgent** | 问题生成、去重、触发后台 KB 查询 | generate_warmup, generate_initial, generate_followup, deduplicate_check |
| **EvaluateAgent** | 回答评估 | evaluate_with_standard, evaluate_without_standard |
| **ReviewAgent** | 审查评估合理性 | review_evaluation |
| **FeedBackAgent** | 反馈生成 | generate_correction, generate_guidance, generate_comment, generate_reminder |

### Agent 流转图

```mermaid
flowchart TB
    subgraph Orchestrator
        A[START] --> B[init]
        B --> C[orchestrator]
        C --> D{decide_next}
    end

    subgraph Agents
        D -->|resume_agent| E[ResumeAgent]
        D -->|knowledge_agent| F[KnowledgeAgent]
        D -->|question_agent| G[QuestionAgent]
        D -->|evaluate_agent| H[EvaluateAgent]
        D -->|review_agent| I[ReviewAgent]
        D -->|feedback_agent| J[FeedBackAgent]
    end

    G --> H
    H --> I
    I --> J
    J --> D

    D -->|end_interview| K[END]
```

### 追问退出条件

- `deviation_score >= 0.8` **且** `depth >= max_followup_depth` → 退出追问
- `deviation_score >= 0.8` → 该逻辑问题去重，不再出现
- `deviation_score < 0.8` → 同一逻辑问题允许重复

---

## RAG 工具 (src/tools/)

| 文件 | 说明 |
|------|------|
| `rag_tools.py` | 知识检索、相似问题检索、标准答案检索 |
| `rag_enhancements.py` | MultiVectorRetriever, HybridRetriever, Reranker, BM25 |
| `enterprise_knowledge.py` | 企业级知识检索 (KB API 客户端) |

**融合算法:**

- RRF (Reciprocal Rank Fusion)
- DRR (Distribution-Based Rank Fusion)
- SBERT (Sentence BERT Cross-Encoder)

---

## 项目结构

```
src/
├── agent/
│   ├── __init__.py              # 导出所有 agent graphs
│   ├── state.py                 # InterviewState (TypedDict), Question, Answer, Feedback
│   ├── base.py                  # AgentPhase, AgentResult, ReviewVoter
│   ├── orchestrator.py          # Main orchestrator graph
│   ├── resume_agent.py          # ResumeAgent subgraph
│   ├── knowledge_agent.py       # KnowledgeAgent subgraph
│   ├── question_agent.py        # QuestionAgent subgraph
│   ├── evaluate_agent.py        # EvaluateAgent subgraph
│   ├── review_agent.py          # ReviewAgent subgraph
│   └── feedback_agent.py        # FeedBackAgent subgraph
├── api/
│   ├── interview.py             # /interview/* 端点
│   ├── training.py              # /train/* 端点
│   ├── knowledge.py            # /knowledge/* 端点
│   └── models.py                # Pydantic 请求/响应模型
├── config/
│   └── __init__.py              # 配置管理
├── db/
│   ├── models.py                # SQLAlchemy 异步模型
│   ├── database.py              # 数据库连接管理
│   ├── vector_store.py          # pgvector 向量存储
│   └── redis_client.py         # Redis 队列/哈希操作
├── domain/
│   ├── enums.py                 # 枚举类型 (QuestionType, FeedbackType 等)
│   └── models.py                # 域模型 (Question, QuestionResult 等)
├── infrastructure/
│   └── session_store.py         # Redis 会话存储操作
├── llm/
│   ├── client.py                # get_chat_model, invoke_llm 等
│   ├── prompts.py               # Prompt 模板
│   └── usage.py                 # LLM 使用量追踪
├── services/
│   ├── interview_service.py     # 核心面试逻辑
│   ├── resume_parser.py         # 简历解析
│   ├── training_selector.py     # 技能选择
│   ├── training_followup.py     # 训练追问扩展
│   └── llm_service.py           # LLM 服务 (结构化输出等)
├── session/
│   ├── context.py               # 会话上下文管理
│   └── snapshot.py              # 状态快照
└── tools/
    ├── rag_tools.py             # RAG 检索
    ├── rag_enhancements.py      # MultiVector, Hybrid, Reranker, BM25
    ├── enterprise_knowledge.py # 企业知识 (KB API 客户端)
    └── code_tools.py            # 源代码解析
```

---

## 配置

所有配置统一管理在 `pyproject.toml` 的 `[tool.ai-interview]` 下：

```toml
[tool.ai-interview.redis]
host = "localhost"
port = 6379
db = 0
password = ""

[tool.ai-interview.database]
url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
pool_size = 10
pool_timeout = 30
pool_recycle = 3600

[tool.ai-interview.llm]
api_key = "your_api_key"
base_url = "https://open.bigmodel.cn/api/paas/v4"
model = "glm-4"
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
question_dedup_threshold = 0.85

[tool.ai-interview.rag]
top_k = 5
reranker_top_k = 10
similarity_threshold = 0.7

[tool.ai-interview.enterprise_kb]
base_url = "http://localhost:8080"
timeout = 10
```

### 环境变量覆盖

配置项支持 `${VAR_NAME}` 格式的环境变量覆盖：

```toml
[tool.ai-interview.database]
url = "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres"
```

---

## 数据模型

### InterviewState (TypedDict)

```python
InterviewState:
  - session_id: str           # 会话ID
  - resume_id: str            # 简历ID
  - phase: str                # 当前阶段 (init, warmup, initial, followup, final_feedback)
  - current_series: int       # 当前系列号
  - current_question: Question # 当前问题
  - current_module: str       # 当前模块
  - current_skill_point: str  # 当前技能点
  - enterprise_docs: list     # 企业KB文档 (已缓存)
  - enterprise_docs_retrieved: bool # KB是否已查询
  - answers: dict             # 回答记录
  - evaluation_results: dict  # 评估结果
  - feedbacks: list           # 反馈记录
  - followup_depth: int       # 追问深度
  - error_count: int          # 连续错误计数
```

### 反馈类型

| 类型 | 说明 | 触发条件 |
|------|------|---------|
| `comment` | 正面点评 | deviation >= 0.6 |
| `correction` | 直接纠错 | deviation < 0.3 |
| `guidance` | 引导追问 | 0.3 <= deviation < 0.6 |
| `reminder` | 错题提醒 | 连续答错 >= error_threshold |

---

## API 端点

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

详细 API 文档请参考 [docs/API_docs.md](docs/API_docs.md)。

---

## SSE 流式输出

面试 API 全程使用 Server-Sent Events (SSE) 实现流式输出。

### SSE 事件类型

| 事件类型 | 说明 |
|---------|------|
| `question` | 问题数据 |
| `feedback` | 即时反馈 (realtime 模式) |
| `end` | 流结束 |
| `error` | 错误 |

### 前端 SSE 解析示例

```javascript
const response = await fetch(`/interview/question?session_id=${id}&stream=true`);
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
        if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
            const data = JSON.parse(line.slice(5).trim());

            if (eventType === 'question') {
                console.log(`Q${data.series}.${data.number}: ${data.content}`);
            } else if (eventType === 'feedback') {
                console.log(`Feedback: ${data.content}`);
            } else if (eventType === 'end') {
                console.log('Interview ended');
            }
        }
    }
}
```

---

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_interview_flow.py -v

# 查看覆盖率
uv run pytest --cov=src --cov-report=term-missing
```

### 关键测试文件

| 文件 | 覆盖内容 |
|------|----------|
| `tests/integration/test_agent_integration.py` | 完整面试流程 |
| `tests/integration/test_enterprise_kb_integration.py` | 企业 KB 缓存 |
| `tests/test_question_agent.py` | 问题生成、module/skill_point 提取 |
| `tests/test_rag_enhancements.py` | MultiVector, Hybrid, Reranker, BM25 |
| `tests/test_evaluate_agent.py` | 回答评估 |
| `tests/test_feedback_agent.py` | 反馈生成 |

---

## API 使用示例

### cURL

```bash
# 开始面试
curl -X POST http://localhost:8000/interview/start \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"r1","session_id":"s1","interview_mode":"free","feedback_mode":"recorded"}'

# SSE 流式获取问题
curl -X GET "http://localhost:8000/interview/question?session_id=s1"

# 提交回答
curl -X POST http://localhost:8000/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","question_id":"q1","user_answer":"我的回答"}'

# 结束面试
curl -X POST "http://localhost:8000/interview/end?session_id=s1"
```

---

## 后续开发

- [ ] 添加认证机制
- [ ] 添加 WebSocket 支持
- [ ] 集成 Spring Boot 应用
- [ ] 多租户支持
- [ ] 前端界面优化

---

## 更新日志

### 2026-04-20 企业知识库优化

#### 已完成

| 优化项 | 说明 |
|--------|------|
| **Eager KB Query** | QuestionAgent 生成问题时并行查询企业 KB，减少用户响应延迟 |
| **Structured Output** | 使用 LangChain `with_structured_output` + Pydantic 模型确保可靠输出 |
| **Module/Skill Point 设置** | 修复 `current_module` 和 `current_skill_point` 从未设置的 bug |
| **KB 缓存机制** | `enterprise_docs_retrieved` 标志防止重复查询 |

### 2026-04-19 Agent 层重构

#### 已完成

| 优化项 | 说明 |
|--------|------|
| **Domain 层拆分** | 独立的 domain/ 目录存放枚举和域模型 |
| **Infrastructure 层** | 独立的 infrastructure/ 目录存放基础设施代码 |
| **Session 层** | 独立的 session/ 目录存放会话管理 |
| **ReviewAgent 新增** | 评估合理性审查 |

### 2026-04-13 高并发/高可用优化

| 优化项 | 说明 |
|--------|------|
| **优雅关闭机制** | 连接追踪、排空机制、分阶段关闭 |
| **健康检查端点** | `/health` `/health/ready` `/health/startup` |
| **SSE 连接追踪** | 追踪活跃连接，关闭时排空 |
| **Redis 异步化** | 同步→异步，解除事件循环阻塞 |
| **Context Catch 异步化** | 同步→异步，解除事件循环阻塞 |

---

## License

MIT
