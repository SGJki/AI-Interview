# AI-Interview 高并发/高可用诊断报告

**日期**: 2026-04-13
**项目**: AI-Interview
**分支**: dev

---

## 一、现状总览

| 组件 | 现状 | 多用户就绪 | 高并发就绪 | 高可用就绪 |
|------|------|------------|------------|------------|
| 数据库模型 | User/Resume/InterviewSession 已有 user_id 外键 | ✅ | ⚠️ 连接池小 | ⚠️ 单库 |
| API 路由 | 无认证中间件 | ❌ | ✅ | ✅ 优雅关闭 |
| 会话访问控制 | 无用户-会话绑定验证 | ❌ | - | - |
| 状态存储 | Redis 异步化，无用户隔离 | ⚠️ | ✅ 异步化 | ⚠️ 单机 |
| LLM 调用 | 无熔断/重试/队列 | - | ❌ | ❌ |

### ✅ 已完成的优化 (2026-04-13)

| 优化项 | 状态 | 文件 |
|--------|------|------|
| 优雅关闭机制 | ✅ 已完成 | `src/core/lifespan_manager.py` |
| 健康检查端点 | ✅ 已完成 | `src/main.py` |
| SSE 连接追踪 | ✅ 已完成 | `src/api/interview.py` |
| Redis 同步/异步混用修复 | ✅ 已完成 | `src/tools/memory_tools.py`, `src/core/context_catch.py` |

---

## 二、高并发风险 (P0-P1)

### 2.1 LLM API 是最大瓶颈 🔴

**现状**:
```python
# client.py - 直接调用，无任何保护
response = await llm.ainvoke(messages)  # 失败 = 直接报错
```

**问题**:
| 问题 | 影响 |
|------|------|
| 无熔断器(Circuit Breaker) | LLM 故障时级联崩溃 |
| 无重试机制 | 偶发失败直接返回错误 |
| 无请求队列 | 高并发时请求堆积 |
| 无并发限制 | 触发 API 限流 |

### 2.2 SSE 长连接耗尽资源 🔴

**现状**:
- 无最大并发连接数限制
- 无连接超时配置
- 无心跳保活机制
- 断连处理不明确

### 2.3 数据库连接池偏小 🔴

```python
pool_size: int = 10,
max_overflow: int = 20,  # 最多 30 个连接
```

高并发时 30 个连接不够用，导致请求排队和超时。

### 2.4 Redis 客户端混用同步/异步 🔴

```python
# context_catch.py 第 20 行
import redis  # 同步库！在 async def 中使用会阻塞事件循环

# memory_tools.py
import redis.asyncio as redis  # 异步库
```

这会导致**事件循环阻塞**，高并发下性能急剧下降。

---

## 三、高可用风险 (P0-P1)

### 3.1 Redis 单点故障 🔴

```python
self._client = redis.from_url(self.url)  # 单机 Redis，无 Sentinel/Cluster
```

- Redis 挂了 → 所有面试会话丢失
- 无持久化备份
- 无 Redis HA 配置

### 3.2 会话状态无持久化 🔴

面试过程状态存在 Redis：
- Redis 重启 → 用户被迫重新开始
- 只能依赖手动触发的 ContextCatch 快照

### 3.3 无水平扩展设计 🟡

```
当前架构：单体应用
         ↓
    单个 FastAPI 实例
         ↓
    直接连 DB/Redis
```

- 多实例部署时 Redis session key 无命名空间隔离
- 无共享 session 存储
- 无读写分离

### 3.4 无优雅关闭 ✅ 已修复

**解决方案**: `src/core/lifespan_manager.py`

1. **连接追踪器** (`ConnectionTracker`)
   - 追踪所有活跃 SSE 连接
   - 支持 `register/unregister` 自动管理
   - `wait_for_drain()` 等待排空

2. **分阶段关闭**
   ```
   Phase 1: begin_shutdown() - 禁止新连接
   Phase 2: wait_for_drain() - 等待活跃连接完成（30s 超时）
   Phase 3: close_database() - 关闭 DB 连接
   Phase 4: close_redis() - 关闭 Redis 连接
   ```

3. **SSE 连接追踪** (`src/api/interview.py`)
   - 每个 `/question` 和 `/answer` SSE 请求独立追踪
   - 连接断开时自动注销
   - 关闭期间返回 503

---

## 四、其他风险

### 4.1 Context Catch 可能成为性能拐点 🟡

压缩时调用 LLM 生成摘要，如果面试很长，成本高。

### 4.2 无健康检查端点 ✅ 已修复

**新增端点** (`src/main.py`):

| 端点 | 用途 | 检查内容 |
|------|------|---------|
| `GET /health` | 存活检查 | 服务状态 |
| `GET /health/ready` | 就绪检查 | PostgreSQL + Redis + 活跃连接数 |
| `GET /health/startup` | 启动探针 | K8s startup probe |

### 4.3 数据库单库无读写分离 🟡

所有操作走同一个 PostgreSQL，高并发读+写互相影响。

---

## 五、优化优先级

| 优先级 | 优化项 | 风险等级 | 工作量 |
|--------|--------|----------|--------|
| **P0** | ~~**修复 Redis 同步/异步混用**~~ ✅ 已完成 | 🔴 高 | 小 |
| **P0** | **添加 LLM 熔断器 + 重试** | 🔴 高 | 中 |
| **P0** | **增大数据库连接池** | 🔴 高 | 小 |
| **P0** | **添加 SSE 连接数限制** | 🔴 高 | 中 |
| **P0** | ~~**实现完整优雅关闭**~~ ✅ 已完成 | 🔴 高 | 中 |
| **P0** | ~~**添加健康检查端点**~~ ✅ 已完成 | 🟡 中 | 小 |
| **P0** | **Redis 升级为 Sentinel** | 🔴 高 | 中 |
| P1 | ~~**Redis 异步化**~~ ✅ 已完成 | 🔴 高 | 小 |
| P2 | 实现请求队列化 | 🟡 中 | 大 |
| P2 | 数据库读写分离 | 🟡 中 | 大 |
| P3 | 多实例部署支持 | 🟡 中 | 中 |

---

## 六、认证/多租户改造

参见 [multi-user-design.md](./multi-user-design.md)

---

## 七、已完成的优化

- 2026-04-13: **graceful-shutdown** - 优雅关闭机制（连接追踪、排空、健康检查）
- 2026-04-13: **redis-async-fix** - Redis 同步/异步混用修复（统一使用 redis.asyncio）
- 2026-04-13: prompt-caching-recovery - 实现 Prompt 缓存和恢复
- 2026-04-13: invoke-llm-usage - 实现 LLM 使用量追踪
