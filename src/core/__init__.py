"""
核心模块。

提供配置管理、异常定义、日志管理、适配器接口等核心功能。
"""

from src.core.config import Settings, get_settings, reload_settings
from src.core.exceptions import (
    MedGraphError,
    DocumentError,
    QueryError,
    GraphError,
    ConfigError,
    AuthenticationError,
    StorageError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)
from src.core.adapters import (
    RAGAnythingAdapter,
    IngestResult,
    QueryResult,
    GraphStats,
    QueryMode,
)

__all__ = [
    # 配置管理
    "Settings",
    "get_settings",
    "reload_settings",
    # 异常
    "MedGraphError",
    "DocumentError",
    "QueryError",
    "GraphError",
    "ConfigError",
    "AuthenticationError",
    "StorageError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    # 适配器
    "RAGAnythingAdapter",
    "IngestResult",
    "QueryResult",
    "GraphStats",
    "QueryMode",
]
