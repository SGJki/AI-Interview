---
name: 偏差分数计算
description: deviation_score 计算方法
version: 1.0.0
agent: evaluate
triggers:
  - action: calculate_deviation
---

# 偏差分数计算

## 定义

`deviation_score` 表示用户回答与标准答案的偏差程度：

- **1.0**: 完全符合
- **0.5**: 部分符合，中等偏差
- **0.0**: 完全偏离

## 计算公式

```
deviation_score = base_score * completeness * accuracy

其中:
- base_score: 基础匹配分 (0-1)
- completeness: 完整度因子 (0-1)
- accuracy: 准确性因子 (0-1)
```

## 简化计算

实际使用中简化为：

```python
def calculate_deviation(user_answer: str, standard_answer: str) -> float:
    # 1. 关键词匹配
    keywords = extract_keywords(standard_answer)
    keyword_match = sum(1 for k in keywords if k in user_answer) / len(keywords)

    # 2. 语义相似度
    semantic_sim = compute_similarity(user_answer, standard_answer)

    # 3. 完整性调整
    length_ratio = len(user_answer) / len(standard_answer)
    completeness = min(length_ratio, 1.0)

    # 4. 综合得分
    score = keyword_match * 0.4 + semantic_sim * 0.4 + completeness * 0.2

    return max(0.0, min(1.0, score))
```

## 无标准答案时

当没有标准答案时，使用语义分析：

```python
def calculate_without_standard(user_answer: str, question: str) -> float:
    # 基于问题类型和质量判断
    expected_keywords = extract_expected_keywords(question)

    # 检查回答是否实质性地回应了问题
    if not expected_keywords:
        return 0.5  # 默认中等

    keyword_coverage = calculate_coverage(user_answer, expected_keywords)

    # 长度检查
    if len(user_answer) < 20:
        return keyword_coverage * 0.5  # 太短，降低分数

    return keyword_coverage
```

## 分数解释

| 分数范围 | 解释 | 后续动作 |
|---------|------|----------|
| 0.8 - 1.0 | 优秀，可深入追问 | 生成深度追问 |
| 0.6 - 0.8 | 良好，稍有不足 | 引导补充 |
| 0.3 - 0.6 | 一般，需要引导 | 生成引导性问题 |
| 0.0 - 0.3 | 较差，需纠正 | 生成纠错反馈 |

## 特殊情况

### 回答过短
```python
if len(user_answer) < 10:
    # 可能是敷衍或不理解问题
    return {"deviation": 0.3, "suggestion": "请详细描述你的经验"}
```

### 跑题
```python
if semantic_sim < 0.2:
    return {"deviation": 0.1, "suggestion": "你的回答似乎偏离了问题，请重新回答"}
```

### 完美回答
```python
if deviation >= 0.95:
    return {"deviation": 1.0, "suggestion": "回答非常完美！"}
```
