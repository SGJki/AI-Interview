# Prompt Caching + Context Catch 会话恢复设计

**Problem solved**: 通过组合 Context Catch（状态层）和 Prompt Caching（效率层），实现面试会话中断后的快速恢复，同时利用 GLM 原生缓存降低延迟和成本。

---

## 一、整体架构

### 1.1 分层职责

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      分层架构                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Recovery Manager (统一入口)                    │   │
│  │  • 协调 context_catch 和 prompt_cache                           │   │
│  │  • 对调用方暴露统一接口                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              ┌───────────────┴───────────────┐                         │
│              ▼                               ▼                         │
│  ┌───────────────────────────┐   ┌───────────────────────────┐         │
│  │      Context Catch        │   │      Prompt Cache         │         │
│  │      (状态层)             │   │      (效率层)             │         │
│  │                           │   │                           │         │
│  │  • 快照存储               │   │  • 利用 GLM 原生缓存      │         │
│  │  • 压缩                   │   │  • 验证 cache 有效性     │         │
│  │  • 对话历史恢复           │   │  • 降级策略              │         │
│  │                           │   │  • 监控                  │         │
│  │  [src/core/              │   │  [src/core/              │         │
│  │   context_catch.py]       │   │   prompt_cache.py]        │         │
│  └───────────────────────────┘   └───────────────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

| 层 | 组件 | 职责 |
|----|------|------|
| **状态层** | Context Catch | 快照存储、压缩、对话历史恢复 |
| **效率层** | Prompt Cache | GLM 原生缓存利用、有效性验证、降级策略 |
| **统一入口** | Recovery Manager | 协调两者，对外暴露统一接口 |

### 1.2 Context Catch 与 Prompt Cache 协作关系

| 组件 | 职责 | 不做 |
|------|------|------|
| **Context Catch** | 保存/恢复对话状态 | 不关心缓存 |
| **Prompt Cache** | 验证/优化 LLM 调用效率 | 不存储业务状态 |
| **Recovery Manager** | 协调两者，按序执行恢复 | - |

---

## 二、Context Catch（状态层）

保持现有 `src/core/context_catch.py` 不变，职责：

| 职责 | 说明 |
|------|------|
| 快照存储 | 每轮保存 `conversation_history` + `resume_context` |
| 压缩 | 减少存储大小 |
| 恢复 | 会话中断后还原状态 |

---

## 三、Prompt Cache（效率层）- 新增

### 3.1 缓存标识设计

```python
cache_key = hash(resume_id + responsibilities_hash)
```

| 设计选择 | 说明 |
|---------|------|
| **粒度** | Resume 级别（不同简历用不同缓存） |
| **组合** | `resume_id` + `responsibilities_hash` |
| **原因** | 同一简历的面试共享缓存，简历变化则缓存失效 |

### 3.2 职责

| 职责 | 说明 |
|------|------|
| 缓存标识生成 | 基于 `resume_id + responsibilities_hash` |
| 有效性验证 | 检查 GLM 返回的 `cached_tokens` 判断是否命中 |
| 降级处理 | 缓存失效时降级到原始会话恢复 |
| 监控 | 记录缓存命中率 |

### 3.3 GLM Prompt Caching 特性

| 特性 | 说明 |
|------|------|
| **缓存方式** | 自动识别，隐式缓存，无需手动配置 `cache_key` |
| **缓存指标** | `response.usage.prompt_tokens_details.cached_tokens` |
| **支持模型** | GLM-4.6, GLM-4.5 系列等 |
| **计费** | 缓存命中的 Token 按优惠价（约 50%） |
| **API 响应示例** | `{"cached_tokens": 800, "prompt_tokens": 1200}` |

### 3.4 失效策略

| 失效类型 | 处理方式 |
|---------|---------|
| **TTL 过期** | 自动重建缓存，对调用方透明 |
| **内容变更**（简历更新） | 降级到原始对话历史，通知调用方 |
| **GLM API 错误** | 降级到原始对话历史，记录日志 |

---

## 四、恢复流程

### 4.1 时序图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         会话恢复流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  T1: 会话中断前保存                                                      │
│  ┌─────────────────┐                                                    │
│  │ context_catch   │  snapshot = {                                     │
│  │ save_checkpoint │      conversation_history,                        │
│  └────────┬────────┘      resume_context,                              │
│           │               responsibilities_hash,                        │
│           │               current_series,                              │
│           │               ...                                          │
│           │     }                                                      │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ prompt_cache    │  记录 cache_key, cache_status                    │
│  │ record_cache    │                                                    │
│  └─────────────────┘                                                    │
│                                                                         │
│  T2: 用户重新连接                                                       │
│                                                                         │
│  T3: 恢复执行                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Recovery Manager                               │   │
│  │                                                                  │   │
│  │  1. context_catch.load_snapshot(session_id)                      │   │
│  │     └── 返回: conversation_history, resume_context, ...          │   │
│  │                                                                  │   │
│  │  2. prompt_cache.validate_cache(                                 │   │
│  │       cache_key, responsibilities_hash                           │   │
│  │     )                                                            │   │
│  │     └── 发送测试请求检查 cached_tokens                            │   │
│  │                                                                  │   │
│  │  3a. [缓存有效]                                                  │   │
│  │      直接使用 GLM 缓存，无额外处理                                 │   │
│  │                                                                  │   │
│  │  3b. [缓存失效] → 降级                                           │   │
│  │      使用原始 conversation_history 重建上下文                     │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  T4: 恢复完成，返回 {snapshot, cache_status, degraded}                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 降级路径

```
正常流程：resume_context + responsibilities → GLM 缓存命中 → 快速恢复

降级流程：
  resume_context + responsibilities → 缓存失效 → conversation_history → 重建上下文 → 恢复
```

---

## 五、数据结构

### 5.1 PromptCacheState

```python
@dataclass
class PromptCacheState:
    """Prompt Cache 状态"""
    cache_key: str                    # resume_id + responsibilities_hash
    responsibilities_hash: str        # 用于验证
    is_valid: bool                   # 缓存是否有效
    last_cached_tokens: int          # 最近一次缓存命中 token 数
    created_at: str                  # 创建时间（用于 TTL 判断）
    hit_count: int = 0              # 命中次数
    miss_count: int = 0             # 未命中次数
```

### 5.2 RecoveryResult

```python
@dataclass
class RecoveryResult:
    """恢复结果"""
    session_id: str
    snapshot: ConversationSnapshot    # 来自 context_catch
    cache_state: PromptCacheState   # 缓存状态
    degraded: bool                  # 是否降级
    cache_hit_rate: float           # 缓存命中率（用于监控）
```

### 5.3 ConversationSnapshot（现有 context_catch）

```python
@dataclass
class ConversationSnapshot:
    """对话快照"""
    session_id: str
    resume_id: str
    resume_context: str
    responsibilities: list[str]
    responsibilities_hash: str
    conversation_history: list[dict]  # [{role, content}, ...]
    current_series: int
    current_round: int
    created_at: str
```

---

## 六、错误处理

| 场景 | 处理方式 |
|------|---------|
| 缓存有效 | 正常使用 |
| 缓存失效（TTL） | 自动重建缓存 |
| 缓存失效（内容变更） | 降级到原始对话历史 |
| GLM API 错误 | 降级到原始对话历史，记录日志 |

### 降级策略

```python
async def recover_session(session_id: str) -> RecoveryResult:
    # 1. 加载快照
    snapshot = await context_catch.load_snapshot(session_id)
    
    # 2. 验证缓存
    cache_state = await prompt_cache.validate_cache(
        cache_key=snapshot.cache_key,
        responsibilities_hash=snapshot.responsibilities_hash
    )
    
    # 3. 根据缓存状态决定路径
    if cache_state.is_valid:
        return RecoveryResult(
            snapshot=snapshot,
            cache_state=cache_state,
            degraded=False
        )
    else:
        # 降级：使用原始对话历史重建上下文
        return RecoveryResult(
            snapshot=snapshot,
            cache_state=cache_state,
            degraded=True
        )
```

---

## 七、文件结构

```
src/core/
├── context_catch.py          # 已存在 - 快照/压缩
├── prompt_cache.py           # 新增 - KV 缓存管理
└── recovery_manager.py       # 新增 - 统一恢复入口
```

---

## 八、实现顺序

1. **prompt_cache.py** - 新增 PromptCache 类
2. **recovery_manager.py** - 新增 RecoveryManager 类
3. **集成** - 在现有面试流程中集成恢复逻辑
4. **测试** - 验证恢复流程和降级逻辑

---

## 九、监控指标

| 指标 | 说明 |
|------|------|
| `cache_hit_rate` | 缓存命中率 |
| `cached_tokens` | 缓存命中的 token 数 |
| `degraded_count` | 降级恢复次数 |
| `recovery_latency` | 恢复延迟 |
