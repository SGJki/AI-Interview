# API Layer Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/api/`
**Main App:** `src/main.py`

## Routers

| Router | Prefix | File | Purpose |
|--------|--------|------|---------|
| `interview_router` | `/interview` | `interview.py` | Interview session management |
| `training_router` | `/train` | `training.py` | Training mode endpoints |
| `knowledge_router` | `/knowledge` | `knowledge.py` | Knowledge base management |

## Interview Endpoints (`src/api/interview.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/interview/start` | Start new interview session |
| GET | `/interview/question` | SSE stream - get question |
| POST | `/interview/answer` | SSE stream - submit answer |
| POST | `/interview/end` | End interview session |
| GET | `/interview/history` | Get interview history |
| GET | `/health` | Health check |

## Training Endpoints (`src/api/training.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/train/start` | Start training session |
| POST | `/train/answer` | Submit training answer |
| POST | `/train/end` | End training session |

## Knowledge Endpoints (`src/api/knowledge.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/knowledge/query` | Query RAG knowledge |
| POST | `/knowledge/build` | Build knowledge base |
| POST | `/knowledge/insert` | Insert knowledge entry |
| GET | `/knowledge/status` | Get knowledge status |

## Request/Response Models (`src/api/models.py`)

| Model | Type | Purpose |
|-------|------|---------|
| `InterviewStartRequest` | Request | Start interview payload |
| `InterviewStartResponse` | Response | Initial question |
| `AnswerRequest` | Request | Submit answer payload |
| `SSEEvent` | Response | Server-sent event types |

## SSE Event Types

| Event | Data | Purpose |
|-------|------|---------|
| `question_start` | `{question_id, series, number, question_type}` | Question begins |
| `token` | `{content}` | Question token (streaming) |
| `question_end` | `{question_id}` | Question complete |
| `evaluation` | `{deviation_score, is_correct, error_count}` | Answer evaluation |
| `feedback` | `{feedback_content, feedback_type, guidance}` | Feedback content |
| `end` | `{status, should_continue}` | Stream end |
| `error` | `{error}` | Error occurred |

## Architecture

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│                      src/main.py                             │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Router Layer                            │
│  interview_router │ training_router │ knowledge_router     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                              │
│  InterviewService │ TrainingService │ KnowledgeService     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer                               │
│              LangGraph Orchestrator                          │
└─────────────────────────────────────────────────────────────┘
```

## Related Areas

- [Services](../services/) - Business logic
- [Agent Architecture](../agents/) - LangGraph integration
