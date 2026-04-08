"""Configuration module."""
import os
import re
import tomllib
from pathlib import Path
from typing import Optional

from src.config.interview_config import InterviewConfig, config


# =============================================================================
# Standalone Config Module Imports (from src/config.py)
# These are needed by src/llm/client.py which does "from src.config import get_llm_config"
# =============================================================================

# Re-use global config from interview_config if available, otherwise load it
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


class LLMConfig:
    """LLM (Language Model) configuration"""
    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("llm", {})
        self.api_key: str = config.get("api_key", "")
        self.base_url: str = config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        self.model: str = config.get("model", "glm-4")
        self.max_tokens: int = config.get("max_tokens", 2048)
        self.temperature: float = config.get("temperature", 0.7)


def get_llm_config() -> LLMConfig:
    """Get LLM configuration"""
    return LLMConfig()


class EmbeddingConfig:
    """Embedding model configuration (Alibaba Cloud DashScope)"""
    def __init__(self, config: dict = None):
        if config is None:
            config = _load_config().get("embedding", {})
        self.api_key: str = config.get("api_key", "")
        self.base_url: str = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings")
        self.model: str = config.get("model", "text-embedding-v3")
        self.dimensions: int = config.get("dimensions", 1024)


def get_embedding_config() -> EmbeddingConfig:
    """Get embedding configuration"""
    return EmbeddingConfig()


__all__ = ["InterviewConfig", "config", "get_llm_config", "LLMConfig", "get_embedding_config", "EmbeddingConfig"]
