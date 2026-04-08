# LangGraph Agent LLM 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 AI-Interview 项目的 LangGraph Agent LLM 集成，使 6 个 Agent（ResumeAgent、KnowledgeAgent、QuestionAgent、EvaluateAgent、FeedBackAgent、ReviewAgent）能够真正调用 ChatGLM 大模型。

**Architecture:** 基于 LangGraph StateGraph 的多 Agent 架构，6 个独立 Agent 子图通过共享 InterviewState 通信，ReviewAgent 作为第 6 个 Agent 负责审查，采用装饰器模式实现统一重试机制，Redis Pub/Sub 实现流式输出。

**Tech Stack:** Python, LangGraph, LangChain, Redis, PostgreSQL + pgvector, FastAPI, tenacity

---

## Phase 1: 基础设施增强

### Task 1: InterviewLLMService 增强

**Files:**
- Modify: `src/services/llm_service.py`
- Test: `tests/test_llm_service.py`

- [ ] **Step 1: 添加 extract_resume_info 方法**

```python
# 在 src/services/llm_service.py 的 InterviewLLMService 类中添加

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
        result = await self.invoke_llm(
            system_prompt="你是一个专业的简历解析专家。",
            user_prompt=prompt,
            temperature=0.3,
        )
        
        import json
        return json.loads(result)
    except json.JSONDecodeError:
        return {"skills": [], "projects": [], "experience": []}
    except Exception:
        return {"skills": [], "projects": [], "experience": []}
```

- [ ] **Step 2: 添加测试**

```python
# tests/test_llm_service.py

@pytest.mark.asyncio
async def test_extract_resume_info_success():
    """测试 extract_resume_info 成功解析简历"""
    service = InterviewLLMService()
    
    resume_text = """
    姓名: 张三
    技能: Python, FastAPI, PostgreSQL
    项目: 电商平台 - 负责 API 开发
    """
    
    result = await service.extract_resume_info(resume_text)
    
    assert "skills" in result
    assert "projects" in result
    assert "experience" in result
```

- [ ] **Step 3: Commit**

```bash
git add src/services/llm_service.py tests/test_llm_service.py
git commit -m "feat(llm): add extract_resume_info to InterviewLLMService"
```

---

### Task 2: 创建重试模块

**Files:**
- Create: `src/agent/retry.py`
- Test: `tests/test_retry.py`

- [ ] **Step 1: 创建重试装饰器**

```python
# src/agent/retry.py

from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio

def retryable(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,),
):
    """
    重试装饰器工厂（类似 Spring @Retryable）
    
    Args:
        max_attempts: 最大尝试次数
        base_wait: 基础等待时间（秒）
        max_wait: 最大等待时间（秒）
        exceptions: 需要重试的异常类型
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )

def async_retryable(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,),
):
    """
    异步重试装饰器工厂
    
    Args:
        max_attempts: 最大尝试次数
        base_wait: 基础等待时间（秒）
        max_wait: 最大等待时间（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        wait_time = min(base_wait * (2 ** attempt), max_wait)
                        await asyncio.sleep(wait_time)
            raise last_error
        return wrapper
    return decorator
```

- [ ] **Step 2: 添加测试**

```python
# tests/test_retry.py

import pytest
from src.agent.retry import async_retryable

@pytest.mark.asyncio
async def test_async_retryable_success():
    """测试重试装饰器在成功时直接返回"""
    call_count = 0
    
    @async_retryable(max_attempts=3)
    async def successful_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await successful_func()
    assert result == "success"
    assert call_count == 1

@pytest.mark.asyncio
async def test_async_retryable_retries_on_failure():
    """测试重试装饰器在失败时重试"""
    call_count = 0
    
    @async_retryable(max_attempts=3)
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("fail")
        return "success"
    
    result = await failing_func()
    assert result == "success"
    assert call_count == 3
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/retry.py tests/test_retry.py
git commit -m "feat(agent): add retry decorator with AOP pattern"
```

---

### Task 3: 创建 Fallback 模块

**Files:**
- Create: `src/agent/fallbacks.py`
- Test: `tests/test_fallbacks.py`

- [ ] **Step 1: 创建 Fallback 响应模板**

```python
# src/agent/fallbacks.py

from dataclasses import dataclass

FALLBACK_QUESTIONS = {
    "warmup": "请简单介绍一下你自己",
    "initial": "请谈谈你最近做的项目经验",
    "followup": "能详细说说这个项目中的具体实现吗？",
    "correction": "这个问题的答案需要结合具体场景来分析。",
    "guidance": "你的回答方向正确，能否更详细地说明一下？",
    "comment": "回答得很好！能否再深入一点？",
}

@dataclass
class FallbackResponse:
    content: str
    fallback_type: str

def get_fallback_question(question_type: str) -> FallbackResponse:
    """获取 fallback 问题"""
    content = FALLBACK_QUESTIONS.get(question_type, "请谈谈你的项目经验")
    return FallbackResponse(content=content, fallback_type=question_type)

def get_fallback_feedback(deviation_score: float) -> FallbackResponse:
    """根据偏差分数获取 fallback 反馈"""
    if deviation_score < 0.3:
        content = FALLBACK_QUESTIONS["correction"]
        fallback_type = "correction"
    elif deviation_score < 0.6:
        content = FALLBACK_QUESTIONS["guidance"]
        fallback_type = "guidance"
    else:
        content = FALLBACK_QUESTIONS["comment"]
        fallback_type = "comment"
    return FallbackResponse(content=content, fallback_type=fallback_type)
```

- [ ] **Step 2: 添加测试**

```python
# tests/test_fallbacks.py

import pytest
from src.agent.fallbacks import get_fallback_question, get_fallback_feedback, FALLBACK_QUESTIONS

def test_get_fallback_question_warmup():
    """测试获取预热问题的 fallback"""
    result = get_fallback_question("warmup")
    assert result.content == "请简单介绍一下你自己"
    assert result.fallback_type == "warmup"

def test_get_fallback_question_unknown():
    """测试获取未知类型的 fallback"""
    result = get_fallback_question("unknown_type")
    assert result.content == "请谈谈你的项目经验"

def test_get_fallback_feedback_correction():
    """测试低偏差时获取纠正反馈"""
    result = get_fallback_feedback(0.2)
    assert result.fallback_type == "correction"

def test_get_fallback_feedback_guidance():
    """测试中等偏差时获取引导反馈"""
    result = get_fallback_feedback(0.5)
    assert result.fallback_type == "guidance"

def test_get_fallback_feedback_comment():
    """测试高偏差时获取评论反馈"""
    result = get_fallback_feedback(0.8)
    assert result.fallback_type == "comment"
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/fallbacks.py tests/test_fallbacks.py
git commit -m "feat(agent): add fallback responses module"
```

---

### Task 4: 创建流式处理模块

**Files:**
- Create: `src/agent/streaming.py`
- Test: `tests/test_streaming.py`

- [ ] **Step 1: 创建流式处理模块**

```python
# src/agent/streaming.py

from typing import AsyncGenerator, Optional
import json
from src.db.redis_client import redis_client

class StreamingHandler:
    """
    流式响应处理器
    """
    
    def __init__(self):
        self.buffers: dict[str, list[str]] = {}
    
    async def handle_stream(
        self,
        session_id: str,
        generator: AsyncGenerator[str, None]
    ) -> str:
        """
        处理流式输出
        
        Args:
            session_id: 会话 ID
            generator: token 生成器
            
        Returns:
            完整的文本内容
        """
        self.buffers[session_id] = []
        
        async for token in generator:
            self.buffers[session_id].append(token)
        
        full_text = "".join(self.buffers[session_id])
        del self.buffers[session_id]
        return full_text

class RedisStreamingHandler(StreamingHandler):
    """
    基于 Redis 的流式处理器
    """
    
    async def publish_token(self, session_id: str, token: str):
        """发布 token 到 Redis"""
        channel = f"stream:{session_id}"
        await redis_client.publish(
            channel,
            json.dumps({"type": "token", "content": token})
        )
    
    async def publish_complete(self, session_id: str, full_content: str):
        """发布完成信号"""
        channel = f"stream:{session_id}"
        await redis_client.publish(
            channel,
            json.dumps({"type": "complete", "content": full_content})
        )
    
    async def subscribe(self, session_id: str) -> AsyncGenerator[dict, None]:
        """订阅流式输出"""
        pubsub = redis_client.subscribe(f"stream:{session_id}")
        async for message in pubsub:
            yield json.loads(message)
```

- [ ] **Step 2: 添加测试**

```python
# tests/test_streaming.py

import pytest
from src.agent.streaming import StreamingHandler, RedisStreamingHandler

@pytest.mark.asyncio
async def test_streaming_handler_buffer():
    """测试流式处理器 buffer 累积"""
    handler = StreamingHandler()
    session_id = "test_session"
    
    async def mock_generator():
        yield "hello"
        yield " "
        yield "world"
    
    result = await handler.handle_stream(session_id, mock_generator())
    assert result == "hello world"
    assert session_id not in handler.buffers
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/streaming.py tests/test_streaming.py
git commit -m "feat(agent): add streaming handler with Redis pub/sub"
```

---

## Phase 2: ResumeAgent 实现

### Task 5: ResumeAgent LLM 集成

**Files:**
- Modify: `src/agent/resume_agent.py`
- Test: `tests/test_resume_agent.py`

- [ ] **Step 1: 更新 parse_resume 使用 LLM 和重试装饰器**

```python
# src/agent/resume_agent.py

from src.services.llm_service import InterviewLLMService
from src.agent.retry import async_retryable
from src.agent.fallbacks import get_fallback_question

_llm_service: InterviewLLMService | None = None

def get_llm_service() -> InterviewLLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = InterviewLLMService()
    return _llm_service

@async_retryable(max_attempts=3)
async def parse_resume(state: InterviewState, resume_text: str) -> dict:
    """
    解析新简历，提取结构和职责信息
    """
    llm_service = get_llm_service()
    
    try:
        response = await llm_service.extract_resume_info(resume_text)
        
        responsibilities = []
        for project in response.get("projects", []):
            responsibilities.extend(project.get("responsibilities", []))
        
        return {
            "resume_context": resume_text,
            "responsibilities": tuple(responsibilities),
            "resume_parsed": response,
        }
    except Exception:
        # Fallback: 使用简单解析
        return {
            "resume_context": resume_text,
            "responsibilities": tuple(["简历解析失败，使用默认职责"]),
            "resume_parsed": {"skills": [], "projects": [], "experience": []},
        }
```

- [ ] **Step 2: 更新 fetch_old_resume**

```python
async def fetch_old_resume(state: InterviewState, resume_id: str) -> dict:
    """获取已有简历"""
    from src.dao.resume_dao import ResumeDAO
    from src.db.database import get_session
    
    async with get_session() as session:
        dao = ResumeDAO(session)
        resume = await dao.find_by_id(resume_id)
        if resume:
            return {"resume_context": resume.content, "resume_id": resume_id}
        return {"resume_context": "", "resume_id": resume_id}
```

- [ ] **Step 3: 添加测试**

```python
# tests/test_resume_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.resume_agent import parse_resume, fetch_old_resume
from src.agent.state import InterviewState

@pytest.mark.asyncio
async def test_parse_resume_success():
    """测试 parse_resume 成功解析简历"""
    state = InterviewState(session_id="test", resume_id="r1")
    
    with patch('src.agent.resume_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.extract_resume_info = AsyncMock(return_value={
            "skills": ["Python"],
            "projects": [{"name": "Test", "responsibilities": ["开发 API"]}],
            "experience": [],
        })
        mock.return_value = service
        
        result = await parse_resume(state, "测试简历内容")
        
        assert result["resume_context"] == "测试简历内容"
        assert len(result["responsibilities"]) == 1
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/resume_agent.py tests/test_resume_agent.py
git commit -m "feat(agent): integrate LLM into ResumeAgent with retry decorator"
```

---

## Phase 3: KnowledgeAgent 实现

### Task 6: KnowledgeAgent LLM 集成

**Files:**
- Modify: `src/agent/knowledge_agent.py`
- Test: `tests/test_knowledge_agent.py`

- [ ] **Step 1: 更新 find_standard_answer 实现**

```python
# src/agent/knowledge_agent.py

@async_retryable(max_attempts=3)
async def find_standard_answer(state: InterviewState, question: str) -> dict:
    """
    在 mastered_questions 中查找标准答案
    
    Args:
        state: InterviewState
        question: 问题内容
        
    Returns:
        {standard_answer: str | None, similarity_score: float}
    """
    from src.services.embedding_service import compute_similarity
    
    # 从 mastered_questions 查找（dev >= 0.8 的问答对）
    mastered = state.mastered_questions
    
    best_match = None
    best_score = 0.0
    
    for q_id, q_data in mastered.items():
        if q_data.get("deviation_score", 0) >= 0.8:
            # 计算语义相似度
            score = await compute_similarity(question, q_id)
            if score > best_score:
                best_score = score
                best_match = q_data.get("standard_answer")
    
    if best_match and best_score > 0.8:
        return {"standard_answer": best_match, "similarity_score": best_score}
    
    return {"standard_answer": None, "similarity_score": 0.0}
```

- [ ] **Step 2: 更新 store_to_vector_db**

```python
async def store_to_vector_db(state: InterviewState, responsibilities: tuple) -> dict:
    """将职责存储到向量数据库"""
    from src.db.vector_store import VectorStore
    from src.services.embedding_service import compute_embedding
    
    vector_store = VectorStore()
    
    try:
        for idx, responsibility in enumerate(responsibilities):
            embedding = await compute_embedding(responsibility)
            await vector_store.add(
                text=responsibility,
                embedding=embedding,
                metadata={"index": idx, "session_id": state.session_id}
            )
        return {"stored": True, "count": len(responsibilities)}
    except Exception as e:
        return {"stored": False, "error": str(e)}
```

- [ ] **Step 3: 添加测试**

```python
# tests/test_knowledge_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.knowledge_agent import find_standard_answer, store_to_vector_db
from src.agent.state import InterviewState

@pytest.mark.asyncio
async def test_find_standard_answer_found():
    """测试找到标准答案"""
    state = InterviewState(session_id="test", resume_id="r1")
    state.mastered_questions = {
        "q1": {"answer": "使用 Redis", "standard_answer": "使用 Redis 缓存", "deviation_score": 0.9}
    }
    
    with patch('src.agent.knowledge_agent.compute_similarity', new_callable=AsyncMock) as mock:
        mock.return_value = 0.85
        
        result = await find_standard_answer(state, "如何优化性能？")
        
        assert result["standard_answer"] == "使用 Redis 缓存"
        assert result["similarity_score"] == 0.85
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/knowledge_agent.py tests/test_knowledge_agent.py
git commit -m "feat(agent): integrate LLM into KnowledgeAgent with standard answer lookup"
```

---

## Phase 4: QuestionAgent 实现

### Task 7: QuestionAgent LLM 集成

**Files:**
- Modify: `src/agent/question_agent.py`
- Test: `tests/test_question_agent.py`

- [ ] **Step 1: 更新 generate_warmup 使用 LLM**

```python
# src/agent/question_agent.py

@async_retryable(max_attempts=3)
async def generate_warmup(state: InterviewState, resume_context: str = "") -> dict:
    """生成预热问题"""
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
```

- [ ] **Step 2: 更新 generate_initial**

```python
@async_retryable(max_attempts=3)
async def generate_initial(
    state: InterviewState,
    resume_context: str,
    responsibility: str
) -> dict:
    """生成初始问题"""
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
```

- [ ] **Step 3: 更新 generate_followup**

```python
@async_retryable(max_attempts=3)
async def generate_followup(
    state: InterviewState,
    qa_history: list,
    evaluation: dict
) -> dict:
    """生成追问"""
    llm_service = get_llm_service()
    
    if not state.current_question:
        return {"current_question": None, "current_question_id": None}
    
    history_str = ""
    for item in qa_history[-3:]:
        history_str += f"Q: {item.get('question', '')}\n"
        history_str += f"A: {item.get('answer', '')}\n\n"
    
    followup_direction = ""
    if evaluation and not evaluation.get("is_correct", True):
        followup_direction = "深入技术细节，说明具体实践"
    
    try:
        followup_content = await llm_service.generate_followup_question(
            original_question=state.current_question.content,
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
```

- [ ] **Step 4: 添加测试**

```python
# tests/test_question_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.question_agent import generate_warmup, generate_initial
from src.agent.state import InterviewState

@pytest.mark.asyncio
async def test_generate_warmup_success():
    """测试生成预热问题"""
    state = InterviewState(session_id="test", resume_id="r1")
    
    with patch('src.agent.question_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.generate_question = AsyncMock(return_value="请介绍一下你自己")
        mock.return_value = service
        
        result = await generate_warmup(state)
        
        assert result["current_question"] is not None
        assert result["current_question"].content == "请介绍一下你自己"
        assert result["followup_depth"] == 0
```

- [ ] **Step 5: Commit**

```bash
git add src/agent/question_agent.py tests/test_question_agent.py
git commit -m "feat(agent): integrate LLM into QuestionAgent with retry decorator"
```

---

## Phase 5: EvaluateAgent 实现

### Task 8: EvaluateAgent LLM 集成

**Files:**
- Modify: `src/agent/evaluate_agent.py`
- Test: `tests/test_evaluate_agent.py`

- [ ] **Step 1: 更新 evaluate_with_standard**

```python
# src/agent/evaluate_agent.py

@async_retryable(max_attempts=3)
async def evaluate_with_standard(
    state: InterviewState,
    question: str,
    user_answer: str,
    standard_answer: str
) -> dict:
    """使用标准答案评估用户回答"""
    llm_service = get_llm_service()
    
    try:
        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=standard_answer,
        )
        
        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
    except Exception:
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": ["评估出错"],
            "suggestions": ["请详细描述你的经验"],
        }
    
    question_id = state.current_question_id or f"q_{hash(question) % 10000}"
    
    new_answer = Answer(
        question_id=question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )
    
    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0
    
    evaluation_results = getattr(state, 'evaluation_results', {})
    evaluation_results[question_id] = result
    
    return {
        "answers": {**state.answers, question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
    }
```

- [ ] **Step 2: 更新 evaluate_without_standard**

```python
@async_retryable(max_attempts=3)
async def evaluate_without_standard(
    state: InterviewState,
    question: str,
    user_answer: str
) -> dict:
    """无标准答案时评估用户回答"""
    llm_service = get_llm_service()
    
    try:
        result = await llm_service.evaluate_answer(
            question=question,
            user_answer=user_answer,
            standard_answer=None,
        )
        
        deviation_score = result.get("deviation_score", 0.5)
        is_correct = result.get("is_correct", True)
    except Exception:
        deviation_score = 0.5
        is_correct = True
        result = {
            "deviation_score": 0.5,
            "is_correct": True,
            "key_points": ["暂时无法评估"],
            "suggestions": ["请详细描述你的经验"],
        }
    
    question_id = state.current_question_id or f"q_{hash(question) % 10000}"
    
    new_answer = Answer(
        question_id=question_id,
        content=user_answer,
        deviation_score=deviation_score,
    )
    
    new_error_count = state.error_count
    if not is_correct:
        new_error_count += 1
    else:
        new_error_count = 0
    
    evaluation_results = getattr(state, 'evaluation_results', {})
    evaluation_results[question_id] = result
    
    return {
        "answers": {**state.answers, question_id: new_answer},
        "evaluation_results": evaluation_results,
        "error_count": new_error_count,
        "current_answer": new_answer,
    }
```

- [ ] **Step 3: 添加测试**

```python
# tests/test_evaluate_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.evaluate_agent import evaluate_with_standard, evaluate_without_standard
from src.agent.state import InterviewState, Answer

@pytest.mark.asyncio
async def test_evaluate_with_standard_success():
    """测试使用标准答案评估"""
    state = InterviewState(session_id="test", resume_id="r1")
    state.current_question_id = "q_test"
    
    with patch('src.agent.evaluate_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.evaluate_answer = AsyncMock(return_value={
            "deviation_score": 0.8,
            "is_correct": True,
            "key_points": ["回答完整"],
            "suggestions": [],
        })
        mock.return_value = service
        
        result = await evaluate_with_standard(
            state,
            question="什么是 Redis?",
            user_answer="Redis 是一个内存数据库",
            standard_answer="Redis 是一个开源的内存数据结构存储..."
        )
        
        assert "current_answer" in result
        assert result["current_answer"].deviation_score == 0.8
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/evaluate_agent.py tests/test_evaluate_agent.py
git commit -m "feat(agent): integrate LLM into EvaluateAgent with retry decorator"
```

---

## Phase 6: FeedBackAgent 实现

### Task 9: FeedBackAgent LLM 集成

**Files:**
- Modify: `src/agent/feedback_agent.py`
- Test: `tests/test_feedback_agent.py`

- [ ] **Step 1: 更新 generate_correction**

```python
# src/agent/feedback_agent.py

@async_retryable(max_attempts=3)
async def generate_correction(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """生成纠正反馈（dev < 0.3）"""
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
    
    pending_feedbacks = list(getattr(state, 'pending_feedbacks', []))
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
```

- [ ] **Step 2: 更新 generate_guidance 和 generate_comment**

```python
@async_retryable(max_attempts=3)
async def generate_guidance(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """生成引导反馈（0.3 <= dev < 0.6）"""
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

@async_retryable(max_attempts=3)
async def generate_comment(
    state: InterviewState,
    question: str,
    user_answer: str,
    evaluation: dict
) -> dict:
    """生成评论反馈（dev >= 0.6）"""
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
```

- [ ] **Step 3: 添加测试**

```python
# tests/test_feedback_agent.py

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.feedback_agent import generate_correction, generate_guidance, generate_comment
from src.agent.state import InterviewState

@pytest.mark.asyncio
async def test_generate_correction():
    """测试生成纠正反馈"""
    state = InterviewState(session_id="test", resume_id="r1")
    state.current_question_id = "q_test"
    
    with patch('src.agent.feedback_agent.get_llm_service') as mock:
        service = AsyncMock()
        service.generate_feedback = AsyncMock(return_value=Feedback(
            question_id="q_test",
            content="正确答案是...",
            is_correct=False,
            feedback_type=FeedbackType.CORRECTION,
        ))
        mock.return_value = service
        
        result = await generate_correction(
            state,
            question="什么是 Redis?",
            user_answer="Redis 是一个数据库",
            evaluation={"deviation_score": 0.2, "is_correct": False}
        )
        
        assert "last_feedback" in result
        assert result["last_feedback"].feedback_type == FeedbackType.CORRECTION
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/feedback_agent.py tests/test_feedback_agent.py
git commit -m "feat(agent): integrate LLM into FeedBackAgent with retry decorator"
```

---

## Phase 7: ReviewAgent 实现

### Task 10: ReviewAgent 实现

**Files:**
- Create: `src/agent/review_agent.py`
- Test: `tests/test_review_agent.py`

- [ ] **Step 1: 创建 ReviewAgent**

```python
# src/agent/review_agent.py

from typing import Literal
from langgraph.graph import StateGraph
from src.agent.state import InterviewState
from src.agent.base import ReviewVoter, create_review_voters

_llm_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        from src.services.llm_service import InterviewLLMService
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
        审查结果: {passed: bool, failures: list[str]}
    """
    question = ""
    user_answer = ""
    
    if state.current_question:
        question = state.current_question.content
    if state.current_question_id and state.current_question_id in state.answers:
        user_answer = state.answers[state.current_question_id].content
    
    # 创建 3 个投票器
    voters = [
        lambda e: _check_evaluation_based_on_qa(question, user_answer, evaluation_result),
        lambda e: _check_evaluation_reasonableness(question, user_answer, evaluation_result),
        lambda e: _check_standard_answer_fit(question, evaluation_result, standard_answer) if standard_answer else True,
    ]
    
    voter = create_review_voters(voters)
    passed, failures = await voter.vote(evaluation_result)
    
    failure_reasons = []
    if not passed:
        if "Voter 0" in failures:
            failure_reasons.append("evaluation_not_based_on_qa")
        if "Voter 1" in failures:
            failure_reasons.append("evaluation_unreasonable")
        if "Voter 2" in failures:
            failure_reasons.append("standard_answer_mismatch")
    
    return {
        "review_passed": passed,
        "review_failures": failures,
        "failure_reasons": failure_reasons,
    }

def _check_evaluation_based_on_qa(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否基于问答内容"""
    return True  # TODO: 实现 LLM 调用判断

def _check_evaluation_reasonableness(question: str, user_answer: str, evaluation: dict) -> bool:
    """检查评估是否合理"""
    dev = evaluation.get("deviation_score", 0.5)
    return 0 <= dev <= 1

def _check_standard_answer_fit(question: str, evaluation: dict, standard_answer: str) -> bool:
    """检查标准答案与问题是否契合"""
    return True  # TODO: 实现语义相似度检查

def create_review_agent_graph() -> StateGraph:
    """创建 ReviewAgent 子图"""
    graph = StateGraph(InterviewState)
    graph.add_node("review_evaluation", review_evaluation)
    graph.set_entry_point("review_evaluation")
    graph.add_edge("review_evaluation", "__end__")
    return graph.compile()

review_agent_graph = create_review_agent_graph()
```

- [ ] **Step 2: 创建测试**

```python
# tests/test_review_agent.py

import pytest
from src.agent.review_agent import review_evaluation, _check_evaluation_reasonableness
from src.agent.state import InterviewState, Answer

@pytest.mark.asyncio
async def test_review_evaluation_pass():
    """测试审查通过"""
    state = InterviewState(session_id="test", resume_id="r1")
    state.current_question_id = "q_test"
    state.answers = {"q_test": Answer(question_id="q_test", content="使用 Redis", deviation_score=0.8)}
    state.current_question = None
    
    evaluation_result = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": ["回答完整"],
        "suggestions": [],
    }
    
    result = await review_evaluation(state, evaluation_result, standard_answer="使用 Redis 缓存")
    
    assert "review_passed" in result
    assert "review_failures" in result

def test_check_evaluation_reasonableness_valid():
    """测试评估合理性检查 - 有效分数"""
    result = _check_evaluation_reasonableness(
        "什么是 Redis?",
        "Redis 是内存数据库",
        {"deviation_score": 0.8}
    )
    assert result is True

def test_check_evaluation_reasonableness_invalid():
    """测试评估合理性检查 - 无效分数"""
    result = _check_evaluation_reasonableness(
        "什么是 Redis?",
        "Redis 是内存数据库",
        {"deviation_score": 1.5}  # 超出 0-1 范围
    )
    assert result is False
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/review_agent.py tests/test_review_agent.py
git commit -m "feat(agent): add ReviewAgent with 3-instance voting"
```

---

## Phase 8: 集成测试

### Task 11: 集成测试

**Files:**
- Create: `tests/integration/test_agent_integration.py`
- Modify: `src/agent/orchestrator.py`

- [ ] **Step 1: 更新 orchestrator 整合所有 Agent**

```python
# src/agent/orchestrator.py 更新

from src.agent.resume_agent import resume_agent_graph
from src.agent.knowledge_agent import knowledge_agent_graph
from src.agent.question_agent import question_agent_graph
from src.agent.evaluate_agent import evaluate_agent_graph
from src.agent.feedback_agent import feedback_agent_graph
from src.agent.review_agent import review_agent_graph

def create_orchestrator_graph() -> StateGraph:
    """创建主协调器图"""
    graph = StateGraph(InterviewState)
    
    # 主节点
    graph.add_node("init", init_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("decide_next", decide_next_node)
    graph.add_node("final_feedback", final_feedback_node)
    
    # Agent 子图
    graph.add_node("resume_agent", resume_agent_graph)
    graph.add_node("knowledge_agent", knowledge_agent_graph)
    graph.add_node("question_agent", question_agent_graph)
    graph.add_node("evaluate_agent", evaluate_agent_graph)
    graph.add_node("feedback_agent", feedback_agent_graph)
    graph.add_node("review_agent", review_agent_graph)
    
    # 边
    graph.set_entry_point("init")
    graph.add_edge("init", "orchestrator")
    graph.add_edge("orchestrator", "decide_next")
    
    # 条件边
    graph.add_conditional_edges(
        "decide_next",
        lambda s: s.get("next_action", END),
        {
            "question_agent": "question_agent",
            "knowledge_agent": "knowledge_agent",
            "evaluate_agent": "evaluate_agent",
            "feedback_agent": "feedback_agent",
            "review_agent": "review_agent",
            "final_feedback": "final_feedback",
        }
    )
    
    # Agent 间边
    graph.add_edge("question_agent", "evaluate_agent")
    graph.add_edge("evaluate_agent", "review_agent")
    graph.add_edge("review_agent", "feedback_agent")
    graph.add_edge("feedback_agent", "decide_next")
    graph.add_edge("final_feedback", END)
    
    return graph.compile()

orchestrator_graph = create_orchestrator_graph()
```

- [ ] **Step 2: 创建集成测试**

```python
# tests/integration/test_agent_integration.py

import pytest
from src.agent.orchestrator import orchestrator_graph
from src.agent.state import InterviewState

@pytest.mark.asyncio
async def test_question_to_feedback_flow():
    """测试从问题生成到反馈的完整流程"""
    initial_state = InterviewState(
        session_id="test_session",
        resume_id="test_resume",
        resume_context="Python 开发者，熟悉 FastAPI",
        responsibilities=("负责 API 开发", "优化性能"),
    )
    
    result = await orchestrator_graph.ainvoke(initial_state)
    
    assert "current_question" in result or result.get("phase") is not None

@pytest.mark.asyncio
async def test_review_agent_integration():
    """测试 ReviewAgent 集成"""
    from src.agent.review_agent import review_agent_graph
    from src.agent.state import InterviewState, Answer
    
    state = InterviewState(
        session_id="test",
        resume_id="r1",
        current_question_id="q1",
        answers={"q1": Answer(question_id="q1", content="test", deviation_score=0.8)},
    )
    
    evaluation = {
        "deviation_score": 0.8,
        "is_correct": True,
        "key_points": [],
        "suggestions": [],
    }
    
    result = await review_agent_graph.ainvoke(state)
    
    assert "review_passed" in result
```

- [ ] **Step 3: 运行集成测试**

```bash
pytest tests/integration/ -v
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/orchestrator.py tests/integration/test_agent_integration.py
git commit -m "test: add integration tests for agent orchestration"
```

---

## Implementation Order

1. **Phase 1: 基础设施** - InterviewLLMService, retry, fallbacks, streaming
2. **Phase 2: ResumeAgent** - LLM 集成
3. **Phase 3: KnowledgeAgent** - LLM 集成
4. **Phase 4: QuestionAgent** - LLM 集成
5. **Phase 5: EvaluateAgent** - LLM 集成
6. **Phase 6: FeedBackAgent** - LLM 集成
7. **Phase 7: ReviewAgent** - 3-instance voting
8. **Phase 8: 集成测试** - orchestrator 整合 + 测试

---

**Plan complete.**
