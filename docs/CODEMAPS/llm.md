# LLM Integration Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/llm/`

## Components

| Component | File | Purpose |
|-----------|------|---------|
| `LLMClient` | `client.py` | LLM API client wrapper |
| `Prompts` | `prompts.py` | All prompt templates |

## LLM Client (`src/llm/client.py`)

| Class/Function | Purpose |
|----------------|---------|
| `LLMClient` | Main client for LLM API calls |
| `get_llm_client()` | Factory function for client |
| `ChatGLMClient` | ChatGLM-specific implementation |

## Prompts (`src/llm/prompts.py`)

Contains all system prompts and templates:

| Category | Purpose |
|----------|---------|
| `resume_parsing_prompt` | Parse resume text to structured data |
| `question_generation_prompt` | Generate interview questions |
| `answer_evaluation_prompt` | Evaluate user answers |
| `feedback_generation_prompt` | Generate feedback content |
| `responsibility_extraction_prompt` | Extract responsibilities from projects |

## Configuration

LLM settings in `config.toml`:

```toml
[tool.ai-interview.llm]
api_key = "your_api_key"
base_url = "https://xplt.sdu.edu.cn:4000"
model = "Ali-dashscope/Qwen3-Max"
max_tokens = 2048
temperature = 0.7

[tool.ai-interview.embedding]
api_key = "your_embedding_key"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "text-embedding-v3"
```

## Data Flow

```
Agent Request
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM Client                               │
│                                                                 │
│  1. Format prompt with context                                │
│  2. Call LLM API (dashscope/Qwen)                           │
│  3. Parse response                                            │
│  4. Return structured result                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

## Supported Models

| Model | Provider | Use Case |
|-------|----------|----------|
| `Ali-dashscope/Qwen3-Max` | DashScope | Main reasoning |
| `text-embedding-v3` | DashScope | Embeddings |

## Related Areas

- [Agent Architecture](../agents/) - Uses LLM for reasoning
- [Services](../services/) - Uses LLM for interview logic
