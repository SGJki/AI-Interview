# AI Interview Agent - API Documentation

> Version: 0.1.0
> Base URL: `http://localhost:8000`

## Overview

AI Interview Agent 是一个基于 LangGraph + LangChain 的智能面试模拟系统，支持多系列面试、实时点评、流式输出和专项训练功能。

### Features

- **多系列面试**: 支持自由问答和专项训练两种模式
- **实时点评**: 实时反馈 + 全程记录两种反馈模式
- **流式输出**: SSE 流式推送问题、追问和反馈
- **追问机制**: 基于偏差检测的智能追问引导
- **RAG 知识库**: 模块级、项目级、企业级三层知识体系
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
│  State → Nodes (load_context, generate_question, etc.)     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Memory Layer                           │
│  LangGraph State │ Redis │ PostgreSQL + pgvector           │
└─────────────────────────────────────────────────────────────┘
```

### Three-Layer Memory

| Layer | Storage | Purpose |
|-------|---------|---------|
| **Short-term** | LangGraph State | Current question, followup chain |
| **Short-mid-term** | Redis | Session Q&A, pending feedbacks |
| **Long-term** | PostgreSQL + pgvector | Q&A history, RAG knowledge |

### Three-Layer Knowledge

| Layer | Content | Storage |
|-------|---------|---------|
| **Module-level** | Source code per module | pgvector |
| **Project-level** | README, architecture, workflows | pgvector |
| **Enterprise-level** | Tech best practices, industry standards | pgvector |

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

## Feedback Types

| Type | Description | Trigger |
|------|-------------|---------|
| `comment` | Positive feedback | Correct answer with good depth |
| `correction` | Direct answer | High deviation (>0.7) |
| `guidance` | Hinting question | Medium deviation (0.3-0.7) |
| `reminder` | Error reminder | Consecutive errors >= threshold |

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

### Environment Variables (TODO)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `LLM_API_KEY` | - | LLM API key |
| `LLM_BASE_URL` | - | LLM base URL |

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
│   ├── state.py       # InterviewState, Question, Answer, Feedback
│   └── graph.py       # LangGraph definition
├── api/
│   ├── interview.py   # /interview/* endpoints
│   ├── training.py    # /train/* endpoints
│   ├── knowledge.py   # /knowledge/* endpoints
│   ├── models.py      # Pydantic request/response models
│   └── routers.py     # Router configuration
├── tools/
│   ├── rag_tools.py           # RAG retrieval
│   ├── rag_enhancements.py    # MultiVector, Hybrid, Reranker
│   ├── enterprise_knowledge.py # Enterprise knowledge
│   ├── memory_tools.py        # Redis session management
│   └── code_tools.py          # Source code parsing
├── services/
│   ├── interview_service.py   # Core interview logic
│   ├── resume_parser.py        # Resume parsing
│   ├── training_selector.py    # Skill selection
│   └── training_knowledge_matcher.py
├── db/
│   ├── models.py       # SQLAlchemy models
│   ├── database.py     # Async DB connection
│   └── vector_store.py # pgvector operations
└── dao/                # Data Access Objects
```
