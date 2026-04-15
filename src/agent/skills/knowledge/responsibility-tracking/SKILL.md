---
name: 职责追踪
description: 职责分配和追踪策略
version: 1.0.0
agent: knowledge
triggers:
  - action: track_responsibility
---

# 职责追踪

## 职责管理流程

```
简历解析
    ↓
抽取 responsibilities
    ↓
打散 (shuffle)
    ↓
分配到各 series
    ↓
按顺序提问
```

## 职责分配

### 打散策略

```python
import random

def shuffle_responsibilities(responsibilities: list[str]) -> list[str]:
    """打散职责顺序，增加多样性"""
    shuffled = list(responsibilities)
    random.shuffle(shuffled)
    return shuffled
```

### Series 分配

```python
def assign_responsibilities_to_series(
    responsibilities: tuple[str],
    num_series: int = 5
) -> dict[int, list[int]]:
    """将职责分配到各 series"""

    responsibilities_per_series = len(responsibilities) // num_series
    remainder = len(responsibilities) % num_series

    assignment = {}
    idx = 0
    for series in range(1, num_series + 1):
        count = responsibilities_per_series + (1 if series <= remainder else 0)
        assignment[series] = list(range(idx, idx + count))
        idx += count

    return assignment
```

## 职责状态追踪

```python
# state 中职责相关字段
responsibilities: tuple[str, ...]  # 所有职责
series_responsibility_map: dict[int, int]  # series -> responsibility_index
current_responsibility_index: int  # 当前职责索引

# 使用示例
current_resp = responsibilities[current_responsibility_index]
```

## 职责完成判断

```python
def is_responsibility_mastered(
    responsibility: str,
    mastered_questions: dict[str, dict]
) -> bool:
    """判断某职责是否已掌握"""
    # 找到该职责相关的问答对
    related_qa = [
        qa for qa in mastered_questions.values()
        if responsibility in qa.get("question", "")
    ]

    if not related_qa:
        return False

    # 所有相关问答的 deviation 都 >= 0.8 才算掌握
    return all(qa.get("deviation_score", 0) >= 0.8 for qa in related_qa)
```

## 职责轮转

```
series 1: responsibility[0], responsibility[1]
series 2: responsibility[2], responsibility[3]
series 3: responsibility[4], responsibility[5]
...
```

## 完成条件

满足以下任一条件终止面试：

```python
all_responsibilities_used: bool  # 所有职责都已提问过
# OR
current_series >= max_series  # 达到最大 series 数
```
