# AI-Interview Agent 层集成企业知识库设计

**日期**: 2026-04-19
**类型**: 架构改进
**目的**: 将企业知识库检索集成到面试流程的评估与反馈环节

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI-Interview 面试流程                        │
├─────────────────────────────────────────────────────────────────┤
│  KnowledgeAgent                                                  │
│  ├── 解析简历                                                      │
│  ├── 提取职责（responsibility）                                      │
│  └── 识别 module（向量嵌入 + 最近邻匹配）                              │
│       └── 将 module 存入 InterviewState                            │
│                                                                  │
│  QuestionAgent                                                   │
│  ├── generate_warmup()                                           │
│  ├── generate_initial(responsibility) → 提取 skill_point           │
│  └── generate_followup()                                        │
│       └── 将 skill_point 存入 InterviewState                      │
│                                                                  │
│  EvaluateAgent  ◄───────────────────────────────────────────── │
│  ├── evaluate_with_standard()                                      │    │
│  │   └── 查询企业知识库（优先 module，其次 skill_point）             │    │
│  └── evaluate_without_standard()                                 │    │
│       └── 查询企业知识库（skill_point）                              │    │
│                                                                      │    │
│  FeedbackAgent  ◄─────────────────────────────────────────────── │    │
│  ├── generate_correction()                                        │    │
│  │   └── 查询企业知识库（module + skill_point）                      │    │
│  ├── generate_guidance()                                           │    │
│  │   └── 查询企业知识库（module + skill_point）                      │    │
│  └── generate_comment()                                           │    │
│      └── 查询企业知识库（module + skill_point）                      │    │
│                                                                      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    enterprise-kb 服务                            │
├─────────────────────────────────────────────────────────────────┤
│  POST /retrieve/by-module   ← 优先调用                            │
│  POST /retrieve/by-skill    ← fallback                            │
│  GET  /health                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 企业知识库检索策略

### 2.1 检索优先级

```
评估/反馈时：
1. 优先使用 module 查询企业知识库（更精确的业务上下文）
2. fallback 使用 skill_point 查询
3. 如果两者都无结果，返回空列表
```

### 2.2 API 调用接口

```python
# src/tools/rag_enhancements.py

async def retrieve_enterprise_knowledge(
    module: str | None = None,
    skill_point: str | None = None,
    top_k: int = 3
) -> list[Document]:
    """
    检索企业知识库文档
    
    Args:
        module: 模块名（优先使用）
        skill_point: 技能点（fallback）
        top_k: 返回数量
    
    Returns:
        企业知识库文档列表
    """
    # 优先按 module 查询
    if module:
        docs = await _call_enterprise_kb_by_module(module, top_k)
        if docs:
            return docs
    
    # fallback 按 skill_point 查询
    if skill_point:
        return await _call_enterprise_kb_by_skill(skill_point, top_k)
    
    return []
```

### 2.3 融合检索接口（用于评估）

```python
async def retrieve_enterprise_knowledge_with_fusion(
    query: str,
    top_k: int = 5
) -> list[Document]:
    """
    使用 HybridRetriever 融合检索企业知识
    BM25 + 向量语义融合
    """
    # 内部调用 enterprise-kb 的 /retrieve/by-skill（支持融合）
    return await _call_enterprise_kb_with_fusion(query, top_k)
```

---

## 3. EvaluateAgent 集成

### 3.1 评估策略

采用 **相似度分数 + LLM 结合** 的评估方式：

```python
async def evaluate_answer(
    state: InterviewState,
    user_answer: str,
    question: Question,
    enterprise_docs: list[Document],
) -> EvaluationResult:
    """
    评估用户回答
    
    有企业知识库文档时：
    1. 计算用户回答与标准答案的相似度分数
    2. 将相似度分数 + 文档 + 原问题一起交给 LLM 指导评估
    3. LLM 综合给出评估结果
    
    无企业知识库文档时：
    - LLM 独立评估
    """
    
    if enterprise_docs:
        # 1. 计算相似度分数
        similarity_scores = []
        for doc in enterprise_docs:
            score = await compute_similarity(user_answer, doc.content)
            similarity_scores.append(score)
        
        best_score = max(similarity_scores)
        
        # 2. 构建含相似度分数的评估提示词
        evaluation_prompt = _build_evaluation_prompt_with_similarity(
            question=question.content,
            user_answer=user_answer,
            enterprise_docs=enterprise_docs,
            similarity_score=best_score,
            responsibility=state.current_responsibility,
        )
        
        # 3. LLM 评估（受相似度分数指导）
        evaluation = await llm_service.evaluate(evaluation_prompt)
        
        return EvaluationResult(
            evaluation=evaluation,
            similarity_score=best_score,
            docs_used=True,
        )
    else:
        # 无企业知识库，LLM 独立评估
        evaluation = await llm_service.evaluate_independent(
            question=question.content,
            user_answer=user_answer,
        )
        
        return EvaluationResult(
            evaluation=evaluation,
            similarity_score=None,
            docs_used=False,
        )
```

### 3.3 evaluate_without_standard

```python
async def evaluate_without_standard(
    state: InterviewState,
    responsibility: str,
    user_answer: str,
    question: Question,
) -> dict:
    """不使用标准答案评估（企业知识库作为背景知识）"""

    module = state.current_module
    skill_point = state.current_skill_point or _extract_skill_point(question.content)

    # 查询企业知识库作为背景
    enterprise_docs = await retrieve_enterprise_knowledge(
        module=module,
        skill_point=skill_point,
        top_k=3
    )

    # 评估（相似度分数 + LLM 结合）
    result = await evaluate_answer(state, user_answer, question, enterprise_docs)

    return {
        "evaluation_result": result.evaluation,
        "similarity_score": result.similarity_score,
        "enterprise_docs_used": result.docs_used,
    }
```

---

## 4. FeedbackAgent 集成

### 4.1 generate_correction

```python
async def generate_correction(
    state: InterviewState,
    question: Question,
    user_answer: str,
    evaluation: dict,
) -> Feedback:
    """生成纠正反馈"""
    
    module = state.current_module
    skill_point = state.current_skill_point or _extract_skill_point(question.content)
    
    # 查询企业知识库（优先级：module > skill_point）
    enterprise_docs = await retrieve_enterprise_knowledge(
        module=module,
        skill_point=skill_point,
        top_k=3
    )
    
    correction_prompt = _build_correction_prompt(
        question=question.content,
        user_answer=user_answer,
        evaluation=evaluation,
        enterprise_docs=enterprise_docs,
    )
    
    return await llm_service.generate_correction(correction_prompt)
```

### 4.2 generate_guidance

```python
async def generate_guidance(
    state: InterviewState,
    question: Question,
    user_answer: str,
    evaluation: dict,
) -> Feedback:
    """生成指导反馈"""
    
    module = state.current_module
    skill_point = state.current_skill_point or _extract_skill_point(question.content)
    
    enterprise_docs = await retrieve_enterprise_knowledge(
        module=module,
        skill_point=skill_point,
        top_k=3
    )
    
    guidance_prompt = _build_guidance_prompt(
        question=question.content,
        user_answer=user_answer,
        evaluation=evaluation,
        enterprise_docs=enterprise_docs,
        skill_point=skill_point,
    )
    
    return await llm_service.generate_guidance(guidance_prompt)
```

### 4.3 generate_comment

```python
async def generate_comment(
    state: InterviewState,
    question: Question,
    user_answer: str,
    evaluation: dict,
) -> Feedback:
    """生成评语反馈"""
    
    module = state.current_module
    skill_point = state.current_skill_point or _extract_skill_point(question.content)
    
    enterprise_docs = await retrieve_enterprise_knowledge(
        module=module,
        skill_point=skill_point,
        top_k=3
    )
    
    comment_prompt = _build_comment_prompt(
        question=question.content,
        user_answer=user_answer,
        evaluation=evaluation,
        enterprise_docs=enterprise_docs,
    )
    
    return await llm_service.generate_comment(comment_prompt)
```

---

## 5. KnowledgeAgent - Module 识别

### 5.1 职责解析时识别 module

```python
# src/agent/knowledge_agent.py

MODULE_DESCRIPTIONS = {
    "用户认证": "用户登录、注册、Token管理、SSO单点登录、会话管理、安全认证...",
    "订单处理": "订单创建、订单查询、订单取消、订单状态流转、订单支付...",
    "缓存系统": "Redis缓存、缓存策略、缓存穿透、缓存雪崩、分布式缓存...",
    "消息队列": "Kafka、RabbitMQ、消息发布订阅、异步处理、削峰填谷...",
    "数据库": "MySQL、PostgreSQL、SQL优化、索引设计、分库分表...",
    # ... 其他模块
}

async def identify_module(responsibility_text: str) -> str | None:
    """
    通过向量嵌入 + 最近邻匹配识别职责对应的 module
    
    Returns:
        模块名（匹配度 >= 0.7），否则返回 None
    """
    # 1. 嵌入职责文本
    responsibility_embedding = await embed_text(responsibility_text)
    
    # 2. 计算与所有模块描述的相似度
    scores = {}
    for module, desc_embedding in module_embeddings.items():
        scores[module] = cosine_similarity(responsibility_embedding, desc_embedding)
    
    # 3. 返回最相似模块（阈值 0.7）
    best_match = max(scores.items(), key=lambda x: x[1])
    if best_match[1] >= 0.7:
        return best_match[0]
    return None
```

### 5.2 解析简历时存储 module

```python
async def parse_resume_and_identify_module(resume_text: str) -> dict:
    """解析简历并识别 module"""
    
    responsibilities = extract_responsibilities(resume_text)
    
    # 收集所有识别的 module
    modules = []
    for resp in responsibilities:
        module = await identify_module(resp)
        if module:
            modules.append(module)
    
    # 去重 + 选择最常见的 module
    primary_module = most_frequent(modules) if modules else None
    
    return {
        "responsibilities": responsibilities,
        "identified_modules": list(set(modules)),
        "primary_module": primary_module,
    }
```

---

## 6. InterviewState 变更

### 6.1 新增字段

```python
# src/agent/state.py

@dataclass
class InterviewState:
    """面试 Agent 状态"""
    
    # ... 现有字段 ...
    
    # 新增：企业知识库相关
    current_module: str | None = None           # 当前问题所属 module
    current_skill_point: str | None = None      # 当前问题关联的 skill_point
    identified_modules: list[str] = field(default_factory=list)  # 简历中识别的所有 module
```

### 6.2 状态更新时机

```
1. KnowledgeAgent.parse_resume()
   → identified_modules, primary_module → state

2. QuestionAgent.generate_initial()
   → skill_point → state.current_skill_point

3. EvaluateAgent / FeedbackAgent
   ← 读取 state.current_module, state.current_skill_point
```

---

## 7. 辅助函数

### 7.1 提取 skill_point

```python
def _extract_skill_point(question_content: str) -> str | None:
    """
    从问题内容中提取 skill_point
    通常问题会包含技能关键词
    """
    # 简单实现：基于关键词匹配
    skill_keywords = [
        "Python", "Java", "Go", "Rust", "Redis", "MySQL", "PostgreSQL",
        "缓存", "队列", "微服务", "Docker", "Kubernetes", ...
    ]
    
    for keyword in skill_keywords:
        if keyword in question_content:
            return keyword
    
    return None
```

### 7.2 构架评估提示词（含相似度分数）

```python
def _build_evaluation_prompt_with_similarity(
    question: str,
    user_answer: str,
    enterprise_docs: list[Document],
    similarity_score: float,
    responsibility: str,
) -> str:
    """
    构架评估提示词，将相似度分数 + 企业知识库内容作为参考答案
    """
    prompt = f"""你是一个面试评估专家。请根据以下信息评估候选人的回答。

## 问题
{question}

## 候选人回答
{user_answer}

## 候选人职责背景
{responsibility}

## 回答与参考答案的相似度
{similarity_score:.2%}

## 企业最佳实践参考答案
"""

    for i, doc in enumerate(enterprise_docs, 1):
        prompt += f"\n{i}. {doc.content}\n"

    prompt += """
请结合相似度分数和参考答案，从以下几个方面评估：
1. 回答的正确性
2. 回答的完整性
3. 与企业最佳实践的差距
4. 相似度分数对评估的参考价值

评估时：
- 相似度 > 0.8：回答与标准答案高度一致，可适当简化评估
- 相似度 0.5-0.8：回答部分一致，需指出具体差距
- 相似度 < 0.5：回答与标准答案差距较大，需详细指出问题
"""

    return prompt
```

---

## 8. 数据流

```
简历输入
    │
    ▼
KnowledgeAgent.parse_resume()
    │  识别 module（向量嵌入 + 最近邻）
    ▼
InterviewState.identified_modules = ["用户认证", "缓存系统"]
InterviewState.primary_module = "用户认证"
    │
    ▼
QuestionAgent.generate_initial(responsibility)
    │  生成问题 + 提取 skill_point
    ▼
InterviewState.current_skill_point = "Redis缓存"
InterviewState.current_module = "用户认证"  # 从 primary_module 继承
    │
    ▼
用户回答
    │
    ▼
EvaluateAgent.evaluate_with_standard()
    │  读取 state.current_module, state.current_skill_point
    │  调用 retrieve_enterprise_knowledge(module, skill_point)
    ▼
企业知识库 API（/retrieve/by-module 优先）
    │
    ▼
返回企业知识文档列表
    │
    ▼
LLM 根据企业知识作为参考进行评估
```

---

## 9. 配置

### 9.1 环境变量

```bash
# enterprise-kb 服务地址
ENTERPRISE_KB_BASE_URL=http://localhost:8080

# 检索数量
ENTERPRISE_KB_TOP_K=3

# 超时设置（秒）
ENTERPRISE_KB_TIMEOUT=10
```

### 9.2 异常处理

```python
async def retrieve_enterprise_knowledge_with_fallback(
    module: str | None = None,
    skill_point: str | None = None,
    top_k: int = 3,
) -> list[Document]:
    """
    带降级处理的检索
    - 企业知识库服务不可用时返回空列表
    - 不阻塞面试流程
    """
    try:
        return await retrieve_enterprise_knowledge(module, skill_point, top_k)
    except httpx.TimeoutException:
        logger.warning("Enterprise KB timeout, proceeding without it")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"Enterprise KB returned {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Enterprise KB error: {e}")
        return []
```

---

## 10. 待实现清单

- [ ] 修改 `InterviewState` 添加 `current_module`, `current_skill_point`, `identified_modules` 字段
- [ ] 实现 `identify_module()` 函数（向量嵌入 + 最近邻匹配）
- [ ] 修改 `KnowledgeAgent.parse_resume()` 存储 module 到 state
- [ ] 修改 `QuestionAgent.generate_initial()` 提取并存储 skill_point 到 state
- [ ] 实现 `retrieve_enterprise_knowledge()` 检索函数
- [ ] 修改 `EvaluateAgent.evaluate_with_standard()` 集成企业知识库
- [ ] 修改 `EvaluateAgent.evaluate_without_standard()` 集成企业知识库
- [ ] 修改 `FeedbackAgent` 三个方法集成企业知识库
- [ ] 添加环境变量配置
- [ ] 添加异常处理和降级逻辑
- [ ] 编写单元测试
