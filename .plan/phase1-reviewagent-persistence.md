# Phase 1: ReviewAgent LLM判断 + 结束持久化

**Problem solved**: 实现 ReviewAgent 的 LLM 判断功能，完善面试结束时的持久化流程

## Goal

1. **ReviewAgent LLM 判断**：实现 `_check_evaluation_based_on_qa` 和 `_check_standard_answer_fit` 的 LLM 调用和语义相似度检查
2. **结束持久化**：新增 `end_interview_node`，在面试结束时写入 PostgreSQL 并清理 Redis

## Architecture

### Memory Layer (不变)

| Layer | Storage | Purpose |
|-------|---------|---------|
| Short-term | LangGraph State | Current question, followup chain |
| Short-mid-term | Redis | Session Q&A, pending feedbacks (interview结束后清理) |
| Long-term | PostgreSQL + pgvector | Q&A history, RAG knowledge |

### Orchestrator Flow (更新后)

```
init → orchestrator → decide_next
                        ↓
              ┌── question_agent ──→ evaluate_agent ──→ review_agent ──→ feedback_agent
              ↓
         final_feedback → end_interview_node → END
```

## Implementation Steps

- [ ] **Step 1**: 创建 `src/agent/prompts.py`，包含 ReviewAgent 使用的 prompt 模板
- [ ] **Step 2**: 更新 `review_agent.py`，实现 `_check_evaluation_based_on_qa` 使用 LLM 判断
- [ ] **Step 3**: 更新 `review_agent.py`，实现 `_check_standard_answer_fit` 使用语义相似度
- [ ] **Step 4**: 更新 `orchestrator.py`，添加 `end_interview_node` 节点
- [ ] **Step 5**: 更新 `decide_next` 路由，添加 `end_interview` 条件
- [ ] **Step 6**: 添加测试
- [ ] **Step 7**: 运行完整测试套件验证

## Files

### 新建

| File | Description |
|------|-------------|
| `src/agent/prompts.py` | Agent Prompt 模板统一管理 |

### 修改

| File | Description |
|------|-------------|
| `src/agent/review_agent.py` | 实现 LLM 判断逻辑 |
| `src/agent/orchestrator.py` | 添加 end_interview_node |
| `tests/test_review_agent.py` | 添加 LLM 相关测试 |

## Prompt Templates (prompts.py)

```python
# ReviewAgent
REVIEW_EVALUATION_BASED_ON_QA = """判断以下评估是否基于实际的问答内容：
问题: {question}
回答: {user_answer}
评估: {evaluation}
评估是否基于问答内容而非外部信息？只回答 YES 或 NO。"""

REVIEW_STANDARD_ANSWER_FIT = """判断以下标准答案是否与问题相关：
问题: {question}
标准答案: {standard_answer}
标准答案是否适合作为该问题的参考？只回答 YES 或 NO。"""
```

## API Changes

### orchestrator.py

```python
async def end_interview_node(state: InterviewState) -> dict:
    """结束面试：写入 PostgreSQL + 清理 Redis"""
    from src.tools.memory_tools import clear_session_memory
    from src.dao.interview_dao import InterviewDAO

    # 1. 写入 PostgreSQL
    session_record = {
        "session_id": state.session_id,
        "resume_id": state.resume_id,
        "answers": state.answers,
        "feedbacks": state.feedbacks,
        "evaluation_results": state.evaluation_results,
    }
    await InterviewDAO.save_session(session_record)

    # 2. 清理 Redis
    await clear_session_memory(state.session_id)

    return {"phase": "completed"}
```

## Testing

- [ ] `test_review_llm_judgment` - 测试 LLM 判断逻辑
- [ ] `test_review_similarity_check` - 测试语义相似度检查
- [ ] `test_end_interview_persistence` - 测试结束持久化
- [ ] `test_orchestrator_end_flow` - 测试完整流程

## Notes

- ReviewAgent 的两个 checker 函数从同步改为异步，以支持 LLM 调用
- 持久化仅在面试结束时执行，不在过程中增量持久化（符合三层记忆设计）
- Redis 清理在 PostgreSQL 写入成功后执行
