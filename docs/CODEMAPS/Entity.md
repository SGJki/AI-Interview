# 实体关系图 (Entity Relationship Diagram)

**Last Updated:** 2026-04-10
**Author:** 数据库迁移 (UUID → BIGSERIAL)

## 实体关系总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    PostgreSQL Schema                              │
│                              BIGSERIAL PK + BIGINT FK                            │
│                                 + pgvector Extension                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 实体关系图 (ER Diagram)

```
┌──────────────────────────┐          ┌──────────────────────────┐
│         users            │          │         resumes           │
│ ────────────────────────  │          │ ────────────────────────  │
│ ● id: BIGSERIAL (PK)     │◄────────│ ● id: BIGSERIAL (PK)     │
│ ○ uuid: UUID (API用)     │  user_id │ ○ user_id: BIGINT (FK)   │
│ ○ name: VARCHAR(100)     │  BIGINT  │ ○ file_path: VARCHAR(500)│
│ ○ email: VARCHAR(255)   │          │ ○ parsed_content: JSONB  │
│ ● created_at: TIMESTAMP  │          │ ● created_at: TIMESTAMP  │
└──────────────────────────┘          └───────────┬──────────────┘
                                                   │ resume_id
                                                   │ BIGINT
                                                   │
                           ┌───────────────────────┴───────────────────────┐
                           │                                              │
                           ▼                                              ▼
┌──────────────────────────────────┐          ┌──────────────────────────────────┐
│          projects                │          │      interview_sessions           │
│ ────────────────────────────────│          │ ─────────────────────────────────│
│ ● id: BIGSERIAL (PK)            │          │ ● id: BIGSERIAL (PK)             │
│ ○ resume_id: BIGINT (FK)        │          │ ○ user_id: BIGINT (FK)          │
│ ○ name: VARCHAR(200)            │          │ ○ resume_id: BIGINT (FK)        │
│ ○ repo_path: VARCHAR(500)       │          │ ○ mode: VARCHAR(50)             │
│ ○ description: TEXT             │          │ ○ feedback_mode: VARCHAR(50)    │
│ ● created_at: TIMESTAMP         │          │ ○ status: VARCHAR(50)           │
└───────────┬──────────────────────┘          │ ● started_at: TIMESTAMP          │
            │ project_id (BIGINT)             │ ○ ended_at: TIMESTAMP            │
            │                                  └───────────┬────────────────────┘
            │                                              │ session_id (BIGINT)
            ▼                                              │
┌──────────────────────────────────┐          ┌───────────┴────────────────────┐
│       knowledge_base             │          │                                │
│ ────────────────────────────────│          │     ┌─────────────────────┐     │
│ ● id: BIGSERIAL (PK)            │          │     │    qa_history        │     │
│ ○ project_id: BIGINT (FK)       │          │     │ ────────────────────│     │
│ ○ type: VARCHAR(50)             │          │     │ ● id: BIGSERIAL (PK)│     │
│ ○ skill_point: VARCHAR(200)     │          │     │ ○ session_id: BIGINT│     │
│ ○ content: TEXT                 │          │     │ ○ series: INTEGER   │     │
│ ○ embedding_id: INTEGER         │          │     │ ○ question_number   │     │
│ ○ responsibility_id: INTEGER    │          │     │ ○ question: TEXT    │     │
│ ○ question_id: VARCHAR(100)    │          │     │ ○ user_answer: TEXT │     │
│ ○ session_id: VARCHAR(100)      │          │     │ ○ standard_answer  │     │
│ ● created_at: TIMESTAMP         │          │     │ ○ feedback: TEXT    │     │
└──────────────────────────────────┘          │     │ ○ deviation_score  │     │
                                              │     │ ● created_at       │     │
                                              │     └─────────────────────┘     │
                                              │                                     │
                                              │     ┌─────────────────────┐     │
                                              │     │ interview_feedback  │     │
                                              │     │ ────────────────────│     │
                                              │     │ ● id: BIGSERIAL (PK)│     │
                                              │     │ ○ session_id: BIGINT │     │
                                              │     │ ○ overall_score     │     │
                                              │     │ ○ strengths: JSONB  │     │
                                              │     │ ○ weaknesses: JSONB │     │
                                              │     │ ○ suggestions: JSONB│     │
                                              │     │ ● created_at        │     │
                                              │     └─────────────────────┘     │
                                              │                                      │
                                              └──────────────────────────────────────┘

┌──────────────────────────────────┐
│        embeddings                │
│ ────────────────────────────────│
│ ● id: SERIAL (PK)               │
│ ○ embedding: VECTOR(1536)       │
│ ○ content: TEXT                 │
│ ○ metadata: JSONB                │
│ ● created_at: TIMESTAMP          │
└──────────────────────────────────┘
```

## 图例

| 符号 | 含义 |
|------|------|
| ● | NOT NULL 列 |
| ○ | nullable 列 |
| (PK) | 主键 (Primary Key) |
| (FK) | 外键 (Foreign Key) |
| BIGSERIAL | 自增BIGINT，主键专用 |
| BIGINT | 64位整数，用于外键 |
| UUID | 通用唯一标识符，仅 users 表保留 |

## 外键关系表

| 父表 | 子表 | 外键列 | 类型 | 级联删除 |
|------|------|--------|------|----------|
| `users` | `resumes` | `user_id` | BIGINT | CASCADE |
| `resumes` | `projects` | `resume_id` | BIGINT | CASCADE |
| `projects` | `knowledge_base` | `project_id` | BIGINT | CASCADE |
| `users` | `interview_sessions` | `user_id` | BIGINT | CASCADE |
| `resumes` | `interview_sessions` | `resume_id` | BIGINT | CASCADE |
| `interview_sessions` | `qa_history` | `session_id` | BIGINT | CASCADE |
| `interview_sessions` | `interview_feedback` | `session_id` | BIGINT | CASCADE |

## 主键设计

| 表 | 主键 | 类型 | 序列 | 说明 |
|---|------|------|------|------|
| `users` | `id` | BIGSERIAL | users_id_seq | 内部主键 |
| `users` | `uuid` | UUID | - | API外部标识符(唯一) |
| `resumes` | `id` | BIGSERIAL | resumes_id_seq | 内部主键 |
| `projects` | `id` | BIGSERIAL | projects_id_seq | 内部主键 |
| `knowledge_base` | `id` | BIGSERIAL | knowledge_base_id_seq | 内部主键 |
| `interview_sessions` | `id` | BIGSERIAL | interview_sessions_id_seq | 内部主键 |
| `qa_history` | `id` | BIGSERIAL | qa_history_id_seq | 内部主键 |
| `interview_feedback` | `id` | BIGSERIAL | interview_feedback_id_seq | 内部主键 |
| `embeddings` | `id` | SERIAL | embeddings_id_seq | 向量嵌入主键 |

## 核心设计原则

1. **唯一 UUID 策略**: 仅 `users` 表保留 UUID 作为 API 外部标识符
2. **BIGSERIAL 主键**: 所有表使用 BIGSERIAL 作为主键，优化 B+tree 索引性能
3. **BIGINT 外键**: 所有外键使用 BIGINT 类型，确保类型一致性
4. **网关转换**: UUID → BIGSERIAL 转换由网关层处理，应用层不感知 UUID

## 迁移文件

- `migrations/001_initial_schema.sql` - 初始数据库结构（UUID 主键）
- `migrations/002_uuid_to_bigserial.sql` - UUID 主键迁移到 BIGSERIAL

## 相关文档

- [Database Codemap](./database.md) - 完整数据库文档
- [DAO Layer](./dao.md) - 数据访问层
- [Services](./services.md) - 业务服务层
