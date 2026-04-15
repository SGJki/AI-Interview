---
name: LLM 调用规范
description: LLM 调用最佳实践
version: 1.0.0
agent: common
triggers:
  - condition: "llm_call == true"
---

# LLM 调用规范

## 调用前检查

1. **State 验证**: 确保 state 中有所需字段
2. **参数准备**: 提取 question/answer/evaluation 等核心数据
3. **上下文组装**: 按 Agent 需求组装 prompt

## Prompt 组装原则

### 分离系统 Prompt 和用户 Prompt

```python
system_prompt = """
你是一个专业的 AI 面试官。
遵循面试礼仪，保持专业态度。
"""
user_prompt = f"""
问题: {question}
回答: {user_answer}
评估要求: {evaluation_criteria}
"""
```

### Skill 注入

使用 `ContextAwareSkillLoader.inject_skills_to_prompt()` 按需注入方法论：

```python
enhanced_prompt = skill_loader.inject_skills_to_prompt(
    agent="evaluate",
    phase=state.phase,
    action="evaluate_answer",
    state=asdict(state),
    base_prompt=user_prompt,
)
```

## 调用参数配置

| 参数 | 场景 | 推荐值 |
|------|------|--------|
| temperature | 评估/反馈 | 0.3 - 0.5 |
| temperature | 问题生成 | 0.7 - 0.9 |
| max_tokens | 短回复 | 200 - 500 |
| max_tokens | 长回复 | 1000 - 2000 |

## 调用后处理

1. **响应解析**: 提取结构化数据 (JSON)
2. **默认值**: 解析失败时返回安全的默认值
3. **日志记录**: 记录输入输出便于调试

## 常见问题处理

| 问题 | 处理方式 |
|------|----------|
| 响应为空 | 返回 fallback 内容 |
| JSON 解析失败 | 尝试正则提取，或返回默认结构 |
| 响应格式不符 | 使用默认字段值填充 |
