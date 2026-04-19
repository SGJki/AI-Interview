# 架构重构导入路径映射表

## 重构概述

**目的**：消除模块间循环依赖，理清分层职责
**日期**：2026-04-19
**重构方式**：一次性完整重构

---

## 一、类型重映射表（agent/state.py → 新模块）

### 1.1 枚举类型 → `domain/enums.py`

| 类型名 | 当前导入路径 | 重构后导入路径 | 调用方文件 |
|--------|------------|---------------|-----------|
| `InterviewMode` | `src.agent.state` | `src.domain.enums` | src/api/interview.py, src/api/training.py, src/agent/__init__.py, src/services/orchestrator_adapter.py, src/tools/memory_tools.py |
| `FeedbackMode` | `src.agent.state` | `src.domain.enums` | src/api/interview.py, src/api/training.py, src/agent/__init__.py, src/tools/memory_tools.py |
| `FeedbackType` | `src.agent.state` | `src.domain.enums` | src/api/interview.py, src/agent/__init__.py, src/agent/feedback_agent.py, src/services/llm_service.py |
| `SessionStatus` | `src.agent.state` | `src.domain.enums` | src/agent/__init__.py |
| `QuestionType` | `src.agent.state` | `src.domain.enums` | src/api/interview.py, src/api/training.py, src/agent/__init__.py, src/agent/question_agent.py, src/services/llm_service.py, src/services/training_followup.py |
| `FollowupStrategy` | `src.agent.state` | `src.domain.enums` | (仅agent内部使用) |

### 1.2 核心模型 → `domain/models.py`

| 类型名 | 当前导入路径 | 重构后导入路径 | 调用方文件 |
|--------|------------|---------------|-----------|
| `Question` | `src.agent.state` | `src.domain.models` | src/api/interview.py, src/api/training.py, src/agent/__init__.py, src/agent/question_agent.py, src/services/llm_service.py, src/services/orchestrator_adapter.py, src/services/training_followup.py |
| `Answer` | `src.agent.state` | `src.domain.models` | src/api/interview.py, src/api/training.py, src/agent/__init__.py, src/agent/evaluate_agent.py, src/services/orchestrator_adapter.py |
| `Feedback` | `src.agent.state` | `src.domain.models` | src/api/interview.py, src/agent/__init__.py, src/agent/feedback_agent.py, src/services/llm_service.py, src/services/orchestrator_adapter.py |
| `SeriesRecord` | `src.agent.state` | `src.domain.models` | (仅agent内部使用) |

### 1.3 Agent专用类型 → `agent/state.py`（保留）

| 类型名 | 当前导入路径 | 重构后导入路径 | 调用方文件 |
|--------|------------|---------------|-----------|
| `InterviewState` | `src.agent.state` | `src.agent.state` | src/agent/__init__.py, src/agent/orchestrator.py, src/agent/evaluate_agent.py, src/agent/feedback_agent.py, src/agent/knowledge_agent.py, src/agent/question_agent.py, src/agent/resume_agent.py, src/agent/review_agent.py, src/api/interview.py, src/api/training.py, src/services/orchestrator_adapter.py |

### 1.4 会话/持久化类型 → `session/context.py` + `session/snapshot.py`

| 类型名 | 当前导入路径 | 重构后导入路径 | 调用方文件 |
|--------|------------|---------------|-----------|
| `InterviewContext` | `src.agent.state` | `src.session.context` | src/tools/memory_tools.py, src/services/interview_service.py (TYPE_CHECKING), src/core/context_catch.py (lazy), src/agent/__init__.py |
| `ProgressSnapshot` | `src.agent.state` | `src.session.snapshot` | src/services/interview_service.py (TYPE_CHECKING), src/core/context_catch.py (lazy) |
| `EvaluationSnapshot` | `src.agent.state` | `src.session.snapshot` | src/services/interview_service.py (TYPE_CHECKING), src/core/context_catch.py (lazy) |
| `InsightSummary` | `src.agent.state` | `src.session.snapshot` | src/services/interview_service.py (TYPE_CHECKING), src/core/context_catch.py (lazy) |
| `ContextSnapshotData` | `src.agent.state` | `src.session.snapshot` | src/services/interview_service.py (TYPE_CHECKING), src/core/context_catch.py (lazy) |

---

## 二、模块重映射表

### 2.1 基础设施模块

| 模块 | 当前路径 | 重构后路径 | 调用方 |
|------|---------|-----------|--------|
| `SessionStateManager` | `src.tools.memory_tools` | `src.infrastructure.session_store` | src/api/interview.py, src/api/training.py |
| `save_to_session_memory` | `src.tools.memory_tools` | `src.infrastructure.session_store` | src/services/interview_service.py |
| `get_session_memory` | `src.tools.memory_tools` | `src.infrastructure.session_store` | (被API层延迟导入) |
| `clear_session_memory` | `src.tools.memory_tools` | `src.infrastructure.session_store` | src/agent/orchestrator.py, src/services/interview_service.py |
| `update_session_series` | `src.tools.memory_tools` | `src.infrastructure.session_store` | (被API层延迟导入) |
| `cache_next_series_question` | `src.tools.memory_tools` | `src.infrastructure.session_store` | src/services/interview_service.py |
| `get_cached_next_question` | `src.tools.memory_tools` | `src.infrastructure.session_store` | (被API层延迟导入) |
| `set_user_current_interview` | `src.tools.memory_tools` | `src.infrastructure.session_store` | (被API层延迟导入) |
| `get_user_current_interview` | `src.tools.memory_tools` | `src.infrastructure.session_store` | (被API层延迟导入) |

---

## 三、新目录结构

```
src/
├── domain/                    # 共享域类型（无依赖）
│   ├── __init__.py           # 导出 enums, models
│   ├── enums.py              # InterviewMode, FeedbackMode, FeedbackType, SessionStatus, QuestionType, FollowupStrategy
│   └── models.py             # Question, Answer, Feedback, SeriesRecord
│
├── session/                   # 会话/持久化层
│   ├── __init__.py           # 导出 context, snapshot
│   ├── context.py            # InterviewContext
│   └── snapshot.py           # ProgressSnapshot, EvaluationSnapshot, InsightSummary, ContextSnapshotData
│
├── infrastructure/           # 基础设施层
│   ├── __init__.py           # 导出 session_store
│   ├── redis_client.py       # Redis连接（从db/redis_client.py移动）
│   └── session_store.py      # memory_tools重构后的位置
│
├── agent/                    # Agent层
│   ├── __init__.py           # 更新导入路径
│   ├── state.py              # 仅保留InterviewState
│   ├── orchestrator.py       # 更新导入
│   └── agents/               # 各个Agent更新导入
│
├── services/                 # 应用服务层
│   ├── __init__.py           # 更新导入
│   ├── interview_service.py  # 更新导入
│   ├── llm_service.py        # 更新导入
│   └── ...
│
├── api/                      # API层
│   ├── __init__.py
│   ├── interview.py          # 更新导入
│   └── training.py           # 更新导入
│
├── core/                     # 核心层
│   ├── __init__.py
│   └── context_catch.py      # 更新lazy导入路径
│
└── tools/                    # 工具层
    ├── __init__.py           # 重导出 infrastructure.session_store
    └── ...
```

---

## 四、调用方导入更新清单

### 4.1 需要更新 `agent/state.py` → `domain/enums.py` 的文件
- [ ] `src/api/interview.py`
- [ ] `src/api/training.py`
- [ ] `src/agent/__init__.py`
- [ ] `src/services/orchestrator_adapter.py`
- [ ] `src/tools/memory_tools.py`

### 4.2 需要更新 `agent/state.py` → `domain/models.py` 的文件
- [ ] `src/api/interview.py`
- [ ] `src/api/training.py`
- [ ] `src/agent/__init__.py`
- [ ] `src/agent/question_agent.py`
- [ ] `src/services/llm_service.py`
- [ ] `src/services/orchestrator_adapter.py`
- [ ] `src/services/training_followup.py`

### 4.3 需要更新 `agent/state.py` → `session/context.py` 的文件
- [ ] `src/tools/memory_tools.py`
- [ ] `src/agent/__init__.py`
- [ ] `src/core/context_catch.py` (lazy import)

### 4.4 需要更新 `agent/state.py` → `session/snapshot.py` 的文件
- [ ] `src/core/context_catch.py` (lazy import)

### 4.5 需要更新 `tools/memory_tools.py` → `infrastructure/session_store.py` 的文件
- [ ] `src/agent/__init__.py` (重导出)
- [ ] `src/agent/orchestrator.py`
- [ ] `src/api/interview.py`
- [ ] `src/api/training.py`
- [ ] `src/services/interview_service.py`
- [ ] `src/tools/__init__.py` (重导出)

### 4.6 需要移动的文件
- [ ] `src/db/redis_client.py` → `src/infrastructure/redis_client.py`

### 4.7 需要删除/归档的文件
- [ ] `src/tools/memory_tools.py` (功能已迁移到 infrastructure)

---

## 五、重构执行步骤

1. **创建新目录结构**
   - 创建 `src/domain/` 目录
   - 创建 `src/session/` 目录
   - 创建 `src/infrastructure/` 目录

2. **创建新模块文件**
   - `src/domain/__init__.py`
   - `src/domain/enums.py`
   - `src/domain/models.py`
   - `src/session/__init__.py`
   - `src/session/context.py`
   - `src/session/snapshot.py`
   - `src/infrastructure/__init__.py`
   - `src/infrastructure/redis_client.py` (移动)
   - `src/infrastructure/session_store.py` (重构自memory_tools)

3. **更新 `src/agent/state.py`**
   - 删除枚举类型
   - 删除核心模型类型
   - 删除InterviewContext和快照类型
   - 仅保留InterviewState

4. **更新所有调用方导入路径**
   - 按上述清单逐个更新

5. **更新 `src/tools/__init__.py`**
   - 改为重导出 `infrastructure.session_store`

6. **运行测试验证**

7. **删除旧文件**
   - 删除 `src/tools/memory_tools.py`

---

## 六、风险与注意事项

1. **循环导入风险**：重构过程中，特别是步骤3-5期间，某些模块可能暂时无法导入。按顺序执行可避免。
2. **Lazy Import**：`core/context_catch.py` 使用了 lazy import，重构后仍需保持此模式。
3. **TYPE_CHECKING**：`services/interview_service.py` 中的类型只在 TYPE_CHECKING 块中使用，重构后仍需保持。
4. **向后兼容**：本次重构为 breaking change，不提供向后兼容路径。
