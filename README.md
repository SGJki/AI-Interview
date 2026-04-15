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
| 测试 | pytest + pytest-asyncio | 698 测试用例 |

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
- Web UI: http://localhost:8000 (如果配置了前端)

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
| `orchestrator.py` | Main orchestrator graph - composes all agents |
| `base.py` | AgentPhase, AgentResult, ReviewVoter base classes |
| `resume_agent.py` | ResumeAgent subgraph - Resume parsing and storage |
| `knowledge_agent.py` | KnowledgeAgent subgraph - Knowledge base and responsibility management |
| `question_agent.py` | QuestionAgent subgraph - Question generation and deduplication |
| `evaluate_agent.py` | EvaluateAgent subgraph - Answer evaluation |
| `feedback_agent.py` | FeedBackAgent subgraph - Feedback generation |

## Multi-Agent 架构

### Agent 组成

| Agent | 职责 | 核心节点 |
|-------|------|---------|
| **Main Orchestrator** | 主协调 Agent，规则驱动流程控制 | init, orchestrator, decide_next, final_feedback |
| **ResumeAgent** | 简历解析与存储 | parse_resume, fetch_old_resume |
| **KnowledgeAgent** | 知识库检索与职责管理 | shuffle_responsibilities, find_standard_answer |
| **QuestionAgent** | 问题生成与去重 | generate_warmup, generate_initial, generate_followup |
| **EvaluateAgent** | 回答评估 | evaluate_with_standard, evaluate_without_standard |
| **FeedBackAgent** | 反馈生成 | generate_correction, generate_guidance, generate_comment |

### Agent 流转图

```mermaid
flowchart TB
    subgraph Orchestrator
        A[START] --> B[init]
        B --> C[orchestrator]
        C --> D{decide_next}
    end

    subgraph Agents
        D -->|question_agent| E[QuestionAgent]
        D -->|resume_agent| F[ResumeAgent]
        D -->|knowledge_agent| G[KnowledgeAgent]
        D -->|evaluate_agent| H[EvaluateAgent]
        D -->|feedback_agent| I[FeedBackAgent]
    end

    E --> H
    H --> I
    I --> D

    D -->|final_feedback| J[final_feedback]
    J --> K[END]

    style Orchestrator fill:#e1f5fe
    style Agents fill:#f3e5f5
```

### 主流程时序图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Orch as Orchestrator
    participant QA as QuestionAgent
    participant KA as KnowledgeAgent
    participant EA as EvaluateAgent
    participant FB as FeedBackAgent

    User->>Orch: 开始面试
    Orch->>Orch: init phase
    Orch->>QA: 生成预热问题
    QA-->>User: 预热问题
    User->>Orch: 回答

    loop 面试循环
        Orch->>KA: 查找标准答案
        KA-->>Orch: 标准答案/无标准答案
        Orch->>EA: 评估回答
        EA-->>Orch: 评估结果
        Orch->>FB: 生成反馈
        FB-->>User: 反馈
        Orch->>QA: 生成追问/下一问题
        QA-->>User: 问题
        User->>Orch: 回答
    end

    Orch->>Orch: final_feedback
    Orch-->>User: 最终报告
```

### 各 Agent 内部运行详解

#### 1. ResumeAgent

```mermaid
flowchart LR
    subgraph ResumeAgent
        A{新简历?} -->|Yes| B[parse_resume]
        A -->|No| C[fetch_old_resume]
        B --> D[存储到DB]
        B --> E[提取responsibilities]
        E --> F[Review3审核]
        F -->|通过| G[传给KnowledgeAgent]
        F -->|失败| H[反馈环重试]
        C --> G
    end
```

**职责**: 解析新简历文本或获取已有简历，提取结构化信息。

| 节点 | 功能 |
|------|------|
| `parse_resume` | 调用 LLM 解析简历文本，提取 skills、projects、responsibilities |
| `fetch_old_resume` | 从数据库读取已有简历 |

#### 2. KnowledgeAgent

```mermaid
flowchart TB
    subgraph KnowledgeAgent
        A[接收responsibilities] --> B[shuffle_responsibilities]
        B --> C[随机打乱顺序]
        C --> D[取第一条]
        D --> E[传给QuestionAgent]
        D --> F[其余存入向量库]

        G[标准答案查询] --> H{从mastered_questions查找}
        H -->|找到| I[Review3审核]
        I -->|通过| J[标准答案传给EvaluateAgent]
        I -->|失败| K[重试一次]
        K -->|失败| L[告知无标准答案]
        H -->|未找到| L
    end
```

**职责**: 职责列表随机化、向量库存储、标准答案查找。

| 节点 | 功能 |
|------|------|
| `shuffle_responsibilities` | 随机打乱职责列表，确保面试问题顺序随机 |
| `store_to_vector_db` | 将职责存入 pgvector 向量数据库 |
| `find_standard_answer` | 在 mastered_questions 中查找相似问题的标准答案 |

#### 3. QuestionAgent

```mermaid
flowchart TB
    subgraph QuestionAgent
        A{check_phase} -->|warmup| B[generate_warmup]
        A -->|initial| C[generate_initial]
        A -->|followup| D{deduplicate_check}

        D -->|不重复| E[generate_followup]
        D -->|重复且dev>=0.8| F[跳过]
        D -->|重复且dev<0.8| E

        E --> G[Review3审核]
        G -->|通过| H[输出问题]
        G -->|失败| I[反馈环]

        B --> H
        C --> H
    end
```

**职责**: 生成预热/初始/追问问题，问题去重检查。

| 节点 | 功能 |
|------|------|
| `generate_warmup` | 生成预热问题，让候选人放松 |
| `generate_initial` | 基于简历和职责生成初始问题 |
| `generate_followup` | 基于原始问题、用户回答生成追问 |
| `deduplicate_check` | 检查问题是否重复（逻辑重复检测） |

#### 4. EvaluateAgent

```mermaid
flowchart TB
    subgraph EvaluateAgent
        A{有标准答案?} -->|Yes| B[evaluate_with_standard]
        A -->|No| C[evaluate_without_standard]

        B --> D[Review3审核]
        C --> D
        D -->|通过| E[输出评估结果]
        D -->|失败| F[反馈环重试]
    end
```

**职责**: 使用标准答案或无标准答案模式评估用户回答。

| 节点 | 功能 |
|------|------|
| `evaluate_with_standard` | 有标准答案时，基于标准答案评估偏差度 |
| `evaluate_without_standard` | 无标准答案时，基于问答质量评估 |

**评估输出**:
- `deviation_score`: 偏差分数 (0-1)
- `is_correct`: 是否正确
- `key_points`: 关键点评
- `suggestions`: 改进建议

#### 5. FeedBackAgent

```mermaid
flowchart TB
    subgraph FeedBackAgent
        A[接收evaluation] --> B{dev < 0.3?}
        B -->|Yes| C[CORRECTION纠错]
        B -->|No| D{dev < 0.6?}
        D -->|Yes| E[GUIDANCE引导]
        D -->|No| F[COMMENT点评]

        C --> G[Review3审核]
        E --> G
        F --> G
        G -->|通过| H[输出反馈]
        G -->|失败| I[反馈环]
    end
```

**职责**: 根据偏差分数生成不同类型的反馈。

| 反馈类型 | 触发条件 | 说明 |
|---------|---------|------|
| `correction` | dev < 0.3 | 直接给出正确答案 |
| `guidance` | 0.3 ≤ dev < 0.6 | 提示性追问引导 |
| `comment` | dev ≥ 0.6 | 正面鼓励继续深入 |

### Review 审核机制

每个 Agent 输出后经过 **3 实例投票审核**：

```mermaid
flowchart LR
    A[Agent输出] --> B[Review Voter 1]
    A --> C[Review Voter 2]
    A --> D[Review Voter 3]

    B --> E{通过?}
    C --> E
    D --> E

    E -->|≥2通过| F[输出给下一阶段]
    E -->|<2通过| G[反馈环重试]
```

**审核标准**:

| Agent | 审核项 |
|-------|-------|
| ResumeAgent | responsibilities 非空、技能 ≥3、项目 ≥1 |
| KnowledgeAgent | is_used=false、SessionID 匹配、标准答案契合 |
| QuestionAgent | 问题不重复、追问基于 Q+A+E |
| EvaluateAgent | 评估基于 Q+A、评估合理 |
| FeedBackAgent | 反馈基于 Q+A+E、反馈类型匹配 |

### 追问退出条件

```mermaid
flowchart TB
    A{dev >= 0.8 且 depth >= max?} -->|Yes| B[退出追问]
    A -->|No| C[继续生成追问]
```

- `deviation_score >= 0.8` **且** `depth >= max_followup_depth` → 退出追问
- `deviation_score >= 0.8` → 该逻辑问题去重，不再出现
- `deviation_score < 0.8` → 同一逻辑问题允许重复

### 顶层流程

```mermaid
stateDiagram-v2
    [*] --> init
    init --> orchestrator
    orchestrator --> decide_next
    decide_next --> question_agent: 继续面试
    decide_next --> final_feedback: 结束
    question_agent --> evaluate_agent
    evaluate_agent --> feedback_agent
    feedback_agent --> decide_next
    final_feedback --> [*]
```

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
│ 加载简历知识库  │
│ + responsibilities │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ 基于职责生成    │
│ 系列问题        │
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
 │ 问题去重检查    │
 │ (跨会话)        │
 └─────────────────┘
      │
      ▼
 ┌─────────────────┐
 │ 所有系列完成    │
 │ 输出最终反馈    │
 └─────────────────┘
```

### 基于职责的系列生成

每个面试系列（series）对应简历中的一个职责（responsibility）：

1. **职责提取**: LLM 从简历项目中提取职责列表
2. **随机排序**: 以时间戳为种子打乱职责顺序
3. **系列分配**: 每个系列对应一个职责
4. **针对性提问**: 问题围绕该职责展开

### 数据持久化

| 数据 | 存储位置 | 说明 |
|------|---------|------|
| 简历原始内容 | Chroma | 元数据: `type=raw_resume` |
| 技能列表 | Chroma | 元数据: `type=skills` |
| 项目信息 | Chroma | 元数据: `type=project` |
| 职责列表 | Chroma | 元数据: `type=responsibility` |
| 问答历史 | Redis | 实时会话状态 |
| 面试记录 | PostgreSQL | 持久化数据（待实现） |

## SSE 流式输出

面试 API 全程使用 Server-Sent Events (SSE) 实现流式输出，前端逐 token 显示打字机效果。

### SSE 事件类型

| 事件类型 | 说明 | 数据内容 |
|---------|------|---------|
| `question_start` | 问题开始 | question_id, series, number, question_type |
| `token` | 问题 token | content (单字/词) |
| `question_end` | 问题结束 | question_id |
| `evaluation` | 回答评估 | deviation_score, is_correct, error_count |
| `feedback` | 反馈内容 | feedback_content, feedback_type, guidance |
| `end` | 流结束 | status, should_continue |
| `error` | 错误 | error message |

### 请求处理时序图

#### 1. 开始面试 + 获取问题

```
Client              API                Service              LLM
  │                  │                    │                  │
  │──POST /start────>│                    │                  │
  │                  │──create_service───>│                  │
  │                  │                    │                  │
  │                  │<─question──────────│                  │
  │<─JSON Response───│                    │                  │
  │                  │                    │                  │
  │──GET /question──>│                    │                  │
  │   ?stream=true   │                    │                  │
  │                  │                    │──invoke_llm─────>│
  │                  │                    │<─tokens──────────│
  │<─SSE stream──────│                    │                  │
  │  event:question_start                 │                  │
  │  event:token {content:"第"}           │                  │
  │  event:token {content:"一"}           │                  │
  │  event:token {content:"题"}           │                  │
  │  ...                                  │                  │
  │  event:question_end                   │                  │
  │  event:feedback {...}                 │                  │
  │  event:end {status:"ready"}          │                  │
```

#### 2. 提交回答 + 获取追问

```
Client              API                Service              LLM
  │                  │                    │                  │
  │──POST /answer───>│                    │                  │
  │                  │                    │──_evaluate──────│
  │                  │                    │<─deviation──────│
  │                  │                    │                  │
  │                  │                    │──_generate_fb───>│
  │                  │                    │<─feedback────────│
  │<─SSE stream──────│                    │                  │
  │  event:evaluation {deviation:0.3}    │                  │
  │  event:feedback {content:"..."}       │                  │
  │                  │                    │                  │
  │                  │                    │──_ask_followup──│
  │                  │                    │  (if deviation)  │
  │                  │                    │──invoke_llm─────>│
  │<─SSE stream──────│                    │<─tokens──────────│
  │  event:question_start                 │                  │
  │  event:token {content:"追"}          │                  │
  │  event:token {content:"问"}          │                  │
  │  ...                                  │                  │
  │  event:question_end                   │                  │
  │  event:end {status:"ready"}          │                  │
```

#### 3. 前端 SSE 解析示例

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

            if (eventType === 'question_start') {
                // 问题开始，显示容器
            } else if (eventType === 'token') {
                // 打字机效果：在光标前插入 token
                cursor.insertAdjacentText('beforebegin', data.content);
            } else if (eventType === 'question_end') {
                // 问题完成，移除光标
            } else if (eventType === 'feedback') {
                // 显示反馈（思考过程 + 点评）
            } else if (eventType === 'end') {
                // 启用输入框，准备下一轮
            }
        }
    }
}
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
pool_timeout = 30
pool_recycle = 3600

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
question_dedup_threshold = 0.85

[tool.ai-interview.rag]
top_k = 5
reranker_top_k = 10
similarity_threshold = 0.7
```

### 环境变量覆盖

配置项支持 `${VAR_NAME}` 格式的环境变量覆盖：

```toml
[tool.ai-interview.database]
url = "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres"
```

### 数据库配置验证

启动时会自动验证配置：
- `url` 必须使用 `postgresql+asyncpg://` 驱动
- `pool_size` 建议 1-100
- `max_overflow` 建议 0-50
- `pool_timeout` 建议 1-300 秒
- `pool_recycle` 建议 >= 300 秒（连接健康检查）

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

- 总计: 698 测试用例
- 覆盖: Agent, RAG, API, 数据库, 服务层, 优雅关闭, Redis 异步化

## 项目结构

```
ai-interview/
├── main.py                  # FastAPI 入口
├── pyproject.toml           # 项目配置
├── CLAUDE.md               # Claude 项目说明
├── README.md               # 本文档
├── config/
│   └── config.toml          # 配置文件
├── scripts/
│   └── init_db.py           # 数据库初始化脚本
├── data/
│   └── vectorstore/         # Chroma 向量数据库持久化
├── src/
│   ├── agent/              # LangGraph Agent
│   ├── api/                # FastAPI 路由
│   ├── dao/                # 数据访问层
│   ├── db/                 # 数据库
│   ├── llm/                # LLM 客户端和 Prompt
│   ├── services/           # 业务服务
│   ├── tools/             # 工具函数
│   └── web/                # Web 前端
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

// 3. 提交回答（SSE 流式获取追问）
const answerRes = await fetch('/interview/answer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'session-456',
    question_id: first_question.question_id,
    user_answer: '我的回答是...'
  })
});
const answerReader = answerRes.body.getReader();
// 解析 SSE 流，显示追问打字机效果
// 事件: evaluation → feedback → question_start/token/question_end → end

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

# 提交回答（SSE 流式输出）
curl -X POST http://localhost:8000/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","question_id":"q1","user_answer":"我的回答"}'
# 返回 SSE 流: evaluation → feedback → question_start/token/question_end → end

# 结束面试
curl -X POST "http://localhost:8000/interview/end?session_id=s1"
```

## 后续开发

- [ ] 添加认证机制
- [ ] 添加 WebSocket 支持
- [ ] 集成 Spring Boot 应用
- [ ] 多租户支持
- [ ] 前端界面优化

## 更新日志

### 2026-04-13 高并发/高可用优化

#### 已完成

| 优化项 | 文件 | 说明 |
|--------|------|------|
| **优雅关闭机制** | `src/core/lifespan_manager.py` | 连接追踪、排空机制、分阶段关闭 |
| **健康检查端点** | `src/main.py` | `/health` `/health/ready` `/health/startup` |
| **SSE 连接追踪** | `src/api/interview.py` | 追踪活跃连接，关闭时排空 |
| **Redis 异步化** | `src/tools/memory_tools.py` | 同步→异步，解除事件循环阻塞 |
| **Context Catch 异步化** | `src/core/context_catch.py` | 同步→异步，解除事件循环阻塞 |

#### 技术细节

**优雅关闭 (Graceful Shutdown)**
- 关闭分阶段：停止接受新连接 → 排空活跃连接 → 关闭 DB → 关闭 Redis
- 连接追踪器追踪所有活跃 SSE 连接
- 30s 排空超时，强制关闭

**健康检查端点**
- `GET /health` - 存活检查
- `GET /health/ready` - 就绪检查（含 DB/Redis 依赖检查）
- `GET /health/startup` - 启动探针（K8s startup probe）

**Redis 异步化收益**
- 高并发吞吐提升：从同步串行 → 异步并行
- 事件循环不再阻塞
- 并发 100 请求延迟：从 ~1000ms → ~10ms

#### 待优化项

| 优先级 | 优化项 | 风险 |
|--------|--------|------|
| P0 | 增大数据库连接池 (pool_size=50+) | 连接不足 |
| P0 | LLM 熔断器 + 重试机制 | 级联故障 |
| P0 | Redis Sentinel 高可用 | 单点故障 |
| P1 | SSE 连接数限制 | 资源耗尽 |
| P2 | 请求队列化 | 高峰排队 |

## License

MIT
