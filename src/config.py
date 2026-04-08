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

# Simple config object for backwards compatibility
class _SimpleConfig:
    """Simple config object providing direct attribute access."""
    def __init__(self, config_dict: dict):
        self._config = config_dict
        interview = config_dict.get("interview", {})
        self.max_series: int = interview.get("default_max_series", 5)
        self.error_threshold: int = interview.get("default_error_threshold", 2)
        self.max_followup_depth: int = interview.get("max_followup_depth", 3)
        self.deviation_threshold: float = 0.8

    def get(self, key: str, default=None):
        return self._config.get(key, default)

# Global config instance
_config_instance = _load_config()
config = _SimpleConfig(_config_instance) if _config_instance else None


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

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate Redis configuration"""
        errors = []

        if not self.host:
            errors.append("Redis host is required")

        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            errors.append(f"Redis port must be between 1 and 65535, got: {self.port}")

        if not isinstance(self.db, int) or self.db < 0:
            errors.append(f"Redis db must be a non-negative integer, got: {self.db}")

        if errors:
            raise ValueError(f"Redis configuration errors: {'; '.join(errors)}")

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

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate database configuration (except password)"""
        errors = []

        # Validate URL format
        if not self.url:
            errors.append("Database URL is required")
        elif not self.url.startswith("postgresql+asyncpg://"):
            errors.append("Database URL must use postgresql+asyncpg:// driver")

        # Validate pool_size
        if not isinstance(self.pool_size, int) or self.pool_size < 1:
            errors.append(f"pool_size must be a positive integer, got: {self.pool_size}")
        elif self.pool_size > 100:
            errors.append(f"pool_size seems too large (max 100 recommended): {self.pool_size}")

        # Validate max_overflow
        if not isinstance(self.max_overflow, int) or self.max_overflow < 0:
            errors.append(f"max_overflow must be a non-negative integer, got: {self.max_overflow}")
        elif self.max_overflow > 50:
            errors.append(f"max_overflow seems too large (max 50 recommended): {self.max_overflow}")

        # Validate pool_timeout
        if not isinstance(self.pool_timeout, int) or self.pool_timeout < 1:
            errors.append(f"pool_timeout must be a positive integer, got: {self.pool_timeout}")
        elif self.pool_timeout > 300:
            errors.append(f"pool_timeout seems too large (max 300 recommended): {self.pool_timeout}")

        # Validate pool_recycle
        if not isinstance(self.pool_recycle, int) or self.pool_recycle < 1:
            errors.append(f"pool_recycle must be a positive integer, got: {self.pool_recycle}")
        elif self.pool_recycle < 300:
            errors.append(f"pool_recycle should be at least 300 seconds for connection health")

        if errors:
            raise ValueError(f"Database configuration errors: {'; '.join(errors)}")

    def get_connection_params(self) -> dict:
        """Extract connection parameters from URL for validation"""
        # Parse URL to extract host, port, database
        # URL format: postgresql+asyncpg://user:pass@host:port/dbname
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(self.url.replace("postgresql+asyncpg://", "postgresql://"))
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/") or "postgres",
            }
        except Exception:
            return {}


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

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate LLM configuration"""
        warnings = []

        if not self.api_key:
            warnings.append("LLM api_key is not set")

        if not self.base_url:
            warnings.append("LLM base_url is required")
        elif not self.base_url.startswith(("http://", "https://")):
            warnings.append(f"LLM base_url should start with http:// or https://: {self.base_url}")

        if not self.model:
            warnings.append("LLM model is not set")

        if self.max_tokens < 1 or self.max_tokens > 128000:
            warnings.append(f"max_tokens should be between 1 and 128000, got: {self.max_tokens}")

        if self.temperature < 0 or self.temperature > 2:
            warnings.append(f"temperature should be between 0 and 2, got: {self.temperature}")

        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for w in warnings:
                logger.warning(f"[LLMConfig] {w}")


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

    def _validate(self):
        """Validate Embedding configuration"""
        warnings = []

        if not self.api_key:
            warnings.append("Embedding api_key is not set")

        if not self.base_url:
            warnings.append("Embedding base_url is required")
        elif not self.base_url.startswith(("http://", "https://")):
            warnings.append(f"Embedding base_url should start with http:// or https://: {self.base_url}")

        if not self.model:
            warnings.append("Embedding model is not set")

        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for w in warnings:
                logger.warning(f"[EmbeddingConfig] {w}")


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
