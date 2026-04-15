---
name: 重试策略
description: LLM 调用失败时的重试机制
version: 1.0.0
agent: common
triggers:
  - condition: "error in ['LLM_ERROR', 'NETWORK_ERROR', 'TIMEOUT']"
---

# 重试策略

## 核心原则

当 LLM 调用失败时，采用指数退避策略进行重试，避免雪崩效应。

## 重试配置

| 参数 | 值 | 说明 |
|------|-----|------|
| 最大重试次数 | 3 | 超过后放弃 |
| 初始延迟 | 1s | 第一次重试等待时间 |
| 退避倍数 | 2 | 指数退避倍数 |
| 最大延迟 | 10s | 单次重试最大等待 |

## 重试流程

```
调用 LLM
    ↓
失败？
    ↓ 是
重试次数 < 3？
    ↓ 是
等待 delay = min(initial_delay * (2 ^ retry_count), max_delay)
    ↓
重试
    ↓
失败
    ↓
retry_count++
    ↓
返回 fallback 结果
```

## 适用错误类型

- `LLM_ERROR`: LLM 服务内部错误
- `NETWORK_ERROR`: 网络连接失败
- `TIMEOUT`: 请求超时
- `RATE_LIMIT`: 限流错误

## 降级处理

重试耗尽后使用 fallback 返回默认响应，确保面试流程不中断。

## 注意事项

1. 不要对业务逻辑错误（如参数错误）进行重试
2. 重试之间要有退避，避免加剧服务器负载
3. 记录重试次数和原因，便于后续分析
