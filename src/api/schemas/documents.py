"""文档相关的 API Schema 模型。

定义文档上传、详情、删除等操作的请求和响应模型。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

# 从 SDK 导入类型定义，复用以确保一致性
from src.sdk.types import DocumentInfo as SDKDocumentInfo


class DocumentUploadRequest(BaseModel):
    """文档上传请求模型。

    定义文档上传 API 的请求参数，支持文件上传和配置选项。

    Attributes:
        file_name: 文件名（用于识别文档）
        file_content: 文件内容（Base64 编码或原始文本）
        file_type: 文件类型（txt, pdf, md, json, csv）
        graph_id: 目标图谱 ID（可选，默认使用默认工作空间）
        chunk_size: 文本块大小（可选，覆盖默认配置）
        overlap: 文本块重叠大小（可选，覆盖默认配置）

    Example:
        >>> request = DocumentUploadRequest(
        ...     file_name="医学论文.pdf",
        ...     file_content="base64_encoded_content",
        ...     file_type="pdf",
        ...     graph_id="graph-123"
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "file_name": "糖尿病诊疗指南.pdf",
                "file_content": "SGVsbG8gV29ybGQ...",
                "file_type": "pdf",
                "graph_id": "graph-123",
                "chunk_size": 512,
                "overlap": 50,
            }
        },
    )

    file_name: str = Field(..., min_length=1, description="文件名")
    file_content: str = Field(..., description="文件内容（Base64 编码或文本）")
    file_type: Literal["txt", "pdf", "md", "json", "csv"] = Field(
        ..., description="文件类型"
    )
    graph_id: Optional[str] = Field(
        default=None, description="目标图谱 ID（可选）"
    )
    chunk_size: Optional[int] = Field(
        default=None, gt=0, description="文本块大小（可选）"
    )
    overlap: Optional[int] = Field(
        default=None, ge=0, description="文本块重叠大小（可选）"
    )


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型。

    返回文档上传操作的结果，包括文档 ID 和状态信息。

    Attributes:
        doc_id: 文档 ID
        file_name: 文件名
        status: 处理状态（pending, processing, completed, failed）
        message: 状态消息
        entity_count: 提取的实体数量（完成后）
        relationship_count: 提取的关系数量（完成后）

    Example:
        >>> response = DocumentUploadResponse(
        ...     doc_id="doc-123",
        ...     file_name="医学论文.pdf",
        ...     status="processing",
        ...     message="文档正在处理中"
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "doc_id": "doc-123",
                "file_name": "糖尿病诊疗指南.pdf",
                "status": "processing",
                "message": "文档正在处理中",
                "entity_count": 0,
                "relationship_count": 0,
            }
        },
    )

    doc_id: str = Field(..., description="文档 ID")
    file_name: str = Field(..., description="文件名")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="处理状态"
    )
    message: str = Field(..., description="状态消息")
    entity_count: int = Field(default=0, ge=0, description="提取的实体数量")
    relationship_count: int = Field(default=0, ge=0, description="提取的关系数量")


class DocumentDetailResponse(BaseModel):
    """文档详情响应模型。

    返回文档的完整信息，复用 SDK 的 DocumentInfo 类型。

    Attributes:
        所有字段继承自 SDKDocumentInfo

    Example:
        >>> response = DocumentDetailResponse(
        ...     doc_id="doc-123",
        ...     file_name="医学论文.pdf",
        ...     file_path="/data/documents/doc-123.pdf",
        ...     status="completed",
        ...     entity_count=150,
        ...     relationship_count=200,
        ...     created_at="2026-01-11T10:00:00Z"
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,  # 允许从对象创建
        json_schema_extra={
            "example": {
                "doc_id": "doc-123",
                "file_name": "糖尿病诊疗指南.pdf",
                "file_path": "/data/documents/doc-123.pdf",
                "status": "completed",
                "entity_count": 150,
                "relationship_count": 200,
                "created_at": "2026-01-11T10:00:00Z",
                "updated_at": "2026-01-11T10:05:00Z",
            }
        },
    )

    # 直接使用 SDK 类型
    doc_id: str = Field(..., description="文档 ID")
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="文档状态"
    )
    entity_count: int = Field(default=0, ge=0, description="提取的实体数量")
    relationship_count: int = Field(default=0, ge=0, description="提取的关系数量")
    created_at: str = Field(..., description="创建时间（ISO 8601）")
    updated_at: Optional[str] = Field(default=None, description="更新时间（ISO 8601）")

    @classmethod
    def from_sdk_type(cls, doc_info: SDKDocumentInfo) -> "DocumentDetailResponse":
        """从 SDK DocumentInfo 创建 API 响应模型。

        Args:
            doc_info: SDK DocumentInfo 实例

        Returns:
            DocumentDetailResponse 实例
        """
        return cls(
            doc_id=doc_info.doc_id,
            file_name=doc_info.file_name,
            file_path=doc_info.file_path,
            status=doc_info.status,
            entity_count=doc_info.entity_count,
            relationship_count=doc_info.relationship_count,
            created_at=doc_info.created_at,
            updated_at=doc_info.updated_at,
        )


class DocumentDeleteResponse(BaseModel):
    """文档删除响应模型。

    Attributes:
        doc_id: 文档 ID
        success: 是否删除成功
        message: 响应消息
    """

    model_config = ConfigDict(validate_assignment=True)

    doc_id: str = Field(..., description="文档 ID")
    success: bool = Field(..., description="是否删除成功")
    message: str = Field(..., description="响应消息")
