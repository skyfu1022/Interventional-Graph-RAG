"""多模态查询的 API Schema 模型。

定义支持图像、表格等多模态数据的查询请求模型。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

# 从 SDK 导入类型定义，复用以确保一致性
from src.sdk.types import QueryMode


class MultimodalQueryRequest(BaseModel):
    """多模态查询请求模型。

    支持带图像或表格的查询请求。

    Attributes:
        query_text: 查询文本
        image_data: 图像数据（Base64 编码，可选）
        image_type: 图像类型（jpg, png, dicom，可选）
        table_data: 表格数据（JSON 格式，可选）
        mode: 查询模式
        graph_id: 图谱 ID（可选）

    Example:
        >>> request = MultimodalQueryRequest(
        ...     query_text="这张X光片显示什么？",
        ...     image_data="base64_encoded_image",
        ...     image_type="jpg",
        ...     mode="hybrid"
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "query_text": "这张X光片显示什么？",
                "image_data": "SGVsbG8gV29ybGQ...",
                "image_type": "jpg",
                "table_data": None,
                "mode": "hybrid",
                "graph_id": "graph-123",
            }
        },
    )

    query_text: str = Field(..., min_length=1, description="查询文本")
    image_data: Optional[str] = Field(default=None, description="图像数据（Base64）")
    image_type: Optional[Literal["jpg", "png", "dicom"]] = Field(
        default=None, description="图像类型"
    )
    table_data: Optional[Dict[str, Any]] = Field(
        default=None, description="表格数据（JSON 格式）"
    )
    mode: QueryMode = Field(default=QueryMode.HYBRID, description="查询模式")
    graph_id: Optional[str] = Field(default=None, description="图谱 ID（可选）")

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """验证查询文本。

        Args:
            v: 查询文本

        Returns:
            验证后的查询文本

        Raises:
            ValueError: 如果查询文本无效
        """
        if not v or v.isspace():
            raise ValueError("query_text 不能为空")
        return v
