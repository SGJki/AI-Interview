# AI-Interview Project

## 项目概述

基于 LangGraph + LangChain 的 AI 模拟面试官 Agent。

## 技术栈

- **Agent 框架**: LangGraph + LangChain 混合
- **大模型**: 智谱 GLM (ChatGLM)
- **向量数据库**: PostgreSQL + pgvector
- **缓存**: Redis
- **API 框架**: FastAPI

## 开发指南

### Python 脚本执行

使用 `uv run` 执行 Python 脚本（项目使用 UV 虚拟环境）：
首先激活uv虚拟环境：
```bash

.venv\Scripts\activate
```
然后使用uv运行python脚本

```bash

uv run python main.py
uv run pytest tests/
```

### 测试

```bash
uv run pytest tests/ -v
```

## 项目结构

```
ai-interview/
├── main.py              # 入口文件
├── tests/               # 测试目录
├── src/                 # 源代码目录
└── docs/                # 文档目录
```
