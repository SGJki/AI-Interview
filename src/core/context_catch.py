"""
Context Catch - 面试会话压缩/恢复引擎

职责：
- compress(): 生成压缩摘要（规则提取 + LLM）
- restore(): 恢复会话上下文
- save_checkpoint(): PostgreSQL 快照写入
- load_from_pg(): PostgreSQL 快照加载
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Literal
from dataclasses import asdict

import redis.asyncio as redis

if TYPE_CHECKING:
    from src.agent.state import (
        InterviewContext,
        ProgressSnapshot,
        EvaluationSnapshot,
        InsightSummary,
        ContextSnapshotData,
    )
    from src.db.context_snapshot import ContextSnapshot

logger = logging.getLogger(__name__)


def _get_redis_client() -> redis.Redis:
    """获取 Redis 客户端（异步）"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_module", "src/config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    get_redis_config = config_module.get_redis_config
    cfg = get_redis_config()
    return redis.from_url(cfg.url)


def _get_state_classes():
    """Lazy import state classes to avoid circular imports"""
    from src.agent.state import (
        InterviewContext,
        ProgressSnapshot,
        EvaluationSnapshot,
        InsightSummary,
        ContextSnapshotData,
    )
    return InterviewContext, ProgressSnapshot, EvaluationSnapshot, InsightSummary, ContextSnapshotData


def _get_context_snapshot_class():
    """Lazy import ContextSnapshot to avoid circular imports"""
    from src.db.context_snapshot import ContextSnapshot
    return ContextSnapshot


def _get_db_session():
    """Lazy import get_db_session to avoid circular imports"""
    from src.db.database import get_db_session as _get_db_session
    return _get_db_session


def _snapshot_to_dict(snapshot: "ContextSnapshotData") -> dict:
    """
    将 ContextSnapshotData 转换为字典，用于 JSON 序列化

    处理 set 类型（不可 JSON 序列化）转换为 list
    """
    return {
        "session_id": snapshot.session_id,
        "version": snapshot.version,
        "timestamp": snapshot.timestamp.isoformat(),
        "progress": _dataclass_to_dict(snapshot.progress),
        "evaluation": _dataclass_to_dict(snapshot.evaluation),
        "insights": _dataclass_to_dict(snapshot.insights),
    }


def _dataclass_to_dict(obj) -> dict:
    """将 dataclass 转换为字典，处理 set 类型"""
    result = {}
    for key, value in asdict(obj).items():
        if isinstance(value, set):
            result[key] = list(value)
        elif isinstance(value, dict):
            result[key] = {k: list(v) if isinstance(v, set) else v for k, v in value.items()}
        else:
            result[key] = value
    return result


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
        state: "InterviewContext",
        trigger: Literal["auto", "manual"] = "auto",
    ) -> "ContextSnapshotData":
        """
        压缩当前状态生成摘要

        Args:
            state: 当前 InterviewContext
            trigger: 触发方式

        Returns:
            ContextSnapshotData 压缩摘要
        """
        InterviewContext, ProgressSnapshot, EvaluationSnapshot, InsightSummary, ContextSnapshotData = _get_state_classes()

        # 1. 生成版本号
        session_id = state.session_id
        version = await self.redis.incr(_version_key(session_id))

        # 2. 规则提取 - 进度快照
        progress = self._extract_progress(state, ProgressSnapshot)

        # 3. 规则提取 - 评估快照
        evaluation = self._extract_evaluation(state, EvaluationSnapshot)

        # 4. LLM 生成 - 洞察摘要
        insights = await self._generate_insights(state, InsightSummary)

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

    def _extract_progress(self, state: "InterviewContext", ProgressSnapshot: type) -> "ProgressSnapshot":
        """规则提取 - 进度快照"""
        return ProgressSnapshot(
            current_series=state.current_series,
            current_question_index=len(state.answers) + 1,
            current_phase=state.phase,
            series_history=state.series_history,
            followup_chain=state.followup_chain,
            responsibilities=state.responsibilities,
        )

    def _extract_evaluation(self, state: "InterviewContext", EvaluationSnapshot: type) -> "EvaluationSnapshot":
        """规则提取 - 评估快照"""
        # 从 answers 中计算各系列得分
        series_scores: dict[int, list[float]] = {}
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

    async def _generate_insights(self, state: "InterviewContext", InsightSummary: type) -> "InsightSummary":
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

    async def _save_to_redis(self, snapshot: "ContextSnapshotData") -> None:
        """写入 Redis"""
        key = _snapshot_key(snapshot.session_id)
        data = _snapshot_to_dict(snapshot)
        await self.redis.setex(key, 86400, json.dumps(data))  # 24h TTL

    async def _load_from_redis(
        self, session_id: str
    ) -> Optional["ContextSnapshotData"]:
        """从 Redis 加载"""
        InterviewContext, ProgressSnapshot, EvaluationSnapshot, InsightSummary, ContextSnapshotData = _get_state_classes()

        key = _snapshot_key(session_id)
        data = await self.redis.get(key)
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

    # -------------------------------------------------------------------------
    # Restore - 恢复会话
    # -------------------------------------------------------------------------

    async def restore(
        self,
        session_id: str,
        mode: Literal["full", "key_points"] = "full",
    ) -> Optional["InterviewContext"]:
        """
        恢复会话上下文

        Args:
            session_id: 会话ID
            mode: full=完整恢复摘要, key_points=从关键点重新开始

        Returns:
            InterviewContext 或 None
        """
        InterviewContext, _, _, _, _ = _get_state_classes()

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
        self, snapshot: "ContextSnapshotData"
    ) -> "InterviewContext":
        """
        完整恢复 - 重构完整 InterviewContext

        基于快照恢复所有可用的上下文信息
        """
        InterviewContext, _, _, _, _ = _get_state_classes()

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
        )

    def _reconstruct_key_points_context(
        self, snapshot: "ContextSnapshotData"
    ) -> "InterviewContext":
        """
        关键点恢复 - 只保留关键进度信息

        从关键点重新开始面试，不恢复详细上下文
        """
        InterviewContext, _, _, _, _ = _get_state_classes()

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

    async def save_checkpoint(self, snapshot: "ContextSnapshotData") -> None:
        """
        保存快照到 PostgreSQL（容灾）

        Args:
            snapshot: 压缩摘要
        """
        ContextSnapshot = _get_context_snapshot_class()
        get_db_session = _get_db_session()

        async for session in get_db_session():
            db_snapshot = ContextSnapshot(
                session_id=snapshot.session_id,
                version=snapshot.version,
                timestamp=snapshot.timestamp,
                compressed_summary=_dataclass_to_dict(snapshot),
            )
            session.add(db_snapshot)
            logger.info(
                f"ContextCatch: saved checkpoint for session {snapshot.session_id}, version {snapshot.version}"
            )
            break

    async def load_from_pg(self, session_id: str) -> Optional["ContextSnapshotData"]:
        """
        从 PostgreSQL 加载最新快照（Redis 失效时重建）

        Args:
            session_id: 会话ID

        Returns:
            ContextSnapshotData 或 None
        """
        InterviewContext, ProgressSnapshot, EvaluationSnapshot, InsightSummary, ContextSnapshotData = _get_state_classes()
        ContextSnapshot = _get_context_snapshot_class()
        get_db_session = _get_db_session()

        async for session in get_db_session():
            # 查询最新版本
            stmt = (
                ContextSnapshot.__table__.select()
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
