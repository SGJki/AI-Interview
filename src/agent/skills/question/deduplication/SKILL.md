---
name: 问题去重检查
description: 检测重复或相似问题
version: 1.0.0
agent: question
triggers:
  - action: deduplicate
---

# 问题去重检查

## 去重层级

### 1. 精确去重
相同的问题文本不重复提问：

```python
if question_content in asked_questions:
    return {"deduplicate": True, "reason": "exact_match"}
```

### 2. 语义去重
使用向量相似度检测语义重复：

```python
similarity = compute_similarity(new_question, existing_question)
if similarity > 0.85:
    return {"deduplicate": True, "reason": "semantic_match"}
```

### 3. 话题去重
同一话题的多个问题避免重复：

```python
topic = extract_topic(new_question)
if topic in current_series_topics:
    return {"deduplicate": True, "reason": "topic_match"}
```

## 去重存储

记录已问问题：

```python
asked_logical_questions: set[str]  # 已问问题的语义哈希
# 用于语义去重

asked_question_texts: list[str]  # 已问问题文本
# 用于精确去重

asked_topics: set[str]  # 已覆盖话题
# 用于话题去重
```

## 去重决策流程

```
生成新问题
    ↓
检查精确匹配？
    ↓ 是 → 跳过，返回 None
    ↓ 否
检查语义相似度 > 0.85？
    ↓ 是 → 跳过，生成变体
    ↓ 否
检查话题重复？
    ↓ 是 → 调整问题方向
    ↓ 否
通过检查 → 返回问题
```

## 变体问题生成

当检测到重复时，生成变体：

```
原始: "FastAPI 高并发如何处理？"
变体1: "你使用 FastAPI 时遇到过性能瓶颈吗？"
变体2: "FastAPI 处理请求的流程是怎样的？"
变体3: "除了 FastAPI，你还用過哪些框架？"
```
