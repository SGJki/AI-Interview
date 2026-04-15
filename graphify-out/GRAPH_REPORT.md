# Graph Report - .  (2026-04-14)

## Corpus Check
- 172 files · ~101,787 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3136 nodes · 12453 edges · 72 communities detected
- Extraction: 26% EXTRACTED · 74% INFERRED · 0% AMBIGUOUS · INFERRED: 9172 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Interview Service & LLM|Interview Service & LLM]]
- [[_COMMUNITY_Database Management|Database Management]]
- [[_COMMUNITY_Resume Extraction|Resume Extraction]]
- [[_COMMUNITY_FastAPI Routers|FastAPI Routers]]
- [[_COMMUNITY_Agent State Management|Agent State Management]]
- [[_COMMUNITY_Context Snapshot Engine|Context Snapshot Engine]]
- [[_COMMUNITY_LLM Client|LLM Client]]
- [[_COMMUNITY_RAG Fusion Algorithms|RAG Fusion Algorithms]]
- [[_COMMUNITY_Knowledge Base Service|Knowledge Base Service]]
- [[_COMMUNITY_Architecture Detection|Architecture Detection]]
- [[_COMMUNITY_Config Validation|Config Validation]]
- [[_COMMUNITY_Redis State Management|Redis State Management]]
- [[_COMMUNITY_Enterprise Knowledge Retrieval|Enterprise Knowledge Retrieval]]
- [[_COMMUNITY_Config Loading|Config Loading]]
- [[_COMMUNITY_Interview Service Tests|Interview Service Tests]]
- [[_COMMUNITY_Agent Core (Voting, Base Classes)|Agent Core (Voting, Base Classes)]]
- [[_COMMUNITY_Graceful Shutdown|Graceful Shutdown]]
- [[_COMMUNITY_Orchestrator Tests|Orchestrator Tests]]
- [[_COMMUNITY_Orchestrator Adapter|Orchestrator Adapter]]
- [[_COMMUNITY_Knowledge Agent Tests|Knowledge Agent Tests]]
- [[_COMMUNITY_Integration Tests|Integration Tests]]
- [[_COMMUNITY_Skill Loader|Skill Loader]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_Resume Agent Tests|Resume Agent Tests]]
- [[_COMMUNITY_API Entry Points|API Entry Points]]
- [[_COMMUNITY_Interview Context Tests|Interview Context Tests]]
- [[_COMMUNITY_Interview Service Creation Tests|Interview Service Creation Tests]]
- [[_COMMUNITY_Recorded Mode Tests|Recorded Mode Tests]]
- [[_COMMUNITY_Feedback Generation Tests|Feedback Generation Tests]]
- [[_COMMUNITY_Orchestrator Graph Nodes|Orchestrator Graph Nodes]]
- [[_COMMUNITY_Streaming Infrastructure|Streaming Infrastructure]]
- [[_COMMUNITY_Review Evaluation Tests|Review Evaluation Tests]]
- [[_COMMUNITY_Question Pre-generation Tests|Question Pre-generation Tests]]
- [[_COMMUNITY_FeedBack Agent Graph|FeedBack Agent Graph]]
- [[_COMMUNITY_Question Agent Graph|Question Agent Graph]]
- [[_COMMUNITY_Redis Session Memory|Redis Session Memory]]
- [[_COMMUNITY_Embedding Service|Embedding Service]]
- [[_COMMUNITY_Review Agent Graph|Review Agent Graph]]
- [[_COMMUNITY_FastAPI App & Health Checks|FastAPI App & Health Checks]]
- [[_COMMUNITY_Resume Parser Error Handling|Resume Parser Error Handling]]
- [[_COMMUNITY_Coverage HTML|Coverage HTML]]
- [[_COMMUNITY_Knowledge Agent Graph|Knowledge Agent Graph]]
- [[_COMMUNITY_Fallback QuestionsFeedback|Fallback Questions/Feedback]]
- [[_COMMUNITY_Question Generation Tests|Question Generation Tests]]
- [[_COMMUNITY_Responsibility Service|Responsibility Service]]
- [[_COMMUNITY_Feedback Agent Tests|Feedback Agent Tests]]
- [[_COMMUNITY_Fallback Response|Fallback Response]]
- [[_COMMUNITY_Evaluate Agent Tests|Evaluate Agent Tests]]
- [[_COMMUNITY_Retry Decorator Tests|Retry Decorator Tests]]
- [[_COMMUNITY_RAG Tools|RAG Tools]]
- [[_COMMUNITY_Prompt Templates|Prompt Templates]]
- [[_COMMUNITY_Async Retry Decorator|Async Retry Decorator]]
- [[_COMMUNITY_Hybrid RAG Fusion|Hybrid RAG Fusion]]
- [[_COMMUNITY_main entry|main entry]]
- [[_COMMUNITY_test_api|test_api]]
- [[_COMMUNITY_test_interview_flow|test_interview_flow]]
- [[_COMMUNITY_test_resume_interview|test_resume_interview]]
- [[_COMMUNITY_LLM Usage dataclasses|LLM Usage dataclasses]]
- [[_COMMUNITY_MultiVector Retriever|MultiVector Retriever]]
- [[_COMMUNITY_Vector Store doc count|Vector Store doc count]]
- [[_COMMUNITY_Enterprise knowledge tool|Enterprise knowledge tool]]
- [[_COMMUNITY_Enterprise knowledge tool instance|Enterprise knowledge tool instance]]
- [[_COMMUNITY_Pregeneration TTL test|Pregeneration TTL test]]
- [[_COMMUNITY_resume_agent_graph|resume_agent_graph]]
- [[_COMMUNITY_knowledge_agent_graph|knowledge_agent_graph]]
- [[_COMMUNITY_question_agent_graph|question_agent_graph]]
- [[_COMMUNITY_evaluate_agent_graph|evaluate_agent_graph]]
- [[_COMMUNITY_feedback_agent_graph|feedback_agent_graph]]
- [[_COMMUNITY_Reranker|Reranker]]
- [[_COMMUNITY_EnterpriseKnowledge|EnterpriseKnowledge]]
- [[_COMMUNITY_ContextAwareSkillLoader|ContextAwareSkillLoader]]
- [[_COMMUNITY_main.py singleton|main.py singleton]]

## God Nodes (most connected - your core abstractions)
1. `InterviewState` - 650 edges
2. `Question` - 605 edges
3. `QuestionType` - 598 edges
4. `InterviewMode` - 529 edges
5. `Answer` - 525 edges
6. `FeedbackMode` - 503 edges
7. `InterviewService` - 419 edges
8. `InterviewContext` - 412 edges
9. `Feedback` - 364 edges
10. `FeedbackType` - 339 edges

## Surprising Connections (you probably didn't know these)
- `Multi-Agent Architecture` --rationale_for--> `orchestrator_graph`  [INFERRED]
  docs/CODEMAPS/agents.md → src/agent/orchestrator.py
- `Review Mechanism (3-instance voting)` --rationale_for--> `ReviewVoter`  [INFERRED]
  docs/CODEMAPS/agents.md → src/agent/base.py
- `AI Interview Agent - Tools Package  LangChain 工具链实现` --uses--> `SimilarQuestionRetriever`  [INFERRED]
  src\tools\__init__.py → src\tools\rag_tools.py
- `AI Interview Agent - Tools Package  LangChain 工具链实现` --uses--> `StandardAnswerRetriever`  [INFERRED]
  src\tools\__init__.py → src\tools\rag_tools.py
- `Tests for KnowledgeAgent - Knowledge base and responsibility management subgraph` --uses--> `InterviewState`  [INFERRED]
  tests\test_knowledge_agent.py → src\agent\state.py

## Hyperedges (group relationships)
- **Multi-Agent System with 3-Instance Voting** — orchestrator_graph, resume_agent, knowledge_agent, question_agent, evaluate_agent, feedback_agent, review_voter [EXTRACTED 1.00]
- **Session Recovery System** — context_catch_engine, prompt_cache, recovery_manager, context_snapshot, llm_usage [EXTRACTED 1.00]
- **Three-Tier Memory Architecture** — interview_state, session_state_manager, redis, postgresql_pgvector [EXTRACTED 1.00]
- **RAG Fusion Algorithms** — rrf_algorithm, drr_algorithm, sbert_algorithm, multi_vector_retriever, hybrid_retriever [EXTRACTED 1.00]
- **Skill Loading System** — skill_loader, skill_aware_prompt, skill_context, resume_agent, question_agent, evaluate_agent, feedback_agent [EXTRACTED 1.00]
- **LLM Usage Tracking** — llm_client, invoke_llm_with_usage, llm_response, llm_usage, prompt_tokens_details [EXTRACTED 1.00]
- **Context Snapshot Data Classes** — context_snapshot_data, progress_snapshot, evaluation_snapshot, insight_summary, context_snapshot [EXTRACTED 1.00]
- **Graceful Shutdown System** — graceful_shutdown, connection_tracker, sse_streaming, redis, postgresql_pgvector [EXTRACTED 1.00]
- **Database and DAO Layer** — user_model, resume_model, project_model, knowledge_base_model, interview_session_model, qa_history_model, interview_feedback_model, user_dao, resume_dao, project_dao, knowledge_base_dao, interview_session_dao, qa_history_dao, interview_feedback_dao [EXTRACTED 1.00]
- **Agent State Enums** — interview_mode, feedback_mode, feedback_type, question_type, followup_strategy, agent_phase [EXTRACTED 1.00]
- **Evaluation Flow** — interviewstate, question_agent, evaluate_agent, review_agent, feedback_agent, orchestrator_agent, deviation_score [EXTRACTED 1.00]
- **Question Generation Flow** — question_agent, responsibilities_tuple, star_framework, question_deduplication, followup_decision, warmup_question, initial_question, followup_question [EXTRACTED 1.00]
- **Resume Parse Flow** — resume_agent, resume_parsing, llm_extract_resume_info, responsibility_extraction, knowledge_base, vector_storage [EXTRACTED 1.00]
- **Voting Mechanism** — review_agent, three_voter_mechanism, voter_0_llm_judgment, voter_1_reasonability, voter_2_standard_answer, evaluation_results [EXTRACTED 1.00]
- **Feedback Type Routing** — deviation_score, correction_feedback, guidance_feedback, comment_feedback, feedback_agent [EXTRACTED 1.00]
- **Deduplication Layers** — question_deduplication, exact_match_dedup, semantic_similarity_dedup, topic_match_dedup, asked_logical_questions, asked_topics, variant_question_generation [EXTRACTED 1.00]
- **Scoring Dimensions** — scoring_method, technical_accuracy, completeness_dimension, depth_dimension, expression_clarity [EXTRACTED 1.00]
- **Dual Storage** — dual_storage_strategy, chroma_vectorstore, pgvector_storage, knowledge_base [EXTRACTED 1.00]
- **Session Management** — session_lifecycle, session_status, postgres_persistence, redis_cleanup, phase_flow, termination_conditions [EXTRACTED 1.00]
- **Error Handling Hierarchy** — error_handling_patterns, recoverable_error, business_error, critical_error, fallback_strategy, error_count, error_threshold [EXTRACTED 1.00]

## Communities

### Community 0 - "Interview Service & LLM"
Cohesion: 0.02
Nodes (495): InterviewService, LLM Service for AI Interview Agent  提供面试相关任务的 LLM 服务：问题生成、回答评估、反馈生成、追问生成, 生成面试问题（流式）          Args:             series_num: 系列编号             question_, 评估用户回答          Args:             question: 问题内容             user_answer: 用户, 生成反馈          Args:             question: 问题内容             user_answer: 用户回答, 面试 LLM 服务      封装所有面试相关的 LLM 调用, 生成追问          Args:             original_question: 原始问题             user_ans, 生成追问（流式）          Args:             original_question: 原始问题             user (+487 more)

### Community 1 - "Database Management"
Cohesion: 0.02
Nodes (244): close_database_manager(), DatabaseManager, get_database_manager(), get_db_session(), PostgreSQL Database Manager - Async SQLAlchemy Engine with Connection Pool, Drop all tables (for testing)., Get the underlying SQLAlchemy async engine., Get default database manager instance. (+236 more)

### Community 2 - "Resume Extraction"
Cohesion: 0.03
Nodes (120): Enum, IntEnum, _categorize_skills(), EducationInfo, _extract_education(), _extract_projects(), _extract_responsibilities(), _extract_skills_from_text() (+112 more)

### Community 3 - "FastAPI Routers"
Cohesion: 0.04
Nodes (153): interview_router, knowledge_router, training_router, BaseModel, FastAPI, _create_service_from_request(), create_snapshot(), end_interview() (+145 more)

### Community 4 - "Agent State Management"
Cohesion: 0.02
Nodes (157): AgentPhase Enum, AgentResult, AI-Interview Project, All Responsibilities Used Flag, Answers Dictionary, Asked Logical Questions Set, Asked Topics Set, BusinessError (+149 more)

### Community 5 - "Context Snapshot Engine"
Cohesion: 0.04
Nodes (83): ContextCatchEngine, _dataclass_to_dict(), _get_context_snapshot_class(), _get_db_session(), _get_redis_client(), _get_state_classes(), Context Catch - 面试会话压缩/恢复引擎  职责： - compress(): 生成压缩摘要（规则提取 + LLM） - restore(): 恢, Context Catch 快照 Redis key (+75 more)

### Community 6 - "LLM Client"
Cohesion: 0.04
Nodes (63): get_chat_model(), get_llm_client(), invoke_llm(), invoke_llm_stream(), invoke_llm_with_history(), invoke_llm_with_usage(), _process_llm_response_content(), LLM Client for AI Interview Agent  基于 LangChain 的 ChatOpenAI 客户端，支持 OpenAI 兼容 (+55 more)

### Community 7 - "RAG Fusion Algorithms"
Cohesion: 0.05
Nodes (62): _drr_fusion(), fusion_results(), FusionType, HybridRetriever, MultiVectorRetriever, RAG Enhancement Tools for AI Interview Agent  Advanced retrieval strategies in, Multi-vector store retriever supporting fusion retrieval      Allows querying, Initialize MultiVectorRetriever          Args:             vectorstores: List (+54 more)

### Community 8 - "Knowledge Base Service"
Cohesion: 0.03
Nodes (55): KnowledgeBaseService, Knowledge Base Service for AI Interview Agent  提供知识库的构建和管理功能, 构建预设面试题库          常见面试问题按技能分类          Returns:             构建结果, 构建标准回答知识库          为常见问题添加标准回答          Returns:             构建结果, 知识库服务      提供知识库构建、文档管理等功能, 构建技能点知识库          Args:             skill_points: 技能点列表          Returns:, 添加单个文档到知识库          Args:             content: 文档内容             metadata: 元数, 初始化知识库服务          Args:             persist_directory: 向量数据库持久化路径 (+47 more)

### Community 9 - "Architecture Detection"
Cohesion: 0.06
Nodes (53): ArchitectureInfo, _detect_language(), _detect_tech_stack(), extract_architecture(), _extract_classes(), _extract_components(), _extract_data_flow(), _extract_dependencies() (+45 more)

### Community 10 - "Config Validation"
Cohesion: 0.05
Nodes (47): DatabaseConfig, EmbeddingConfig, _expand_env_vars(), get_config(), get_database_config(), get_embedding_config(), get_interview_config(), get_llm_config() (+39 more)

### Community 11 - "Redis State Management"
Cohesion: 0.04
Nodes (33): Redis client for interview state management., Push pre-generated question to queue., Pop next question from queue., Save review information based on is_production config., Publish a message to a channel., Subscribe to a channel and return a PubSub object., RedisClient, Tests for Redis Client - Interview State Management (+25 more)

### Community 12 - "Enterprise Knowledge Retrieval"
Cohesion: 0.06
Nodes (38): as_tool(), EnterpriseKnowledgeRetriever, EnterpriseKnowledgeRetrieverTool, invoke(), KnowledgeFusionResult, Enterprise Knowledge Retrieval - Phase 3  Dynamic retrieval of enterprise-leve, Search web for latest technical best practices      Uses web search to supplem, Dynamically retrieve enterprise-level technical best practices      This funct (+30 more)

### Community 13 - "Config Loading"
Cohesion: 0.06
Nodes (34): EmbeddingConfig, _expand_env_vars(), get_embedding_config(), get_llm_config(), LLMConfig, _load_config(), _process_config(), Expand environment variables in ${VAR_NAME} format (+26 more)

### Community 14 - "Interview Service Tests"
Cohesion: 0.07
Nodes (28): _make_mock_state(), _make_realtime_service(), _make_recorded_service(), test_end_interview_clears_pending_feedbacks(), test_end_interview_returns_summary(), test_error_count_resets_on_correct_answer(), test_evaluate_answer_returns_deviation_and_correctness(), test_generate_followup_updates_state() (+20 more)

### Community 15 - "Agent Core (Voting, Base Classes)"
Cohesion: 0.09
Nodes (33): AgentPhase, AgentResult, create_review_voters(), Base classes for all agents., Agent execution phase., Result from agent execution., 3-instance voting mechanism for reviews., Run voting and return (passed, failures).         At least 2 votes needed to pas (+25 more)

### Community 16 - "Graceful Shutdown"
Cohesion: 0.07
Nodes (29): ConnectionTracker, get_connection_tracker(), 优雅关闭管理器 - 连接追踪与排空机制  功能: - 追踪活跃的 SSE 连接 - 支持连接排空（drain）实现优雅关闭 - 提供 readiness 健康检, SSE 连接上下文管理器      用法:         async with SSEConnection(connection_id, metadata), SSE 连接追踪依赖      用法:         @app.get("/stream")         async def stream(request, 服务器生命周期管理器      实现:     1. 启动时: 初始化数据库、Redis 等资源     2. 运行中: 追踪活跃连接     3. 关闭时:, 连接追踪器 - 追踪活跃的 SSE/长连接      用于优雅关闭时等待所有活跃请求完成, 等待所有活跃连接完成（排空）          Args:             timeout: 最大等待时间（秒）          Returns: (+21 more)

### Community 17 - "Orchestrator Tests"
Cohesion: 0.05
Nodes (23): Tests for Orchestrator - Main entry point that composes all agent subgraphs, Test decide_next_node routing logic, Test that all agent graphs can be imported, Test resume_agent_graph can be imported, Test knowledge_agent_graph can be imported, Test question_agent_graph can be imported, Test evaluate_agent_graph can be imported, Test feedback_agent_graph can be imported (+15 more)

### Community 18 - "Orchestrator Adapter"
Cohesion: 0.09
Nodes (24): OrchestratorAdapter, QAResponse, # TODO: 生成最终反馈 (需要 aggregation 逻辑), Tests for OrchestratorAdapter, Test that start_interview updates adapter state, Test OrchestratorAdapter class, Test adapter submit_answer method, Test that submit_answer raises if interview not started (+16 more)

### Community 19 - "Knowledge Agent Tests"
Cohesion: 0.06
Nodes (20): Tests for KnowledgeAgent - Knowledge base and responsibility management subgraph, Test KnowledgeAgent function signatures, Test that shuffle_responsibilities is an async function, Test that store_to_vector_db is an async function, Test that fetch_responsibility is an async function, Test that find_standard_answer is an async function, Test shuffle_responsibilities function signature, Test store_to_vector_db function signature (+12 more)

### Community 20 - "Integration Tests"
Cohesion: 0.06
Nodes (20): Integration tests for agent orchestration., Test the full flow from question generation to feedback., Integration tests for ReviewAgent with orchestrator., Test review_agent_graph can be imported., Test review_agent_graph has review_evaluation node., Integration tests for the orchestrator graph., Test that all agent graphs can be imported through orchestrator., Test all agent graphs can be imported. (+12 more)

### Community 21 - "Skill Loader"
Cohesion: 0.09
Nodes (14): ContextAwareSkillLoader, get_skill_loader(), Context-Aware Skill Loader for AI Interview Agents  按上下文动态加载 Skill，支持 phase/acti, 解析 Skill 内容和 frontmatter, 将匹配的 Skills 注入到 prompt, 获取所有 Skills 或指定 Agent 的 Skills, 为 Agent 生成带 Skills 的增强 prompt      用法:         prompt = skill_aware_prompt(, Agent Skill 上下文管理器      用法:         with SkillContext("question", state) as ctx: (+6 more)

### Community 22 - "Test Fixtures"
Cohesion: 0.08
Nodes (4): async_iter(), AsyncIteratorMock, mock_redis(), test_get_active_session_count()

### Community 23 - "Resume Agent Tests"
Cohesion: 0.08
Nodes (16): Tests for ResumeAgent - Resume parsing and storage subgraph, Test ResumeAgent subgraph structure, Test that the compiled graph exists, Test creating a new resume agent graph, Test graph contains the expected nodes, Test graph entry point is set to parse_resume, Test that the graph returned from create_resume_agent_graph is already compiled, Test ResumeAgent function signatures (+8 more)

### Community 24 - "API Entry Points"
Cohesion: 0.14
Nodes (18): checkApiStatus(), displayInterviewQuestion(), displayTrainingQuestion(), endInterview(), endTraining(), getNextQuestion(), getNextTrainingQuestion(), init() (+10 more)

### Community 25 - "Interview Context Tests"
Cohesion: 0.09
Nodes (2): _make_service_with_context(), service()

### Community 26 - "Interview Service Creation Tests"
Cohesion: 0.15
Nodes (15): _make_service(), test_evaluate_answer_uses_knowledge_context(), test_final_feedback_extracts_series_from_question_id(), test_final_feedback_no_pending_feedbacks(), test_final_feedback_with_series_history(), test_generate_feedback_sets_question_id(), test_get_current_question_returns_none_when_no_state(), test_get_current_question_returns_question() (+7 more)

### Community 27 - "Recorded Mode Tests"
Cohesion: 0.11
Nodes (0): 

### Community 28 - "Feedback Generation Tests"
Cohesion: 0.13
Nodes (2): _make_service_with_context(), service()

### Community 29 - "Orchestrator Graph Nodes"
Cohesion: 0.13
Nodes (3): end_interview_node(), Main Orchestrator - LangGraph main entry point., 结束面试：写入 PostgreSQL + 清理 Redis

### Community 30 - "Streaming Infrastructure"
Cohesion: 0.18
Nodes (5): Streaming output handler for AI Interview Agent., 处理流式输出          Args:             session_id: 会话 ID             generator: token, RedisStreamingHandler, StreamingHandler, Tests for streaming module.

### Community 31 - "Review Evaluation Tests"
Cohesion: 0.15
Nodes (1): test_check_evaluation_based_on_qa_llm_true()

### Community 32 - "Question Pre-generation Tests"
Cohesion: 0.15
Nodes (0): 

### Community 33 - "FeedBack Agent Graph"
Cohesion: 0.21
Nodes (9): generate_comment(), generate_correction(), generate_guidance(), get_llm_service(), FeedBackAgent - Feedback generation., 生成评论反馈（dev >= 0.6）      Extracts question, user_answer, and evaluation from stat, Get or create the global LLM service instance., 生成纠正反馈（dev < 0.3）      Extracts question, user_answer, and evaluation from state (+1 more)

### Community 34 - "Question Agent Graph"
Cohesion: 0.26
Nodes (8): generate_followup(), generate_initial(), generate_question_id(), generate_warmup(), get_llm_service(), QuestionAgent - Question generation and deduplication., Get or create the global LLM service instance., Generate a unique question ID.

### Community 35 - "Redis Session Memory"
Cohesion: 0.35
Nodes (11): cache_next_series_question(), clear_session_memory(), get_cached_next_question(), get_redis_client(), get_session_memory(), get_user_current_interview(), redis(), save_to_session_memory() (+3 more)

### Community 36 - "Embedding Service"
Cohesion: 0.25
Nodes (10): compute_similarities(), compute_similarity(), _get_embedding_langchain(), _get_embeddings(), get_text_embedding(), Embedding Service for AI Interview Agent  提供文本嵌入和相似度计算功能, 获取文本的 embedding 向量      Args:         text: 输入文本      Returns:         emb, 使用 LangChain DashScopeEmbeddings 获取嵌入      Args:         texts: 文本列表      R (+2 more)

### Community 37 - "Review Agent Graph"
Cohesion: 0.2
Nodes (5): get_llm_service(), ReviewAgent - Review evaluation results with 3-instance voting., Get or create the global LLM service instance., 审查 EvaluateAgent 的评估结果      Extracts evaluation_result and standard_answer from, review_evaluation()

### Community 38 - "FastAPI App & Health Checks"
Cohesion: 0.22
Nodes (7): health_check(), FastAPI Application Entry Point  AI Interview Agent - FastAPI Server  启动方式:, 启动检查 (Startup) - 用于 Kubernetes startup probe      在启动完成前返回 error，启动完成后返回 ok, 存活检查 (Liveness) - 判断进程是否存活, 就绪检查 (Readiness) - 判断依赖服务是否可用      检查:     - PostgreSQL 数据库连接     - Redis 连接, readiness_check(), startup_check()

### Community 39 - "Resume Parser Error Handling"
Cohesion: 0.28
Nodes (7): evaluate_with_standard(), evaluate_without_standard(), get_llm_service(), EvaluateAgent - Answer evaluation., Get or create the global LLM service instance., 使用标准答案评估用户回答      Extracts question, user_answer, and standard_answer from state, 无标准答案时评估用户回答      Extracts question and user_answer from state.

### Community 40 - "Coverage HTML"
Cohesion: 0.22
Nodes (8): 测试 extract_resume_info JSON 解析失败时返回空结构, 测试 extract_resume_info 返回非字典时返回空结构, 测试 extract_resume_info 通用异常时返回空结构, 测试 extract_resume_info 成功解析简历, test_extract_resume_info_general_exception(), test_extract_resume_info_json_decode_error(), test_extract_resume_info_non_dict_return(), test_extract_resume_info_success()

### Community 41 - "Knowledge Agent Graph"
Cohesion: 0.29
Nodes (2): getCellValue(), rowComparator()

### Community 42 - "Fallback Questions/Feedback"
Cohesion: 0.25
Nodes (3): find_standard_answer(), KnowledgeAgent - Knowledge base and responsibility management., 在 mastered_questions 中查找标准答案      Args:         state: InterviewState         qu

### Community 43 - "Question Generation Tests"
Cohesion: 0.25
Nodes (2): 测试所有 fallback 问题类型都存在, test_fallback_questions_all_types()

### Community 44 - "Responsibility Service"
Cohesion: 0.33
Nodes (0): 

### Community 45 - "Feedback Agent Tests"
Cohesion: 0.6
Nodes (4): get_responsibilities_by_resume(), get_responsibilities_by_resume_from_chroma(), save_responsibilities_from_project(), save_responsibilities_from_resume()

### Community 46 - "Fallback Response"
Cohesion: 0.4
Nodes (1): test_generate_correction_updates_feedbacks_dict()

### Community 47 - "Evaluate Agent Tests"
Cohesion: 0.83
Nodes (3): FallbackResponse, get_fallback_feedback(), get_fallback_question()

### Community 48 - "Retry Decorator Tests"
Cohesion: 0.5
Nodes (0): 

### Community 49 - "RAG Tools"
Cohesion: 0.5
Nodes (0): 

### Community 50 - "Prompt Templates"
Cohesion: 0.5
Nodes (4): KnowledgeRetriever, RAGTools, SimilarQuestionRetriever, StandardAnswerRetriever

### Community 51 - "Async Retry Decorator"
Cohesion: 0.67
Nodes (1): Prompt Templates for AI Interview Agent  面试各环节的提示词模板

### Community 52 - "Hybrid RAG Fusion"
Cohesion: 0.67
Nodes (2): async_retryable(), 异步重试装饰器工厂（类似 Spring @Retryable）      Args:         max_attempts: 最大尝试次数

### Community 53 - "main entry"
Cohesion: 0.67
Nodes (3): DRR Fusion Algorithm, HybridRetriever, SBERT Fusion Algorithm

### Community 54 - "test_api"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "test_interview_flow"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "test_resume_interview"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "LLM Usage dataclasses"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "MultiVector Retriever"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Vector Store doc count"
Cohesion: 1.0
Nodes (2): MultiVectorRetriever, RRF Fusion Algorithm

### Community 60 - "Enterprise knowledge tool"
Cohesion: 1.0
Nodes (1): Get number of documents in store.

### Community 61 - "Enterprise knowledge tool instance"
Cohesion: 1.0
Nodes (1): Invoke the enterprise knowledge retrieval          Args:             skill_po

### Community 62 - "Pregeneration TTL test"
Cohesion: 1.0
Nodes (1): Get as a LangChain tool instance          Returns:             EnterpriseKnow

### Community 63 - "resume_agent_graph"
Cohesion: 1.0
Nodes (1): Test that pregeneration uses correct TTL (3600 seconds)

### Community 64 - "knowledge_agent_graph"
Cohesion: 1.0
Nodes (1): resume_agent_graph

### Community 65 - "question_agent_graph"
Cohesion: 1.0
Nodes (1): knowledge_agent_graph

### Community 66 - "evaluate_agent_graph"
Cohesion: 1.0
Nodes (1): question_agent_graph

### Community 67 - "feedback_agent_graph"
Cohesion: 1.0
Nodes (1): evaluate_agent_graph

### Community 68 - "Reranker"
Cohesion: 1.0
Nodes (1): feedback_agent_graph

### Community 69 - "EnterpriseKnowledge"
Cohesion: 1.0
Nodes (1): Reranker

### Community 70 - "ContextAwareSkillLoader"
Cohesion: 1.0
Nodes (1): EnterpriseKnowledge

### Community 71 - "main.py singleton"
Cohesion: 1.0
Nodes (1): ContextAwareSkillLoader

## Knowledge Gaps
- **277 isolated node(s):** `Configuration Management for AI Interview Agent  统一配置管理 - 从 pyproject.toml [to`, `Simple config object providing direct attribute access.`, `Expand environment variables in ${VAR_NAME} format`, `Recursively process config to expand environment variables`, `Load configuration from pyproject.toml with env var expansion` (+272 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `test_api`** (2 nodes): `main()`, `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `test_interview_flow`** (2 nodes): `test_api.py`, `test_api()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `test_resume_interview`** (2 nodes): `test_interview_flow.py`, `test_interview_flow()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `LLM Usage dataclasses`** (2 nodes): `test_resume_interview.py`, `test_interview_flow()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MultiVector Retriever`** (2 nodes): `test_llm_response_holds_content_and_usage()`, `test_llm_usage_data.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vector Store doc count`** (2 nodes): `MultiVectorRetriever`, `RRF Fusion Algorithm`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Enterprise knowledge tool`** (1 nodes): `Get number of documents in store.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Enterprise knowledge tool instance`** (1 nodes): `Invoke the enterprise knowledge retrieval          Args:             skill_po`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pregeneration TTL test`** (1 nodes): `Get as a LangChain tool instance          Returns:             EnterpriseKnow`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `resume_agent_graph`** (1 nodes): `Test that pregeneration uses correct TTL (3600 seconds)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `knowledge_agent_graph`** (1 nodes): `resume_agent_graph`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `question_agent_graph`** (1 nodes): `knowledge_agent_graph`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `evaluate_agent_graph`** (1 nodes): `question_agent_graph`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `feedback_agent_graph`** (1 nodes): `evaluate_agent_graph`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Reranker`** (1 nodes): `feedback_agent_graph`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `EnterpriseKnowledge`** (1 nodes): `Reranker`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ContextAwareSkillLoader`** (1 nodes): `EnterpriseKnowledge`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `main.py singleton`** (1 nodes): `ContextAwareSkillLoader`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.