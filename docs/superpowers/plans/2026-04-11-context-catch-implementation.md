# Context Catch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AI-Interview 实现 Context Catch 机制，支持面试会话中断后基于摘要的快速恢复。

**Architecture:** 新建 `src/tools/context_catch.py` 模块，实现 `ContextCatchEngine` 压缩/恢复引擎。与现有 `memory_tools.py` 解耦。中短期记忆从存储原始问答改为存储压缩摘要（进度快照 + 评估状态 + LLM 洞察）。持久层采用 Redis 主存储 + PostgreSQL 快照版本表。

**Tech Stack:** Python async, SQLAlchemy (async), Redis, Pydantic dataclass, LangGraph, LLM 调用

---

## File Structure

```
src/
├── tools/
│   ├── memory_tools.py           # 现有：短期+中短期记忆
│   └── context_catch.py          # 新增：压缩/恢复模块（核心）
├── db/
│   ├── database.py               # 现有：PostgreSQL 连接管理
│   ├── models.py                 # 现有：SQLAlchemy 模型
│   └── context_snapshot.py       # 新增：ContextSnapshot ORM 模型
├── agent/
│   └── state.py                  # 现有：InterviewContext 数据类
└── services/
    └── llm_service.py            # 现有：LLM 调用封装

migrations/
└── 001_create_context_snapshots.sql  # 新增：数据库迁移脚本
```

---

## Task 1: Create ContextSnapshot ORM Model

**Files:**
- Create: `src/db/context_snapshot.py`
- Modify: `src/db/models.py` — 导入 ContextSnapshot
- Test: `tests/unit/test_context_snapshot.py`

- [ ] **Step 1: Create migration script**

```sql
-- migrations/001_create_context_snapshots.sql

CREATE TABLE context_snapshots (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    compressed_summary JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_context_snapshots_session_version
    ON context_snapshots(session_id, version DESC);
```

Run: 保存到 `migrations/001_create_context_snapshots.sql`

- [ ] **Step 2: Create ORM model**

```python
# src/db/context_snapshot.py

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class ContextSnapshot(Base):
    """
    Context Catch 快照版本表

    Attributes:
        id: 主键
        session_id: 会话ID
        version: 版本号，每次压缩递增
        timestamp: 快照时间戳
        compressed_summary: 压缩后的摘要（JSONB）
        created_at: 创建时间
    """

    __tablename__ = "context_snapshots"
    __table_args__ = (
        Index("idx_context_snapshots_session_version", "session_id", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    compressed_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
```

- [ ] **Step 3: Import ContextSnapshot in models.py**

在 `src/db/models.py` 末尾添加：
```python
from src.db.context_snapshot import ContextSnapshot  # noqa: F401
```

- [ ] **Step 4: Run migration to verify**

Run: `psql $DATABASE_URL -f migrations/001_create_context_snapshots.sql`
Expected: `CREATE TABLE` success

- [ ] **Step 5: Write unit test**

```python
# tests/unit/test_context_snapshot.py

import pytest
from datetime import datetime
from src.db.context_snapshot import ContextSnapshot


def test_context_snapshot_creation():
    snapshot = ContextSnapshot(
        session_id="test-session-123",
        version=1,
        timestamp=datetime.now(),
        compressed_summary={
            "progress": {"current_series": 1},
            "evaluation": {"error_count": 0},
            "insights": {"covered_technologies": ["Python"]},
        },
    )
    assert snapshot.session_id == "test-session-123"
    assert snapshot.version == 1
    assert snapshot.compressed_summary["progress"]["current_series"] == 1
```

- [ ] **Step 6: Commit**

```bash
git add src/db/context_snapshot.py src/db/models.py migrations/001_create_context_snapshots.sql tests/unit/test_context_snapshot.py
git commit -m "feat(context-catch): add ContextSnapshot ORM model and migration"
```

---

## Task 2: Define Snapshot Data Structures

**Files:**
- Modify: `src/agent/state.py` — 添加 ProgressSnapshot, EvaluationSnapshot, InsightSummary
- Test: `tests/unit/test_snapshot_dataclasses.py`

- [ ] **Step 1: Add dataclasses to state.py**

在 `src/agent/state.py` 末尾添加：

```python
# =============================================================================
# Context Catch Snapshot Data Classes
# =============================================================================


@dataclass(frozen=True)
class ProgressSnapshot:
    """
    进度快照 - 规则提取

    Attributes:
        current_series: 当前系列号
        current_question_index: 当前问题索引
        current_phase: 当前阶段 (init/warmup/initial/followup/final_feedback)
        series_history: 系列历史记录 {series_num: SeriesRecord}
        followup_chain: 追问链
        responsibilities: 职责列表
    """
    current_series: int = 1
    current_question_index: int = 1
    current_phase: str = "init"
    series_history: dict[int, dict] = field(default_factory=dict)
    followup_chain: list[str] = field(default_factory=list)
    responsibilities: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvaluationSnapshot:
    """
    评估快照 - 规则提取

    Attributes:
        series_scores: 各系列得分
        error_count: 当前连续错误次数
        error_threshold: 错误阈值
        mastered_questions: 已掌握问题
        asked_logical_questions: 已问的逻辑问题
    """
    series_scores: dict[int, float] = field(default_factory=dict)
    error_count: int = 0
    error_threshold: int = 2
    mastered_questions: dict[str, dict] = field(default_factory=dict)
    asked_logical_questions: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class InsightSummary:
    """
    洞察摘要 - LLM 生成

    Attributes:
        covered_technologies: 已覆盖技术点
        weak_areas: 薄弱领域
        error_patterns: 错误模式
        followup_triggers: 追问触发原因
        interview_continuity_note: 面试连续性备注
    """
    covered_technologies: list[str] = field(default_factory=list)
    weak_areas: list[str] = field(default_factory=list)
    error_patterns: list[str] = field(default_factory=list)
    followup_triggers: list[str] = field(default_factory=list)
    interview_continuity_note: str = ""


@dataclass(frozen=True)
class ContextSnapshotData:
    """
    Context Catch 压缩摘要（内存数据结构）

    Attributes:
        session_id: 会话ID
        version: 版本号
        timestamp: 时间戳
        progress: 进度快照
        evaluation: 评估快照
        insights: LLM 洞察摘要
    """
    session_id: str
    version: int
    timestamp: datetime
    progress: ProgressSnapshot
    evaluation: EvaluationSnapshot
    insights: InsightSummary
```

- [ ] **Step 2: Write unit test**

```python
# tests/unit/test_snapshot_dataclasses.py

import pytest
from datetime import datetime
from src.agent.state import (
    ProgressSnapshot,
    EvaluationSnapshot,
    InsightSummary,
    ContextSnapshotData,
)


def test_progress_snapshot():
    progress = ProgressSnapshot(
        current_series=2,
        current_question_index=3,
        current_phase="followup",
        responsibilities=("后端开发", "微服务"),
    )
    assert progress.current_series == 2
    assert progress.current_phase == "followup"


def test_evaluation_snapshot():
    evaluation = EvaluationSnapshot(
        series_scores={1: 0.85, 2: 0.72},
        error_count=1,
        mastered_questions={"q1": {"answer": "ok"}},
    )
    assert evaluation.series_scores[1] == 0.85
    assert evaluation.error_count == 1


def test_insight_summary():
    insights = InsightSummary(
        covered_technologies=["Python", "Redis"],
        weak_areas=["分布式系统"],
        error_patterns=["混淆一致性级别"],
    )
    assert "Python" in insights.covered_technologies
    assert insights.weak_areas == ["分布式系统"]


def test_context_snapshot_data():
    snapshot = ContextSnapshotData(
        session_id="sess-123",
        version=1,
        timestamp=datetime.now(),
        progress=ProgressSnapshot(current_series=1),
        evaluation=EvaluationSnapshot(error_count=0),
        insights=InsightSummary(),
    )
    assert snapshot.session_id == "sess-123"
    assert snapshot.version == 1
```

- [ ] **Step 3: Commit**

```bash
git add src/agent/state.py tests/unit/test_snapshot_dataclasses.py
git commit -m "feat(context-catch): add ProgressSnapshot, EvaluationSnapshot, InsightSummary dataclasses"
```

---

## Task 3: Implement ContextCatchEngine.compress()

**Files:**
- Create: `src/tools/context_catch.py`
- Test: `tests/unit/test_context_catch.py`

- [ ] **Step 1: Create context_catch.py with compress logic**

```python
# src/tools/context_catch.py

"""
Context Catch - 面试会话压缩/恢复引擎

职责：
- compress(): 生成压缩摘要（规则提取 + LLM）
- restore(): 恢复会话上下文
- save_checkpoint(): PostgreSQL 快照写入
- load_from_pg(): PostgreSQL 快照加载
"""

import json
import logging
from datetime import datetime
from typing import Optional, Literal
from dataclasses import asdict

import redis
from sqlalchemy import select, func

from src.agent.state import (
    InterviewContext,
    ProgressSnapshot,
    EvaluationSnapshot,
    InsightSummary,
    ContextSnapshotData,
)
from src.db.context_snapshot import ContextSnapshot
from src.db.database import get_db_session

logger = logging.getLogger(__name__)


def _get_redis_client() -> redis.Redis:
    """获取 Redis 客户端"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_module", "src/config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    get_redis_config = config_module.get_redis_config
    cfg = get_redis_config()
    kwargs = cfg.to_redis_kwargs()
    return redis.Redis(**kwargs)


# =============================================================================
# Redis Key Patterns
# =============================================================================

def _snapshot_key(session_id: str) -> str:
    """Context Catch 快照 Redis key"""
    return f"context_catch:{session_id}:snapshot"


def _version_key(session_id: str) -> str:
    """版本号 Redis key"""
    return f"context_catch:{session_id}:version"


# =============================================================================
# ContextCatchEngine
# =============================================================================

class ContextCatchEngine:
    """
    Context Catch 压缩/恢复引擎
    """

    def __init__(self):
        self._redis = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = _get_redis_client()
        return self._redis

    # -------------------------------------------------------------------------
    # Compress - 生成摘要
    # -------------------------------------------------------------------------

    async def compress(
        self,
        state: InterviewContext,
        trigger: Literal["auto", "manual"] = "auto",
    ) -> ContextSnapshotData:
        """
        压缩当前状态生成摘要

        Args:
            state: 当前 InterviewContext
            trigger: 触发方式

        Returns:
            ContextSnapshotData 压缩摘要
        """
        # 1. 生成版本号
        session_id = state.session_id
        version = self.redis.incr(_version_key(session_id))

        # 2. 规则提取 - 进度快照
        progress = self._extract_progress(state)

        # 3. 规则提取 - 评估快照
        evaluation = self._extract_evaluation(state)

        # 4. LLM 生成 - 洞察摘要
        insights = await self._generate_insights(state)

        snapshot = ContextSnapshotData(
            session_id=session_id,
            version=version,
            timestamp=datetime.now(),
            progress=progress,
            evaluation=evaluation,
            insights=insights,
        )

        # 5. 写入 Redis
        await self._save_to_redis(snapshot)

        # 6. 写入 PostgreSQL
        await self.save_checkpoint(snapshot)

        logger.info(
            f"ContextCatch: compressed session {session_id}, version {version}, trigger={trigger}"
        )
        return snapshot

    def _extract_progress(self, state: InterviewContext) -> ProgressSnapshot:
        """规则提取 - 进度快照"""
        return ProgressSnapshot(
            current_series=state.current_series,
            current_question_index=len(state.answers) + 1,
            current_phase=state.phase,
            series_history=state.series_history,
            followup_chain=state.followup_chain,
            responsibilities=state.responsibilities,
        )

    def _extract_evaluation(self, state: InterviewContext) -> EvaluationSnapshot:
        """规则提取 - 评估快照"""
        # 从 answers 中计算各系列得分
        series_scores: dict[int, float] = {}
        for answer_record in state.answers:
            if isinstance(answer_record, dict):
                series = answer_record.get("series", 1)
                deviation = answer_record.get("deviation", 1.0)
                if series not in series_scores:
                    series_scores[series] = []
                series_scores[series].append(deviation)

        # 计算平均分
        avg_scores = {
            s: sum(scores) / len(scores)
            for s, scores in series_scores.items()
        }

        return EvaluationSnapshot(
            series_scores=avg_scores,
            error_count=state.error_count,
            error_threshold=state.error_threshold,
        )

    async def _generate_insights(self, state: InterviewContext) -> InsightSummary:
        """
        LLM 生成 - 洞察摘要

        基于当前面试上下文生成结构化洞察
        """
        # 构建 LLM 提示
        answers_summary = self._summarize_answers(state.answers)
        feedbacks_summary = self._summarize_feedbacks(state.feedbacks)

        prompt = f"""
基于以下面试上下文，生成结构化洞察摘要：

当前系列: {state.current_series}
已回答问题数: {len(state.answers)}
错误计数: {state.error_count}

已覆盖技术点（从回答中推断）:
{answers_summary}

反馈摘要:
{feedbacks_summary}

请生成以下格式的 JSON：
{{
    "covered_technologies": ["技术点1", "技术点2"],
    "weak_areas": ["薄弱领域1"],
    "error_patterns": ["错误模式1"],
    "followup_triggers": ["追问触发原因1"],
    "interview_continuity_note": "面试连续性备注"
}}
"""

        try:
            # 调用 LLM
            from src.llm.client import invoke_llm

            response = await invoke_llm(
                system_prompt="你是一个专业的面试分析助手，生成结构化 JSON 输出。",
                user_prompt=prompt,
                temperature=0.3,
            )

            # 解析 JSON
            import re
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return InsightSummary(
                    covered_technologies=data.get("covered_technologies", []),
                    weak_areas=data.get("weak_areas", []),
                    error_patterns=data.get("error_patterns", []),
                    followup_triggers=data.get("followup_triggers", []),
                    interview_continuity_note=data.get("interview_continuity_note", ""),
                )
        except Exception as e:
            logger.warning(f"LLM insight generation failed: {e}")

        return InsightSummary()

    def _summarize_answers(self, answers: list) -> str:
        """摘要回答列表"""
        if not answers:
            return "暂无回答"
        lines = []
        for i, answer in enumerate(answers[-5:], 1):  # 只取最近5个
            if isinstance(answer, dict):
                lines.append(f"- Q{len(answers)-5+i}: {answer.get('question', 'N/A')[:50]}...")
        return "\n".join(lines) if lines else "暂无回答"

    def _summarize_feedbacks(self, feedbacks: list) -> str:
        """摘要反馈列表"""
        if not feedbacks:
            return "暂无反馈"
        lines = []
        for fb in feedbacks[-3:]:
            if isinstance(fb, dict):
                is_correct = fb.get("is_correct", True)
                lines.append(f"- {'✓' if is_correct else '✗'} {fb.get('feedback', 'N/A')[:50]}...")
        return "\n".join(lines) if lines else "暂无反馈"

    # -------------------------------------------------------------------------
    # Redis Operations
    # -------------------------------------------------------------------------

    async def _save_to_redis(self, snapshot: ContextSnapshotData) -> None:
        """写入 Redis"""
        key = _snapshot_key(snapshot.session_id)
        data = {
            "session_id": snapshot.session_id,
            "version": snapshot.version,
            "timestamp": snapshot.timestamp.isoformat(),
            "progress": asdict(snapshot.progress),
            "evaluation": asdict(snapshot.evaluation),
            "insights": asdict(snapshot.insights),
        }
        self.redis.setex(key, 86400, json.dumps(data))  # 24h TTL

    async def _load_from_redis(
        self, session_id: str
    ) -> Optional[ContextSnapshotData]:
        """从 Redis 加载"""
        key = _snapshot_key(session_id)
        data = self.redis.get(key)
        if not data:
            return None

        state_data = json.loads(data)
        return ContextSnapshotData(
            session_id=state_data["session_id"],
            version=state_data["version"],
            timestamp=datetime.fromisoformat(state_data["timestamp"]),
            progress=ProgressSnapshot(**state_data["progress"]),
            evaluation=EvaluationSnapshot(**state_data["evaluation"]),
            insights=InsightSummary(**state_data["insights"]),
        )
```

- [ ] **Step 2: Write unit test for compress**

```python
# tests/unit/test_context_catch.py

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from src.tools.context_catch import ContextCatchEngine
from src.agent.state import InterviewContext, InterviewMode, FeedbackMode


@pytest.fixture
def engine():
    return ContextCatchEngine()


@pytest.fixture
def mock_state():
    return InterviewContext(
        session_id="test-session-123",
        resume_id="resume-456",
        knowledge_base_id="kb-789",
        current_series=2,
        phase="followup",
        answers=[
            {"question": "Python 装饰器是什么？", "deviation": 0.9, "series": 1},
            {"question": "Redis 持久化机制？", "deviation": 0.7, "series": 1},
        ],
        feedbacks=[
            {"question_id": "q1", "is_correct": True},
            {"question_id": "q2", "is_correct": False},
        ],
        error_count=1,
        responsibilities=("后端开发",),
    )


def test_extract_progress(engine, mock_state):
    progress = engine._extract_progress(mock_state)
    assert progress.current_series == 2
    assert progress.current_phase == "followup"
    assert progress.responsibilities == ("后端开发",)


def test_extract_evaluation(engine, mock_state):
    evaluation = engine._extract_evaluation(mock_state)
    assert evaluation.series_scores[1] == pytest.approx(0.8)
    assert evaluation.error_count == 1


@pytest.mark.asyncio
async def test_compress_generates_snapshot(engine, mock_state):
    with patch.object(engine, "redis") as mock_redis:
        mock_redis.incr.return_value = 1
        mock_redis.setex = MagicMock()

        with patch.object(engine, "_generate_insights") as mock_insights:
            mock_insights.return_value = MagicMock(
                covered_technologies=["Python"],
                weak_areas=[],
                error_patterns=[],
                followup_triggers=[],
                interview_continuity_note="",
            )

            snapshot = await engine.compress(mock_state)

            assert snapshot.session_id == "test-session-123"
            assert snapshot.version == 1
            assert snapshot.progress.current_series == 2
            mock_redis.setex.assert_called_once()
```

- [ ] **Step 3: Run test**

Run: `cd /c/Users/13253/dataDisk/Agent_AI/AI-Interview && uv run pytest tests/unit/test_context_catch.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/tools/context_catch.py tests/unit/test_context_catch.py
git commit -m "feat(context-catch): implement ContextCatchEngine with compress()"
```

---

## Task 4: Implement restore() + save_checkpoint() + load_from_pg()

**Files:**
- Modify: `src/tools/context_catch.py`
- Test: `tests/unit/test_context_catch.py`

- [ ] **Step 1: Add restore() method**

继续编辑 `src/tools/context_catch.py`，在 `ContextCatchEngine` 类中添加：

```python
    # -------------------------------------------------------------------------
    # Restore - 恢复会话
    # -------------------------------------------------------------------------

    async def restore(
        self,
        session_id: str,
        mode: Literal["full", "key_points"] = "full",
    ) -> Optional[InterviewContext]:
        """
        恢复会话上下文

        Args:
            session_id: 会话ID
            mode: full=完整恢复摘要, key_points=从关键点重新开始

        Returns:
            InterviewContext 或 None
        """
        # 1. 尝试从 Redis 加载
        snapshot = await self._load_from_redis(session_id)

        # 2. Redis 未命中，从 PostgreSQL 重建
        if not snapshot:
            snapshot = await self.load_from_pg(session_id)
            if not snapshot:
                return None
            # 回填 Redis
            await self._save_to_redis(snapshot)

        # 3. 重构 InterviewContext
        if mode == "full":
            return self._reconstruct_full_context(snapshot)
        else:
            return self._reconstruct_key_points_context(snapshot)

    def _reconstruct_full_context(
        self, snapshot: ContextSnapshotData
    ) -> InterviewContext:
        """
        完整恢复 - 重构完整 InterviewContext

        基于快照恢复所有可用的上下文信息
        """
        return InterviewContext(
            session_id=snapshot.session_id,
            resume_id="",  # 需要从调用方传入
            knowledge_base_id="",
            current_series=snapshot.progress.current_series,
            current_question_id=None,
            phase=snapshot.progress.current_phase,
            series_history=snapshot.progress.series_history,
            answers=[],  # 摘要中不保留原始回答
            feedbacks=[],
            followup_chain=snapshot.progress.followup_chain,
            error_count=snapshot.evaluation.error_count,
            error_threshold=snapshot.evaluation.error_threshold,
            responsibilities=snapshot.progress.responsibilities,
            # LLM 洞察通过其他方式传递
        )

    def _reconstruct_key_points_context(
        self, snapshot: ContextSnapshotData
    ) -> InterviewContext:
        """
        关键点恢复 - 只保留关键进度信息

        从关键点重新开始面试，不恢复详细上下文
        """
        return InterviewContext(
            session_id=snapshot.session_id,
            resume_id="",
            knowledge_base_id="",
            current_series=snapshot.progress.current_series,
            phase="initial",  # 重置到 initial 阶段
            answers=[],
            feedbacks=[],
            followup_chain=[],
            error_count=0,  # 重置错误计数
            responsibilities=snapshot.progress.responsibilities,
        )

    # -------------------------------------------------------------------------
    # PostgreSQL Operations
    # -------------------------------------------------------------------------

    async def save_checkpoint(self, snapshot: ContextSnapshotData) -> None:
        """
        保存快照到 PostgreSQL（容灾）

        Args:
            snapshot: 压缩摘要
        """
        async for session in get_db_session():
            db_snapshot = ContextSnapshot(
                session_id=snapshot.session_id,
                version=snapshot.version,
                timestamp=snapshot.timestamp,
                compressed_summary={
                    "progress": asdict(snapshot.progress),
                    "evaluation": asdict(snapshot.evaluation),
                    "insights": asdict(snapshot.insights),
                },
            )
            session.add(db_snapshot)
            # get_db_session context manager handles commit
            logger.info(
                f"ContextCatch: saved checkpoint for session {snapshot.session_id}, version {snapshot.version}"
            )
            break

    async def load_from_pg(self, session_id: str) -> Optional[ContextSnapshotData]:
        """
        从 PostgreSQL 加载最新快照（Redis 失效时重建）

        Args:
            session_id: 会话ID

        Returns:
            ContextSnapshotData 或 None
        """
        async for session in get_db_session():
            # 查询最新版本
            stmt = (
                select(ContextSnapshot)
                .where(ContextSnapshot.session_id == session_id)
                .order_by(ContextSnapshot.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if not row:
                return None

            summary = row.compressed_summary
            return ContextSnapshotData(
                session_id=row.session_id,
                version=row.version,
                timestamp=row.timestamp,
                progress=ProgressSnapshot(**summary["progress"]),
                evaluation=EvaluationSnapshot(**summary["evaluation"]),
                insights=InsightSummary(**summary["insights"]),
            )
```

- [ ] **Step 2: Add unit tests for restore and checkpoint**

```python
# tests/unit/test_context_catch.py (追加)


@pytest.mark.asyncio
async def test_restore_full_mode(engine):
    """测试完整恢复模式"""
    with patch.object(engine, "_load_from_redis") as mock_redis:
        mock_redis.return_value = ContextSnapshotData(
            session_id="test-session",
            version=1,
            timestamp=datetime.now(),
            progress=ProgressSnapshot(
                current_series=2,
                current_phase="followup",
                responsibilities=("后端开发",),
            ),
            evaluation=EvaluationSnapshot(error_count=1),
            insights=InsightSummary(),
        )

        context = await engine.restore("test-session", mode="full")
        assert context is not None
        assert context.current_series == 2
        assert context.phase == "followup"
        assert context.error_count == 1


@pytest.mark.asyncio
async def test_restore_key_points_mode(engine):
    """测试关键点恢复模式"""
    with patch.object(engine, "_load_from_redis") as mock_redis:
        mock_redis.return_value = ContextSnapshotData(
            session_id="test-session",
            version=1,
            timestamp=datetime.now(),
            progress=ProgressSnapshot(
                current_series=2,
                current_phase="followup",
                responsibilities=("后端开发",),
            ),
            evaluation=EvaluationSnapshot(error_count=3),
            insights=InsightSummary(),
        )

        context = await engine.restore("test-session", mode="key_points")
        assert context is not None
        assert context.current_series == 2
        assert context.phase == "initial"  # 重置
        assert context.error_count == 0  # 重置


@pytest.mark.asyncio
async def test_restore_fallback_to_pg(engine):
    """测试 Redis 未命中时回退到 PostgreSQL"""
    with patch.object(engine, "_load_from_redis") as mock_redis:
        mock_redis.return_value = None  # Redis 未命中

        with patch.object(engine, "load_from_pg") as mock_pg:
            mock_pg.return_value = ContextSnapshotData(
                session_id="test-session",
                version=1,
                timestamp=datetime.now(),
                progress=ProgressSnapshot(current_series=1),
                evaluation=EvaluationSnapshot(),
                insights=InsightSummary(),
            )

            with patch.object(engine, "_save_to_redis") as mock_save:
                context = await engine.restore("test-session", mode="full")
                assert context is not None
                mock_save.assert_called_once()  # 回填 Redis
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_context_catch.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/tools/context_catch.py tests/unit/test_context_catch.py
git commit -m "feat(context-catch): implement restore(), save_checkpoint(), load_from_pg()"
```

---

## Task 5: Integrate into orchestrator.py

**Files:**
- Modify: `src/agent/orchestrator.py`

- [ ] **Step 1: Add compression trigger on series end**

在 `orchestrator.py` 中找到系列结束的判断逻辑（`decide_next_node` 或类似位置），在系列切换时调用 `compress()`：

```python
async def end_interview_node(state: InterviewState) -> dict:
    """结束面试：写入 PostgreSQL + 清理 Redis"""
    from src.tools.context_catch import ContextCatchEngine
    from src.tools.memory_tools import clear_session_memory
    from src.dao.interview_session_dao import InterviewSessionDAO
    from src.db.database import get_db_session
    from src.agent.state import InterviewContext
    from uuid import UUID

    # 1. 压缩当前状态（自动触发）
    try:
        engine = ContextCatchEngine()
        # 从 state 构建 InterviewContext
        context = InterviewContext(
            session_id=state.session_id,
            resume_id=state.resume_id,
            knowledge_base_id="",  # 需要传递
            current_series=state.current_series,
            phase=state.phase,
            series_history={
                k: {"questions": v.questions, "answers": v.answers}
                for k, v in state.series_history.items()
            },
            answers=[
                {"question": a.question_id, "deviation": a.deviation_score}
                for a in state.answers.values()
            ],
            feedbacks=[
                {"question_id": f.question_id, "is_correct": f.is_correct}
                for f in state.feedbacks.values()
            ],
            followup_chain=state.followup_chain,
            error_count=state.error_count,
            error_threshold=state.error_threshold,
        )
        await engine.compress(context, trigger="auto")
    except Exception as e:
        logger.warning(f"ContextCatch compression failed: {e}")

    # 2. 写入 PostgreSQL
    async for session in get_db_session():
        dao = InterviewSessionDAO(session)
        try:
            session_uuid = UUID(state.session_id) if state.session_id else None
        except ValueError:
            session_uuid = None

        if session_uuid:
            interview_session = await dao.find_by_uuid(session_uuid)
            if interview_session:
                await dao.end_session(interview_session.id)
        break

    # 3. 清理 Redis（可选，ContextCatch 会保留快照）
    await clear_session_memory(state.session_id)

    return {"phase": "completed"}
```

- [ ] **Step 2: Add API endpoints for manual trigger and restore**

在 `src/api/routers.py` 或新建 `src/api/context_catch.py`：

```python
# src/api/context_catch.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

router = APIRouter(prefix="/context-catch", tags=["context-catch"])


class CompressRequest(BaseModel):
    session_id: str
    trigger: Literal["auto", "manual"] = "manual"


class RestoreRequest(BaseModel):
    session_id: str
    mode: Literal["full", "key_points"] = "full"


class CompressResponse(BaseModel):
    session_id: str
    version: int
    timestamp: str


@router.post("/compress", response_model=CompressResponse)
async def compress_session(request: CompressRequest):
    """用户主动触发压缩"""
    from src.tools.context_catch import ContextCatchEngine
    from src.tools.memory_tools import get_session_memory

    engine = ContextCatchEngine()
    state = await get_session_memory(request.session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    snapshot = await engine.compress(state, trigger=request.trigger)

    return CompressResponse(
        session_id=snapshot.session_id,
        version=snapshot.version,
        timestamp=snapshot.timestamp.isoformat(),
    )


@router.post("/restore")
async def restore_session(request: RestoreRequest):
    """恢复会话"""
    from src.tools.context_catch import ContextCatchEngine

    engine = ContextCatchEngine()
    context = await engine.restore(request.session_id, mode=request.mode)

    if not context:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "session_id": context.session_id,
        "current_series": context.current_series,
        "phase": context.phase,
        "mode": request.mode,
        "message": "Session restored successfully" if request.mode == "full"
                   else "Session restored to key points",
    }
```

- [ ] **Step 3: Register router in main.py**

```python
# src/main.py (添加)

from src.api.context_catch import router as context_catch_router

app.include_router(context_catch_router)
```

- [ ] **Step 4: Commit**

```bash
git add src/agent/orchestrator.py src/api/context_catch.py src/main.py
git commit -m "feat(context-catch): integrate into orchestrator and add API endpoints"
```

---

## Task 6: Add Integration Test

**Files:**
- Create: `tests/integration/test_context_catch_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_context_catch_integration.py

import pytest
import asyncio
from datetime import datetime
from src.tools.context_catch import ContextCatchEngine
from src.agent.state import InterviewContext, InterviewMode


@pytest.fixture
def engine():
    return ContextCatchEngine()


@pytest.fixture
def sample_state():
    return InterviewContext(
        session_id="integration-test-session",
        resume_id="resume-123",
        knowledge_base_id="kb-456",
        current_series=2,
        phase="followup",
        answers=[
            {"question": "Python 是什么？", "deviation": 0.9, "series": 1},
            {"question": "FastAPI 是什么？", "deviation": 0.8, "series": 1},
        ],
        feedbacks=[
            {"question_id": "q1", "is_correct": True},
        ],
        error_count=1,
        responsibilities=("全栈开发", "API 设计"),
    )


@pytest.mark.asyncio
async def test_compress_and_restore_flow(engine, sample_state):
    """测试压缩 -> PostgreSQL 存储 -> Redis 恢复完整流程"""
    # 1. 压缩
    snapshot = await engine.compress(sample_state, trigger="manual")
    assert snapshot.version >= 1
    assert snapshot.progress.current_series == 2

    # 2. 从 Redis 恢复
    restored = await engine.restore(sample_state.session_id, mode="full")
    assert restored is not None
    assert restored.session_id == sample_state.session_id
    assert restored.current_series == 2


@pytest.mark.asyncio
async def test_key_points_restore_resets_state(engine, sample_state):
    """测试关键点恢复重置状态"""
    await engine.compress(sample_state, trigger="manual")

    restored = await engine.restore(sample_state.session_id, mode="key_points")
    assert restored.phase == "initial"
    assert restored.error_count == 0


@pytest.mark.asyncio
async def test_pg_fallback_when_redis_empty(engine):
    """测试 Redis 空时从 PostgreSQL 恢复"""
    # 模拟 Redis 未命中场景
    snapshot = await engine.load_from_pg("non-existent-session")
    assert snapshot is None
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/integration/test_context_catch_integration.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_context_catch_integration.py
git commit -m "test(context-catch): add integration tests"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create ContextSnapshot ORM + migration | `src/db/context_snapshot.py`, `migrations/001_create_context_snapshots.sql` |
| 2 | Define Snapshot dataclasses | `src/agent/state.py` |
| 3 | Implement `compress()` | `src/tools/context_catch.py` |
| 4 | Implement `restore()`, `save_checkpoint()`, `load_from_pg()` | `src/tools/context_catch.py` |
| 5 | Integrate into orchestrator + API | `src/agent/orchestrator.py`, `src/api/context_catch.py` |
| 6 | Integration tests | `tests/integration/test_context_catch_integration.py` |
