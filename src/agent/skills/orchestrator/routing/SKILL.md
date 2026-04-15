---
name: 路由决策
description: 决定下一步执行哪个 Agent
version: 1.0.0
agent: orchestrator
triggers:
  - action: decide_next
---

# 路由决策

## 决策流程

```
decide_next 节点
    ↓
检查终止条件
    ↓
决定下一步 action
    ↓
├─ question_agent
├─ end_interview
├─ final_feedback
└─ 其他
```

## 决策条件

### 1. 终止条件检查

```python
def decide_next_node(state: InterviewState) -> dict:
    """决定下一步"""

    # 1. 用户主动结束
    if getattr(state, "user_end_requested", False):
        return {"next_action": "end_interview"}

    # 2. 连续错误超限
    if state.error_count >= config.error_threshold:
        return {"next_action": "end_interview"}

    # 3. 所有职责已使用
    if getattr(state, "all_responsibilities_used", False):
        return {"next_action": "end_interview"}

    # 4. 达到最大 series
    if state.current_series >= config.max_series:
        return {"next_action": "final_feedback"}

    # 继续提问
    return {"next_action": "question_agent"}
```

### 2. 条件优先级

| 优先级 | 条件 | Action |
|--------|------|--------|
| 1 | user_end_requested | end_interview |
| 2 | error_count >= threshold | end_interview |
| 3 | all_responsibilities_used | end_interview |
| 4 | current_series >= max_series | final_feedback |
| 5 | 其他 | question_agent |

## 路由映射

```python
# graph 中的路由配置
graph.add_conditional_edges(
    "decide_next",
    lambda s: s.next_action if s.next_action is not None else END,
    {
        "question_agent": "question_agent",
        "resume_agent": "resume_agent",
        "knowledge_agent": "knowledge_agent",
        "evaluate_agent": "evaluate_agent",
        "feedback_agent": "feedback_agent",
        "review_agent": "review_agent",
        "final_feedback": "final_feedback",
        "end_interview": "end_interview",
    }
)
```

## 标准流程边

```python
# 标准流程
question_agent → evaluate_agent
evaluate_agent → review_agent
review_agent → feedback_agent
feedback_agent → decide_next
```

## 异常流程边

```python
# 评估不通过时
evaluate_agent → question_agent (重新提问)

# 审查失败时
review_agent → evaluate_agent (重新评估)
```
