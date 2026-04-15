# Skill System - AI Interview Agent 方法论系统

**Last Updated:** 2026-04-10
**Entry Point:** `src/agent/skill_loader.py`
**Skills:** `src/agent/skills/`

## Overview

Skill 系统为 AI Interview 项目提供**Context-Aware 方法论加载机制**。只有当检测到需要使用 Skill 时，才将匹配的 Skill 内容与 base-prompt 一起输入给 LLM。

```
传统方式:
  prompt = base_prompt + 大量 skill 文档（一次性全部注入）

Skill 系统方式:
  if ContextAwareSkillLoader 检测到需要 skill:
      prompt = base_prompt + 匹配的 skill（按需加载）
```

## Core Design

### Detection Logic

```python
class ContextAwareSkillLoader:

    def get_skills_for_context(self, agent, phase, action, state):
        """
        检测哪些 skill 需要被加载
        """
        matched_skills = []

        for skill_dir in [common/, agent/]:
            for skill_file in skill_dir.glob("**/SKILL.md"):
                skill = self._parse_skill(skill_file)

                # 关键：检测逻辑
                if self._matches_triggers(skill, phase, action, state):
                    matched_skills.append(skill)

        return matched_skills
```

### Trigger Detection

三种触发方式，任一满足即加载：

```python
def _matches_triggers(self, skill, phase, action, state):
    for trigger in skill.triggers:

        # 1. Phase 触发
        if "phase" in trigger and trigger["phase"] == phase:
            return True

        # 2. Action 触发
        if "action" in trigger and trigger["action"] == action:
            return True

        # 3. Condition 触发
        if "condition" in trigger and self._eval_condition(trigger["condition"], state):
            return True

    return False
```

### Condition Expression

```python
def _eval_condition(self, condition: str, state: dict) -> bool:
    # 示例: "state.deviation_score < 0.3"
    # 转换为: state["deviation_score"] < 0.3
    expr = condition
    for key, value in state.items():
        expr = expr.replace(f"state.{key}", repr(value))
    return eval(expr, {"__builtins__": {}}, {"state": state})
```

## Skill Loading Flow

```
Agent 调用 LLM
        │
        ▼
skill_aware_prompt(agent, phase, action, state)
        │
        ▼
ContextAwareSkillLoader.get_skills_for_context()
        │
        ▼
遍历: common/*/SKILL.md + {agent}/*/SKILL.md
        │
        ▼
对每个 skill 调用 _matches_triggers()
        │
        ├── 命中 ──→ 添加到 matched_skills
        └── 未命中 ──→ 跳过
        │
        ▼
inject_skills_to_prompt() 注入到 prompt
        │
        ▼
LLM 调用
```

## Skill File Format

```yaml
---
name: skill-name
description: 技能描述及使用场景
version: 1.0.0
agent: <agent-name>  # common 表示通用
triggers:            # 按触发条件加载
  - phase: <phase-name>
  - action: <action-name>
  - condition: <condition-expression>
---

# Skill Title

## 何时使用
- 场景1
- 场景2

## 核心方法论
详细步骤...

## 最佳实践
1. ...
```

## Directory Structure

```
src/agent/skills/
├── common/                          # 通用技能（所有 Agent 共享）
│   ├── SKILL.md                    # 通用技能清单
│   ├── retry/                     # 重试策略
│   │   └── SKILL.md              # triggers: error 类型
│   ├── error-handling/            # 错误处理
│   │   └── SKILL.md
│   ├── llm-calling/               # LLM 调用规范
│   │   └── SKILL.md
│   └── state-management/           # 状态管理
│       └── SKILL.md
│
├── orchestrator/                   # 编排协调
│   ├── SKILL.md
│   ├── session-management/
│   │   └── SKILL.md              # triggers: phase=init
│   └── routing/
│       └── SKILL.md              # triggers: action=decide_next
│
├── resume/                         # 简历解析
│   ├── SKILL.md
│   ├── parsing/
│   │   └── SKILL.md              # triggers: action=parse_resume
│   └── extraction/
│       └── SKILL.md              # triggers: action=extract_info
│
├── question/                       # 问题生成
│   ├── SKILL.md
│   ├── generation/
│   │   └── SKILL.md              # triggers: phase=warmup/initial
│   ├── followup/
│   │   └── SKILL.md             # triggers: phase=followup
│   └── deduplication/
│       └── SKILL.md             # triggers: action=deduplicate
│
├── evaluate/                       # 评估
│   ├── SKILL.md
│   ├── scoring/
│   │   └── SKILL.md             # triggers: action=evaluate
│   └── deviation/
│       └── SKILL.md             # triggers: action=calculate_deviation
│
├── feedback/                       # 反馈
│   ├── SKILL.md
│   ├── correction/
│   │   └── SKILL.md             # triggers: deviation < 0.3
│   ├── guidance/
│   │   └── SKILL.md             # triggers: 0.3 <= deviation < 0.6
│   └── comment/
│       └── SKILL.md             # triggers: deviation >= 0.6
│
├── review/                         # 审查
│   ├── SKILL.md
│   ├── voting/
│   │   └── SKILL.md             # triggers: action=review_evaluation
│   └── validation/
│       └── SKILL.md             # triggers: action=validate_evaluation
│
└── knowledge/                      # 知识管理
    ├── SKILL.md
    ├── vector-store/
    │   └── SKILL.md             # triggers: action=store_vector
    └── responsibility-tracking/
        └── SKILL.md             # triggers: action=track_responsibility
```

## Agent Integration

### Using skill_aware_prompt (Recommended)

```python
from dataclasses import asdict
from src.agent.skill_loader import skill_aware_prompt

async def generate_followup(state: InterviewState, ...):
    # Original prompt
    prompt = f"问题: {question}\n回答: {answer}\n"

    # Skill-enhanced prompt
    enhanced = skill_aware_prompt(
        agent="question",
        phase=state.phase,          # warmup / initial / followup
        action="generate_followup",
        base_prompt=prompt,
        state=asdict(state),        # For condition matching
    )

    result = await invoke_llm(enhanced)
```

### Using SkillContext

```python
from src.agent.skill_loader import SkillContext

async def some_agent_method(state: InterviewState):
    prompt = "Original prompt..."

    with SkillContext(
        agent="question",
        phase="followup",
        action="generate_followup"
    ) as ctx:
        ctx.set_state(asdict(state))
        enhanced_prompt = ctx.enhance(prompt)
```

## Key Benefits

| Traditional Approach | Skill System |
|--------------------|-------------|
| Inject all skills at once | Load only matched skills |
| Prompt becomes bloated | Prompt stays concise |
| LLM overwhelmed by docs | LLM receives only relevant methodology |
| Hard to test and maintain | Skills are independent and testable |

## Design Principles

1. **Zero Overhead**: No cost when skills are not used
2. **Precise Matching**: Only load when triggers match
3. **Hierarchical Composition**: Common → Agent → Action
4. **Context-Aware**: Dynamic decision via state

## Related Documentation

- [Agent Architecture](agents.md) - Agent structure and orchestration
- [Services](services.md) - Business logic layer
- [State Management](../src/agent/state.py) - InterviewState definition
