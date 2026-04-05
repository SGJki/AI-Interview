"""
AI Interview Agent - Tools Package

LangChain 工具链实现
"""

from src.tools.rag_tools import (
    retrieve_knowledge,
    retrieve_similar_questions,
    retrieve_standard_answer,
    retrieve_by_skill_point,
    add_to_knowledge_base,
    RAGTools,
    SimilarQuestionRetriever,
    StandardAnswerRetriever,
)

from src.tools.rag_enhancements import (
    FusionType,
    MultiVectorRetriever,
    HybridRetriever,
    Reranker,
    RerankerConfig,
    fusion_results,
    retrieve_with_fusion,
)

from src.tools.memory_tools import (
    save_to_session_memory,
    get_session_memory,
    clear_session_memory,
    update_session_series,
    cache_next_series_question,
    get_cached_next_question,
    set_user_current_interview,
    get_user_current_interview,
)

from src.tools.code_tools import (
    parse_source_code,
    extract_module_structure,
    extract_architecture,
    extract_project_info,
    ModuleInfo,
    ProjectInfo,
    ArchitectureInfo,
)

from src.tools.enterprise_knowledge import (
    retrieve_enterprise_knowledge,
    retrieve_enterprise_knowledge_with_fusion,
    EnterpriseKnowledgeRetriever,
    KnowledgeFusionResult,
    search_enterprise_best_practices,
    search_web_best_practices,
)

__all__ = [
    # RAG Tools
    "retrieve_knowledge",
    "retrieve_similar_questions",
    "retrieve_standard_answer",
    "retrieve_by_skill_point",
    "add_to_knowledge_base",
    "RAGTools",
    "SimilarQuestionRetriever",
    "StandardAnswerRetriever",
    # RAG Enhancement Tools
    "FusionType",
    "MultiVectorRetriever",
    "HybridRetriever",
    "Reranker",
    "RerankerConfig",
    "fusion_results",
    "retrieve_with_fusion",
    # Memory Tools
    "save_to_session_memory",
    "get_session_memory",
    "clear_session_memory",
    "update_session_series",
    "cache_next_series_question",
    "get_cached_next_question",
    "set_user_current_interview",
    "get_user_current_interview",
    # Code Tools
    "parse_source_code",
    "extract_module_structure",
    "extract_architecture",
    "extract_project_info",
    "ModuleInfo",
    "ProjectInfo",
    "ArchitectureInfo",
    # Enterprise Knowledge Tools
    "retrieve_enterprise_knowledge",
    "retrieve_enterprise_knowledge_with_fusion",
    "EnterpriseKnowledgeRetriever",
    "KnowledgeFusionResult",
    "search_enterprise_best_practices",
    "search_web_best_practices",
]
