---
name: 评估验证
description: 评估结果验证标准
version: 1.0.0
agent: review
triggers:
  - action: validate_evaluation
---

# 评估验证

## 验证维度

### 1. 数值合理性

```python
def validate_scores(evaluation: dict) -> list[str]:
    """验证分数合理性"""
    errors = []
    dev = evaluation.get("deviation_score", 0.5)

    if not 0 <= dev <= 1:
        errors.append(f"deviation_score {dev} out of range [0, 1]")

    return errors
```

### 2. 内容完整性

```python
def validate_completeness(evaluation: dict) -> list[str]:
    """验证评估完整性"""
    errors = []

    required_fields = ["deviation_score", "is_correct"]
    for field in required_fields:
        if field not in evaluation:
            errors.append(f"missing field: {field}")

    return errors
```

### 3. 与回答的一致性

```python
def validate_consistency(
    evaluation: dict,
    question: str,
    answer: str
) -> list[str]:
    """验证评估与问答的一致性"""
    errors = []

    dev = evaluation.get("deviation_score", 0.5)
    key_points = evaluation.get("key_points", [])

    # 如果 deviation 高但 key_points 少，有问题
    if dev > 0.7 and len(key_points) < 2:
        errors.append("high score but few key points")

    # 如果 deviation 低但说有正确点，有问题
    if dev < 0.4 and evaluation.get("is_correct"):
        errors.append("low score but marked as correct")

    return errors
```

## 验证决策

```python
def decide_review_result(
    evaluation: dict,
    question: str,
    answer: str,
    standard_answer: str = None
) -> dict:
    """综合验证结果决定审查是否通过"""

    all_errors = []
    all_errors.extend(validate_scores(evaluation))
    all_errors.extend(validate_completeness(evaluation))
    all_errors.extend(validate_consistency(evaluation, question, answer))

    if all_errors:
        return {
            "passed": False,
            "errors": all_errors,
            "action": "regenerate"
        }

    return {
        "passed": True,
        "errors": [],
        "action": "continue"
    }
```

## 修复策略

| 错误类型 | 修复策略 |
|---------|---------|
| 分数超范围 | clamp 到 [0, 1] |
| 缺少字段 | 使用默认值填充 |
| 一致性问题 | 重新调用 LLM 生成 |
| 标准答案不匹配 | 忽略该标准答案 |
