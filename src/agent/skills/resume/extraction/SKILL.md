---
name: 信息抽取规范
description: 从简历中抽取关键信息的标准
version: 1.0.0
agent: resume
triggers:
  - action: extract_info
---

# 信息抽取规范

## 抽取优先级

### P0 - 必须抽取
- 项目经验 (projects)
- 技术栈 (skills)
- 职责描述 (responsibilities)

### P1 - 尽量抽取
- 工作年限
- 教育背景
- 证书认证

### P2 - 可选
- 兴趣爱好
- 自我评价

## 项目经验抽取

每个项目需包含：

```python
{
    "name": str,           # 项目名称
    "description": str,     # 项目描述
    "tech_stack": list[str],  # 技术栈
    "responsibilities": list[str],  # 职责
    "achievements": list[str]  # 成果（可选）
}
```

## 职责文本规范

### 良好示例 ✅
- "使用 FastAPI 构建 REST API，支持 1000+ 并发请求"
- "优化数据库查询，P99 延迟从 500ms 降至 50ms"
- "设计并实现 RAG 知识库系统，提升问答准确率 30%"

### 糟糕示例 ❌
- "参与项目开发"
- "负责后端工作"
- "使用各种技术"

## 职责去重

同一项目的多个职责：
- 合并相似的
- 保留最具特色的
- 总数控制在 5-8 个
