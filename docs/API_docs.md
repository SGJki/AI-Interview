# AI Interview Agent - API Documentation

> Version: 0.2.0
> Base URL: `http://localhost:8000`

## Overview

AI Interview Agent 是一个基于 LangGraph + LangChain 的智能面试模拟系统，支持多系列面试、实时点评、流式输出和专项训练功能。

### Features

- **多系列面试**: 支持自由问答和专项训练两种模式
- **实时点评**: 实时反馈 + 全程记录两种反馈模式
- **流式输出**: SSE 流式推送问题、追问和反馈
- **追问机制**: 基于偏差检测的智能追问引导
- **RAG 知识库**: 模块级、项目级、企业级三层知识体系
- **企业 KB 提前查询**: QuestionAgent 生成问题时并行查询企业知识库，减少用户响应延迟
- **会话管理**: Redis 短中期记忆 + PostgreSQL 持久化

---

## Quick Start

### 1. Install Dependencies

```bash
# 激活 uv 虚拟环境
.venv\Scripts\activate

# 或直接使用 uv run
uv run python main.py
```

### 2. Start Server

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Run Tests

```bash
uv run pytest tests/ -v
```

---

## Architecture

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
│        Main Orchestrator + 6 Agent Subgraphs               │
│  ResumeAgent │ KnowledgeAgent │ QuestionAgent │ ReviewAgent │
│  EvaluateAgent │ FeedBackAgent                              │
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
  │ orchestrator │  (根据 phase 决定下一步: init→warmup→initial→...)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ decide_next  │  (条件路由: 根据 state 决定 next_action)
  └──┬───────┬───┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► resume_agent   │ (简历解析)
     │       │  └─────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► knowledge_agent │ (知识检索)
     │       │  └─────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► question_agent  │ (生成问题 + 触发后台 KB 查询)
     │       │  └────────┬────────┘
     │       │           │         ┌──────────────────────────┐
     │       │           └────────►│ asyncio.create_task       │
     │       │                     │ (ensure_enterprise_docs) │
     │       │                     └──────────────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► evaluate_agent  │ (评估回答 - 读取已缓存的 KB 文档)
     │       │  └─────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► review_agent   │ (审查评估质量)
     │       │  └─────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       ├──► feedback_agent │ (生成反馈)
     │       │  └─────────────────┘
     │       │
     │       │  ┌─────────────────┐
     │       └──► end_interview  │ (结束面试)
     │          └─────────────────┘
     │
     ▼
  [END]

decide_next 条件路由逻辑:
┌──────────────────────────────────────────────────────────────────┐
│  if user_end_requested:       → end_interview                    │
│  if current_series >= max:    → end_interview                    │
│  if error_count >= threshold  → end_interview                    │
│  if all_responsibilities_used → end_interview                     │
│  else:                        → question_agent                    │
└──────────────────────────────────────────────────────────────────┘
```

### Multi-Agent Architecture

```
orchestrator_graph
├── resume_agent_graph      → parse_resume, fetch_old_resume
├── knowledge_agent_graph   → shuffle_responsibilities, store_to_vector_db, fetch_responsibility
├── question_agent_graph    → generate_warmup, generate_initial, generate_followup, deduplicate_check
├── evaluate_agent_graph    → evaluate_with_standard, evaluate_without_standard
├── review_agent_graph      → review_evaluation (审查评估合理性)
└── feedback_agent_graph    → generate_correction, generate_guidance, generate_comment, generate_reminder
```

### Enterprise KB Integration (Eager Query)

```
用户思考期间 (后台并行)
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ QuestionAgent: generate_initial / generate_followup              │
│   1. LLM 生成问题 + module + skill_point                          │
│   2. asyncio.create_task(ensure_enterprise_docs(state))           │
│                   │                                              │
│                   └─→ retrieve_enterprise_knowledge()            │
│                           │                                      │
│                           └─→ /retrieve/by-module (优先)        │
│                               或 /retrieve/by-skill (fallback)    │
│                                    │                              │
│                                    └─→ state.enterprise_docs    │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ EvaluateAgent: evaluate_with_standard                            │
│   - 直接读取 state.enterprise_docs (已缓存，无额外 KB 调用)         │
└──────────────────────────────────────────────────────────────────┘
```

### Three-Layer Memory

| Layer | Storage | Purpose |
|-------|---------|---------|
| **Short-term** | LangGraph State | Current question, followup chain, KB docs |
| **Short-mid-term** | Redis | Session Q&A, pending feedbacks |
| **Long-term** | PostgreSQL + pgvector | Q&A history, RAG knowledge |

### Three-Layer Knowledge

| Layer | Content | Storage | API Endpoint |
|-------|---------|---------|--------------|
| **Module-level** | Source code per module | pgvector | `/knowledge/query` |
| **Project-level** | README, architecture, workflows | pgvector | `/knowledge/query` |
| **Enterprise-level** | Tech best practices, industry standards | Enterprise KB API | `/retrieve/by-module`, `/retrieve/by-skill` |

---

## Authentication

Currently no authentication. Configure CORS in production.

---

## Interview API

### Start Interview

**POST** `/interview/start`

Start a new interview session.

**Request Body:**

```json
{
  "resume_id": "string (required)",
  "session_id": "string (required)",
  "knowledge_base_id": "string (optional)",
  "interview_mode": "free | training (default: free)",
  "feedback_mode": "realtime | recorded (default: recorded)",
  "max_series": 5,
  "error_threshold": 2
}
```

**Response:**

```json
{
  "session_id": "string",
  "status": "active",
  "first_question": {
    "question_id": "string",
    "series": 1,
    "number": 1,
    "content": "string",
    "question_type": "initial"
  }
}
```

---

### Get Question (SSE)

**GET** `/interview/question?session_id={session_id}`

Stream questions, followups, and feedback via Server-Sent Events.

**SSE Events:**

| Event | Description |
|-------|-------------|
| `question` | New question data |
| `feedback` | Immediate feedback (realtime mode) |
| `end` | Stream completed |
| `error` | Error occurred |

**Example:**

```javascript
const eventSource = new EventSource('/interview/question?session_id=xxx');
eventSource.addEventListener('question', (e) => {
  const data = JSON.parse(e.data);
  console.log(data.content);
});
```

---

### Submit Answer

**POST** `/interview/answer`

Submit user answer and receive feedback/next question.

**Request Body:**

```json
{
  "session_id": "string (required)",
  "question_id": "string (required)",
  "user_answer": "string (required)"
}
```

**Response:**

```json
{
  "question_id": "string",
  "question_content": "string",
  "feedback": {
    "content": "string",
    "feedback_type": "comment | correction | guidance | reminder",
    "is_correct": true,
    "guidance": "string | null"
  },
  "next_question_id": "string | null",
  "next_question_content": "string | null",
  "should_continue": true,
  "interview_status": "active | completed"
}
```

---

### End Interview

**POST** `/interview/end?session_id={session_id}`

End interview and get final feedback.

**Response:**

```json
{
  "session_id": "string",
  "status": "completed",
  "total_questions": 10,
  "total_series": 3,
  "final_feedback": {
    "overall_score": 0.85,
    "series_scores": { "1": 0.9, "2": 0.8, "3": 0.85 },
    "strengths": ["技术深度好", "项目经验扎实"],
    "weaknesses": ["分布式系统理解需加强"],
    "suggestions": ["建议深入学习 Redis 集群"]
  }
}
```

---

## Training API

### Start Training

**POST** `/train/start`

Start a skill-focused training session.

**Request Body:**

```json
{
  "resume_id": "string (required)",
  "session_id": "string (required)",
  "skill_point": "string (required, e.g., 'Redis')",
  "knowledge_base_id": "string (optional)"
}
```

**Response:**

```json
{
  "session_id": "string",
  "status": "active",
  "skill_point": "Redis",
  "first_question": {
    "question_id": "string",
    "series": 1,
    "number": 1,
    "content": "string"
  }
}
```

---

### Submit Training Answer

**POST** `/train/answer`

Submit answer during training (same format as `/interview/answer`).

---

### End Training

**POST** `/train/end?session_id={session_id}`

End training session and get results.

---

## Knowledge API

### Query RAG

**POST** `/knowledge/query`

Query the RAG knowledge base.

**Request Body:**

```json
{
  "query": "string (required)",
  "knowledge_base_id": "string (required)",
  "top_k": 5
}
```

**Response:**

```json
{
  "query": "string",
  "results": [
    {
      "content": "string",
      "metadata": { "source": "string", "skill_point": "string" },
      "score": 0.95
    }
  ],
  "total": 5
}
```

---

### Build Knowledge Base

**POST** `/knowledge/build`

Build or update knowledge base from data source.

**Request Body:**

```json
{
  "knowledge_base_id": "string (required)",
  "source_type": "pdf | url | text (required)",
  "source_path": "string (optional)"
}
```

**Response:**

```json
{
  "knowledge_base_id": "string",
  "status": "building",
  "documents_count": 0
}
```

---

## Enterprise Knowledge API

### Retrieve by Module

**POST** `http://localhost:8080/retrieve/by-module`

Query enterprise knowledge by module name.

**Request Body:**

```json
{
  "module": "string (e.g., 'Redis缓存')",
  "top_k": 3
}
```

**Response:**

```json
{
  "documents": [
    {
      "content": "string",
      "score": 0.85,
      "metadata": { "module": "string", "skill_points": ["string"] }
    }
  ]
}
```

---

### Retrieve by Skill

**POST** `http://localhost:8080/retrieve/by-skill`

Query enterprise knowledge by skill point.

**Request Body:**

```json
{
  "skill_point": "string (e.g., 'Redis缓存')",
  "top_k": 3
}
```

**Response:**

```json
{
  "documents": [
    {
      "content": "string",
      "score": 0.85,
      "metadata": { "module": "string", "skill_points": ["string"] }
    }
  ]
}
```

---

## Feedback Types

| Type | Description | Trigger |
|------|-------------|---------|
| `comment` | Positive feedback | Correct answer with good depth (deviation >= 0.6) |
| `correction` | Direct answer | High deviation (< 0.3) |
| `guidance` | Hinting question | Medium deviation (0.3-0.6) |
| `reminder` | Error reminder | Consecutive errors >= error_threshold |

---

## Question Types

| Type | Description |
|------|-------------|
| `initial` | First question in a series |
| `followup` | Follow-up question for depth |
| `guidance` | Hint question for deviation |
| `clarification` | Clarification request |

---

## Interview Modes

### Interview Mode

| Mode | Description |
|------|-------------|
| `free` | Full interview with all resume topics |
| `training` | Focused training on specific skill |

### Feedback Mode

| Mode | Description |
|------|-------------|
| `realtime` | Feedback after each answer (interruptive) |
| `recorded` | Feedback at end of series (non-interruptive) |

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Session/resource not found |
| 500 | Internal Server Error |

Error response format:

```json
{
  "detail": "Error message description"
}
```

---

## WebSocket / SSE Client Examples

### JavaScript

```javascript
// Start interview
const startRes = await fetch('/interview/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ resume_id: 'xxx', session_id: 'yyy' })
});

// Stream questions via SSE
const eventSource = new EventSource(`/interview/question?session_id=${sessionId}`);
eventSource.addEventListener('question', (e) => {
  const q = JSON.parse(e.data);
  console.log(`Q${q.series}.${q.number}: ${q.content}`);
});

// Submit answer
await fetch('/interview/answer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_id, question_id, user_answer })
});

// End interview
const endRes = await fetch(`/interview/end?session_id=${sessionId}`, { method: 'POST' });
```

### cURL

```bash
# Start interview
curl -X POST http://localhost:8000/interview/start \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"r1","session_id":"s1","interview_mode":"free"}'

# Submit answer
curl -X POST http://localhost:8000/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","question_id":"q1","user_answer":"我的回答"}'

# End interview
curl -X POST "http://localhost:8000/interview/end?session_id=s1"
```

---

## Health Check

**GET** `/health`

Returns service health status.

```json
{
  "status": "healthy",
  "service": "ai-interview"
}
```

---

## Configuration

All configuration is managed in `pyproject.toml` under `[tool.ai-interview]`.

### Configuration Sections

| Section | Description |
|---------|-------------|
| `[tool.ai-interview.redis]` | Redis connection settings |
| `[tool.ai-interview.database]` | PostgreSQL connection settings |
| `[tool.ai-interview.llm]` | LLM API settings (OpenAI-compatible) |
| `[tool.ai-interview.vector]` | Vector store settings |
| `[tool.ai-interview.server]` | FastAPI server settings |
| `[tool.ai-interview.interview]` | Interview behavior settings |
| `[tool.ai-interview.rag]` | RAG retrieval settings |
| `[tool.ai-interview.enterprise_kb]` | Enterprise KB API settings |

### Enterprise KB Configuration

```toml
[tool.ai-interview.enterprise_kb]
base_url = "http://localhost:8080"  # Enterprise KB API base URL
timeout = 10                         # Request timeout in seconds
```

### Example Configuration

```toml
[tool.ai-interview.redis]
host = "localhost"
port = 6379
db = 0
password = ""

[tool.ai-interview.database]
url = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_interview"
pool_size = 10

[tool.ai-interview.llm]
api_key = "your_api_key"
base_url = "https://open.bigmodel.cn/api/paas/v4"
model = "glm-4"
embedding_model = "embedding-2"

[tool.ai-interview.server]
host = "0.0.0.0"
port = 8000
reload = true

[tool.ai-interview.enterprise_kb]
base_url = "http://localhost:8080"
timeout = 10
```

---

## Database Schema

### Main Tables

- `users` - User accounts
- `resumes` - Resume files and parsed content
- `projects` - Project repositories
- `knowledge_base` - RAG knowledge (pgvector)
- `interview_sessions` - Interview session records
- `qa_history` - Q&A history
- `interview_feedback` - Final feedback records

See `migrations/001_initial_schema.sql` for full schema.

---

## Redis Key Design

```
interview:{session_id}:state     → Session state (Hash)
interview:{session_id}:series:{n}:q1 → Pre-generated first question
user:{user_id}:current_interview  → Active session mapping
interview:lock:{session_id}       → Distributed lock
```

---

## Project Structure

```
src/
├── agent/
│   ├── __init__.py              # Exports all agent graphs
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
│   ├── interview.py             # /interview/* endpoints
│   ├── training.py              # /train/* endpoints
│   ├── knowledge.py             # /knowledge/* endpoints
│   ├── models.py                # Pydantic request/response models
│   └── routers.py               # Router configuration
├── config/
│   ├── __init__.py
│   └── interview_config.py      # InterviewConfig dataclass
├── db/
│   ├── __init__.py
│   ├── models.py                # SQLAlchemy models
│   ├── database.py              # Async DB connection
│   ├── vector_store.py          # pgvector operations
│   └── redis_client.py          # Redis queue/hash operations
├── domain/
│   ├── __init__.py
│   ├── enums.py                 # Enums (QuestionType, FeedbackType, etc.)
│   └── models.py                # Domain models (Question, QuestionResult, etc.)
├── infrastructure/
│   ├── __init__.py
│   └── session_store.py         # Redis session storage operations
├── session/
│   ├── __init__.py
│   ├── context.py               # Session context management
│   └── snapshot.py              # State snapshot for persistence
├── tools/
│   ├── rag_tools.py             # RAG retrieval
│   ├── rag_enhancements.py      # MultiVector, Hybrid, Reranker, BM25
│   ├── enterprise_knowledge.py  # Enterprise knowledge (KB API client)
│   ├── memory_tools.py          # Redis session management
│   └── code_tools.py            # Source code parsing
├── services/
│   ├── interview_service.py     # Core interview logic
│   ├── resume_parser.py         # Resume parsing
│   ├── training_selector.py     # Skill selection
│   ├── training_knowledge_matcher.py
│   └── llm_service.py           # LLM service (structured output, etc.)
├── dao/                         # Data Access Objects
├── llm/
│   ├── client.py                # get_chat_model, invoke_llm, etc.
│   ├── prompts.py               # Prompt templates
│   └── usage.py                 # LLM usage tracking
└── main.py                      # FastAPI app entry point
```

---

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_question_agent.py -v

# Run integration tests
uv run pytest tests/integration/ -v
```

### Key Test Files

| File | Coverage |
|------|----------|
| `tests/integration/test_agent_integration.py` | Full interview flow |
| `tests/integration/test_enterprise_kb_integration.py` | Enterprise KB caching |
| `tests/test_question_agent.py` | Question generation, module/skill_point extraction |
| `tests/test_rag_enhancements.py` | MultiVector, Hybrid, Reranker, BM25 |
| `tests/test_evaluate_agent.py` | Answer evaluation |
| `tests/test_feedback_agent.py` | Feedback generation |
