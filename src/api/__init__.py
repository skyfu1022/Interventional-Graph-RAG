"""
API 模块初始化文件。

导出 API 层的主要组件，包括应用实例、路由和模型。
"""


# 注意：不要在模块级别导入 app，以避免循环导入问题
# 使用函数导入来延迟加载
def _get_app():
    from src.api.app import app

    return app


def _get_create_app():
    from src.api.app import create_app

    return create_app


# 导出 schemas（这些可以立即导入）
from src.api.schemas import (  # noqa: E402 - 延迟导入以避免循环导入问题
    # 文档模型
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
    # 查询模型
    QueryRequest,
    QueryResponse,
    StreamQueryRequest,
    # 图谱模型
    GraphListResponse,
    GraphInfoItem,
    GraphDetailResponse,
    GraphConfigItem,
    GraphDeleteRequest,
    GraphDeleteResponse,
    GraphMergeRequest,
    GraphMergeResponse,
    GraphExportRequest,
    # 多模态模型
    MultimodalQueryRequest,
    # 通用模型
    HealthResponse,
    # 错误模型
    ErrorResponse,
)

__all__ = [
    # 应用（延迟导入）
    "app",
    "create_app",
    # 文档模型
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "DocumentDetailResponse",
    "DocumentDeleteResponse",
    # 查询模型
    "QueryRequest",
    "QueryResponse",
    "StreamQueryRequest",
    # 图谱模型
    "GraphListResponse",
    "GraphInfoItem",
    "GraphDetailResponse",
    "GraphConfigItem",
    "GraphDeleteRequest",
    "GraphDeleteResponse",
    "GraphMergeRequest",
    "GraphMergeResponse",
    "GraphExportRequest",
    # 多模态模型
    "MultimodalQueryRequest",
    # 通用模型
    "HealthResponse",
    # 错误模型
    "ErrorResponse",
]


# 提供延迟导入的属性访问
def __getattr__(name: str):
    """延迟导入 app 和 create_app 以避免循环导入问题。

    Args:
        name: 属性名称

    Returns:
        请求的属性值

    Raises:
        AttributeError: 如果属性不存在
    """
    if name == "app":
        from src.api.app import app as _app

        return _app
    elif name == "create_app":
        from src.api.app import create_app as _create_app

        return _create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
