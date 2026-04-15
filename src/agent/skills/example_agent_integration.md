# Skill 系统集成示例

本文档展示如何将 Skill 系统集成到 Agent 中。

## 基本集成模式

### 1. 使用 skill_aware_prompt 函数（推荐）

```python
from dataclasses import asdict
from src.agent.skill_loader import skill_aware_prompt

async def generate_warmup(state: InterviewState, resume_context: str = "") -> dict:
    """生成预热问题 - 带 Skill 增强"""
    # 构建原始 prompt
    prompt = QUESTION_GENERATION_PROMPT.format(
        resume_info=resume_context,
        series_num=0,
        question_num=0,
        interview_mode="warmup",
        knowledge_context="预热阶段",
        responsibility_context="",
    )

    # 使用 skill_aware_prompt 增强
    enhanced_prompt = skill_aware_prompt(
        agent="question",
        phase=state.phase,
        action="generate_question",
        base_prompt=prompt,
        state=asdict(state),
    )

    # 调用 LLM
    result = await invoke_llm(
        system_prompt="",
        user_prompt=enhanced_prompt,
        temperature=0.7,
    )

    return {"current_question": parse_question(result)}
```

### 2. 使用 SkillContext 上下文管理器

```python
from src.agent.skill_loader import SkillContext

async def generate_initial(state: InterviewState, resume_context: str, responsibility: str) -> dict:
    """生成初始问题 - 使用上下文管理器"""
    prompt = QUESTION_GENERATION_PROMPT.format(...)

    with SkillContext(agent="question", phase=state.phase, action="generate_question") as ctx:
        ctx.set_state(asdict(state))
        enhanced_prompt = ctx.enhance(prompt)

    result = await invoke_llm(...)
    return {"current_question": parse_question(result)}
```

## 完整集成示例：question_agent

```python
# question_agent.py
"""QuestionAgent - 问题生成（带 Skill 增强）"""
import logging
from dataclasses import asdict
from langgraph.graph import StateGraph

from src.agent.state import InterviewState, Question, QuestionType
from src.agent.retry import async_retryable
from src.agent.skill_loader import skill_aware_prompt
from src.llm.prompts import QUESTION_GENERATION_PROMPT
from src.llm.client import invoke_llm

logger = logging.getLogger(__name__)


@async_retryable(max_attempts=3)
async def generate_warmup(state: InterviewState, resume_context: str = "") -> dict:
    """生成预热问题"""
    prompt = QUESTION_GENERATION_PROMPT.format(
        resume_info=resume_context or "无简历信息",
        series_num=0,
        question_num=0,
        interview_mode="warmup",
        knowledge_context="预热阶段",
        responsibility_context="",
    )

    # Skill 增强
    enhanced_prompt = skill_aware_prompt(
        agent="question",
        phase="warmup",
        action="generate_question",
        base_prompt=prompt,
        state=asdict(state),
    )

    try:
        question_content = await invoke_llm(
            system_prompt="",
            user_prompt=enhanced_prompt,
            temperature=0.7,
        )
        question_content = question_content.strip()
    except Exception as e:
        logger.warning(f"generate_warmup LLM call failed: {e}, using fallback")
        question_content = "请简单介绍一下你自己"

    question_id = generate_question_id()

    return {
        "current_question": Question(
            content=question_content,
            question_type=QuestionType.INITIAL,
            series=0,
            number=0,
            parent_question_id=None,
        ),
        "current_question_id": question_id,
        "followup_depth": 0,
        "followup_chain": [question_id],
    }


@async_retryable(max_attempts=3)
async def generate_followup(state: InterviewState, qa_history: list, evaluation: dict) -> dict:
    """生成追问"""
    # ... 构建 prompt ...

    # Skill 增强 - 根据当前 phase 和 action 匹配
    enhanced_prompt = skill_aware_prompt(
        agent="question",
        phase="followup",
        action="generate_followup",
        base_prompt=prompt,
        state=asdict(state),
    )

    try:
        followup_content = await invoke_llm(...)
    except Exception:
        followup_content = "能详细说说吗？"

    return {...}


def create_question_agent_graph() -> StateGraph:
    graph = StateGraph(InterviewState)
    graph.add_node("generate_warmup", generate_warmup)
    graph.add_node("generate_initial", generate_initial)
    graph.add_node("generate_followup", generate_followup)
    graph.set_entry_point("generate_warmup")
    graph.add_edge("generate_warmup", "__end__")
    return graph.compile()
```

## 集成检查清单

在将 Skill 系统集成到 Agent 时，确保：

- [ ] 导入了 `skill_aware_prompt` 或 `SkillContext`
- [ ] 使用 `asdict(state)` 将 InterviewState 转为 dict
- [ ] 传入正确的 `agent` 名称
- [ ] 传入正确的 `phase`（warmup/initial/followup）
- [ ] 传入正确的 `action`（generate_question/evaluate/feedback）
- [ ] Skills 已创建并配置了正确的 triggers
