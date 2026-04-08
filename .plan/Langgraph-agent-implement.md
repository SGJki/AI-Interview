# AI-Interview LangGraph Agent LLM 集成实现规划

**Problem solved**: 为 AI-Interview 项目实现 LangGraph Agent 的 LLM 集成，使 ResumeAgent、KnowledgeAgent、QuestionAgent、EvaluateAgent、FeedBackAgent、ReviewAgent 能够真正调用 ChatGLM 大模型，实现智能面试流程。

**基于**: [langgraph-agent-orchestration.md](./langgraph-agent-orchestration.md)

---

## 一、架构设计总览

### 1.1 核心设计原则

1. **LLM 服务集中化**: 所有 LLM 调用通过 `InterviewLLMService` 统一管理
2. **Prompt 模板化**: 每个 Agent 使用预定义的 Prompt 模板
3. **状态驱动**: Agent 通过读写 `InterviewState` 实现状态共享
4. **流式输出**: 支持流式响应以提升用户体验
5. **容错机制**: 多级重试、降级策略

### 1.2 LLM 集成架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LangGraph State                              │
│                    (InterviewState / InterviewContext)               │
└─────────────────────────────────────────────────────────────────────┘
        ▲                    │                    ▲                    │
        │                    │                    │                    │
┌───────┴───────┐   ┌───────┴───────┐   ┌───────┴───────┐   ┌───────┴───────┐
│  ResumeAgent  │   │KnowledgeAgent │   │ QuestionAgent│   │  FeedBackAgent │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
                                                       │                   
                                              ┌───────┴───────┐           
                                              │ EvaluateAgent │           
                                              └───────┬───────┘           
                                                      │                   
                                              ┌───────┴───────┐           
                                              │  ReviewAgent  │           
                                              └───────────────┘           
```

### 1.3 现有代码分析

**已有组件**:
- `src/llm/client.py`: 包含 `invoke_llm`, `invoke_llm_stream`, `invoke_llm_with_history`
- `src/llm/prompts.py`: 包含完整的 Prompt 模板（QUESTION_GENERATION_PROMPT, ANSWER_EVALUATION_PROMPT 等）
- `src/services/llm_service.py`: 包含 `InterviewLLMService` 类
- `src/agent/state.py`: 定义 `InterviewState`, `InterviewContext`

**需要实现的 Agent** (当前为占位符):
- `src/agent/resume_agent.py`: ResumeAgent
- `src/agent/knowledge_agent.py`: KnowledgeAgent
- `src/agent/question_agent.py`: QuestionAgent
- `src/agent/evaluate_agent.py`: EvaluateAgent
- `src/agent/feedback_agent.py`: FeedBackAgent
- `src/agent/review_agent.py`: ReviewAgent (第6个Agent，负责审查其他Agent的输出)

---

## 二、各 Agent LLM 集成详细设计

### 2.1 ResumeAgent LLM 集成

#### 2.1.1 职责
- 解析新简历文本，提取结构化信息
- 获取已有简历
- 存储简历到数据库

#### 2.1.2 Prompt 模板

**RESUME_EXTRACTION_PROMPT** (已在 `src/llm/prompts.py`):
```
Role: 简历信息架构师
- 解析 {resume_content} 为 JSON 格式
- 输出: skills, projects, experience
```

#### 2.1.3 工具调用设计

| 工具 | 用途 | LLM 调用 |
|------|------|----------|
| `parse_resume` | 解析简历文本 | `invoke_llm(resume_extraction_prompt)` |
| `fetch_old_resume` | 读取已有简历 | 数据库查询，无需 LLM |

#### 2.1.4 状态读写

**读取**:
- `state.resume_id`: 简历 ID

**写入**:
- `state.resume_context`: 简历原文
- `state.responsibilities`: 职责元组
- `InterviewContext.resume_context`: 解析后简历

#### 2.1.5 实现代码

```python
# src/agent/resume_agent.py

from src.services.llm_service import InterviewLLMService
from src.llm.prompts import RESUME_EXTRACTION_PROMPT
from src.agent.state import InterviewState

# 全局 LLM 服务实例
_llm_service: InterviewLLMService | None = None

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """
    解析新简历，提取结构和职责信息
    
    Args:
        state: InterviewState
        resume_text: 简历文本
        
    Returns:
        更新状态字典
    """
    llm_service = get_llm_service()
    
    try:
        # 调用 LLM 解析简历
        response = await llm_service.extract_resume_info(resume_text)
        
        responsibilities = []
        for project in response.get("projects", []):
            responsibilities.extend(project.get("responsibilities", []))
        
        return {
            "resume_context": resume_text,
            "responsibilities": tuple(responsibilities),
            "resume_parsed": response,
        }
    except Exception as e:
        # LLM 调用失败，使用简单解析
        return {
            "resume_context": resume_text,
            "responsibilities": tuple(["简历解析失败，使用默认职责"]),
            "resume_parsed": {"skills": [], "projects": [], "experience": []},
        }

async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """
    获取已有简历
    
    Args:
        state: InterviewState
        resume_id: 简历 ID
        
    Returns:
        更新状态字典
    """
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session
    
    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        
        if resume:
            return {
                "resume_context": resume.content,
                "resume_id": resume_id,
            }
        return {
            "resume_context": "",
            "resume_id": resume_id,
        }
```

#### 2.1.6 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| LLM 超时 | 使用 fallback prompt，提取基本信息 |
| LLM 解析失败 | 返回空 responsibilities |
| JSON 解析失败 | 尝试修复或使用默认结构 |

---

### 2.2 KnowledgeAgent LLM 集成

#### 2.2.1 职责
- 职责列表随机化
- 存储到向量数据库
- 获取当前职责
- **查找标准答案（核心功能）**
- **将标准答案传给 EvaluateAgent**

#### 2.2.2 状态读写

**读取**:
- `state.responsibilities`: 职责元组
- `state.current_responsibility_index`: 当前职责索引
- `state.series_responsibility_map`: 系列职责映射
- `state.mastered_questions`: 已掌握的问题（用于查找标准答案）

**写入**:
- `state.responsibilities`: 随机后的职责
- `state.series_responsibility_map`: 职责分配映射
- `state.current_responsibility_index`: 更新索引
- `state.current_standard_answer`: **标准答案（传给 EvaluateAgent）**

#### 2.2.3 标准答案查找流程

```
QuestionAgent 生成问题
       ↓
KnowledgeAgent.find_standard_answer
       ↓
┌─ 从 mastered_questions 查找（dev >= 0.8 的问答对）
│      ↓
│  语义相似度 + 关键词检验
│      ↓
│  ┌─ 找到候选 ──→ ReviewAgent 审查 ──┐
│  │                                    │
│  │                           通过 ──→ 标准答案传给 EvaluateAgent
│  │                           失败 ──→ 重试一次（再审查）
│  │                                    │
│  │                                    └──→ 失败 ──→ 告知"无标准答案"
│  └─ 未找到 ──→ 直接告知"无标准答案"
```

#### 2.2.4 与 EvaluateAgent 的交互

```
KnowledgeAgent
    │
    └──► 设置 state.current_standard_answer
              │
              ↓
         EvaluateAgent
              │ 读取 state.current_standard_answer
              │ 决定调用 evaluate_with_standard 或 evaluate_without_standard
              ↓
         ReviewAgent 审查评估结果

#### 2.2.3 实现代码

```python
# src/agent/knowledge_agent.py

import random
from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState

async def shuffle_responsibilities(state: InterviewState, responsibilities: tuple) -> dict:
    """
    随机打乱职责列表，确保面试问题顺序随机
    
    Args:
        state: InterviewState
        responsibilities: 原始职责元组
        
    Returns:
        更新状态字典，包含随机后的 responsibilities 和 series_responsibility_map
    """
    if not responsibilities:
        return {"responsibilities": (), "series_responsibility_map": {}}
    
    # 复制并打乱
    shuffled = list(responsibilities)
    random.shuffle(shuffled)
    
    # 创建系列到职责的映射
    series_map = {}
    for idx, resp in enumerate(shuffled):
        series_num = (idx % state.max_series) + 1 if hasattr(state, 'max_series') else idx + 1
        if series_num not in series_map:
            series_map[series_num] = []
        series_map[series_num].append(resp)
    
    return {
        "responsibilities": tuple(shuffled),
        "series_responsibility_map": series_map,
        "current_responsibility_index": 0,
    }

async def store_to_vector_db(state: InterviewState, responsibilities: tuple) -> dict:
    """
    将职责存储到向量数据库
    
    Args:
        state: InterviewState
        responsibilities: 职责元组
        
    Returns:
        存储结果
    """
    from src.db.vector_store import VectorStore
    from src.services.embedding_service import compute_embedding
    
    vector_store = VectorStore()
    
    try:
        # 为每个职责计算 embedding 并存储
        for idx, responsibility in enumerate(responsibilities):
            embedding = await compute_embedding(responsibility)
            await vector_store.add(
                text=responsibility,
                embedding=embedding,
                metadata={
                    "index": idx,
                    "session_id": state.session_id,
                }
            )
        return {"stored": True, "count": len(responsibilities)}
    except Exception as e:
        return {"stored": False, "error": str(e)}

async def fetch_responsibility(state: InterviewState, session_id: str) -> dict:
    """
    获取当前系列对应的职责
    
    Args:
        state: InterviewState
        session_id: 会话 ID
        
    Returns:
        当前职责
    """
    current_series = state.current_series
    current_idx = state.current_responsibility_index
    
    # 从 series_responsibility_map 获取当前系列的职责
    if state.series_responsibility_map and current_series in state.series_responsibility_map:
        series_responsibilities = state.series_responsibility_map[current_series]
        if current_idx < len(series_responsibilities):
            responsibility = series_responsibilities[current_idx]
            return {
                "current_responsibility": responsibility,
                "current_responsibility_index": current_idx,
            }
    
    # Fallback: 从 responsibilities 获取
    if state.responsibilities and current_idx < len(state.responsibilities):
        responsibility = state.responsibilities[current_idx]
        return {
            "current_responsibility": responsibility,
            "current_responsibility_index": current_idx,
        }
    
    return {"current_responsibility": "", "current_responsibility_index": current_idx}

async def find_standard_answer(state: InterviewState, question: str) -> dict:
    """
    在向量数据库中查找标准答案
    
    Args:
        state: InterviewState
        question: 问题内容
        
    Returns:
        标准答案（如果有）
    """
    from src.db.vector_store import VectorStore
    from src.services.embedding_service import compute_similarity
    
    vector_store = VectorStore()
    
    try:
        # 计算问题的 embedding
        question_embedding = await compute_similarity(question, "")  # 只获取 embedding
        
        # 检索最相似的职责
        results = await vector_store.search(
            query_embedding=question_embedding,
            top_k=1,
            filter={"session_id": state.session_id}
        )
        
        if results and results[0].get("score", 0) > 0.8:
            return {
                "standard_answer": results[0].get("text"),
                "similarity_score": results[0].get("score"),
            }
        return {"standard_answer": None, "similarity_score": 0}
    except Exception:
        return {"standard_answer": None, "similarity_score": 0}

def create_knowledge_agent_graph() -> StateGraph:
    """
    创建 KnowledgeAgent 子图
    """
    graph = StateGraph(InterviewState)
    graph.add_node("shuffle_responsibilities", shuffle_responsibilities)
    graph.add_node("store_to_vector_db", store_to_vector_db)
    graph.add_node("fetch_responsibility", fetch_responsibility)
    graph.add_node("find_standard_answer", find_standard_answer)
    graph.set_entry_point("shuffle_responsibilities")
    graph.add_edge("shuffle_responsibilities", "store_to_vector_db")
    graph.add_edge("store_to_vector_db", "__end__")
    return graph.compile()

knowledge_agent_graph = create_knowledge_agent_graph()
```

#### 2.2.4 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| 向量存储失败 | 继续使用内存中的 responsibilities |
| 检索失败 | 返回 None，评估时使用无标准答案模式 |
| 索引越界 | 返回空职责，结束面试 |

---

### 2.3 QuestionAgent LLM 集成

#### 2.3.1 职责
- 生成预热问题
- 生成初始问题
- 生成追问
- 问题去重检查

#### 2.3.2 Prompt 模板

**QUESTION_GENERATION_PROMPT** (已在 `src/llm/prompts.py`):
```
Role: AI面试官
- 基于 resume_info, responsibility_context 生成面试问题
- 问题 ≤ 50 字符
```

**FOLLOWUP_QUESTION_PROMPT** (已在 `src/llm/prompts.py`):
```
Role: 专业AI面试官
- 基于原始问题、用户回答、对话历史生成追问
- 追问 ≤ 40 字符
```

#### 2.3.3 状态读写

**读取**:
- `state.resume_context`: 简历上下文
- `state.current_responsibility`: 当前职责
- `state.knowledge_context`: 知识库上下文
- `state.asked_logical_questions`: 已问问题集合
- `state.followup_depth`: 追问深度

**写入**:
- `state.current_question`: 当前问题
- `state.current_question_id`: 问题 ID
- `state.followup_depth`: 更新追问深度
- `state.followup_chain`: 添加到追问链

#### 2.3.4 实现代码

```python
# src/agent/question_agent.py

import uuid
from typing import Literal
from langgraph.graph import StateGraph, END
from src.agent.state import InterviewState, Question, QuestionType
from src.services.llm_service import InterviewLLMService
from src.llm.prompts import QUESTION_GENERATION_PROMPT, FOLLOWUP_QUESTION_PROMPT

# 全局 LLM 服务实例
_llm_service: InterviewLLMService | None = None

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

def generate_question_id() -> str:
    """生成唯一问题 ID"""
    return f"q_{uuid.uuid4().hex[:8]}"

async def generate_warmup(state: InterviewState, resume_context: str = "") -> dict:
    """
    生成预热问题
    
    预热问题是通用问题，让候选人放松心态
    """
    llm_service = get_llm_service()
    
    warmup_prompt = """请生成一个简短的预热问题，用于让候选人放松。
要求：
1. 通用、易于回答，不涉及技术细节
2. 长度控制在30字以内
3. 例如："请简单介绍一下你自己" 或 "你为什么对这个岗位感兴趣？"
"""
    
    try:
        question_content = await llm_service.generate_question(
            series_num=0,
            question_num=0,
            interview_mode="warmup",
            knowledge_context="预热阶段",
        )
        question_content = question_content.strip()
        
        # Fallback
        if not question_content:
            question_content = "请简单介绍一下你自己"
            
    except Exception:
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

async def generate_initial(
    state: InterviewState,
    resume_context: str,
    responsibility: str
) -> dict:
    """
    生成初始问题
    
    基于简历和职责生成针对性的初始问题
    """
    llm_service = get_llm_service()
    
    try:
        question_content = await llm_service.generate_question(
            series_num=state.current_series,
            question_num=1,
            interview_mode=state.interview_mode.value if hasattr(state.interview_mode, 'value') else str(state.interview_mode),
            knowledge_context=state.knowledge_context or "",
            responsibility_context=responsibility,
        )
        question_content = question_content.strip()
        
        # 确保问题不为空
        if not question_content:
            question_content = f"请谈谈你对{responsibility}的经验"
            
    except Exception:
        question_content = f"请谈谈你对{responsibility}的经验"
    
    question_id = generate_question_id()
    
    return {
        "current_question": Question(
            content=question_content,
            question_type=QuestionType.INITIAL,
            series=state.current_series,
            number=1,
            parent_question_id=None,
        ),
        "current_question_id": question_id,
        "followup_depth": 0,
        "followup_chain": [question_id],
    }

async def generate_followup(
    state: InterviewState,
    qa_history: list,
    evaluation: dict
) -> dict:
    """
    生成追问
    
    基于原始问题和用户回答生成深入追问
    """
    llm_service = get_llm_service()
    
    if not state.current_question:
        return {"current_question": None, "current_question_id": None}
    
    # 构建对话历史字符串
    history_str = ""
    for item in qa_history[-3:]:  # 最近3轮对话
        history_str += f"Q: {item.get('question', '')}\n"
        history_str += f"A: {item.get('answer', '')}\n\n"
    
    # 提取追问方向
    followup_direction = ""
    if evaluation and not evaluation.get("is_correct", True):
        followup_direction = "深入技术细节，说明具体实践"
    
    try:
        followup_content = await llm_service.generate_followup_question(
            original_question=state.current_question,
            user_answer=qa_history[-1].get("answer", "") if qa_history else "",
            followup_direction=followup_direction,
            conversation_history=history_str,
        )
        followup_content = followup_content.strip()
        
        if not followup_content:
            followup_content = "能详细说说吗？"
            
    except Exception:
        followup_content = "能详细说说吗？"
    
    new_question_id = generate_question_id()
    new_depth = state.followup_depth + 1
    
    return {
        "current_question": Question(
            content=followup_content,
            question_type=QuestionType.FOLLOWUP,
            series=state.current_series,
            number=state.current_question.number + 1 if state.current_question else 1,
            parent_question_id=state.current_question_id,
        ),
        "current_question_id": new_question_id,
        "followup_depth": new_depth,
        "followup_chain": state.followup_chain + [new_question_id],
    }

async def deduplicate_check(state: InterviewState, question_id: str) -> dict:
    """
    检查问题是否重复（基于逻辑）
    
    使用 ReviewVoter 进行3实例投票
    """
    from src.agent.base import create_review_voters
    
    if not state.current_question:
        return {"deduplicate_passed": True, "deduplicate_failures": []}
    
    voters = [
        # Voter 1: 检查问题是否在已问列表中
        lambda q: q.get("question_id") not in state.asked_logical_questions,
        # Voter 2: 检查与上一个问题的语义相似度
        lambda q: True,  # TODO: 实现语义相似度检查
        # Voter 3: 检查追问深度是否超限
        lambda q: state.followup_depth < state.max_followup_depth,
    ]
    
    voter = create_review_voters(voters)
    passed, failures = await voter.vote({"question_id": question_id})
    
    return {"deduplicate_passed": passed, "deduplicate_failures": failures}

def should_continue_followup(state: InterviewState) -> Literal["generate_followup", END]:
    """
    判断是否继续追问
    """
    from src.config import config
    
    # 获取评估结果中的偏差分数
    dev = 0
    if state.current_question_id and hasattr(state, 'evaluation_results'):
        eval_result = state.evaluation_results.get(state.current_question_id, {})
        dev = eval_result.get("deviation_score", 0)
    
    depth = state.followup_depth
    max_depth = state.max_followup_depth
    threshold = config.deviation_threshold if hasattr(config, 'deviation_threshold') else 0.8
    
    # 退出条件: 偏差足够小（dev >= threshold）且深度足够
    if dev >= threshold and depth >= max_depth:
        return END
    
    # 继续追问: 偏差不够小或深度不够
    return "generate_followup"

def create_question_agent_graph() -> StateGraph:
    """
    创建 QuestionAgent 子图
    """
    graph = StateGraph(InterviewState)
    graph.add_node("generate_warmup", generate_warmup)
    graph.add_node("generate_initial", generate_initial)
    graph.add_node("generate_followup", generate_followup)
    graph.add_node("deduplicate_check", deduplicate_check)
    graph.set_entry_point("generate_warmup")
    graph.add_edge("generate_warmup", "__end__")
    return graph.compile()

question_agent_graph = create_question_agent_graph()
```

#### 2.3.5 流式输出支持

```python
async def generate_initial_stream(
    state: InterviewState,
    resume_context: str,
    responsibility: str
):
    """
    生成初始问题（流式）
    
    Yields:
        每个 token
    """
    llm_service = get_llm_service()
    
    prompt = QUESTION_GENERATION_PROMPT.format(
        resume_info=resume_context,
        series_num=state.current_series,
        question_num=1,
        interview_mode=state.interview_mode.value if hasattr(state.interview_mode, 'value') else "free",
        topic_area="技术能力",
        knowledge_context=state.knowledge_context or "无相关上下文",
        responsibility_context=responsibility,
    )
    
    question_id = generate_question_id()
    
    try:
        async for token in llm_service.generate_question_stream(
            series_num=state.current_series,
            question_num=1,
            interview_mode="free",
            responsibility_context=responsibility,
        ):
            yield token
            
        # 流式结束后返回完整状态更新
        yield {
            "current_question": Question(
                content="",  # 流式过程中逐步更新
                question_type=QuestionType.INITIAL,
                series=state.current_series,
                number=1,
                parent_question_id=None,
            ),
            "current_question_id": question_id,
            "followup_depth": 0,
        }
    except Exception as e:
        yield f"请谈谈你对{responsibility}的经验"
```

#### 2.3.6 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| LLM 超时 | 使用 fallback 问题 |
| 空响应 | 使用默认问题模板 |
| 追问超限 | 强制退出追问循环 |
| 去重失败 | 保守处理，认为重复 |

---

### 2.4 EvaluateAgent LLM 集成

#### 2.4.1 职责
- 使用标准答案评估（标准答案由 KnowledgeAgent 传入）
- 无标准答案评估
- 计算偏差分数
- **输出给 ReviewAgent 进行审查**

#### 2.4.2 Prompt 模板

**ANSWER_EVALUATION_PROMPT** (已在 `src/llm/prompts.py`):
```
Role: AI面试评估专家
- 基于 question, user_answer, standard_answer 评估
- 输出 JSON: deviation_score, is_correct, key_points, suggestions
```

#### 2.4.3 状态读写

**读取**:
- `state.current_question`: 当前问题
- `state.answers`: 回答记录字典
- `state.series_history`: 系列历史
- `state.current_standard_answer`: **标准答案（由 KnowledgeAgent 设置）**

**写入**:
- `state.answers`: 添加新回答
- `state.evaluation_results`: 评估结果
- `state.error_count`: 更新错误计数

#### 2.4.4 流程

```
KnowledgeAgent.find_standard_answer → 标准答案存入 state.current_standard_answer
                                    ↓
                    EvaluateAgent.evaluate_with_standard / evaluate_without_standard
                                    ↓
                                    ReviewAgent.review_evaluation
                                    ↓
                         ┌─ 通过 ──→ 输出给用户
                         │
                         └─ 不通过 ──→ 反馈环

#### 2.4.4 实现代码

```python
# src/agent/evaluate_agent.py

from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState, Answer
from src.services.llm_service import InterviewLLMService

# 全局 LLM 服务实例
_llm_service: InterviewLLMService | None = None

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

async def evaluate_with_standard(
    state: InterviewState,
    question: str,
    user_answer: str,
    standard_answer: str
) -> dict:
    """
    使用标准答案评估用户回答
    
    Args:
        state: InterviewState
        question: 问题内容
        user_answer: 用户回答
        standard_answer: 标准答案
        
    Returns:
        评估结果字典
    """
    llm_service = get_llm_service()
    
    try:
        # 调用 LLM 评估
        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=standard_answer,
        )
        
        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
        
    except Exception as e:
        # Fallback: 使用简单相似度
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": [f"评估出错: {str(e)}"],
            "suggestions": ["请详细描述你的经验"],
        }
    
    # 记录回答
    question_id = state.current_question_id or f"q_{hash(question) % 10000}"
    
    new_answer = Answer(
        question_id=question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )
    
    # 更新错误计数
    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0  # 答对则重置
    
    # 初始化 evaluation_results 如果不存在
    evaluation_results = getattr(state, 'evaluation_results', {})
    evaluation_results[question_id] = result
    
    return {
        "answers": {**state.answers, question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
    }

async def evaluate_without_standard(
    state: InterviewState,
    question: str,
    user_answer: str
) -> dict:
    """
    无标准答案时评估用户回答
    
    Args:
        state: InterviewState
        question: 问题内容
        user_answer: 用户回答
        
    Returns:
        评估结果字典
    """
    llm_service = get_llm_service()
    
    try:
        # 调用 LLM 评估（无标准答案）
        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=None,  # 无标准答案
        )
        
        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
        
    except Exception:
        # Fallback
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": ["暂时无法评估"],
            "suggestions": ["请详细描述你的经验"],
        }
    
    # 记录回答
    question_id = state.current_question_id or f"q_{hash(question) % 10000}"
    
    new_answer = Answer(
        question_id=question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )
    
    # 更新错误计数
    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0
    
    # 初始化 evaluation_results 如果不存在
    evaluation_results = getattr(state, 'evaluation_results', {})
    evaluation_results[question_id] = result
    
    return {
        "answers": {**state.answers, question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
    }

def create_evaluate_agent_graph() -> StateGraph:
    """
    创建 EvaluateAgent 子图
    """
    graph = StateGraph(InterviewState)
    graph.add_node("evaluate_with_standard", evaluate_with_standard)
    graph.add_node("evaluate_without_standard", evaluate_without_standard)
    graph.set_entry_point("evaluate_with_standard")
    graph.add_edge("evaluate_with_standard", "__end__")
    return graph.compile()

evaluate_agent_graph = create_evaluate_agent_graph()
```

#### 2.4.5 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| LLM 超时 | 使用 embedding 相似度作为 fallback |
| JSON 解析失败 | 使用相似度分数 |
| API 错误 | 返回默认分数 0.5 |

---

### 2.5 FeedBackAgent LLM 集成

#### 2.5.1 职责
- 生成纠正反馈（低偏差）
- 生成引导反馈（中低偏差）
- 生成评论反馈（高偏差）
- 生成 fallback 反馈

#### 2.5.2 Prompt 模板

**FEEDBACK_GENERATION_PROMPT** (已在 `src/llm/prompts.py`):
```
Role: AI面试反馈生成专家
- 基于 question, user_answer, deviation_score 生成反馈
- 输出: 【思考过程】...【回答】... (反馈 ≤ 100 字)
```

#### 2.5.3 状态读写

**读取**:
- `state.current_question`: 当前问题
- `state.answers`: 回答记录
- `state.feedback_mode`: 反馈模式

**写入**:
- `state.feedbacks`: 反馈记录字典
- `state.pending_feedbacks`: 待发送反馈队列

#### 2.5.4 实现代码

```python
# src/agent/feedback_agent.py

from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState, Feedback, FeedbackType
from src.services.llm_service import InterviewLLMService

# 全局 LLM 服务实例
_llm_service: InterviewLLMService | None = None

# 偏差分数阈值
DEVIATION_CORRECTION_THRESHOLD = 0.3
DEVIATION_GUIDANCE_THRESHOLD = 0.6

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

def _determine_feedback_type(deviation_score: float) -> FeedbackType:
    """
    根据偏差分数确定反馈类型
    """
    if deviation_score < DEVIATION_CORRECTION_THRESHOLD:
        return FeedbackType.CORRECTION
    elif deviation_score < DEVIATION_GUIDANCE_THRESHOLD:
        return FeedbackType.GUIDANCE
    else:
        return FeedbackType.COMMENT

async def generate_correction(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """
    生成纠正反馈
    
    当偏差分数 < 0.3 时，需要直接给出正确答案
    """
    llm_service = get_llm_service()
    
    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", False)
    
    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
        )
        feedback_content = feedback.content
    except Exception:
        feedback_content = "你对这个问题的理解有偏差，让我来纠正一下..."
    
    question_id = state.current_question_id or ""
    
    new_feedback = Feedback(
        question_id=question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance="建议回顾相关技术原理",
        feedback_type=FeedbackType.CORRECTION,
    )
    
    # 如果是 RECORDED 模式，添加到 pending_feedbacks
    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    if state.feedback_mode.value == "recorded" if hasattr(state.feedback_mode, 'value') else state.feedback_mode == "recorded":
        pending_feedbacks.append({
            "question_id": question_id,
            "feedback": new_feedback,
            "is_correct": is_correct,
        })
    
    return {
        "feedbacks": {**state.feedbacks, question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }

async def generate_guidance(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """
    生成引导反馈
    
    当偏差分数在 0.3-0.6 之间时，通过提问引导候选人思考
    """
    llm_service = get_llm_service()
    
    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", True)
    
    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
        )
        feedback_content = feedback.content
    except Exception:
        feedback_content = "你的回答方向正确，但可以更深入一些..."
    
    question_id = state.current_question_id or ""
    
    new_feedback = Feedback(
        question_id=question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance="请尝试从项目实践角度更详细地说明",
        feedback_type=FeedbackType.GUIDANCE,
    )
    
    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    if state.feedback_mode.value == "recorded" if hasattr(state.feedback_mode, 'value') else state.feedback_mode == "recorded":
        pending_feedbacks.append({
            "question_id": question_id,
            "feedback": new_feedback,
            "is_correct": is_correct,
        })
    
    return {
        "feedbacks": {**state.feedbacks, question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }

async def generate_comment(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """
    生成评论反馈
    
    当偏差分数 >= 0.6 时，给予正面鼓励
    """
    llm_service = get_llm_service()
    
    deviation_score = evaluation.get("deviation_score", 0)
    is_correct = evaluation.get("is_correct", True)
    
    try:
        feedback = await llm_service.generate_feedback(
            question=question,
            user_answer=user_answer,
            deviation_score=deviation_score,
            is_correct=is_correct,
        )
        feedback_content = feedback.content
    except Exception:
        feedback_content = "回答得很好！继续深入。"
    
    question_id = state.current_question_id or ""
    
    new_feedback = Feedback(
        question_id=question_id,
        content=feedback_content,
        is_correct=is_correct,
        guidance=None,
        feedback_type=FeedbackType.COMMENT,
    )
    
    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
    if state.feedback_mode.value == "recorded" if hasattr(state.feedback_mode, 'value') else state.feedback_mode == "recorded":
        pending_feedbacks.append({
            "question_id": question_id,
            "feedback": new_feedback,
            "is_correct": is_correct,
        })
    
    return {
        "feedbacks": {**state.feedbacks, question_id: new_feedback},
        "pending_feedbacks": pending_feedbacks,
        "last_feedback": new_feedback,
    }

async def generate_fallback_feedback(state: InterviewState) -> dict:
    """
    生成 fallback 反馈
    
    当 LLM 调用失败时使用
    """
    fallback_content = "感谢您的回答，我们继续下一个问题。"
    
    question_id = state.current_question_id or ""
    
    new_feedback = Feedback(
        question_id=question_id,
        content=fallback_content,
        is_correct=True,
        guidance=None,
        feedback_type=FeedbackType.COMMENT,
    )
    
    return {
        "feedbacks": {**state.feedbacks, question_id: new_feedback},
        "last_feedback": new_feedback,
    }

async def generate_feedback_by_type(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """
    根据评估结果自动选择反馈类型并生成反馈
    """
    deviation_score = evaluation.get("deviation_score", 0)
    
    if deviation_score < DEVIATION_CORRECTION_THRESHOLD:
        return await generate_correction(state, question, user_answer, evaluation)
    elif deviation_score < DEVIATION_GUIDANCE_THRESHOLD:
        return await generate_guidance(state, question, user_answer, evaluation)
    else:
        return await generate_comment(state, question, user_answer, evaluation)

def create_feedback_agent_graph() -> StateGraph:
    """
    创建 FeedBackAgent 子图
    """
    graph = StateGraph(InterviewState)
    graph.add_node("generate_correction", generate_correction)
    graph.add_node("generate_guidance", generate_guidance)
    graph.add_node("generate_comment", generate_comment)
    graph.add_node("generate_fallback_feedback", generate_fallback_feedback)
    graph.add_node("generate_feedback_by_type", generate_feedback_by_type)
    graph.set_entry_point("generate_feedback_by_type")
    graph.add_edge("generate_feedback_by_type", "__end__")
    return graph.compile()

feedback_agent_graph = create_feedback_agent_graph()
```

#### 2.5.5 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| LLM 超时 | 使用模板生成反馈 |
| 空响应 | 使用默认鼓励语 |
| API 错误 | 使用 fallback 反馈 |

---

### 2.6 ReviewAgent LLM 集成

#### 2.6.1 职责
- 审查其他 Agent 的输出（3-instance 投票机制）
- 评估通过条件：至少 2 个实例通过
- 失败时触发反馈环

#### 2.6.2 审查流程

```
EvaluateAgent 输出
       │
       ▼
ReviewAgent.review_evaluation
       │
       ├──► Voter 1: 评估是否基于 Q+A
       ├──► Voter 2: 评估是否合理（deviation_score 与回答质量匹配）
       └──► Voter 3: 标准答案契合度检查（仅当有标准答案时）
       
       │
       ├──► [通过 (>=2 pass)] ──► 输出给用户
       │
       └──► [不通过] ──► 反馈环
                     │
                     ├──► EvaluateAgent 重新评估
                     └──► KnowledgeAgent 重新查找标准答案
```

#### 2.6.3 审查标准

| 审核项 | 标准 |
|--------|------|
| 评估基于 Q+A | 评估内容与问题和回答相关 |
| 评估合理 | deviation_score 与回答质量匹配 |
| 标准答案契合 | 仅当有标准答案时：标准答案与问题契合 |

#### 2.6.4 实现代码

```python
# src/agent/review_agent.py

from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState
from src.agent.base import ReviewVoter, create_review_voters

# 全局 LLM 服务实例
_llm_service: InterviewLLMService | None = None

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

async def review_evaluation(
    state: InterviewState,
    evaluation_result: dict,
    standard_answer: str | None
) -> dict:
    """
    审查 EvaluateAgent 的评估结果
    
    Args:
        state: InterviewState
        evaluation_result: EvaluateAgent 返回的评估结果
        standard_answer: 标准答案（如果有）
        
    Returns:
        审查结果: {passed: bool, failures: list[str], retry_target: str}
    """
    question = state.current_question.content if state.current_question else ""
    user_answer = state.answers.get(state.current_question_id, Answer("","")).content if state.current_question_id else ""
    
    # 创建 3 个投票器
    voters = [
        # Voter 1: 评估是否基于 Q+A
        lambda e: _check_evaluation_based_on_qa(
            question, user_answer, evaluation_result
        ),
        # Voter 2: 评估是否合理
        lambda e: _check_evaluation_reasonableness(
            question, user_answer, evaluation_result
        ),
        # Voter 3: 标准答案契合度（仅当有标准答案时）
        lambda e: _check_standard_answer_fit(
            question, evaluation_result, standard_answer
        ) if standard_answer else True,
    ]
    
    voter = create_review_voters(voters)
    passed, failures = await voter.vote(evaluation_result)
    
    # 确定反馈环目标
    retry_target = "evaluate"  # 默认重试 EvaluateAgent
    if "standard_answer" in str(failures).lower():
        retry_target = "knowledge"  # 标准答案问题，回调到 KnowledgeAgent
    
    return {
        "review_passed": passed,
        "review_failures": failures,
        "retry_target": retry_target,
    }

def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否基于问答内容"""
    # TODO: 实现 LLM 调用判断评估是否与 Q+A 相关
    return True

def _check_evaluation_reasonableness(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否合理"""
    dev = evaluation.get("deviation_score", 0.5)
    # 简单合理性检查：高分应该表示回答质量好
    # TODO: 实现更复杂的 LLM 判断
    return 0 <= dev <= 1

def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str) -> bool:
    """检查标准答案与问题是否契合"""
    # TODO: 实现语义相似度检查
    return True

def create_review_agent_graph() -> StateGraph:
    """
    创建 ReviewAgent 子图
    """
    graph = StateGraph(InterviewState)
    graph.add_node("review_evaluation", review_evaluation)
    graph.set_entry_point("review_evaluation")
    graph.add_edge("review_evaluation", "__end__")
    return graph.compile()

review_agent_graph = create_review_agent_graph()
```

#### 2.6.5 反馈环

| 失败原因 | 反馈目标 |
|----------|----------|
| 评估不合理 | EvaluateAgent 重新评估 |
| 标准答案不契合 | KnowledgeAgent 重新查找标准答案 |

---

## 三、InterviewLLMService 增强

### 3.1 当前实现分析

现有 `src/services/llm_service.py` 中的 `InterviewLLMService` 已经实现了:
- `generate_question()`
- `generate_question_stream()`
- `evaluate_answer()`
- `generate_feedback()`
- `generate_followup_question()`
- `generate_followup_question_stream()`

### 3.2 需要添加的方法

```python
# src/services/llm_service.py 新增方法

async def extract_resume_info(self, resume_content: str) -> dict:
    """
    提取简历信息
    
    Args:
        resume_content: 简历文本
        
    Returns:
        解析后的简历结构: {skills: [], projects: [], experience: []}
    """
    from src.llm.prompts import RESUME_EXTRACTION_PROMPT
    
    prompt = RESUME_EXTRACTION_PROMPT.format(
        resume_content=resume_content,
    )
    
    try:
        result = await invoke_llm(
            system_prompt="你是一个专业的简历解析专家。",
            user_prompt=prompt,
            temperature=0.3,
        )
        
        # 解析 JSON 结果
        import json
        return json.loads(result)
    except json.JSONDecodeError:
        return {"skills": [], "projects": [], "experience": []}
    except Exception:
        return {"skills": [], "projects": [], "experience": []}
```

---

## 四、流式输出架构

### 4.1 流式输出设计

```python
# src/agent/streaming.py

from typing import AsyncGenerator
from langgraph.graph import StateGraph

async def stream_question_generation(
    agent_graph: StateGraph,
    state: InterviewState,
    node_name: str,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    流式生成问题
    
    Args:
        agent_graph: Agent 图
        state: 初始状态
        node_name: 节点名
        **kwargs: 节点参数
        
    Yields:
        每个 token
    """
    llm_service = get_llm_service()
    
    if node_name == "generate_initial":
        async for token in llm_service.generate_question_stream(**kwargs):
            yield token
    elif node_name == "generate_followup":
        async for token in llm_service.generate_followup_question_stream(**kwargs):
            yield token

class StreamingHandler:
    """
    流式响应处理器
    """
    
    def __init__(self):
        self.buffers: dict[str, list[str]] = {}
    
    async def handle_question_stream(
        self,
        session_id: str,
        generator: AsyncGenerator[str, None]
    ):
        """
        处理问题流式输出
        
        Args:
            session_id: 会话 ID
            generator: token 生成器
        """
        self.buffers[session_id] = []
        
        async for token in generator:
            self.buffers[session_id].append(token)
            # 可以在这里发送 WebSocket 消息或 SSE 事件
            yield token
        
        # 流结束后清空 buffer
        full_text = "".join(self.buffers[session_id])
        del self.buffers[session_id]
        return full_text
```

### 4.2 Redis 发布/订阅集成

```python
# src/agent/streaming.py (续)

import json
from src.db.redis_client import get_redis_client

class RedisStreamingHandler(StreamingHandler):
    """
    基于 Redis 的流式处理器
    """
    
    async def publish_token(self, session_id: str, token: str):
        """
        发布 token 到 Redis
        """
        redis = await get_redis_client()
        channel = f"stream:{session_id}"
        
        await redis.publish(channel, json.dumps({
            "type": "token",
            "content": token,
        }))
    
    async def publish_complete(self, session_id: str, full_content: str):
        """
        发布完成信号
        """
        redis = await get_redis_client()
        channel = f"stream:{session_id}"
        
        await redis.publish(channel, json.dumps({
            "type": "complete",
            "content": full_content,
        }))
```

---

## 五、错误处理与容错

### 5.1 重试策略

```python
# src/agent/retry.py

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import TypeVar, Callable

T = TypeVar('T')

def with_retry(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
):
    """
    重试装饰器工厂
    
    Args:
        max_attempts: 最大尝试次数
        base_wait: 基础等待时间（秒）
        max_wait: 最大等待时间（秒）
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, max=max_wait),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )

class RetryableAgentOperation:
    """
    可重试的 Agent 操作
    """
    
    def __init__(
        self,
        operation: Callable[..., T],
        fallback: Callable[..., T],
        max_attempts: int = 3,
    ):
        self.operation = operation
        self.fallback = fallback
        self.max_attempts = max_attempts
    
    async def execute(self, *args, **kwargs) -> T:
        """
        执行操作，带重试
        """
        last_error = None
        
        for attempt in range(self.max_attempts):
            try:
                return await self.operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_attempts - 1:
                    # 指数退避
                    import asyncio
                    wait_time = min(2 ** attempt, 10)
                    await asyncio.sleep(wait_time)
        
        # 所有重试都失败，使用 fallback
        return self.fallback(*args, **kwargs)
```

### 5.2 容错策略汇总

| 场景 | 策略 |
|------|------|
| LLM 超时 | 重试 3 次，失败后使用 fallback |
| API 限流 | 指数退避等待 |
| 网络错误 | 重试 + fallback |
| 解析失败 | 使用默认/空值 |
| 服务不可用 | 降级到模板响应 |

### 5.3 Fallback 响应模板

```python
# src/agent/fallbacks.py

FALLBACK_QUESTIONS = {
    "warmup": "请简单介绍一下你自己",
    "initial": "请谈谈你最近做的项目经验",
    "followup": "能详细说说这个项目中的具体实现吗？",
    "correction": "这个问题的答案需要结合具体场景来分析。",
    "guidance": "你的回答方向正确，能否更详细地说明一下？",
    "comment": "回答得很好！能否再深入一点？",
}

def get_fallback_question(question_type: str) -> str:
    """获取 fallback 问题"""
    return FALLBACK_QUESTIONS.get(question_type, "请谈谈你的项目经验")

def get_fallback_feedback(deviation_score: float) -> str:
    """根据偏差分数获取 fallback 反馈"""
    if deviation_score < 0.3:
        return FALLBACK_QUESTIONS["correction"]
    elif deviation_score < 0.6:
        return FALLBACK_QUESTIONS["guidance"]
    return FALLBACK_QUESTIONS["comment"]
```

---

## 六、实现阶段规划

### Phase 1: 基础设施增强

**任务**:
1. [ ] 增强 `InterviewLLMService` 添加 `extract_resume_info` 方法
2. [ ] 创建 `src/agent/retry.py` 重试模块
3. [ ] 创建 `src/agent/fallbacks.py` Fallback 响应模块
4. [ ] 创建 `src/agent/streaming.py` 流式处理模块

**交付物**:
- LLM 服务增强
- 重试和容错基础设施

**预计工时**: 4-6 小时

### Phase 2: ResumeAgent 实现

**任务**:
1. [ ] 实现 `parse_resume` 函数，集成 LLM 调用
2. [ ] 实现 `fetch_old_resume` 函数
3. [ ] 添加错误处理和重试逻辑
4. [ ] 编写单元测试

**交付物**:
- `src/agent/resume_agent.py` 完整实现
- 测试覆盖 >= 80%

**预计工时**: 3-4 小时

### Phase 3: KnowledgeAgent 实现

**任务**:
1. [ ] 实现 `shuffle_responsibilities` 函数
2. [ ] 实现 `store_to_vector_db` 函数
3. [ ] 实现 `fetch_responsibility` 函数
4. [ ] 实现 `find_standard_answer` 函数
5. [ ] 编写单元测试

**交付物**:
- `src/agent/knowledge_agent.py` 完整实现
- 测试覆盖 >= 80%

**预计工时**: 4-5 小时

### Phase 4: QuestionAgent 实现

**任务**:
1. [ ] 实现 `generate_warmup` 函数
2. [ ] 实现 `generate_initial` 函数
3. [ ] 实现 `generate_followup` 函数
4. [ ] 实现 `deduplicate_check` 函数
5. [ ] 添加流式输出支持
6. [ ] 编写单元测试

**交付物**:
- `src/agent/question_agent.py` 完整实现
- 流式输出支持
- 测试覆盖 >= 80%

**预计工时**: 6-8 小时

### Phase 5: EvaluateAgent 实现

**任务**:
1. [ ] 实现 `evaluate_with_standard` 函数
2. [ ] 实现 `evaluate_without_standard` 函数
3. [ ] 集成 embedding 相似度计算
4. [ ] 编写单元测试

**交付物**:
- `src/agent/evaluate_agent.py` 完整实现
- 测试覆盖 >= 80%

**预计工时**: 4-5 小时

### Phase 6: FeedBackAgent 实现

**任务**:
1. [ ] 实现 `generate_correction` 函数
2. [ ] 实现 `generate_guidance` 函数
3. [ ] 实现 `generate_comment` 函数
4. [ ] 实现 `generate_fallback_feedback` 函数
5. [ ] 实现 `generate_feedback_by_type` 函数
6. [ ] 编写单元测试

**交付物**:
- `src/agent/feedback_agent.py` 完整实现
- 测试覆盖 >= 80%

**预计工时**: 4-5 小时

### Phase 7: 集成测试

**任务**:
1. [ ] 编写集成测试，验证 Agent 间协作
2. [ ] 测试流式输出
3. [ ] 测试错误处理和容错
4. [ ] 性能测试

**交付物**:
- 集成测试套件
- 性能测试报告

**预计工时**: 6-8 小时

---

## 七、依赖关系

```
Phase 1 (基础设施)
    │
    ├──► Phase 2 (ResumeAgent)
    │
    ├──► Phase 3 (KnowledgeAgent)
    │
    ├──► Phase 4 (QuestionAgent)
    │         │
    │         └──► Phase 5 (EvaluateAgent) ──► Phase 6 (FeedBackAgent)
    │
    └──► Phase 7 (集成测试)
```

---

## 八、测试策略

### 8.1 单元测试

每个 Agent 节点函数需要：
- Mock LLM 调用
- 验证状态更新正确性
- 测试错误处理路径

```python
# tests/unit/test_resume_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.resume_agent import parse_resume, fetch_old_resume
from src.agent.state import InterviewState

@pytest.fixture
def mock_llm_service():
    with patch('src.agent.resume_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.extract_resume_info = AsyncMock(return_value={
            "skills": ["Python", "FastAPI"],
            "projects": [{
                "name": "Test Project",
                "responsibilities": ["开发 API", "优化性能"],
            }],
            "experience": [],
        })
        mock.return_value = service
        yield service

@pytest.mark.asyncio
async def test_parse_resume_success(mock_llm_service):
    state = InterviewState(session_id="test", resume_id="r1")
    resume_text = "我是 Python 开发者..."
    
    result = await parse_resume(state, resume_text)
    
    assert result["resume_context"] == resume_text
    assert "responsibilities" in result
    assert len(result["responsibilities"]) == 2
```

### 8.2 集成测试

```python
# tests/integration/test_agent_integration.py

import pytest
from src.agent.graph import create_interview_graph

@pytest.mark.asyncio
async def test_question_to_feedback_flow():
    """测试从问题生成到反馈的完整流程"""
    graph = create_interview_graph()
    
    # 初始化状态
    initial_state = {
        "session_id": "test_session",
        "resume_id": "test_resume",
        "resume_context": "Python 开发者...",
        "responsibilities": ("负责 API 开发",),
    }
    
    # 运行图
    result = await graph.ainvoke(initial_state)
    
    # 验证
    assert "current_question" in result
    assert "evaluation_results" in result
    assert "feedbacks" in result
```

---

## 九、风险与缓解

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| LLM API 不稳定 | 高 | 实现重试 + fallback 机制 |
| Prompt 注入攻击 | 中 | 输入清理 + Prompt 模板化 |
| 响应延迟 | 中 | 流式输出 + 异步处理 |
| 状态一致性 | 中 | 使用 Redis + checkpointer |
| 测试覆盖率不足 | 低 | TDD 流程 + 80% 覆盖率要求 |

---

## 十、待决策事项

1. **流式输出方式**: WebSocket vs SSE vs Server-Sent Events
2. **Token 预算控制**: 如何防止 LLM 生成过长响应
3. **并发限制**: 单用户多请求 vs 多用户并发
4. **缓存策略**: 是否缓存标准答案检索结果

---

**Plan created**: 2026-04-08
**Plan version**: 1.0
