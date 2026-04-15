# AI-Interview Codemaps

**Last Updated:** 2026-04-10
**Project:** AI-Interview Agent
**Tech Stack:** LangGraph + LangChain, FastAPI, PostgreSQL + pgvector, Redis

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (Spring App / Postman)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                     │
│  /interview/*  /train/*  /knowledge/*                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  InterviewService  TrainingService  KnowledgeService       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer (LangGraph)                   │
│  Orchestrator → QuestionAgent | EvaluateAgent | FeedBackAgent │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Memory Layer                           │
│  LangGraph State │ Redis │ PostgreSQL + pgvector            │
└─────────────────────────────────────────────────────────────┘
```

## Codemap Areas

| Area | File | Purpose |
|------|------|---------|
| [Agent Architecture](agents.md) | `src/agent/` | LangGraph agents, state management, orchestration |
| [Skill System](skill.md) | `src/agent/skills/` | Context-aware methodolog loading |
| [API Layer](api.md) | `src/api/` | FastAPI routers, endpoints, request/response models |
| [Services](services.md) | `src/services/` | Business logic layer |
| [Database](database.md) | `src/db/` | SQLAlchemy models, pgvector, Redis client |
| [Entity Relationship](Entity.md) | `docs/CODEMAPS/` | 实体关系图 (BIGSERIAL/BIGINT) |
| [DAO Layer](dao.md) | `src/dao/` | Data access objects |
| [LLM Integration](llm.md) | `src/llm/` | LLM client, prompts |
| [RAG Tools](rag.md) | `src/tools/` | RAG, memory, enterprise knowledge tools |

## Key Modules

| Module | Entry Point | Exports |
|--------|-------------|---------|
| `src.agent` | `__init__.py` | All agent classes and graph builders |
| `src.api` | `interview.py`, `training.py`, `knowledge.py` | REST endpoints |
| `src.services` | `interview_service.py` | Core interview logic |
| `src.db` | `models.py`, `database.py` | SQLAlchemy models, connection |
| `src.dao` | `*_dao.py` | Data access layer |
| `src.llm` | `client.py`, `prompts.py` | LLM integration |

## External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | 1.1.6+ | Multi-agent orchestration |
| `langchain` | 1.2.15+ | LLM chains, tools |
| `fastapi` | 0.115.0+ | REST API framework |
| `asyncpg` | 0.29.0+ | PostgreSQL async driver |
| `pgvector` | 0.2.0+ | Vector embeddings |
| `redis` | 5.0.0+ | Session cache |
| `dashscope` | 1.25.15+ | Qwen LLM API |

## Related Documentation

- [Main README](../../README.md)
- [API Docs](../../docs/API_docs.md)
