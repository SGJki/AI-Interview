---
name: 引导反馈
description: 一般偏差时的引导反馈
version: 1.0.0
agent: feedback
triggers:
  - condition: "0.3 <= state.deviation_score < 0.6"
---

# 引导反馈

## 触发条件

当 `0.3 <= deviation_score < 0.6` 时触发引导反馈。

## 反馈目标

1. 肯定正确的方向
2. 指出不足之处
3. 提供补充性提示
4. 引导深入回答

## 引导模板

### 结构

```
1. 肯定部分 (建立信心)
2. 补充提示 (引导思考)
3. 具体问题 (指向更完整的回答)
```

### 示例

```
"你的回答方向是对的，特别是对微服务架构的理解很准确。

不过在缓存策略这块可以更深入一些。比如：

- 缓存雪崩如何处理？
- 过期策略是定时还是惰性？
- 命中率如何监控？

能补充一下你项目中缓存的具体实现吗？"
```

## 引导方向

| 偏差类型 | 引导方向 |
|---------|---------|
| 不完整 | "能详细说说...？" |
| 太笼统 | "能具体举例吗？" |
| 缺深度 | "背后的原理是什么？" |
| 缺实践 | "在项目中如何应用的？" |

## 引导问题生成

```python
def generate_guidance_question(
    question: str,
    answer: str,
    missing_topics: list[str]
) -> str:
    """生成引导性问题"""
    if "implementation" in missing_topics:
        return f"你提到{answer}，能详细说说具体实现吗？"
    if "principle" in missing_topics:
        return f"这很有效，能解释一下背后的原理吗？"
    if "example" in missing_topics:
        return f"能举个项目中的具体例子吗？"
    return "能再详细一点吗？"
```

## 与追问的区别

- **引导反馈**: 针对当前回答的补充提示
- **追问**: 基于当前回答深入探索新方向
