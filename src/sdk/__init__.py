"""
Medical Graph RAG Python SDK。

这是一个类型安全、易用的 Python SDK，用于：
- 构建和管理医学知识图谱
- 查询医学知识
- 文档摄入和管理
- 图谱数据导出

快速开始：
    >>> from src.sdk import MedGraphClient
    >>>
    >>> async def main():
    ...     async with MedGraphClient(workspace="medical") as client:
    ...         # 摄入文档
    ...         await client.ingest_document("medical_doc.txt")
    ...
    ...         # 查询知识图谱
    ...         result = await client.query("什么是糖尿病?")
    ...         print(result.answer)
    >>>
    >>> import asyncio
    >>> asyncio.run(main())

版本: 0.2.0
许可: MIT
"""

__version__ = "0.2.0"
__author__ = "Medical Graph RAG Team"
__license__ = "MIT"

# ========== 客户端 ==========

from src.sdk.client import MedGraphClient
from src.sdk.client import create_client

# ========== 类型定义 ==========

from src.sdk.types import (
    QueryMode,
    QueryResult,
    DocumentInfo,
    GraphInfo,
    GraphConfig,
    SourceInfo,
    GraphContext,
)

# ========== 异常 ==========

from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError,
    DocumentNotFoundError,
    ConnectionError,
    ValidationError,
    QueryTimeoutError,
    RateLimitError,
    convert_core_exception,
)

# ========== 性能监控 ==========

from src.sdk.monitoring import (
    PerformanceMonitor,
    PerformanceMetrics,
    QueryPerformanceTimer,
)

# ========== 导出列表 ==========

__all__ = [
    # 客户端
    "MedGraphClient",
    "create_client",
    # 类型
    "QueryMode",
    "QueryResult",
    "DocumentInfo",
    "GraphInfo",
    "GraphConfig",
    "SourceInfo",
    "GraphContext",
    # 异常
    "MedGraphSDKError",
    "ConfigError",
    "DocumentNotFoundError",
    "ConnectionError",
    "ValidationError",
    "QueryTimeoutError",
    "RateLimitError",
    "convert_core_exception",
    # 监控
    "PerformanceMonitor",
    "PerformanceMetrics",
    "QueryPerformanceTimer",
    # 元信息
    "__version__",
    "__author__",
    "__license__",
]

# ========== 模块级别文档 ==========


def get_version() -> str:
    """获取 SDK 版本号。

    Returns:
        str: SDK 版本号
    """
    return __version__


def get_info() -> dict:
    """获取 SDK 信息。

    Returns:
        dict: 包含版本、作者、许可证等信息的字典
    """
    return {
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "name": "Medical Graph RAG SDK",
        "description": "Python SDK for Medical Graph RAG",
    }
