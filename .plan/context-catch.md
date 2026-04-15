# Context Catch 记忆系统在 AI-Interview 中的实现

**Problem solved**: 为 AI-Interview 实现 Context Catch 机制，支持面试会话中断后基于摘要的快速恢复，替代现有 Redis 中存储的原始问答历史。

## 背景

当前三层记忆结构：
- **短期记忆**：LangGraph State（内存）
- **中短期记忆**：Redis（存储原始问答历史）
- **长期记忆**：PostgreSQL（面试结束后持久化）

现有问题：
- Redis 存储完整问答历史，数据量大，加载慢
- 中断恢复时传输完整 state，开销大
- 会话中断后无法快速恢复

## 目标

- 中短期记忆从"存储原始问答"转变为"存储压缩摘要"
- 支持基于摘要的快速恢复，牺牲细节换取速度
- 用户可选择"完整恢复摘要"或"从关键点重新开始"

## 设计决策

| 维度 | 决策 |
|------|------|
| 摘要内容 | 面试进度快照（ProgressSnapshot）+ 实时评估状态（EvaluationSnapshot） |
| LLM 洞察 | 候选人画像从长期记忆检索，无需放入摘要 |
| 触发机制 | 系列结束自动压缩 + 用户主动触发 |
| 恢复方式 | 用户选择"完整恢复摘要"或"从关键点重新开始" |
| 持久层 | Redis 主存储 + PostgreSQL 快照版本表（容灾） |
| 快照版本表 | 每次压缩生成新版本，直接加载无需重放 |
| 模块架构 | 新建 `context_catch.py`，与 `memory_tools.py` 解耦 |
| 压缩算法 | 混合压缩（规则提取 + LLM 判断复杂评估） |

## 数据结构

### ContextSnapshot

```python
@dataclass
class ContextSnapshot:
    session_id: str
    version: int
    timestamp: datetime

    # 进度快照（规则提取）
    progress: ProgressSnapshot

    # 评估状态（规则提取）
    evaluation: EvaluationSnapshot

    # LLM 压缩的洞察摘要
    insights: InsightSummary
```

### ProgressSnapshot（规则提取）

```python
@dataclass
class ProgressSnapshot:
    current_series: int
    current_question_index: int
    current_phase: str
    series_history: dict[int, SeriesRecord]
    followup_chain: list[str]
    responsibilities: tuple[str, ...]
```

### EvaluationSnapshot（规则提取）

```python
@dataclass
class EvaluationSnapshot:
    series_scores: dict[int, float]
    error_count: int
    error_threshold: int
    mastered_questions: dict[str, dict]
    asked_logical_questions: set[str]
```

### InsightSummary（LLM 生成）

```python
@dataclass
class InsightSummary:
    covered_technologies: list[str]
    weak_areas: list[str]
    error_patterns: list[str]
    followup_triggers: list[str]
    interview_continuity_note: str
```

## PostgreSQL 快照版本表

```sql
CREATE TABLE context_snapshots (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    version INT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    compressed_summary JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_context_snapshots_session_version
    ON context_snapshots(session_id, version DESC);
```

## 模块接口

### ContextCatchEngine

```python
class ContextCatchEngine:
    """Context Catch 压缩/恢复引擎"""

    async def compress(
        self,
        state: InterviewContext,
        trigger: Literal["auto", "manual"]
    ) -> ContextSnapshot:
        """
        压缩当前状态生成摘要

        Args:
            state: 当前 InterviewContext
            trigger: 触发方式（auto=系列结束, manual=用户主动）

        Returns:
            ContextSnapshot 压缩摘要
        """

    async def restore(
        self,
        session_id: str,
        mode: Literal["full", "key_points"]
    ) -> Optional[InterviewContext]:
        """
        恢复会话上下文

        Args:
            session_id: 会话ID
            mode: full=完整恢复摘要, key_points=从关键点重新开始

        Returns:
            InterviewContext 或 None
        """

    async def save_checkpoint(
        self,
        snapshot: ContextSnapshot
    ) -> None:
        """
        保存快照到 PostgreSQL（容灾）

        Args:
            snapshot: 压缩摘要
        """

    async def load_from_pg(
        self,
        session_id: str
    ) -> Optional[ContextSnapshot]:
        """
        从 PostgreSQL 加载最新快照（Redis 失效时重建）

        Args:
            session_id: 会话ID

        Returns:
            ContextSnapshot 或 None
        """
```

## 工作流

### 中断时压缩

```
用户中断/系列结束
  → ContextCatchEngine.compress(state)
  → 生成 ProgressSnapshot（规则）
  → 生成 EvaluationSnapshot（规则）
  → 调用 LLM 生成 InsightSummary
  → 写入 Redis（主存储）
  → 写入 PostgreSQL（快照版本表，version++）
```

### 恢复时

```
用户选择恢复方式
  → ContextCatchEngine.restore(session_id, mode)
  → 从 Redis 加载最新摘要
  → 重构 InterviewContext
  → 返回给用户确认/直接继续
```

### Redis 失效时重建

```
从 PostgreSQL 加载最新版本快照
  → 重建 ContextSnapshot
  → 回填 Redis
  → 返回 InterviewContext
```

## 实现步骤

- [ ] 新建 `src/tools/context_catch.py` 模块
- [ ] 定义 `ContextSnapshot`、`ProgressSnapshot`、`EvaluationSnapshot`、`InsightSummary` 数据结构
- [ ] 实现 `ContextCatchEngine.compress()` — 规则提取 + LLM 调用
- [ ] 实现 `ContextCatchEngine.restore()` — Redis 加载 + InterviewContext 重构
- [ ] 实现 `ContextCatchEngine.save_checkpoint()` — PostgreSQL 快照写入
- [ ] 实现 `ContextCatchEngine.load_from_pg()` — PostgreSQL 快照加载
- [ ] 创建 PostgreSQL 迁移脚本 `context_snapshots` 表
- [ ] 集成到 `orchestrator.py`：系列结束触发压缩
- [ ] 添加 API 端点：用户主动触发压缩 / 选择恢复模式
- [ ] 单元测试
