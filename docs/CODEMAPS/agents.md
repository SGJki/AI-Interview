# Agent Architecture Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/agent/__init__.py`
**Main Graph:** `src/agent/graph.py`

## Architecture

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                    InterviewState                           │
                    │  - session_id, resume_id                                    │
                    │  - current_series, current_question                          │
                    │  - followup_depth, answers, feedbacks                        │
                    │  - interview_mode, feedback_mode                            │
                    └──────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Main Orchestrator Graph                                  │
│                                                                                 │
│   init → orchestrator → decide_next ──────────────────────────────────────────┐ │
│                                   │                                             │ │
│                    ┌──────────────┼──────────────┐                             │ │
│                    ▼              ▼              ▼                             │ │
│           question_agent   resume_agent   knowledge_agent                       │ │
│                    │              │              │                              │ │
│                    ▼              │              │                              │ │
│              evaluate_agent ◄─────┴──────────────┘                              │ │
│                    │                                                                │ │
│                    ▼                                                                │ │
│              feedback_agent ◄───────────────────────────────────────────────────┘ │
│                    │                                                                │ │
│                    ▼                                                                │ │
│              decide_next (loop)                                                  │ │
│                                                                                 │
│   decide_next ──────────────────────────────► final_feedback → END               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Agent Components

### Core State (`src/agent/state.py`)

| Class | Type | Purpose |
|-------|------|---------|
| `InterviewState` | `@dataclass(frozen=True)` | LangGraph state - short-term memory |
| `InterviewContext` | `@dataclass` | Full context - short + medium-term memory |
| `Question` | `@dataclass(frozen=True)` | Question data |
| `Answer` | `@dataclass(frozen=True)` | User answer with deviation |
| `Feedback` | `@dataclass(frozen=True)` | Feedback content |
| `FinalFeedback` | `@dataclass(frozen=True)` | End-of-interview summary |

### Enums (`src/agent/state.py`)

| Enum | Values | Purpose |
|------|--------|---------|
| `InterviewMode` | `FREE`, `TRAINING` | Interview type |
| `FeedbackMode` | `REALTIME`, `RECORDED` | Feedback timing |
| `FeedbackType` | `COMMENT`, `CORRECTION`, `GUIDANCE`, `REMINDER` | Feedback classification |
| `SessionStatus` | `ACTIVE`, `COMPLETED`, `CANCELLED` | Session state |
| `QuestionType` | `INITIAL`, `FOLLOWUP`, `GUIDANCE`, `CLARIFICATION` | Question classification |
| `FollowupStrategy` | `IMMEDIATE`, `DEFERRED`, `SKIP` | Followup decision |

### Base Classes (`src/agent/base.py`)

| Class | Purpose |
|-------|---------|
| `AgentPhase` | Enum for agent phases |
| `AgentResult` | Standardized agent output |
| `ReviewVoter` | 3-instance voting mechanism |
| `create_review_voters()` | Factory function |

### Sub-Agents

| Agent | File | Responsibilities |
|-------|------|------------------|
| **ResumeAgent** | `resume_agent.py` | Parse resume, extract responsibilities, fetch old resume |
| **KnowledgeAgent** | `knowledge_agent.py` | Shuffle responsibilities, find standard answers, store to vector DB |
| **QuestionAgent** | `question_agent.py` | Generate warmup/initial/followup questions, deduplicate |
| **EvaluateAgent** | `evaluate_agent.py` | Evaluate with/without standard answers |
| **FeedBackAgent** | `feedback_agent.py` | Generate correction/guidance/comment feedback |

### Supporting Modules

| File | Purpose |
|------|---------|
| `graph.py` | Main interview graph builder |
| `orchestrator.py` | Main orchestrator graph |
| `streaming.py` | SSE streaming utilities |
| `fallbacks.py` | Fallback strategies |
| `retry.py` | Retry logic for agent failures |

## Data Flow

1. **Session Start**: `init` phase creates initial state
2. **Orchestrator Loop**: `decide_next` routes to appropriate agent
3. **Question Flow**: QuestionAgent → EvaluateAgent → FeedBackAgent → decide_next
4. **Session End**: `final_feedback` generates summary

## Review Mechanism

Each agent output passes through **3-instance voting**:
- 2+ votes required to pass
- Failed votes trigger retry loop (max 3 retries)

## External Dependencies

- `langgraph` - Graph state machine
- `langchain-core` - Tool definitions
- `src.llm` - LLM client for agent reasoning

## Related Areas

- [API Layer](../api/) - Calls agent graph
- [Services](../services/) - Orchestrates agent execution
- [LLM Integration](../llm/) - Provides reasoning capability
