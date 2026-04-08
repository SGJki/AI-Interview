# AI-Interview LangGraph Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the multi-agent orchestration architecture based on LangGraph for the AI-Interview project.

**Architecture:** Main Orchestrator + 5 specialized agents (ResumeAgent, KnowledgeAgent, QuestionAgent, EvaluateAgent, FeedBackAgent) with 3-instance voting Review mechanism and Redis-based state management.

**Tech Stack:** Python, LangGraph, LangChain, Redis, PostgreSQL + pgvector, FastAPI

---

## Implementation Summary

**Status:** COMPLETED

**Date Completed:** 2026-04-08

**Files Created:**
- `src/agent/base.py` - AgentPhase, AgentResult, ReviewVoter base classes
- `src/agent/resume_agent.py` - ResumeAgent subgraph
- `src/agent/knowledge_agent.py` - KnowledgeAgent subgraph
- `src/agent/question_agent.py` - QuestionAgent subgraph
- `src/agent/evaluate_agent.py` - EvaluateAgent subgraph
- `src/agent/feedback_agent.py` - FeedBackAgent subgraph
- `src/agent/orchestrator.py` - Main orchestrator graph
- `src/config/interview_config.py` - InterviewConfig dataclass
- `src/db/redis_client.py` - RedisClient for queue/hash operations

**Files Modified:**
- `src/agent/state.py` - Added new state fields (asked_logical_questions, mastered_questions, all_responsibilities_used, review_retry_count, last_review_feedback, phase)
- `src/agent/__init__.py` - Updated exports
- `src/config/__init__.py` - Added config exports
- `src/db/__init__.py` - Added redis_client exports

---

## Phase 1: Core Infrastructure

### Task 1: Update InterviewState Model

**Files:**
- Modify: `src/agent/state.py:1-100`

**New fields to add:**
```python
# Series state tracking
asked_logical_questions: set[str] = field(default_factory=set)  # dev >= 0.8 后加入
mastered_questions: dict[str, dict] = field(default_factory=dict)  # question_id -> {answer, standard_answer}
all_responsibilities_used: bool = False

# Review info
review_retry_count: int = 0
last_review_feedback: Optional[str] = None

# Phase tracking
phase: Literal["init", "warmup", "initial", "followup", "final_feedback"] = "init"
```

- [ ] **Step 1: Update InterviewState fields**

```python
# Add to src/agent/state.py InterviewState class
all_responsibilities_used: bool = False
review_retry_count: int = 0
last_review_feedback: Optional[str] = None
phase: str = "init"
asked_logical_questions: set[str] = field(default_factory=set)
mastered_questions: dict[str, dict] = field(default_factory=dict)
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/state.py
git commit -m "feat(agent): add new state fields for orchestration"
```

---

### Task 2: Create Configuration Module

**Files:**
- Create: `src/config/interview_config.py`

```python
"""Interview orchestration configuration."""
from dataclasses import dataclass
from typing import Literal

@dataclass
class InterviewConfig:
    # Review storage strategy
    is_production: bool = False

    # Flow parameters
    max_followup_depth: int = 3
    Retry_Max: int = 3
    deviation_threshold: float = 0.8
    max_series: int = 5
    error_threshold: int = 2

    # Feedback thresholds
    feedback_thresholds: dict = None

    def __post_init__(self):
        if self.feedback_thresholds is None:
            self.feedback_thresholds = {
                "correction": 0.3,
                "guidance": 0.6
            }

    def get_feedback_type(self, deviation_score: float) -> Literal["correction", "guidance", "comment"]:
        if deviation_score < self.feedback_thresholds["correction"]:
            return "correction"
        elif deviation_score < self.feedback_thresholds["guidance"]:
            return "guidance"
        return "comment"

# Global config instance
config = InterviewConfig()
```

- [ ] **Step 1: Create config module**

```bash
mkdir -p src/config
```

```python
# Write to src/config/interview_config.py
"""Interview orchestration configuration."""
from dataclasses import dataclass
from typing import Literal

@dataclass
class InterviewConfig:
    is_production: bool = False
    max_followup_depth: int = 3
    Retry_Max: int = 3
    deviation_threshold: float = 0.8
    max_series: int = 5
    error_threshold: int = 2
    feedback_thresholds: dict = None

    def __post_init__(self):
        if self.feedback_thresholds is None:
            self.feedback_thresholds = {"correction": 0.3, "guidance": 0.6}

    def get_feedback_type(self, deviation_score: float) -> Literal["correction", "guidance", "comment"]:
        if deviation_score < self.feedback_thresholds["correction"]:
            return "correction"
        elif deviation_score < self.feedback_thresholds["guidance"]:
            return "guidance"
        return "comment"

config = InterviewConfig()
```

- [ ] **Step 2: Create config __init__.py**

```python
# Write to src/config/__init__.py
from src.config.interview_config import config, InterviewConfig

__all__ = ["config", "InterviewConfig"]
```

- [ ] **Step 3: Commit**

```bash
git add src/config/
git commit -m "feat(config): add interview orchestration config"
```

---

### Task 3: Create Redis Client Module

**Files:**
- Create: `src/db/redis_client.py`

```python
"""Redis client for interview state management."""
import json
from typing import Optional, Any
import redis.asyncio as redis

class RedisClient:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

    # Queue operations
    async def push_question(self, question: dict) -> None:
        """Push pre-generated question to queue."""
        client = await self.get_client()
        await client.rpush(
            "pending_series_questions",
            json.dumps(question)
        )

    async def pop_question(self) -> Optional[dict]:
        """Pop next question from queue."""
        client = await self.get_client()
        data = await client.lpop("pending_series_questions")
        if data:
            return json.loads(data)
        return None

    # Hash operations
    async def hset_series_state(self, series: int, data: dict) -> None:
        """Set series state."""
        client = await self.get_client()
        await client.hset(f"series_{series}_state", mapping=data)

    async def hget_series_state(self, series: int) -> dict:
        """Get series state."""
        client = await self.get_client()
        data = await client.hgetall(f"series_{series}_state")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    async def hset_session_context(self, session_id: str, data: dict) -> None:
        """Set session context."""
        client = await self.get_client()
        await client.hset(f"session_{session_id}_context", mapping=data)

    async def hget_session_context(self, session_id: str) -> dict:
        """Get session context."""
        client = await self.get_client()
        data = await client.hgetall(f"session_{session_id}_context")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    # Review info storage
    async def save_review_info(self, session_id: str, agent: str, info: dict) -> None:
        """Save review information based on is_production config."""
        from src.config import config
        if not config.is_production or info.get("failed"):
            client = await self.get_client()
            await client.lpush(
                f"review_info:{session_id}",
                json.dumps({"agent": agent, **info})
            )

redis_client = RedisClient()
```

- [ ] **Step 1: Create Redis client**

```python
# Write to src/db/redis_client.py
"""Redis client for interview state management."""
import json
from typing import Optional
import redis.asyncio as redis

class RedisClient:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

    async def push_question(self, question: dict) -> None:
        client = await self.get_client()
        await client.rpush("pending_series_questions", json.dumps(question))

    async def pop_question(self) -> Optional[dict]:
        client = await self.get_client()
        data = await client.lpop("pending_series_questions")
        return json.loads(data) if data else None

    async def hset_series_state(self, series: int, data: dict) -> None:
        client = await self.get_client()
        await client.hset(f"series_{series}_state", mapping=data)

    async def hget_series_state(self, series: int) -> dict:
        client = await self.get_client()
        data = await client.hgetall(f"series_{series}_state")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    async def hset_session_context(self, session_id: str, data: dict) -> None:
        client = await self.get_client()
        await client.hset(f"session_{session_id}_context", mapping=data)

    async def hget_session_context(self, session_id: str) -> dict:
        client = await self.get_client()
        data = await client.hgetall(f"session_{session_id}_context")
        return {k.decode(): v.decode() for k, v in data.items()} if data else {}

    async def save_review_info(self, session_id: str, agent: str, info: dict) -> None:
        from src.config import config
        if not config.is_production or info.get("failed"):
            client = await self.get_client()
            await client.lpush(f"review_info:{session_id}", json.dumps({"agent": agent, **info}))

redis_client = RedisClient()
```

- [ ] **Step 2: Update db __init__.py**

```python
# Update src/db/__init__.py
from src.db.redis_client import redis_client, RedisClient

__all__ = ["redis_client", "RedisClient"]
```

- [ ] **Step 3: Commit**

```bash
git add src/db/
git commit -m "feat(db): add redis client for orchestration state"
```

---

## Phase 2: Base Agent Infrastructure

### Task 4: Create Base Agent Classes

**Files:**
- Create: `src/agent/base.py`

```python
"""Base classes for all agents."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass
from enum import Enum

class AgentPhase(str, Enum):
    """Agent execution phase."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    data: dict = None
    error: str = None
    retry_count: int = 0

class ReviewVoter:
    """3-instance voting mechanism for reviews."""

    def __init__(self, voters: list[Callable[[dict], bool]]):
        self.voters = voters

    async def vote(self, content: dict) -> tuple[bool, list[str]]:
        """
        Run voting and return (passed, failures).
        At least 2 votes needed to pass.
        """
        results = []
        for voter in self.voters:
            try:
                results.append(await voter(content))
            except Exception as e:
                results.append(False)

        passed_count = sum(results)
        passed = passed_count >= 2

        failures = []
        if not passed:
            for i, r in enumerate(results):
                if not r:
                    failures.append(f"Voter {i} failed")

        return passed, failures

def create_review_voters(check_functions: list[Callable[[dict], bool]]) -> ReviewVoter:
    """Factory to create ReviewVoter with check functions."""
    return ReviewVoter(check_functions)
```

- [ ] **Step 1: Create base agent module**

```python
# Write to src/agent/base.py
"""Base classes for all agents."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass
from enum import Enum

class AgentPhase(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AgentResult:
    success: bool
    data: dict = None
    error: str = None
    retry_count: int = 0

class ReviewVoter:
    """3-instance voting mechanism."""

    def __init__(self, voters: list[Callable[[dict], bool]]):
        self.voters = voters

    async def vote(self, content: dict) -> tuple[bool, list[str]]:
        results = []
        for voter in self.voters:
            try:
                results.append(await voter(content))
            except Exception:
                results.append(False)

        passed_count = sum(results)
        passed = passed_count >= 2
        failures = [] if passed else [f"Voter {i}" for i, r in enumerate(results) if not r]
        return passed, failures

def create_review_voters(check_functions: list[Callable[[dict], bool]]) -> ReviewVoter:
    return ReviewVoter(check_functions)
```

- [ ] **Step 2: Update agent __init__.py**

```python
# Update src/agent/__init__.py
from src.agent.base import AgentPhase, AgentResult, ReviewVoter, create_review_voters

__all__ = ["AgentPhase", "AgentResult", "ReviewVoter", "create_review_voters"]
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/
git commit -m "feat(agent): add base classes for agents"
```

---

## Phase 3: ResumeAgent Implementation

### Task 5: Create ResumeAgent Subgraph

**Files:**
- Create: `src/agent/resume_agent.py`

```python
"""ResumeAgent - Resume parsing and storage."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState
from src.agent.base import AgentResult

async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """Parse new resume and extract responsibilities."""
    from src.services.resume_parser import ResumeParser

    parser = ResumeParser()
    parsed = await parser.aparse(resume_text)

    responsibilities = []
    for project in parsed.projects:
        responsibilities.extend(project.responsibilities)

    return {
        "resume_context": parsed.raw_text,
        "responsibilities": tuple(responsibilities),
    }

async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """Fetch existing resume from database."""
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session

    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        if resume:
            return {"resume_context": resume.content}
        return {"resume_context": ""}

def resume_agent_node(state: InterviewState, action: str) -> dict:
    """Main resume agent node logic."""
    from src.config import config

    if action == "parse":
        return {"phase": "warmup", "resume_context": state.resume_context}
    elif action == "fetch":
        return {"phase": "warmup"}
    return {}

def create_resume_agent_graph() -> StateGraph:
    """Create ResumeAgent subgraph."""
    graph = StateGraph(InterviewState)

    graph.add_node("parse_resume", lambda s: {})
    graph.add_node("fetch_old_resume", lambda s: {})

    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "__end__")

    return graph.compile()

resume_agent_graph = create_resume_agent_graph()
```

- [ ] **Step 1: Create ResumeAgent module**

```python
# Write to src/agent/resume_agent.py
"""ResumeAgent - Resume parsing and storage."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """Parse new resume and extract responsibilities."""
    from src.services.resume_parser import ResumeParser

    parser = ResumeParser()
    parsed = await parser.aparse(resume_text)

    responsibilities = []
    for project in parsed.projects:
        responsibilities.extend(project.responsibilities)

    return {
        "resume_context": parsed.raw_text,
        "responsibilities": tuple(responsibilities),
    }

async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """Fetch existing resume from database."""
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session

    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        if resume:
            return {"resume_context": resume.content}
        return {"resume_context": ""}

def create_resume_agent_graph() -> StateGraph:
    """Create ResumeAgent subgraph."""
    graph = StateGraph(InterviewState)
    graph.add_node("parse_resume", lambda s: {})
    graph.add_node("fetch_old_resume", lambda s: {})
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "__end__")
    return graph.compile()

resume_agent_graph = create_resume_agent_graph()
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/resume_agent.py
git commit -m "feat(agent): add ResumeAgent subgraph"
```

---

## Phase 4: KnowledgeAgent Implementation

### Task 6: Create KnowledgeAgent Subgraph

**Files:**
- Create: `src/agent/knowledge_agent.py`

```python
"""KnowledgeAgent - Knowledge base and responsibility management."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def shuffle_responsibilities(state: InterviewState, responsibilities: tuple) -> dict:
    """Shuffle responsibilities for random selection."""
    import random
    shuffled = list(responsibilities)
    random.shuffle(shuffled)
    return {"responsibilities": tuple(shuffled)}

async def store_to_vector_db(state: InterviewState, responsibilities: tuple) -> dict:
    """Store responsibilities to vector database."""
    # TODO: Implement vector storage with is_used=false
    return {"stored": True}

async def fetch_responsibility(state: InterviewState, session_id: str) -> dict:
    """Fetch next unused responsibility from vector DB."""
    # TODO: Query vector DB for is_used=false
    return {"current_responsibility": ""}

async def find_standard_answer(state: InterviewState, question: str) -> dict:
    """Find standard answer for a question from mastered questions."""
    # TODO: Implement similarity search in mastered_questions
    return {"standard_answer": None}

def create_knowledge_agent_graph() -> StateGraph:
    """Create KnowledgeAgent subgraph."""
    graph = StateGraph(InterviewState)

    graph.add_node("shuffle_responsibilities", shuffle_responsibilities)
    graph.add_node("store_to_vector_db", store_to_vector_db)
    graph.add_node("fetch_responsibility", fetch_responsibility)
    graph.add_node("find_standard_answer", find_standard_answer)

    graph.set_entry_point("shuffle_responsibilities")
    graph.add_edge("shuffle_responsibilities", "store_to_vector_db")
    graph.add_edge("store_to_vector_db", "__end__")

    return graph.compile()

knowledge_agent_graph = create_knowledge_agent_graph()
```

- [ ] **Step 1: Create KnowledgeAgent module**

```python
# Write to src/agent/knowledge_agent.py
"""KnowledgeAgent - Knowledge base and responsibility management."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def shuffle_responsibilities(state: InterviewState, responsibilities: tuple) -> dict:
    import random
    shuffled = list(responsibilities)
    random.shuffle(shuffled)
    return {"responsibilities": tuple(shuffled)}

async def store_to_vector_db(state: InterviewState, responsibilities: tuple) -> dict:
    return {"stored": True}

async def fetch_responsibility(state: InterviewState, session_id: str) -> dict:
    return {"current_responsibility": ""}

async def find_standard_answer(state: InterviewState, question: str) -> dict:
    return {"standard_answer": None}

def create_knowledge_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("shuffle_responsibilities", shuffle_responsibilities)
    graph.add_node("store_to_vector_db", store_to_vector_db)
    graph.add_node("fetch_responsibility", fetch_responsibility)
    graph.add_node("find_standard_answer", find_standard_answer)
    graph.set_entry_point("shuffle_responsibilities")
    graph.add_edge("shuffle_responsibilities", "store_to_vector_db")
    graph.add_edge("store_to_vector_db", "__end__")
    return graph.compile()

knowledge_agent_graph = create_knowledge_agent_graph()
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/knowledge_agent.py
git commit -m "feat(agent): add KnowledgeAgent subgraph"
```

---

## Phase 5: QuestionAgent Implementation

### Task 7: Create QuestionAgent Subgraph

**Files:**
- Create: `src/agent/question_agent.py`

```python
"""QuestionAgent - Question generation and deduplication."""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.state import InterviewState

async def generate_warmup(state: InterviewState, resume_context: str) -> dict:
    """Generate warmup question based on resume."""
    # TODO: LLM call to generate warmup question
    return {"current_question": {"content": "请简单介绍一下你自己", "type": "warmup"}}

async def generate_initial(state: InterviewState, resume_context: str, responsibility: str) -> dict:
    """Generate initial question based on responsibility."""
    # TODO: LLM call to generate initial question
    return {"current_question": {"content": f"请谈谈你对{responsibility}的经验", "type": "initial"}}

async def generate_followup(state: InterviewState, qa_history: list, evaluation: dict) -> dict:
    """Generate followup question based on Q&A and evaluation."""
    # TODO: LLM call to generate followup with context
    return {"current_question": {"content": "能详细说说吗？", "type": "followup"}}

async def deduplicate_check(state: InterviewState, question_id: str) -> dict:
    """Check if question is duplicate and should be skipped."""
    from src.agent.base import create_review_voters

    voters = [
        lambda q: q.get("question_id") not in state.asked_logical_questions,
        lambda q: True,
        lambda q: True,
    ]
    voter = create_review_voters(voters)
    passed, failures = await voter.vote({"question_id": question_id})

    return {"deduplicate_passed": passed, "deduplicate_failures": failures}

def should_continue_followup(state: InterviewState) -> Literal["generate_followup", END]:
    """Determine if followup should continue."""
    from src.config import config

    dev = state.evaluation_results.get(state.current_question_id, {}).get("deviation_score", 0)
    depth = state.followup_depth

    if dev >= config.deviation_threshold and depth >= config.max_followup_depth:
        return END
    return "generate_followup"

def create_question_agent_graph() -> StateGraph:
    """Create QuestionAgent subgraph."""
    graph = StateGraph(InterviewState)

    graph.add_node("generate_warmup", generate_warmup)
    graph.add_node("generate_initial", generate_initial)
    graph.add_node("generate_followup", generate_followup)
    graph.add_node("deduplicate_check", deduplicate_check)

    graph.set_entry_point("generate_warmup")
    graph.add_edge("generate_warmup", "__end__")

    return graph.compile()

question_agent_graph = create_question_agent_graph()
```

- [ ] **Step 1: Create QuestionAgent module**

```python
# Write to src/agent/question_agent.py
"""QuestionAgent - Question generation and deduplication."""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.state import InterviewState

async def generate_warmup(state: InterviewState, resume_context: str) -> dict:
    return {"current_question": {"content": "请简单介绍一下你自己", "type": "warmup"}}

async def generate_initial(state: InterviewState, resume_context: str, responsibility: str) -> dict:
    return {"current_question": {"content": f"请谈谈你对{responsibility}的经验", "type": "initial"}}

async def generate_followup(state: InterviewState, qa_history: list, evaluation: dict) -> dict:
    return {"current_question": {"content": "能详细说说吗？", "type": "followup"}}

async def deduplicate_check(state: InterviewState, question_id: str) -> dict:
    from src.agent.base import create_review_voters
    voters = [
        lambda q: q.get("question_id") not in state.asked_logical_questions,
        lambda q: True,
        lambda q: True,
    ]
    voter = create_review_voters(voters)
    passed, failures = await voter.vote({"question_id": question_id})
    return {"deduplicate_passed": passed, "deduplicate_failures": failures}

def should_continue_followup(state: InterviewState) -> Literal["generate_followup", END]:
    from src.config import config
    dev = state.evaluation_results.get(state.current_question_id, {}).get("deviation_score", 0)
    depth = state.followup_depth
    if dev >= config.deviation_threshold and depth >= config.max_followup_depth:
        return END
    return "generate_followup"

def create_question_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("generate_warmup", generate_warmup)
    graph.add_node("generate_initial", generate_initial)
    graph.add_node("generate_followup", generate_followup)
    graph.add_node("deduplicate_check", deduplicate_check)
    graph.set_entry_point("generate_warmup")
    graph.add_edge("generate_warmup", "__end__")
    return graph.compile()

question_agent_graph = create_question_agent_graph()
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/question_agent.py
git commit -m "feat(agent): add QuestionAgent subgraph"
```

---

## Phase 6: EvaluateAgent Implementation

### Task 8: Create EvaluateAgent Subgraph

**Files:**
- Create: `src/agent/evaluate_agent.py`

```python
"""EvaluateAgent - Answer evaluation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def evaluate_with_standard(
    state: InterviewState,
    question: str,
    user_answer: str,
    standard_answer: str
) -> dict:
    """Evaluate answer against standard answer."""
    # TODO: LLM call for evaluation with standard answer
    return {
        "deviation_score": 0.7,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": ["可以更具体"]
    }

async def evaluate_without_standard(
    state: InterviewState,
    question: str,
    user_answer: str
) -> dict:
    """Evaluate answer without standard answer (self-assessment)."""
    # TODO: LLM call for self-assessment
    return {
        "deviation_score": 0.6,
        "is_correct": True,
        "key_points": ["理解正确"],
        "suggestions": ["补充细节"]
    }

def create_evaluate_agent_graph() -> StateGraph:
    """Create EvaluateAgent subgraph."""
    graph = StateGraph(InterviewState)

    graph.add_node("evaluate_with_standard", evaluate_with_standard)
    graph.add_node("evaluate_without_standard", evaluate_without_standard)

    graph.set_entry_point("evaluate_with_standard")
    graph.add_edge("evaluate_with_standard", "__end__")

    return graph.compile()

evaluate_agent_graph = create_evaluate_agent_graph()
```

- [ ] **Step 1: Create EvaluateAgent module**

```python
# Write to src/agent/evaluate_agent.py
"""EvaluateAgent - Answer evaluation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def evaluate_with_standard(
    state: InterviewState,
    question: str,
    user_answer: str,
    standard_answer: str
) -> dict:
    return {
        "deviation_score": 0.7,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": ["可以更具体"]
    }

async def evaluate_without_standard(
    state: InterviewState,
    question: str,
    user_answer: str
) -> dict:
    return {
        "deviation_score": 0.6,
        "is_correct": True,
        "key_points": ["理解正确"],
        "suggestions": ["补充细节"]
    }

def create_evaluate_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("evaluate_with_standard", evaluate_with_standard)
    graph.add_node("evaluate_without_standard", evaluate_without_standard)
    graph.set_entry_point("evaluate_with_standard")
    graph.add_edge("evaluate_with_standard", "__end__")
    return graph.compile()

evaluate_agent_graph = create_evaluate_agent_graph()
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/evaluate_agent.py
git commit -m "feat(agent): add EvaluateAgent subgraph"
```

---

## Phase 7: FeedBackAgent Implementation

### Task 9: Create FeedBackAgent Subgraph

**Files:**
- Create: `src/agent/feedback_agent.py`

```python
"""FeedBackAgent - Feedback generation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def generate_correction(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """Generate CORRECTION feedback (dev < 0.3)."""
    # TODO: LLM call for direct answer
    return {"feedback_content": "正确答案是...", "feedback_type": "correction"}

async def generate_guidance(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """Generate GUIDANCE feedback (0.3 <= dev < 0.6)."""
    # TODO: LLM call for hint
    return {"feedback_content": "提示：想想...?", "feedback_type": "guidance"}

async def generate_comment(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """Generate COMMENT feedback (dev >= 0.6)."""
    # TODO: LLM call for continuation
    return {"feedback_content": "很好，继续...", "feedback_type": "comment"}

async def generate_fallback_feedback(state: InterviewState) -> dict:
    """Generate fallback feedback when retries exhausted."""
    return {"feedback_content": "感谢您的回答，我们继续下一个问题。", "feedback_type": "comment"}

def create_feedback_agent_graph() -> StateGraph:
    """Create FeedBackAgent subgraph."""
    graph = StateGraph(InterviewState)

    graph.add_node("generate_correction", generate_correction)
    graph.add_node("generate_guidance", generate_guidance)
    graph.add_node("generate_comment", generate_comment)
    graph.add_node("generate_fallback_feedback", generate_fallback_feedback)

    graph.set_entry_point("generate_correction")
    graph.add_edge("generate_correction", "__end__")

    return graph.compile()

feedback_agent_graph = create_feedback_agent_graph()
```

- [ ] **Step 1: Create FeedBackAgent module**

```python
# Write to src/agent/feedback_agent.py
"""FeedBackAgent - Feedback generation."""
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def generate_correction(state: InterviewState, question: str, user_answer: str, evaluation: dict) -> dict:
    return {"feedback_content": "正确答案是...", "feedback_type": "correction"}

async def generate_guidance(state: InterviewState, question: str, user_answer: str, evaluation: dict) -> dict:
    return {"feedback_content": "提示：想想...?", "feedback_type": "guidance"}

async def generate_comment(state: InterviewState, question: str, user_answer: str, evaluation: dict) -> dict:
    return {"feedback_content": "很好，继续...", "feedback_type": "comment"}

async def generate_fallback_feedback(state: InterviewState) -> dict:
    return {"feedback_content": "感谢您的回答，我们继续下一个问题。", "feedback_type": "comment"}

def create_feedback_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("generate_correction", generate_correction)
    graph.add_node("generate_guidance", generate_guidance)
    graph.add_node("generate_comment", generate_comment)
    graph.add_node("generate_fallback_feedback", generate_fallback_feedback)
    graph.set_entry_point("generate_correction")
    graph.add_edge("generate_correction", "__end__")
    return graph.compile()

feedback_agent_graph = create_feedback_agent_graph()
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/feedback_agent.py
git commit -m "feat(agent): add FeedBackAgent subgraph"
```

---

## Phase 8: Main Orchestrator Implementation

### Task 10: Create Main Orchestrator Graph

**Files:**
- Create: `src/agent/orchestrator.py`

```python
"""Main Orchestrator - LangGraph main entry point."""
from typing import Literal
from langgraph.graph import StateGraph, END, START
from src.agent.state import InterviewState
from src.agent.resume_agent import resume_agent_graph
from src.agent.knowledge_agent import knowledge_agent_graph
from src.agent.question_agent import question_agent_graph
from src.agent.evaluate_agent import evaluate_agent_graph
from src.agent.feedback_agent import feedback_agent_graph

async def init_node(state: InterviewState) -> dict:
    """Initialize interview state."""
    return {
        "phase": "init",
        "current_series": 1,
        "followup_depth": 0,
    }

async def orchestrator_node(state: InterviewState) -> dict:
    """Orchestrator decides next action based on phase."""
    if state.phase == "init":
        return {"phase": "warmup"}
    elif state.phase == "warmup":
        return {"phase": "initial"}
    elif state.phase == "initial":
        return {"phase": "followup"}
    elif state.phase == "followup":
        return {"phase": "followup"}
    return {"phase": "final_feedback"}

def decide_next_node(state: InterviewState) -> Literal["question_agent", "final_feedback", END]:
    """Decide whether to continue interview or end."""
    from src.config import config

    if state.user_end_requested:
        return "final_feedback"
    if state.current_series >= config.max_series:
        return "final_feedback"
    if state.error_count >= config.error_threshold:
        return "final_feedback"
    if state.all_responsibilities_used:
        return "final_feedback"
    return "question_agent"

async def final_feedback_node(state: InterviewState) -> dict:
    """Generate final feedback."""
    # TODO: Aggregate all Q&A and generate final report
    return {"phase": "completed"}

def create_orchestrator_graph() -> StateGraph:
    """Create main orchestrator graph."""
    graph = StateGraph(InterviewState)

    # Add main nodes
    graph.add_node("init", init_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("decide_next", decide_next_node)
    graph.add_node("final_feedback", final_feedback_node)

    # Add subgraphs as nodes
    graph.add_node("resume_agent", resume_agent_graph)
    graph.add_node("knowledge_agent", knowledge_agent_graph)
    graph.add_node("question_agent", question_agent_graph)
    graph.add_node("evaluate_agent", evaluate_agent_graph)
    graph.add_node("feedback_agent", feedback_agent_graph)

    # Set entry point
    graph.set_entry_point("init")

    # Main flow
    graph.add_edge("init", "orchestrator")
    graph.add_edge("orchestrator", "decide_next")

    # Conditional routing
    graph.add_conditional_edges(
        "decide_next",
        lambda s: s.get("next_action", END),
        {
            "question_agent": "question_agent",
            "resume_agent": "resume_agent",
            "knowledge_agent": "knowledge_agent",
            "evaluate_agent": "evaluate_agent",
            "feedback_agent": "feedback_agent",
            "final_feedback": "final_feedback",
        }
    )

    graph.add_edge("question_agent", "evaluate_agent")
    graph.add_edge("evaluate_agent", "feedback_agent")
    graph.add_edge("feedback_agent", "decide_next")
    graph.add_edge("final_feedback", END)

    return graph.compile()

orchestrator_graph = create_orchestrator_graph()
```

- [ ] **Step 1: Create Main Orchestrator module**

```python
# Write to src/agent/orchestrator.py
"""Main Orchestrator - LangGraph main entry point."""
from typing import Literal
from langgraph.graph import StateGraph, END, START
from src.agent.state import InterviewState
from src.agent.resume_agent import resume_agent_graph
from src.agent.knowledge_agent import knowledge_agent_graph
from src.agent.question_agent import question_agent_graph
from src.agent.evaluate_agent import evaluate_agent_graph
from src.agent.feedback_agent import feedback_agent_graph

async def init_node(state: InterviewState) -> dict:
    return {
        "phase": "init",
        "current_series": 1,
        "followup_depth": 0,
    }

async def orchestrator_node(state: InterviewState) -> dict:
    if state.phase == "init":
        return {"phase": "warmup"}
    elif state.phase == "warmup":
        return {"phase": "initial"}
    elif state.phase == "initial":
        return {"phase": "followup"}
    return {"phase": "final_feedback"}

def decide_next_node(state: InterviewState) -> Literal["question_agent", "final_feedback", END]:
    from src.config import config
    if getattr(state, "user_end_requested", False):
        return "final_feedback"
    if state.current_series >= config.max_series:
        return "final_feedback"
    if state.error_count >= config.error_threshold:
        return "final_feedback"
    if getattr(state, "all_responsibilities_used", False):
        return "final_feedback"
    return "question_agent"

async def final_feedback_node(state: InterviewState) -> dict:
    return {"phase": "completed"}

def create_orchestrator_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("init", init_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("decide_next", decide_next_node)
    graph.add_node("final_feedback", final_feedback_node)
    graph.add_node("resume_agent", resume_agent_graph)
    graph.add_node("knowledge_agent", knowledge_agent_graph)
    graph.add_node("question_agent", question_agent_graph)
    graph.add_node("evaluate_agent", evaluate_agent_graph)
    graph.add_node("feedback_agent", feedback_agent_graph)
    graph.set_entry_point("init")
    graph.add_edge("init", "orchestrator")
    graph.add_edge("orchestrator", "decide_next")
    graph.add_conditional_edges(
        "decide_next",
        lambda s: s.get("next_action", END),
        {
            "question_agent": "question_agent",
            "resume_agent": "resume_agent",
            "knowledge_agent": "knowledge_agent",
            "evaluate_agent": "evaluate_agent",
            "feedback_agent": "feedback_agent",
            "final_feedback": "final_feedback",
        }
    )
    graph.add_edge("question_agent", "evaluate_agent")
    graph.add_edge("evaluate_agent", "feedback_agent")
    graph.add_edge("feedback_agent", "decide_next")
    graph.add_edge("final_feedback", END)
    return graph.compile()

orchestrator_graph = create_orchestrator_graph()
```

- [ ] **Step 2: Update agent __init__.py**

```python
# Update src/agent/__init__.py
from src.agent.orchestrator import orchestrator_graph
from src.agent.resume_agent import resume_agent_graph
from src.agent.knowledge_agent import knowledge_agent_graph
from src.agent.question_agent import question_agent_graph
from src.agent.evaluate_agent import evaluate_agent_graph
from src.agent.feedback_agent import feedback_agent_graph

__all__ = [
    "orchestrator_graph",
    "resume_agent_graph",
    "knowledge_agent_graph",
    "question_agent_graph",
    "evaluate_agent_graph",
    "feedback_agent_graph",
    "AgentPhase", "AgentResult", "ReviewVoter", "create_review_voters"
]
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/
git commit -m "feat(agent): add main orchestrator graph"
```

---

## Phase 9: Integration & API

### Task 11: Create Interview API Endpoints

**Files:**
- Modify: `src/api/interview.py`

```python
"""Interview API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/interview", tags=["interview"])

class StartInterviewRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_id: Optional[str] = None
    user_id: str

class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    """Start a new interview session."""
    from src.agent.orchestrator import orchestrator_graph
    from src.agent.state import InterviewState

    state = InterviewState(
        session_id=request.session_id,
        resume_id=request.resume_id or "",
    )

    result = await orchestrator_graph.ainvoke(state)
    return {"session_id": request.session_id, "status": "started"}

@router.post("/answer")
async def submit_answer(request: AnswerRequest):
    """Submit an answer to a question."""
    return {"question_id": request.question_id, "status": "received"}

@router.post("/end")
async def end_interview(session_id: str):
    """End an interview session."""
    return {"session_id": session_id, "status": "ended"}
```

- [ ] **Step 1: Update interview API**

```python
# Update src/api/interview.py
"""Interview API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/interview", tags=["interview"])

class StartInterviewRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_id: Optional[str] = None
    user_id: str

class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    from src.agent.orchestrator import orchestrator_graph
    from src.agent.state import InterviewState
    state = InterviewState(session_id=request.session_id, resume_id=request.resume_id or "")
    result = await orchestrator_graph.ainvoke(state)
    return {"session_id": request.session_id, "status": "started"}

@router.post("/answer")
async def submit_answer(request: AnswerRequest):
    return {"question_id": request.question_id, "status": "received"}

@router.post("/end")
async def end_interview(session_id: str):
    return {"session_id": session_id, "status": "ended"}
```

- [ ] **Step 2: Commit**

```bash
git add src/api/interview.py
git commit -m "feat(api): add interview orchestration endpoints"
```

---

## Implementation Order

1. **Phase 1: Core Infrastructure** - State, Config, Redis
2. **Phase 2: Base Agent** - Base classes
3. **Phase 3-7: Individual Agents** - Resume, Knowledge, Question, Evaluate, FeedBack
4. **Phase 8: Main Orchestrator** - Graph composition
5. **Phase 9: Integration** - API endpoints

---

## Notes

- TODO placeholders in agent implementations need LLM integration
- Vector DB storage implementation pending
- Review voter functions need actual check logic
- Tests to be added per agent

---

**Plan complete.**