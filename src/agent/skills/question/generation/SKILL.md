---
name: 问题生成策略
description: 面试问题生成的标准化方法
version: 1.0.0
agent: question
triggers:
  - action: generate_question
  - phase: warmup
  - phase: initial
---

# 问题生成策略

## 问题类型

| 类型 | 触发时机 | 示例 |
|------|----------|------|
| warmup | 面试开始 | "请简单介绍一下你自己" |
| initial | 新系列开始 | 关于某个 responsibility 的问题 |
| followup | 追问 | "能详细说说吗？" |

## 生成原则

### 1. 基于职责
问题应针对简历中的具体职责：

```
responsibility: "使用 FastAPI 构建 REST API，支持 1000+ 并发"
↓
question: "你提到使用 FastAPI 构建了高并发 API，能详细说说你是如何处理 1000+ 并发请求的吗？"
```

### 2. STAR 法则
使用 STAR 框架设计问题：

- **S**ituation: 场景/背景
- **T**ask: 任务/目标
- **A**ction: 行动/做法
- **R**esult: 结果/成果

### 3. 开放性问题
避免是非问题，使用开放式问题：

```
❌ "你用过 FastAPI 吗？" (YES/NO)
✅ "你在项目中如何使用 FastAPI 解决性能问题？" (详细回答)
```

## 问题模板

### 预热问题 (warmup)
```python
warmup_questions = [
    "请简单介绍一下你自己",
    "你能用一句话描述你的技术背景吗？",
    "你最近在做什么项目？",
]
```

### 初始问题 (initial)
```
请谈谈你在{responsibility}方面的经验。
你如何理解{tech_stack}在项目中的应用？
能描述一个你解决过的{challenge}问题吗？
```

### 问题难度梯度

```
简单 → 中等 → 困难
  ↓       ↓       ↓
概念     实践     深度
是什么   怎么做   为什么/改进
```

## 质量检查

| 检查项 | 标准 |
|--------|------|
| 问题长度 | 20-100 字 |
| 是否开放式 | 必须 |
| 是否针对职责 | 必须 |
| 是否可回答 | 必须（有足够信息）|
