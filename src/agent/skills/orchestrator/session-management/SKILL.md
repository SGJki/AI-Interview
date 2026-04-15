---
name: 会话生命周期管理
description: 面试会话的初始化、运行和结束
version: 1.0.0
agent: orchestrator
triggers:
  - phase: init
  - action: end_session
---

# 会话生命周期管理

## 会话状态

```python
class SessionStatus(str, Enum):
    ACTIVE = "active"       # 进行中
    COMPLETED = "completed" # 已完成
    CANCELLED = "cancelled" # 已取消
```

## 会话初始化

```python
async def init_session(state: InterviewState) -> dict:
    """初始化面试会话"""
    return {
        "phase": "warmup",
        "current_series": 1,
        "followup_depth": 0,
        "error_count": 0,
        "created_at": datetime.now(),
    }
```

## 会话流程

```
init
    ↓
warmup (预热)
    ↓
initial (初始问题)
    ↓
followup (追问循环)
    ↓
decide_next (决定下一步)
    ↓ ├── question_agent (继续)
    ↓ ├── end_interview (结束)
    ↓ └── final_feedback (完成)
```

## 会话结束

### 正常结束

```python
async def end_interview_node(state: InterviewState) -> dict:
    """结束面试：写入 PostgreSQL + 清理 Redis"""

    # 1. 写入 PostgreSQL
    async for session in get_db_session():
        dao = InterviewSessionDAO(session)
        interview_session = await dao.find_by_uuid(session_uuid)
        if interview_session:
            await dao.end_session(interview_session.id)

    # 2. 清理 Redis
    await clear_session_memory(state.session_id)

    return {"phase": "completed"}
```

### 异常结束

满足以下条件时异常结束：

| 条件 | 说明 |
|------|------|
| `error_count >= error_threshold` | 连续答错超过阈值 |
| `user_end_requested` | 用户主动结束 |
| `all_responsibilities_used` | 所有职责已覆盖 |
| `current_series >= max_series` | 达到最大系列数 |

## 会话数据持久化

```python
# 会话结束时写入的数据
session_data = {
    "session_id": state.session_id,
    "resume_id": state.resume_id,
    "status": SessionStatus.COMPLETED,
    "started_at": state.created_at,
    "ended_at": datetime.now(),
    "series_history": state.series_history,
    "answers": state.answers,
    "feedbacks": state.feedbacks,
}
```

## Redis 清理

```python
from src.tools.memory_tools import clear_session_memory

# 清理会话相关的 Redis 数据
await clear_session_memory(session_id)
# - interview_state
# - pending_feedbacks
# - conversation_history
```
