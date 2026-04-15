---
name: 投票机制
description: 3-instance 投票审查评估结果
version: 1.0.0
agent: review
triggers:
  - action: review_evaluation
  - phase: followup
---

# 投票机制

## 概述

Review Agent 使用 3 个 Voter 对评估结果进行投票：
- 至少 2 票通过才算通过
- 任何一票失败都需要复查

## Voter 定义

### Voter 0: LLM 判断
```python
async def voter_0(evaluation: dict, question: str, answer: str) -> bool:
    """使用 LLM 判断评估是否基于问答内容"""
    prompt = f"""
    问题: {question}
    回答: {answer}
    评估: {evaluation}

    评估是否基于问答内容而非外部信息？只回答 YES 或 NO。
    """
    result = await invoke_llm(prompt, temperature=0.3)
    return "YES" in result.upper()
```

### Voter 1: 合理性检查
```python
def voter_1(evaluation: dict, question: str, answer: str) -> bool:
    """检查评估是否合理"""
    dev = evaluation.get("deviation_score", 0.5)
    # 偏差分数必须在合理范围内
    return 0 <= dev <= 1
```

### Voter 2: 标准答案契合度
```python
async def voter_2(evaluation: dict, question: str, standard_answer: str) -> bool:
    """使用语义相似度检查标准答案与问题是否契合"""
    if not standard_answer:
        return True  # 没有标准答案时跳过
    score = await compute_similarity(question, standard_answer)
    return score > 0.7
```

## 投票流程

```
收集 3 个 Voter 结果
    ↓
统计通过票数
    ↓
通过票数 >= 2？
    ↓ 是
审查通过 ← 返回 evaluation_results
    ↓ 否
审查失败 ← 返回 failures 列表
```

## 失败类型

| 失败点 | 描述 |
|--------|------|
| voter_0 | 评估未基于问答内容 |
| voter_1 | 评估结果不合理 |
| voter_2 | 标准答案不匹配 |

## 失败处理

```python
if not review_passed:
    if "voter_0" in failures:
        # 重新调用 LLM 判断
        return await regenerate_evaluation()
    if "voter_1" in failures:
        # 修正偏差分数
        evaluation["deviation_score"] = clamp(evaluation["deviation_score"], 0, 1)
    if "voter_2" in failures:
        # 忽略该标准答案
        evaluation["standard_answer"] = None
```
