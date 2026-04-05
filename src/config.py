"""
Configuration Management for AI Interview Agent

统一配置管理 - 从 pyproject.toml [tool.ai-interview] 读取
支持环境变量替换，如 ${VAR_NAME}
"""

import os
import re
import tomllib
from pathlib import Path
from typing import Optional


# Global config cache
_config: Optional[dict] = None


def _expand_env_vars(value: str) -> str:
    """Expand environment variables in ${VAR_NAME} format"""
    if not isinstance(value, str):
        return value

    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return pattern.sub(replacer, value)


def _process_config(obj):
    """Recursively process config to expand environment variables"""
    if isinstance(obj, dict):
        return {k: _process_config(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_process_config(item) for item in obj]
    elif isinstance(obj, str):
        return _expand_env_vars(obj)
    return obj


def _load_config() -> dict:
    """Load configuration from pyproject.toml with env var expansion"""
    global _config

    if _config is not None:
        return _config

    pyproject_path = Path(__file__).parent.parent / "config/config.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    raw_config = pyproject.get("tool", {}).get("ai-interview", {})
    _config = _process_config(raw_config)
    return _config


def get_config() -> dict:
    """Get full configuration dict"""
    return _load_config()


# =============================================================================
# Redis Configuration
# =============================================================================

class RedisConfig:
    """Redis configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("redis", {})
        self.host: str = config.get("host", "localhost")
        self.port: int = config.get("port", 6379)
        self.db: int = config.get("db", 0)
        self.password: Optional[str] = config.get("password") or None

    def to_redis_kwargs(self) -> dict:
        """Convert to redis.Redis kwargs"""
        kwargs = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "decode_responses": True,
        }
        if self.password:
            kwargs["password"] = self.password
        return kwargs


def get_redis_config() -> RedisConfig:
    """Get Redis configuration"""
    return RedisConfig()


# =============================================================================
# Database Configuration
# =============================================================================

class DatabaseConfig:
    """PostgreSQL database configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("database", {})
        self.url: str = config.get(
            "url",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_interview"
        )
        self.pool_size: int = config.get("pool_size", 10)
        self.max_overflow: int = config.get("max_overflow", 20)
        self.pool_timeout: int = config.get("pool_timeout", 30)
        self.pool_recycle: int = config.get("pool_recycle", 3600)


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return DatabaseConfig()


# =============================================================================
# LLM Configuration
# =============================================================================

class LLMConfig:
    """LLM (Language Model) configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("llm", {})
        self.api_key: str = config.get("api_key", "")
        self.base_url: str = config.get(
            "base_url",
            "https://open.bigmodel.cn/api/paas/v4"
        )
        self.model: str = config.get("model", "glm-4")
        self.max_tokens: int = config.get("max_tokens", 2048)
        self.temperature: float = config.get("temperature", 0.7)


# =============================================================================
# Embedding Configuration
# =============================================================================

class EmbeddingConfig:
    """Embedding model configuration (Alibaba Cloud DashScope)"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("embedding", {})
        self.api_key: str = config.get("api_key", "")
        self.base_url: str = config.get(
            "base_url",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
        )
        self.model: str = config.get("model", "text-embedding-v3")
        self.dimensions: int = config.get("dimensions", 1024)


def get_llm_config() -> LLMConfig:
    """Get LLM configuration"""
    return LLMConfig()


def get_embedding_config() -> EmbeddingConfig:
    """Get embedding configuration"""
    return EmbeddingConfig()


# =============================================================================
# Vector Store Configuration
# =============================================================================

class VectorConfig:
    """Vector store configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("vector", {})
        self.persist_directory: str = config.get(
            "persist_directory",
            "./data/vectorstore"
        )
        self.collection_name: str = config.get(
            "collection_name",
            "ai_interview_knowledge"
        )


def get_vector_config() -> VectorConfig:
    """Get vector store configuration"""
    return VectorConfig()


# =============================================================================
# Server Configuration
# =============================================================================

class ServerConfig:
    """Server configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("server", {})
        self.host: str = config.get("host", "0.0.0.0")
        self.port: int = config.get("port", 8000)
        self.reload: bool = config.get("reload", True)
        self.workers: int = config.get("workers", 1)


def get_server_config() -> ServerConfig:
    """Get server configuration"""
    return ServerConfig()


# =============================================================================
# Interview Configuration
# =============================================================================

class InterviewConfig:
    """Interview behavior configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("interview", {})
        self.default_max_series: int = config.get("default_max_series", 5)
        self.default_error_threshold: int = config.get("default_error_threshold", 2)
        self.max_followup_depth: int = config.get("max_followup_depth", 3)
        self.session_ttl: int = config.get("session_ttl", 86400)


def get_interview_config() -> InterviewConfig:
    """Get interview configuration"""
    return InterviewConfig()


# =============================================================================
# RAG Configuration
# =============================================================================

class RAGConfig:
    """RAG (Retrieval-Augmented Generation) configuration"""

    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("rag", {})
        self.top_k: int = config.get("top_k", 5)
        self.reranker_top_k: int = config.get("reranker_top_k", 10)
        self.similarity_threshold: float = config.get("similarity_threshold", 0.7)


def get_rag_config() -> RAGConfig:
    """Get RAG configuration"""
    return RAGConfig()
