# Database Layer Codemap

**Last Updated:** 2026-04-10
**Entry Point:** `src/db/`
**Models:** `src/db/models.py`

## Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Schema                         │
│                    + pgvector Extension                      │
└─────────────────────────────────────────────────────────────┘
```

### Entity Relationship

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              users                                           │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL ◄──────────┐  (PK, 主键)                                    │
│  uuid: UUID                │  (API 暴露, 唯一)                              │
└─────────────────────────────┘                                                │
                              ▲                                                │
                              │ user_id (BIGINT)                               │
                              │                                                │
┌─────────────────────────────────────────────────────────────────────────────┐
│                             resumes                                          │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL ◄──────────────────────────┐  (PK, 主键)                  │
│  uuid: UUID                                │  (已废弃，仅迁移用)             │
│  user_id: BIGINT ──────────────────────────┘                                │
└─────────────────────────────────────────────┘                                │
                              ▲                                                │
                              │ resume_id (BIGINT)                             │
                              │                                                │
┌─────────────────────────────────────────────────────────────────────────────┐
│                             projects                                         │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL ◄────────────────────────────────────────┐  (PK, 主键)    │
│  uuid: UUID                                              │  (已废弃)        │
│  resume_id: BIGINT ──────────────────────────────────────┘                 │
│  name: VARCHAR(200)                                                             │
│  repo_path: VARCHAR(500)                                                        │
│  description: TEXT                                                               │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                                │
                                                │ project_id (BIGINT)
                                                │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         knowledge_base                                        │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL  (PK, 主键)                                                 │
│  uuid: UUID  (已废弃)                                                        │
│  project_id: BIGINT (FK → projects.id)                                       │
│  type: VARCHAR(50)                                                           │
│  skill_point: VARCHAR(200)                                                    │
│  content: TEXT                                                                │
│  embedding_id: INTEGER (引用 embeddings 表)                                   │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                        interview_sessions                                     │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL ◄──────────────────────────┐  (PK, 主键)                   │
│  uuid: UUID                                │  (已废弃)                       │
│  user_id: BIGINT ──────────────────────────┘                                │
│  resume_id: BIGINT ───────────────────────┘                                │
│  mode: VARCHAR(50)                                                            │
│  feedback_mode: VARCHAR(50)                                                   │
│  status: VARCHAR(50)                                                          │
│  started_at: TIMESTAMP                                                         │
│  ended_at: TIMESTAMP                                                         │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    │ session_id (BIGINT)                                  │
                    │                                                        │
┌───────────────────┴───────────────────────────────────────────────────┐    │
│                         qa_history                                        │    │
│  ─────────────────────────────────────────────────────────────────────│    │
│  id: BIGSERIAL  (PK, 主键)                                              │    │
│  uuid: UUID  (已废弃)                                                    │    │
│  session_id: BIGINT (FK → interview_sessions.id)                         │    │
│  series: INTEGER                                                           │    │
│  question_number: INTEGER                                                   │    │
│  question: TEXT                                                           │    │
│  user_answer: TEXT                                                        │    │
│  standard_answer: TEXT                                                     │    │
│  feedback: TEXT                                                           │    │
│  deviation_score: FLOAT                                                    │    │
└───────────────────────────────────────────────────────────────────────────┘    │

┌───────────────────────────┴───────────────────────────────────────────────┐
│                       interview_feedback                                      │
│  ───────────────────────────────────────────────────────────────────────│
│  id: BIGSERIAL  (PK, 主键)                                               │
│  uuid: UUID  (已废弃)                                                     │
│  session_id: BIGINT (FK → interview_sessions.id)                          │
│  overall_score: FLOAT                                                      │
│  strengths: JSONB                                                         │
│  weaknesses: JSONB                                                         │
│  suggestions: JSONB                                                        │
└────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           embeddings                                          │
│  ─────────────────────────────────────────────────────────────────────────│
│  id: SERIAL  (PK, 主键)   ← 已经是自增，无需修改                            │
│  embedding: VECTOR(1536)                                                    │
│  content: TEXT                                                              │
│  metadata: JSONB                                                            │
│  created_at: TIMESTAMP                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 外键关系说明

| 父表 | 子表 | 外键列 | 类型 |
|------|------|--------|------|
| `users` | `resumes` | `user_id` | BIGINT |
| `resumes` | `projects` | `resume_id` | BIGINT |
| `projects` | `knowledge_base` | `project_id` | BIGINT |
| `users` | `interview_sessions` | `user_id` | BIGINT |
| `resumes` | `interview_sessions` | `resume_id` | BIGINT |
| `interview_sessions` | `qa_history` | `session_id` | BIGINT |
| `interview_sessions` | `interview_feedback` | `session_id` | BIGINT |

## 主键设计

| 表 | 主键 | 类型 | 说明 |
|---|------|------|------|
| `users` | `id` | BIGSERIAL | 内部主键，用于外键引用 |
| `users` | `uuid` | UUID | API 暴露的用户标识符 |
| `resumes` | `id` | BIGSERIAL | 内部主键 |
| `projects` | `id` | BIGSERIAL | 内部主键 |
| `knowledge_base` | `id` | BIGSERIAL | 内部主键 |
| `interview_sessions` | `id` | BIGSERIAL | 内部主键 |
| `qa_history` | `id` | BIGSERIAL | 内部主键 |
| `interview_feedback` | `id` | BIGSERIAL | 内部主键 |
| `embeddings` | `id` | SERIAL | 向量嵌入，无需修改 |

## SQLAlchemy Models (`src/db/models.py`)

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | User accounts (multi-tenant ready) |
| `Resume` | `resumes` | Parsed resume data |
| `Project` | `projects` | Project experiences |
| `KnowledgeBase` | `knowledge_base` | RAG knowledge with vectors |
| `InterviewSession` | `interview_sessions` | Interview session tracking |
| `QAHistory` | `qa_history` | Q&A pairs storage |
| `InterviewFeedback` | `interview_feedback` | Final feedback |

## Model Attributes

### User
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK, 主键 |
| `uuid` | UUID | API 标识符, unique |
| `name` | String(100) | nullable |
| `email` | String(255) | unique, nullable |
| `created_at` | DateTime | not null |

### Resume
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `user_id` | BIGINT | FK → users.id |
| `file_path` | String(500) | nullable |
| `parsed_content` | JSONB | nullable |
| `created_at` | DateTime | not null |

### Project
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `resume_id` | BIGINT | FK → resumes.id |
| `name` | String(200) | nullable |
| `repo_path` | String(500) | nullable |
| `description` | Text | nullable |
| `created_at` | DateTime | not null |

### KnowledgeBase
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `project_id` | BIGINT | FK → projects.id |
| `type` | String(50) | nullable |
| `skill_point` | String(200) | indexed |
| `content` | Text | nullable |
| `embedding_id` | Integer | nullable (pgvector ref) |
| `responsibility_id` | Integer | nullable |
| `question_id` | String(100) | indexed |
| `session_id` | String(100) | indexed |
| `created_at` | DateTime | not null |

### InterviewSession
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `user_id` | BIGINT | FK → users.id |
| `resume_id` | BIGINT | FK → resumes.id |
| `mode` | String(50) | default: 'free' |
| `feedback_mode` | String(50) | default: 'recorded' |
| `status` | String(50) | indexed |
| `started_at` | DateTime | not null |
| `ended_at` | DateTime | nullable |

### QAHistory
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `session_id` | BIGINT | FK → interview_sessions.id |
| `series` | Integer | indexed |
| `question_number` | Integer | - |
| `question` | Text | nullable |
| `user_answer` | Text | nullable |
| `standard_answer` | Text | nullable |
| `feedback` | Text | nullable |
| `deviation_score` | Float | nullable |
| `created_at` | DateTime | not null |

### InterviewFeedback
| Attribute | Type | Constraints |
|-----------|------|-------------|
| `id` | BIGSERIAL | PK |
| `session_id` | BIGINT | FK → interview_sessions.id |
| `overall_score` | Float | nullable |
| `strengths` | JSONB | nullable |
| `weaknesses` | JSONB | nullable |
| `suggestions` | JSONB | nullable |
| `created_at` | DateTime | not null |

## Database Components

| Component | File | Purpose |
|-----------|------|---------|
| `Base` | `models.py` | DeclarativeBase for all models |
| `database.py` | `database.py` | Async SQLAlchemy engine, session factory |
| `redis_client.py` | `redis_client.py` | Redis async client for caching |
| `vector_store.py` | `vector_store.py` | pgvector operations |

## Migrations

| File | Description |
|------|-------------|
| `migrations/001_initial_schema.sql` | 初始数据库结构（UUID 主键） |
| `migrations/002_uuid_to_bigserial.sql` | UUID 主键迁移到 BIGSERIAL |

## Related Areas

- [DAO Layer](./dao.md) - Data access using these models
- [Services](./services.md) - Business logic using DAOs
