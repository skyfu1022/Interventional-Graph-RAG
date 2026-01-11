"""API Schema 模块。

定义 Medical Graph RAG REST API 的所有 Pydantic 模型，
包括请求和响应的 Schema 定义。

该模块复用 SDK 的类型定义，确保 API 和 SDK 之间的类型一致性。
遵循 FastAPI 最佳实践和 PEP 8 标准。

所有 Schema 按功能模块分离到不同的文件中：
- documents.py: 文档相关 schemas
- query.py: 查询相关 schemas
- graphs.py: 图谱相关 schemas
- multimodal.py: 多模态查询 schemas
- common.py: 通用响应 schemas

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

# 从子模块导入所有 Schema 类
from src.api.schemas.documents import (
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
)

from src.api.schemas.query import (
    QueryRequest,
    QueryResponse,
    StreamQueryRequest,
)

from src.api.schemas.graphs import (
    GraphListResponse,
    GraphInfoItem,
    GraphDetailResponse,
    GraphConfigItem,
    GraphDeleteRequest,
    GraphDeleteResponse,
    GraphMergeRequest,
    GraphMergeResponse,
    GraphExportRequest,
)

from src.api.schemas.multimodal import (
    MultimodalQueryRequest,
)

from src.api.schemas.common import (
    HealthResponse,
    ErrorResponse,
)

# 从 SDK 导入类型定义（用于兼容性）
from src.sdk.types import (
    QueryMode,
    SourceInfo,
    GraphContext,
    QueryResult as SDKQueryResult,
    DocumentInfo as SDKDocumentInfo,
    GraphInfo as SDKGraphInfo,
    GraphConfig as SDKGraphConfig,
)

# 导出列表
__all__ = [
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
    # SDK 类型（用于兼容性）
    "QueryMode",
    "SourceInfo",
    "GraphContext",
    "SDKQueryResult",
    "SDKDocumentInfo",
    "SDKGraphInfo",
    "SDKGraphConfig",
]
