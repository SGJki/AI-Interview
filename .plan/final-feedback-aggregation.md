# Final Feedback Aggregation Plan

**Problem solved**: 实现 `OrchestratorAdapter.end_interview()` 中的最终反馈聚合逻辑，替代硬编码的占位数据。

## Goal

在面试结束时，根据整个面试过程的评估结果、答案质量、反馈记录，生成有意义的综合反馈。

## Current State

```python
# src/services/orchestrator_adapter.py:194-201
# TODO: 生成最终反馈 (需要 aggregation 逻辑)
final_feedback = {
    "overall_score": 0.8,  # 占位
    "series_scores": {i: 0.8 for i in range(1, total_series + 1)},
    "strengths": ["表达清晰", "技术深度好"],
    "weaknesses": ["可以更详细"],
    "suggestions": ["多练习系统设计"],
}
```

## Data Sources

可用的状态数据：
- `state.answers`: Dict[str, Answer] - 所有回答记录
- `state.evaluation_results`: Dict[str, dict] - 评估结果（含 similarity_score, llm_score, is_correct）
- `state.feedbacks`: Dict[str, Feedback] - 所有反馈
- `state.series_history`: Dict[int, SeriesRecord] - 系列历史

## Implementation Steps

- [ ] **Step 1**: 分析评估结果数据结构
  - 查看 `evaluation_results` 中每个条目的字段
  - 确认 similarity_score, llm_score, is_correct 的范围

- [ ] **Step 2**: 实现 `aggregate_series_score(series_evaluations)` 
  - 计算单个系列的平均分数
  - 输入: List[dict] - 该系列所有问题的评估结果
  - 输出: float - 系列平均分 (0-1)

- [ ] **Step 3**: 实现 `aggregate_overall_score(series_scores)`
  - 综合所有系列的分数计算总评分
  - 考虑权重：后期系列可能更重要

- [ ] **Step 4**: 实现 `extract_strengths(evaluations, feedbacks)` 
  - 从评估结果和反馈中提取优点
  - 基于高评分答案的特征

- [ ] **Step 5**: 实现 `extract_weaknesses(evaluations, feedbacks)`
  - 从评估结果和反馈中提取不足
  - 基于低评分答案和错误答案

- [ ] **Step 6**: 实现 `generate_suggestions(weaknesses)`
  - 根据不足之处生成改进建议
  - 建议应该具体、可操作

- [ ] **Step 7**: 集成到 `end_interview()` 方法
  - 替换硬编码的 final_feedback
  - 保留 fallback 逻辑（数据不足时）

- [ ] **Step 8**: 添加最终反馈 aggregation 单元测试
  - 测试各 aggregation 函数
  - 测试边界情况（无评估结果等）

- [ ] **Step 9**: 为 `validate_cache_with_llm` 添加测试
  - 单元测试：mock LLM 响应，验证 cached_tokens 提取逻辑
  - 测试场景：cached_tokens > 0、cached_tokens = 0、异常处理
