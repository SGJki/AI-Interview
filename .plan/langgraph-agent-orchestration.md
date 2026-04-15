# AI-Interview LangGraph Agent 编排架构设计

**Problem solved**: 为 AI-Interview 项目设计基于 LangGraph 的多 Agent 协作编排架构，实现面试流程的自动化、智能化和可维护性。

---

## 一、顶层架构概览

### 1.1 Agent 组成

| Agent | 职责 |
|-------|------|
| **Main Orchestrator** | 主协调 Agent，规则驱动 + LLM 处理复杂决策 |
| **ResumeAgent** | 简历解析与存储 |
| **KnowledgeAgent** | 知识库检索与职责管理 |
| **QuestionAgent** | 问题生成与去重 |
| **EvaluateAgent** | 回答评估 |
| **FeedBackAgent** | 反馈生成 |

### 1.2 Review 机制

- **3 实例投票**：每个 Agent 配有 3 个 Review 实例
- **通过条件**：至少 2 个实例通过
- **失败处理**：失败时触发反馈环，返回上一层重试
- **保底机制**：重试超限后使用模板问题

---

## 二、顶层流程

```
START ──► init_phase ──► warmup_phase ──► interview_phase ──► final_feedback ──► END
                       │              │(新简历)    │循环
                       │              │           │
                       │              │      question_subgraph
                       │              │           │
                       │              │      evaluate_subgraph
                       │              │           │
                       │              │      feedback_subgraph
                       │              │           │
                       │              │      decide_next ──► (继续下一轮) ──┘
                       │              │           │
                       │              │           └──► (结束)
```

### 2.1 init_phase

| 节点 | 职责 |
|------|------|
| `load_resume` | 加载简历信息 |
| `load_knowledge_base` | 加载知识库 |
| `init_state` | 初始化面试状态 |

### 2.2 Agent 编排时序

#### 旧简历流程（并行）

```
ResumeAgent ──► fetch resume_content ──► QuestionAgent
                           │
                           └──────► KnowledgeAgent (并行)
                                      (fetch responsibilities)
                                      │
                                      └──► 传给 QuestionAgent
```

#### 新简历流程（带预热阶段）

```
阶段1: 预热
ResumeAgent ──► parse ──► resume_content ──► QuestionAgent
       │                                        │
       │                                        │ warmup questions
       │                                        │
       ├──► save to DB (async)                  │
       │                                        │
       └──► responsibilities ──► Review(3) ──┐  │
                                      [通过]  │  │
                                          │  │
                                          └──► KnowledgeAgent
                                                  │
                                                  ├──► shuffle
                                                  ├──► 传第一条给 QuestionAgent
                                                  └──► 其余存入向量库

QuestionAgent ──► 生成预热问题 ──► 用户闲聊

阶段2: 正式开始
QuestionAgent 收到 resume_content + responsibilities
    │
    └──► 声明"正式开始" ──► 生成初始问题 ──► 用户
```

### 2.3 interview_phase

#### 外层循环：series_loop（按系列迭代）

```
series_loop (外层)
│
├── generate_initial_question ──► Redis queue (Q_(N+1)_1 预生成)
├── wait_answer
├── evaluate + feedback
│
└── followup_loop (内层 - 追问循环)
    │
    ├── generate_followup
    ├── wait_answer
    ├── evaluate + feedback
    │
    └── [dev>=0.8 AND depth>=max_followup_depth] ──► 退出追问
        │
        └── [dev<0.8 OR depth<max] ──► 继续追问
```

#### 追问退出条件

- `deviation_score >= 0.8` **且** `depth >= max_followup_depth` → 退出追问
- `deviation_score < 0.8` → 同一逻辑问题允许重复
- `deviation_score >= 0.8` → 该逻辑问题去重，不再出现

#### decide_next 节点

```python
def decide_next(state: InterviewState) -> Literal["question_subgraph", "final_feedback"]:
    if state.user_end:
        return "final_feedback"
    if state.current_series >= state.max_series:
        return "final_feedback"
    if state.error_count >= state.error_threshold:
        return "final_feedback"
    if state.all_responsibilities_used:
        return "final_feedback"
    return "question_subgraph"
```

### 2.4 final_feedback

| 步骤 | 操作 | 用户可见 |
|------|------|---------|
| 1 | 展示所有 Q&A + 每轮反馈 | ✅ 立即 |
| 2 | 后台异步 EvaluateAgent 评估完整面试 | ❌ |
| 3 | 追加评分 + 整体评价 | ✅ 完成后 |

### 2.5 各 Agent 输入汇总

| Agent | 阶段 | 输入 | 来源 |
|-------|------|------|------|
| ResumeAgent | - | resume_text / resume_id | 用户 |
| KnowledgeAgent | - | responsibilities / resume_id | ResumeAgent / 向量库 |
| QuestionAgent | warmup | resume_content | ResumeAgent |
| QuestionAgent | initial | resume_content + responsibility | ResumeAgent + KnowledgeAgent |
| QuestionAgent | followup | responsibility + all Q&A + evaluation | KnowledgeAgent + InterviewState + EvaluateAgent |
| EvaluateAgent | - | question + user_answer (+ standard_answer) | QuestionAgent + 用户 |
| FeedBackAgent | - | question + user_answer + evaluation | EvaluateAgent |

### 2.3 final_feedback

| 步骤 | 操作 | 用户可见 |
|------|------|---------|
| 1 | 展示所有 Q&A + 每轮反馈 | ✅ 立即 |
| 2 | 后台异步 EvaluateAgent 评估完整面试 | ❌ |
| 3 | 追加评分 + 整体评价 | ✅ 完成后 |

---

## 三、各 Agent 详细设计

### 3.1 ResumeAgent

**职责**：简历解析与存储

#### 与其他 Agent 的关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent 编排时序                                     │
│                                                                      │
│  旧简历:                                                             │
│  ResumeAgent ──► fetch resume_content ──► QuestionAgent             │
│                           │                                          │
│                           └──────► KnowledgeAgent (并行)             │
│                                      (fetch responsibilities)        │
│                                                                      │
│  新简历:                                                             │
│  阶段1: ResumeAgent ──► parse ──► resume_content ──► QuestionAgent   │
│                    │                            │                    │
│                    │                            │ warmup questions   │
│                    │                            │                    │
│                    ├──► save to DB (async)                            │
│                    │                            │                    │
│                    └──► responsibilities ──► Review(3) ──┐           │
│                                                          │           │
│                                              [通过] ──► KnowledgeAgent│
│                                                          │           │
│                                                          └── shuffle │
│                                                              │       │
│                                                              ├──► 向量库存储
│                                                              └──► QuestionAgent
│                                                                      │
│  阶段2: QuestionAgent 收到 resume_content + responsibilities          │
│                     │                                                │
│                     └──► 声明"正式开始" ──► 生成初始问题 ──► 用户  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 子图节点详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     ResumeAgent 子图                              │
│                                                                   │
│   input: resume_text (新) / resume_id (旧)                      │
│                                                                   │
│   [新简历?] ──┬── Yes ──→ parse_resume                           │
│               │           │                                      │
│               │           ├──→ resume_content ──► QuestionAgent   │
│               │           │                                      │
│               │           ├──► save to DB (async)                │
│               │           │                                      │
│               │           └──► responsibilities ──► Review(3)     │
│               │                                      │            │
│               │                            ┌───────┴───────┐     │
│               │                         [通过]        [失败]    │
│               │                            │              │     │
│               │                            ▼              ▼     │
│               │              trigger KnowledgeAgent      反馈环  │
│               │                            │                      │
│               │                            └──→ 完成 ──→ 返回     │
│               │                                                    │
│               └── No ──► fetch resume_content ──► QuestionAgent  │
│                              │                                    │
│                              └──→ 完成 ──→ 返回                   │
│                                                                   │
│   注意: 旧简历无需 Review，入库前已审核                             │
└──────────────────────────────────────────────────────────────────┘
```

#### Review(3实例) 审核标准 - 严格标准

| 审核项 | 标准 |
|--------|------|
| responsibilities 非空 | 至少提取到 1 条职责 |
| 技能提取 | 技能数量 >= 3 |
| 项目数量 | 项目数量 >= 1 |
| 字段完整性 | name/email/phone/education 至少部分存在 |
| 格式规范 | 无明显乱码、解析错误 |

#### 反馈环

| 失败原因 | 反馈给 |
|---------|--------|
| responsibilities 为空 | ResumeAgent 重新解析 |
| 字段缺失严重 | ResumeAgent 补充解析 |
| 解析错误 | ResumeAgent 重试 |

#### 与 KnowledgeAgent 的交互

| 简历类型 | 触发方式 | 传递内容 |
|---------|---------|---------|
| 新简历 | Review 通过后触发 | responsibilities (列表) |
| 旧简历 | 无需触发 | responsibilities 已在向量库 |

---

### 3.2 KnowledgeAgent

**职责**：知识库检索与职责管理

#### 子图节点详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    KnowledgeAgent 子图                             │
│                                                                   │
│   input: responsibilities (新简历) / resume_id (旧简历)           │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   职责管理流程                                                    │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   新简历流程 (异步)                                               │
│   收到 responsibilities (from ResumeAgent)                        │
│       │                                                          │
│       ├──► shuffle ──→ 随机打乱顺序                              │
│       │                                                          │
│       ├──► 取第一条 ──► QuestionAgent（无需 Review）             │
│       │         ──→ 标记 is_used=true                           │
│       │                                                          │
│       └──► 其余存入向量库 (is_used=false)                         │
│                                                                   │
│   旧简历流程                                                     │
│   查询向量库: first is_used=false AND SessionID=current          │
│       │                                                          │
│       ├──► Review(3实例)                                        │
│       │        │                                                 │
│       │        ├── 检查: is_used == false?                       │
│       │        └── 检查: SessionID 匹配?                         │
│       │        │                                                 │
│       │    ┌───┴───┐                                             │
│       │  [通过] [失败]                                           │
│       │    │      │                                              │
│       │    │      └──► 反馈: is_used=true 重试                    │
│       │    │               │                                     │
│       │    │               └──► 取下一条 is_used=false ──► Review │
│       │    │                                     │                │
│       │    │                          ┌────┴────┐                │
│       │    │                        [通过]    [失败]              │
│       │    │                          │          │                │
│       │    │                          ▼          ▼                │
│       │    │                     传给 Q&A    反馈环...           │
│       │    │                          │          │                │
│       │    └──► 标记 is_used=true    ▼          │                │
│       │                        QuestionAgent    │                │
│       │                                  │      │                │
│       └──► [找不到 is_used=false]              │                │
│                │                             │                    │
│                ├──► 告诉 ReviewAgent: 已找到 N 条 is_used=true   │
│                │                             │                    │
│                └──► ReviewAgent 判断: 所有 responsibilities 已用完│
│                                     │                             │
│                               ┌────┴────┐                       │
│                            [未用完]   [已用完]                     │
│                               │          │                       │
│                               ▼          ▼                       │
│                           重试        结束面试                    │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   标准答案查询流程 (新增)                                         │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   QuestionAgent 输出问题 (异步触发)                               │
│       │                                                         │
│       ▼                                                         │
│   获取所有 deviation_score > 0.8 的问答对                        │
│       │                                                         │
│       ├──► 语义相似度检验                                        │
│       │                                                         │
│       ├──► 关键词检验                                            │
│       │                                                         │
│       ├──► [找到候选] ──► Review(3) ──► [通过?]                │
│       │                        │                               │
│       │                        ├──► Yes ──► 输出标准答案         │
│       │                        └──► No ──► 重试 (仅一次)         │
│       │                                  │                        │
│       │                                  └──► [失败] ──► 告知 EvaluateAgent "无标准答案"
│       │                                                         │
│       └──► [未找到] ──► 直接输出 "无标准答案"                    │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   反馈环                                                         │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   反馈给 KnowledgeAgent 的情况:                                    │
│   - is_used=true (应被标记为未使用)                               │
│   - SessionID 不匹配                                             │
│                                                                   │
│   反馈给 ReviewAgent 的情况:                                      │
│   - 已用完所有 responsibilities → 结束面试                        │
└──────────────────────────────────────────────────────────────────┘
```

#### Review(3实例) 审核标准

| 审核项 | 标准 |
|--------|------|
| is_used == false | 该 responsibility 尚未被使用 |
| SessionID 匹配 | 属于当前面试会话 |
| **标准答案契合 (新增)** | ReviewAgent 检查标准答案是否与问题契合 |

#### 与其他 Agent 的交互

| 来源 | 接收内容 | 传递内容 |
|------|---------|---------|
| ResumeAgent | responsibilities | 传递第一条给 QuestionAgent |
| 向量库 | is_used=false 查询结果 | 传递第一条给 QuestionAgent |
| QuestionAgent | 反馈（失败原因） | 重试或结束 |
| ReviewAgent | 失败原因 / 结束信号 | 重试或结束面试 |
| **EvaluateAgent** | **标准答案请求** | **标准答案 / "无标准答案"** |

---

### 3.3 QuestionAgent

**职责**：问题生成与去重

#### 子图节点详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    QuestionAgent 子图                              │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   输入                                                            │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   | 阶段 | 输入 | 来源 |                                          │
│   | warmup | resume_content | ResumeAgent |                      │
│   | initial | resume_content + responsibility | ResumeAgent + KnowledgeAgent |
│   | followup | responsibility + all Q&A + evaluation | KnowledgeAgent + InterviewState + EvaluateAgent |
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   流程                                                            │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   check_phase                                                    │
│       │                                                          │
│       ├──► [warmup] ──► generate_warmup ──► 直接输出 (无需Review)│
│       │                                                          │
│       ├──► [initial] ──► generate_initial ──► Review(3) ──┐    │
│       │                                            │          │    │
│       │                                    ┌───────┴───────┐  │    │
│       │                                  [通过]        [失败] │    │
│       │                                    │              │  │    │
│       │                                    ▼              ▼  │    │
│       │                                输出         反馈环  │    │
│       │                                              │  │    │
│       └──► [followup] ──► deduplicate_check ─────────┘  │    │
│                          │                               │    │
│                          ├──► [不重复] ──► generate_followup  │    │
│                          │               │                   │    │
│                          │        Review(3) ──┐             │    │
│                          │              │     │             │    │
│                          │        ┌─────┴─────┴─────┐       │    │
│                          │      [通过]            [失败]     │    │
│                          │        │                │       │    │
│                          │        ▼                ▼       │    │
│                          │     输出            反馈环      │    │
│                          │                                 │    │
│                          └──► [重复且 dev>=0.8] ──► 跳过   │    │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   追问 conditionEdge                                             │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   dev >= 0.8 AND depth >= max_followup_depth ──► 退出追问      │
│   dev < 0.8 OR depth < max_followup_depth ──► 继续生成追问    │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   预生成机制                                                     │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   系列 N 进行中时，预生成系列 N+1 的初始问题                      │
│   存储在 Redis 队列: pending_series_questions                     │
│   系列切换时，直接从队列取出推给用户                              │
└──────────────────────────────────────────────────────────────────┘
```

#### Review(3实例) 审核标准

| 审核项 | 标准 |
|--------|------|
| 问题不重复 | 不在已掌握问题列表中 |
| 追问基于 Q+A+E | 追问内容与问答+评估相关 |
| 问题质量 | 50字以内、清晰、无偏见 |

#### 反馈环

| 失败原因 | 反馈给 |
|---------|--------|
| 问题逻辑重复 | QuestionAgent 生成新问题 |
| responsibility 使用次数超限 | KnowledgeAgent 重新检索 |

---

### 3.4 EvaluateAgent

**职责**：回答评估

#### 子图节点详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│                   EvaluateAgent 子图                               │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   输入                                                            │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   | 输入 | 来源 |                                                │
│   | question | QuestionAgent |                                   │
│   | user_answer | 用户 |                                         │
│   | standard_answer | KnowledgeAgent (异步预查询) |             │
│   | evaluation_result | deviation_score + is_correct + key_points + suggestions |
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   流程                                                            │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   check_standard                                                 │
│       │                                                          │
│       ├──► [有标准答案] ──► evaluate_with_standard              │
│       │                      │                                    │
│       │                      └──► Review(3) ──┐                  │
│       │                                    │                     │
│       │                        ┌─────────────┴─────────────┐   │
│       │                    [通过]                      [失败]    │
│       │                        │                          │        │
│       │                        ▼                          ▼        │
│       │                     输出                    反馈环          │
│       │                                                         │
│       └──► [无标准答案] ──► evaluate_without_standard           │
│                          │                                        │
│                          └──► Review(3) ──┐                     │
│                                        │                        │
│                              ┌─────────┴─────────┐             │
│                          [通过]              [失败]             │
│                              │                  │                 │
│                              ▼                  ▼                 │
│                           输出              反馈环                 │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   Review(3) 审核标准                                             │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   1. 评估基于 Q+A                                               │
│   2. 评估合理 (deviation_score 与回答质量匹配)                  │
│   3. 标准答案与问题契合 (仅当有标准答案时)                      │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   KnowledgeAgent 标准答案查询流程                                 │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   QuestionAgent 输出问题                                          │
│       │                                                         │
│       ▼                                                         │
│   KnowledgeAgent                                                 │
│       │                                                         │
│       ├──► 获取所有 deviation_score > 0.8 的问答对              │
│       │                                                         │
│       ├──► 语义相似度检验 + 关键词检验                           │
│       │                                                         │
│       ├──► [找到候选] ──► Review(3) ──► [通过?]               │
│       │                              │                          │
│       │                              ├──► Yes ──► 输出标准答案  │
│       │                              └──► No ──► 重试 (仅一次)   │
│       │                                        │                   │
│       │                                        └──► [失败] ──► 告知 "无标准答案"
│       │                                                         │
│       └──► [未找到] ──► 直接输出 "无标准答案"                    │
│                                                                   │
│   注意: 标准答案查询是异步的，当用户提交回答时可直接评估           │
└──────────────────────────────────────────────────────────────────┘
```

#### 评估维度

- 技术准确性
- 深度理解
- 实践经验
- 表达清晰度

#### 反馈环

| 失败原因 | 反馈给 |
|---------|--------|
| 评估不合理 | EvaluateAgent 重新评估 |
| 标准答案不契合 | KnowledgeAgent 重新寻找（重试一次） |

---

### 3.5 FeedBackAgent

**职责**：反馈生成

#### 子图节点详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│                   FeedBackAgent 子图                              │
│                                                                   │
│   输入: question + user_answer + evaluation                      │
│         evaluation = {deviation_score, key_points, suggestions}  │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   流程                                                            │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   check_deviation                                                │
│       │                                                          │
│       ├──► [dev < 0.3] ──► CORRECTION                         │
│       │                      │                                    │
│       │                      └──► Review(3) ──► [通过?] ──► 输出
│       │                                                             │
│       ├──► [0.3 <= dev < 0.6] ──► GUIDANCE                    │
│       │                             │                            │
│       │                             └──► Review(3) ──► [通过?] ──► 输出
│       │                                                                    │
│       └──► [dev >= 0.6] ──► COMMENT                             │
│                              │                                    │
│                              └──► Review(3) ──► [通过?] ──► 输出
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   Review(3) 审核标准                                             │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   1. 反馈基于 Q+A+E                                             │
│   2. 反馈内容合适 (100字以内、清晰、建设性)                      │
│   3. 反馈类型与 deviation_score 匹配                            │
│                                                                   │
│   ════════════════════════════════════════════════════════════   │
│   保底机制                                                      │
│   ════════════════════════════════════════════════════════════   │
│                                                                   │
│   重试超限后使用模板反馈 + 记录日志                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、Main Orchestrator 设计

### 4.1 节点设计

| 节点 | 类型 | 职责 |
|------|------|------|
| `init` | 规则 | 初始化状态、加载配置 |
| `orchestrator` | 混合 | 决定调用哪个子图 |
| `decide_next` | 规则 | 判断是否继续下一轮 |
| `final_feedback` | 规则 | 生成最终报告 |

### 4.2 子图调用方式

| 方式 | 使用场景 |
|------|---------|
| `add_node(graph=子图)` | 简单顺序调用 |
| `send_to_node()` | 复杂并行调用 |

### 4.3 LLM 决策触发条件

仅当规则无法判断时触发 LLM：
- Review 失败后的重试决策
- 异常情况处理
- 其他复杂决策

### 4.4 与子图的交互

```
Main Orchestrator
      │
      ├──► 调用子图 ──► 传入相关输入
      │    
      ├──► 接收子图输出 ──► 合并到共享状态
      │
      └──► 共享 InterviewState ──► 所有子图读写同一状态
```

### 4.5 共享状态 (InterviewState)

所有子图共享同一个 InterviewState：

```python
{
    session_id: str
    resume_id: str
    current_series: int
    followup_depth: int
    resume_context: str
    responsibilities: tuple[str, ...]
    answers: dict[str, Answer]
    feedbacks: dict[str, Feedback]
    evaluation_results: dict[str, Evaluation]
    # ... 其他字段
}
```

### 4.6 Main Orchestrator 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                               │
│                                                                   │
│   START ──► init                                                │
│                   │                                               │
│                   ▼                                               │
│            ┌─────────────┐                                       │
│            │ orchestrator │ ←── LLM (仅复杂情况)                  │
│            └──────┬──────┘                                       │
│                   │                                               │
│         ┌─────────┼─────────┬─────────────┐                     │
│         ▼         ▼         ▼             ▼                       │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐               │
│   │Resume- │ │Question│ │Eval-   │ │FeedBack- │               │
│   │Agent   │ │Agent   │ │uateAgent│ │Agent     │               │
│   └────┬───┘ └───┬────┘ └───┬────┘ └───┬──────┘               │
│        │         │           │          │                        │
│        └─────────┴───────────┴──────────┘                       │
│                          │                                       │
│                   ┌──────┴──────┐                               │
│                   │  update_state │                              │
│                   └──────┬──────┘                               │
│                          │                                       │
│                   ┌──────┴──────┐                               │
│                   │ decide_next  │                               │
│                   └──────┬──────┘                               │
│                          │                                       │
│            ┌─────────────┼─────────────┐                        │
│            ▼             ▼             ▼                         │
│     [继续面试]    [final_feedback]  [结束]                       │
│            │             │                                        │
│            └────────────►│◄────────────────────────────────────┘
│                          │                                       │
│                          ▼                                       │
│                   final_feedback                                 │
│                          │                                       │
│                          ▼                                       │
│                         END                                      │
└─────────────────────────────────────────────────────────────────┘
```
```

---

## 四、数据流

### 4.1 Redis 使用

#### 预生成问题队列

```
Key: pending_series_questions
Type: Queue
Value:
{
    "question_id": "q_1_2",
    "content": "请介绍你在项目中遇到的挑战...",
    "series": 2
}
```

#### 系列状态

```
Key: series_{N}_state
Type: Hash
Value:
{
    "current_question_id": "q_1_2",
    "current_depth": 2,
    "is_active": true,
    "asked_questions": ["q_1_1", "q_1_2"],           # 已问过的问题列表（查重）
    "mastered_questions": [                           # 已掌握问题+标准回答
        {
            "question_id": "q_1_1",
            "answer": "我通过优化算法将性能提升了30%...",
            "standard_answer": "使用贪心算法..."
        }
    ],
    "qa_history": [                                    # 当前系列问答（追问生成用）
        {
            "question_id": "q_1_1",
            "question": "...",
            "answer": "...",
            "evaluation": {...}
        }
    ]
}
```

#### 会话上下文

```
Key: session_{id}_context
Type: Hash
Value:
{
    "resume_id": "uuid",
    "resume_content": "...",
    "current_series": 1,
    "max_series": 5
}
```

#### Review 信息存储

| 环境 | 策略 |
|------|------|
| 开发 (`is_production=false`) | 全量存储 |
| 生产 (`is_production=true`) | 仅失败时存储 |

存储内容：反馈原因、重试次数、Agent 名称、时间戳

### 4.2 PostgreSQL 使用

| 表 | 用途 |
|----|------|
| resumes | 简历存储 |
| knowledge_base | 知识库向量 |
| interview_sessions | 会话记录 |
| qa_history | Q&A 历史 |
| feedbacks | 反馈记录 |

### 4.3 向量数据库 (pgvector)

| 用途 | 说明 |
|------|------|
| responsibility 向量 | 每条职责的语义向量(带 is_used, SessionID 元数据) |
| 简历内容向量 | 用于 RAG 检索 |

### 4.4 配置参数

新增配置参数（原有参数不动）：

```python
# Review 信息存储策略
is_production: bool = False  # True: 仅失败时存储, False: 全量存储

# 面试流程参数
max_followup_depth: int = 3      # 最大追问深度
Retry_Max: int = 3              # 重试次数上限
deviation_threshold: float = 0.8 # 追问退出阈值
max_series: int = 5              # 最大系列数
error_threshold: int = 2         # 连续答错阈值
feedback_thresholds: dict = {     # 反馈类型阈值
    "correction": 0.3,
    "guidance": 0.6
}
```

---

## 五、状态模型

### 5.1 InterviewState (已存在于 state.py)

关键字段：

```python
session_id: str
resume_id: str

# 面试进度
current_series: int
current_question: Optional[Question]
followup_depth: int
max_followup_depth: int = 3

# 系列历史
series_history: dict[int, SeriesRecord]
answers: dict[str, Answer]
feedbacks: dict[str, Feedback]

# 配置
interview_mode: InterviewMode
feedback_mode: FeedbackMode
error_threshold: int

# 去重追踪
asked_logical_questions: set[str]  # deviation >= 0.8 后加入
```

---

## 六、后续规划

### 已完成设计

- [x] ResumeAgent 子图内部节点详细设计
- [x] KnowledgeAgent 子图内部节点详细设计
- [x] QuestionAgent 子图内部节点详细设计
- [x] EvaluateAgent 子图内部节点详细设计
- [x] FeedBackAgent 子图内部节点详细设计
- [x] Main Orchestrator 与子图的交互接口设计
- [x] Redis 数据结构详细设计
- [x] 配置文件设计
