---
name: 简历解析方法
description: 简历文本解析的标准化流程
version: 1.0.0
agent: resume
triggers:
  - action: parse_resume
  - phase: warmup
---

# 简历解析方法

## 解析流程

```
原始简历文本
    ↓
LLM 提取信息 (extract_resume_info)
    ↓
结构化数据
    ├── skills: list[str]
    ├── projects: list[Project]
    └── experience: list[Experience]
    ↓
抽取 responsibilities
    ↓
存储到 knowledge_base
```

## LLM 提取字段

```python
{
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "projects": [
        {
            "name": "AI Interview System",
            "description": "基于 LangGraph 的面试系统",
            "responsibilities": [
                "设计架构方案",
                "实现核心模块",
                "优化性能"
            ]
        }
    ],
    "experience": [...]
}
```

## 职责抽取原则

1. **粒度**: 每个 responsibility 独立可问
2. **具体性**: 包含具体技术/方法，而非泛泛描述
3. **可量化**: 包含结果指标（性能提升 X%）

## 解析质量检查

| 检查项 | 标准 |
|--------|------|
| skills 数量 | >= 3 |
| projects 数量 | >= 1 |
| responsibilities 总数 | >= 3 |
| 平均 responsibility 长度 | 20-200 字 |

## 错误处理

解析失败时：
- 返回 fallback: `{"skills": [], "projects": [], "experience": []}`
- responsibilities 使用: `["简历解析失败，使用默认职责"]`
