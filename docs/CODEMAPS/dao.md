# DAO Layer Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/dao/`

## DAO Components

| DAO | File | Purpose |
|-----|------|---------|
| `UserDAO` | `user_dao.py` | User CRUD operations |
| `ResumeDAO` | `resume_dao.py` | Resume CRUD operations |
| `ProjectDAO` | `project_dao.py` | Project CRUD operations |
| `KnowledgeBaseDAO` | `knowledge_base_dao.py` | Knowledge base RAG operations |
| `InterviewSessionDAO` | `interview_session_dao.py` | Session management |
| `QAHistoryDAO` | `qa_history_dao.py` | Q&A history storage |
| `InterviewFeedbackDAO` | `interview_feedback_dao.py` | Feedback storage |

## DAO Pattern Usage

Each DAO provides standard operations:
- `find_by_id(id)` - Get single record
- `find_all()` - Get all records
- `create(data)` - Insert new record
- `update(id, data)` - Update existing record
- `delete(id)` - Delete record

## Data Flow

```
Services Layer
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                      DAO Layer                              │
│                                                                 │
│  UserDAO ──────────► User (users table)                     │
│  ResumeDAO ─────────► Resume (resumes table)               │
│  ProjectDAO ────────► Project (projects table)             │
│  KnowledgeBaseDAO ──► KnowledgeBase (knowledge_base table) │
│  SessionDAO ────────► InterviewSession (interview_sessions) │
│  QAHistoryDAO ──────► QAHistory (qa_history table)         │
│  FeedbackDAO ───────► InterviewFeedback (interview_feedback) │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer                              │
│  PostgreSQL + pgvector │ Redis Cache                        │
└─────────────────────────────────────────────────────────────┘
```

## Key DAO Operations

### InterviewSessionDAO
| Method | Purpose |
|--------|---------|
| `create_session()` | Create new interview session |
| `get_session()` | Get session by ID |
| `update_status()` | Update session status |
| `end_session()` | Mark session as completed |

### QAHistoryDAO
| Method | Purpose |
|--------|---------|
| `add_qa()` | Add Q&A pair to history |
| `get_session_history()` | Get all Q&A for session |
| `get_series_history()` | Get Q&A for specific series |

### KnowledgeBaseDAO
| Method | Purpose |
|--------|---------|
| `insert()` | Insert knowledge entry |
| `search()` | Search by content |
| `find_by_question_id()` | Find by question ID |
| `get_by_session()` | Get knowledge for session |

## Related Areas

- [Database](./database.md) - Uses SQLAlchemy models
- [Services](./services.md) - Consumers of DAO layer
