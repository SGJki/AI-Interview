# RAG Tools Codemap

**Last Updated:** 2026-04-08
**Entry Point:** `src/tools/`

## Tool Components

| Tool | File | Purpose |
|------|------|---------|
| `RAGTools` | `rag_tools.py` | Core RAG retrieval operations |
| `RAGEnhancements` | `rag_enhancements.py` | Advanced retrieval strategies |
| `EnterpriseKnowledge` | `enterprise_knowledge.py` | Enterprise-level knowledge retrieval |
| `MemoryTools` | `memory_tools.py` | Session state management |
| `CodeTools` | `code_tools.py` | Source code parsing |

## RAG Tools (`src/tools/rag_tools.py`)

| Tool | Purpose |
|------|---------|
| `KnowledgeRetriever` | Core knowledge retrieval |
| `SimilarQuestionRetriever` | Find similar past questions |
| `StandardAnswerRetriever` | Retrieve standard answers |

## RAG Enhancements (`src/tools/rag_enhancements.py`)

| Enhancement | Purpose |
|-------------|---------|
| `MultiVectorRetriever` | Multiple vector strategies |
| `HybridRetriever` | Combine dense + sparse retrieval |
| `Reranker` | Re-rank retrieved results |

### Fusion Algorithms

| Algorithm | Description |
|-----------|-------------|
| **RRF** | Reciprocal Rank Fusion |
| **DRR** | Distribution-Based Rank Fusion |
| **SBERT** | Sentence BERT Cross-Encoder |

## Memory Tools (`src/tools/memory_tools.py`)

| Tool | Purpose |
|------|---------|
| `SessionStateManager` | Redis-based session state |
| `SessionHealthMonitor` | Monitor session health |

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Three-Tier Memory                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Long-Term Memory (pgvector)                │   │
│  │  - Resume content                                        │   │
│  │  - Skills, projects, responsibilities                   │   │
│  │  - Standard answers                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           ▲                                    │
│                           │ Write                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Medium-Term Memory (Redis)                 │   │
│  │  - interview:{session_id}:state                         │   │
│  │  - Full Q&A history                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           ▲                                    │
│                           │ Merge Write                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Short-Term Memory (LangGraph State)         │   │
│  │  - Current question chain                               │   │
│  │  - Followup depth                                       │   │
│  │  - Guidance flags                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

## Related Areas

- [Services](../services/) - Uses RAG tools
- [Database](./database.md) - Vector storage
