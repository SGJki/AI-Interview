---
name: 错误处理规范
description: Agent 错误处理的标准模式
version: 1.0.0
agent: common
triggers:
  - condition: "exception raised in agent"
---

# 错误处理规范

## 错误分类

### 1. 可恢复错误 (Recoverable)
- LLM 调用超时/失败
- 临时网络问题
- 限流 (RATE_LIMIT)

**处理方式**: 重试 + fallback

### 2. 业务错误 (Business)
- 无效的 state 参数
- 缺失必要字段
- 业务规则校验失败

**处理方式**: 返回错误信息，不重试

### 3. 严重错误 (Critical)
- 数据库连接失败
- 认证失败
- 系统配置错误

**处理方式**: 记录日志，上报到 orchestrator 决定是否终止

## 错误处理模式

```python
async def agent_operation(state: InterviewState) -> dict:
    try:
        result = await do_operation(state)
        return {"success": True, "data": result}
    except RecoverableError as e:
        logger.warning(f"Recoverable error: {e}")
        return await retry_with_fallback(state)
    except BusinessError as e:
        logger.info(f"Business error: {e}")
        return {"success": False, "error": str(e)}
    except CriticalError as e:
        logger.error(f"Critical error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"success": False, "error": "INTERNAL_ERROR"}
```

## Fallback 策略

| Agent | Fallback 行为 |
|-------|--------------|
| question_agent | 返回通用问题 "请介绍一下你自己" |
| evaluate_agent | 返回 deviation_score=0.5, is_correct=True |
| feedback_agent | 返回通用反馈 "感谢回答" |
| review_agent | 标记 review 为 passed，允许继续 |

## 错误状态传播

错误通过 state.error_count 累积：
- error_count >= config.error_threshold 时终止面试
- 严重错误立即终止当前 Agent 执行
