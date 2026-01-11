"""图谱相关的 API Schema 模型。

定义知识图谱的列表、详情、删除、合并、导出等操作的请求和响应模型。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

# 从 SDK 导入类型定义，复用以确保一致性
from src.sdk.types import GraphInfo as SDKGraphInfo, GraphConfig as SDKGraphConfig


class GraphListResponse(BaseModel):
    """图谱列表响应模型。

    返回所有可用的知识图谱列表。

    Attributes:
        graphs: 图谱信息列表
        total: 图谱总数

    Example:
        >>> response = GraphListResponse(
        ...     graphs=[...],
        ...     total=3
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "graphs": [
                    {
                        "graph_id": "graph-123",
                        "workspace": "medical",
                        "entity_count": 1500,
                        "relationship_count": 2000,
                        "document_count": 10,
                        "created_at": "2026-01-11T10:00:00Z",
                        "updated_at": "2026-01-11T10:05:00Z",
                    }
                ],
                "total": 1,
            }
        },
    )

    graphs: List[GraphInfoItem] = Field(default_factory=list, description="图谱列表")
    total: int = Field(default=0, ge=0, description="图谱总数")


class GraphInfoItem(BaseModel):
    """图谱信息项模型。

    表示单个知识图谱的信息。

    Attributes:
        graph_id: 图谱 ID
        workspace: 工作空间名称
        entity_count: 实体总数
        relationship_count: 关系总数
        document_count: 文档总数
        created_at: 创建时间
        updated_at: 更新时间

    Example:
        >>> item = GraphInfoItem(
        ...     graph_id="graph-123",
        ...     workspace="medical",
        ...     entity_count=1500
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,
    )

    graph_id: str = Field(..., description="图谱 ID")
    workspace: str = Field(..., description="工作空间名称")
    entity_count: int = Field(default=0, ge=0, description="实体总数")
    relationship_count: int = Field(default=0, ge=0, description="关系总数")
    document_count: int = Field(default=0, ge=0, description="文档总数")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    @classmethod
    def from_sdk_type(cls, graph_info: SDKGraphInfo) -> "GraphInfoItem":
        """从 SDK GraphInfo 创建 API 响应模型。

        Args:
            graph_info: SDK GraphInfo 实例

        Returns:
            GraphInfoItem 实例
        """
        return cls(
            graph_id=graph_info.graph_id,
            workspace=graph_info.workspace,
            entity_count=graph_info.entity_count,
            relationship_count=graph_info.relationship_count,
            document_count=graph_info.document_count,
            created_at=graph_info.created_at,
            updated_at=graph_info.updated_at,
        )


class GraphDetailResponse(BaseModel):
    """图谱详情响应模型。

    返回知识图谱的完整信息，包括统计和配置。

    Attributes:
        graph_info: 图谱基本信息
        config: 图谱配置（可选）

    Example:
        >>> response = GraphDetailResponse(
        ...     graph_info=GraphInfoItem(...),
        ...     config=GraphConfigItem(...)
        ... )
    """

    model_config = ConfigDict(validate_assignment=True)

    graph_info: GraphInfoItem = Field(..., description="图谱基本信息")
    config: Optional[GraphConfigItem] = Field(default=None, description="图谱配置")


class GraphConfigItem(BaseModel):
    """图谱配置项模型。

    表示知识图谱的配置参数。

    Attributes:
        workspace: 工作空间名称
        chunk_size: 文本块大小
        overlap: 文本块重叠大小
        entity_types: 医学实体类型列表

    Example:
        >>> config = GraphConfigItem(
        ...     workspace="medical",
        ...     chunk_size=512,
        ...     overlap=50
        ... )
    """

    model_config = ConfigDict(validate_assignment=True)

    workspace: str = Field(default="medical", description="工作空间名称")
    chunk_size: int = Field(default=512, gt=0, description="文本块大小")
    overlap: int = Field(default=50, ge=0, description="文本块重叠大小")
    entity_types: List[str] = Field(
        default_factory=lambda: [
            "DISEASE",
            "MEDICINE",
            "SYMPTOM",
            "ANATOMICAL_STRUCTURE",
            "BODY_FUNCTION",
            "LABORATORY_DATA",
            "PROCEDURE",
        ],
        description="医学实体类型列表",
    )

    @classmethod
    def from_sdk_type(cls, config: SDKGraphConfig) -> "GraphConfigItem":
        """从 SDK GraphConfig 创建 API 响应模型。

        Args:
            config: SDK GraphConfig 实例

        Returns:
            GraphConfigItem 实例
        """
        return cls(
            workspace=config.workspace,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            entity_types=config.entity_types,
        )


class GraphDeleteRequest(BaseModel):
    """图谱删除请求模型。

    用于删除图谱的请求参数。

    Attributes:
        confirm: 是否确认删除（安全措施）
    """

    model_config = ConfigDict(validate_assignment=True)

    confirm: bool = Field(
        default=False, description="是否确认删除（必须为 True 才能执行删除）"
    )

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v: bool) -> bool:
        """验证确认参数。

        Args:
            v: 确认值

        Returns:
            验证后的值

        Raises:
            ValueError: 如果确认值为 False
        """
        if not v:
            raise ValueError("删除操作需要确认，请设置 confirm=True")
        return v


class GraphDeleteResponse(BaseModel):
    """图谱删除响应模型。

    返回删除操作的结果。

    Attributes:
        graph_id: 被删除的图谱 ID
        deleted: 是否成功删除
        message: 操作消息
    """

    model_config = ConfigDict(validate_assignment=True)

    graph_id: str = Field(..., description="被删除的图谱 ID")
    deleted: bool = Field(default=False, description="是否成功删除")
    message: str = Field(default="", description="操作消息")


class GraphMergeRequest(BaseModel):
    """图谱合并请求模型。

    定义图谱节点合并操作的请求参数。

    Attributes:
        threshold: 相似度阈值（0-1），用于判断节点是否应该合并
        merge_strategy: 合并策略（semantic, exact）

    Example:
        >>> request = GraphMergeRequest(
        ...     threshold=0.8,
        ...     merge_strategy="semantic"
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "threshold": 0.8,
                "merge_strategy": "semantic",
            }
        },
    )

    threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="相似度阈值（0-1）"
    )
    merge_strategy: Literal["semantic", "exact"] = Field(
        default="semantic", description="合并策略"
    )


class GraphMergeResponse(BaseModel):
    """图谱合并响应模型。

    返回图谱节点合并操作的结果。

    Attributes:
        merged_count: 合并的节点数量
        message: 操作消息

    Example:
        >>> response = GraphMergeResponse(
        ...     merged_count=15,
        ...     message="成功合并 15 个节点"
        ... )
    """

    model_config = ConfigDict(validate_assignment=True)

    merged_count: int = Field(default=0, ge=0, description="合并的节点数量")
    message: str = Field(..., description="操作消息")


class GraphExportRequest(BaseModel):
    """图谱导出请求模型。

    定义图谱导出操作的请求参数。

    Attributes:
        format: 导出格式（json, csv, mermaid）
        include_entities: 是否包含实体
        include_relationships: 是否包含关系
        include_communities: 是否包含社区

    Example:
        >>> request = GraphExportRequest(
        ...     format="json",
        ...     include_entities=True,
        ...     include_relationships=True
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "format": "json",
                "include_entities": True,
                "include_relationships": True,
                "include_communities": False,
            }
        },
    )

    format: Literal["json", "csv", "mermaid"] = Field(
        default="json", description="导出格式"
    )
    include_entities: bool = Field(default=True, description="是否包含实体")
    include_relationships: bool = Field(default=True, description="是否包含关系")
    include_communities: bool = Field(default=False, description="是否包含社区")
