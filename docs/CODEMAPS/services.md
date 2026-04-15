# Services Layer Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/services/`

## Service Components

| Service | File | Purpose |
|---------|------|---------|
| `InterviewService` | `interview_service.py` | Core interview orchestration logic |
| `ResumeParser` | `resume_parser.py` | Resume text parsing and extraction |
| `EmbeddingService` | `embedding_service.py` | Text embedding generation |
| `KnowledgeBaseService` | `knowledge_base_service.py` | RAG knowledge management |
| `LLMService` | `llm_service.py` | LLM invocation wrapper |
| `ResponsibilityService` | `responsibility_service.py` | Responsibility extraction |
| `TrainingSelector` | `training_selector.py` | Skill point selection for training |
| `TrainingKnowledgeMatcher` | `training_knowledge_matcher.py` | RAG matching for training |
| `TrainingFollowup` | `training_followup.py` | Training followup generation |

## Key Service: InterviewService

Main orchestrator for interview flow:

```
start_interview()
      │
      ▼
create_session() → init_redis_state()
      │
      ▼
load_resume() → load_knowledge_base()
      │
      ▼
generate_first_question() ──► SSE stream
      │
      ▼
process_answer() ──► evaluate() ──► generate_feedback() ──► SSE stream
      │
      ▼
decide_next_action() ──► [continue | final_feedback]
```

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│                                                                 │
│  InterviewService                                              │
│       │                                                         │
│       ├── ResumeParser ──────────────► src/dao/resume_dao     │
│       ├── KnowledgeBaseService ─────► src/dao/knowledge_base_dao
│       ├── EmbeddingService ──────────► src/db/vector_store   │
│       └── LLMService ────────────────► src/llm/client         │
│                                                                 │
│  TrainingSelector ─────────────────────────────────────────► │
│  TrainingKnowledgeMatcher ─────────────────────────────────► │
│  TrainingFollowup ───────────────────────────────────────────► │
└─────────────────────────────────────────────────────────────┘
```

## Data Access

All services use DAO layer for data persistence:
- `src/dao/interview_session_dao.py` - Session management
- `src/dao/qa_history_dao.py` - Q&A history
- `src/dao/interview_feedback_dao.py` - Feedback storage
- `src/dao/knowledge_base_dao.py` - Knowledge RAG
- `src/dao/resume_dao.py` - Resume data

## Related Areas

- [API Layer](../api/) - Calls services
- [Agent Architecture](../agents/) - Uses services
- [DAO Layer](./dao.md) - Data persistence
