---
name: 状态管理
description: InterviewState 状态管理规范
version: 1.0.0
agent: common
triggers:
  - phase: init
---

# 状态管理规范

## InterviewState 核心字段

### 面试进度
```python
session_id: str           # 会话唯一标识
resume_id: str            # 简历标识
current_series: int       # 当前系列号 (1-5)
current_question: Question # 当前问题对象
current_question_id: str  # 问题 ID
```

### 追问追踪
```python
followup_depth: int       # 当前追问深度
max_followup_depth: int   # 最大追问深度 (默认 3)
followup_chain: list[str] # 追问链 [q1, q2, q3]
```

### 回答记录
```python
answers: dict[str, Answer]                    # {question_id: Answer}
feedbacks: dict[str, Feedback]              # {question_id: Feedback}
evaluation_results: dict[str, dict]         # {question_id: eval_result}
```

### 系列历史
```python
series_history: dict[int, SeriesRecord]  # {series_num: SeriesRecord}
mastered_questions: dict[str, dict]     # dev >= 0.8 的问答对
```

## 状态更新原则

### 1. 不可变性
使用 dataclass(frozen=True)，状态更新返回新对象：

```python
# 错误 ❌
state.answers[question_id] = new_answer

# 正确 ✅
return {"answers": {**state.answers, question_id: new_answer}}
```

### 2. 增量更新
只返回变化的字段，LangGraph 自动合并：

```python
return {
    "current_question": new_question,
    "current_question_id": new_question_id,
    "followup_depth": new_depth,
}
```

### 3. 派生状态
从主状态派生，不单独存储：

```python
@property
def is_mastered(self) -> bool:
    return self.deviation_score >= 0.8
```

## Phase 流转

```
init → warmup → initial → followup → final_feedback
         ↓
      (decide_next)
         ↓
    ├── question_agent (继续提问)
    ├── end_interview (终止)
    └── final_feedback (完成)
```

## 错误状态处理

```python
error_count: int  # 当前系列连续错误次数

# 超过阈值时终止
if error_count >= error_threshold:
    return {"next_action": "end_interview"}
```
