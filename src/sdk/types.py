"""
SDK 类型定义模块。

定义 Medical Graph RAG SDK 的所有数据类型，使用 Pydantic BaseModel
提供类型安全和序列化支持。

该模块为 CLI 和 REST API 层提供统一的类型定义，确保整个 SDK 的
类型一致性和数据验证。
"""

from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class QueryMode(str, Enum):
    """查询模式枚举。

    定义了 6 种知识图谱查询模式：
    - naive: 简单检索，直接返回相关内容
    - local: 局部社区检索，关注实体局部关系
    - global: 全局社区检索，关注图谱全局结构
    - hybrid: 混合检索，结合局部和全局优势
    - mix: 混合模式，动态调整检索策略
    - bypass: 绕过图谱，直接检索原始文档
    """

    NAIVE = "naive"
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    MIX = "mix"
    BYPASS = "bypass"


class SourceInfo(BaseModel):
    """来源信息。

    表示查询结果的来源片段，包含文档 ID、内容块 ID、
    实际内容和相关性评分。

    Attributes:
        doc_id: 文档 ID
        chunk_id: 内容块 ID
        content: 内容片段
        relevance: 相关性评分（0-1）
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    doc_id: str = Field(..., description="文档 ID")
    chunk_id: str = Field(..., description="内容块 ID")
    content: str = Field(..., description="内容片段")
    relevance: float = Field(
        default=0.0, ge=0.0, le=1.0, description="相关性评分（0-1）"
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceInfo":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            SourceInfo 实例
        """
        return cls.model_validate(data)


class GraphContext(BaseModel):
    """图谱上下文。

    包含从知识图谱中提取的结构化信息，包括实体、
    关系和社区。

    Attributes:
        entities: 实体列表
        relationships: 关系列表
        communities: 社区列表
    """

    model_config = ConfigDict(validate_assignment=True)

    entities: List[str] = Field(default_factory=list, description="实体列表")
    relationships: List[str] = Field(default_factory=list, description="关系列表")
    communities: List[str] = Field(default_factory=list, description="社区列表")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphContext":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            GraphContext 实例
        """
        return cls.model_validate(data)


class QueryResult(BaseModel):
    """查询结果。

    表示知识图谱查询的完整结果，包含答案、来源、
    上下文和性能指标。

    Attributes:
        query: 查询文本
        answer: 生成的答案
        mode: 查询模式
        graph_id: 图谱 ID
        sources: 来源列表
        context: 上下文列表
        graph_context: 图谱上下文
        retrieval_count: 检索次数
        latency_ms: 查询延迟（毫秒）
    """

    model_config = ConfigDict(validate_assignment=True)

    query: str = Field(..., description="查询文本")
    answer: str = Field(..., description="生成的答案")
    mode: QueryMode = Field(..., description="查询模式")
    graph_id: str = Field(..., description="图谱 ID")

    sources: List[SourceInfo] = Field(default_factory=list, description="来源列表")
    context: List[str] = Field(default_factory=list, description="上下文列表")
    graph_context: Optional[GraphContext] = Field(
        default=None, description="图谱上下文"
    )

    retrieval_count: int = Field(default=0, ge=0, description="检索次数")
    latency_ms: int = Field(default=0, ge=0, description="查询延迟（毫秒）")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典，嵌套对象也会被转换
        """
        data = self.model_dump()
        # 转换嵌套的 Pydantic 对象
        if self.graph_context:
            data["graph_context"] = self.graph_context.to_dict()
        data["sources"] = [s.to_dict() for s in self.sources]
        return data

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            格式化的 JSON 字符串
        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResult":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            QueryResult 实例
        """
        # 处理嵌套的 graph_context
        if "graph_context" in data and data["graph_context"] is not None:
            data["graph_context"] = GraphContext.model_validate(data["graph_context"])
        # 处理嵌套的 sources
        if "sources" in data:
            data["sources"] = [SourceInfo.model_validate(s) for s in data["sources"]]
        return cls.model_validate(data)


class DocumentInfo(BaseModel):
    """文档信息。

    表示文档的元数据和状态信息。

    Attributes:
        doc_id: 文档 ID
        file_name: 文件名
        file_path: 文件路径
        status: 文档状态
        entity_count: 提取的实体数量
        relationship_count: 提取的关系数量
        created_at: 创建时间（ISO 8601）
        updated_at: 更新时间（ISO 8601）
    """

    model_config = ConfigDict(validate_assignment=True)

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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentInfo":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            DocumentInfo 实例
        """
        return cls.model_validate(data)


class GraphInfo(BaseModel):
    """图谱信息。

    表示知识图谱的统计信息和元数据。

    Attributes:
        graph_id: 图谱 ID
        workspace: 工作空间名称
        entity_count: 实体总数
        relationship_count: 关系总数
        document_count: 文档总数
        created_at: 创建时间
        updated_at: 更新时间
    """

    model_config = ConfigDict(validate_assignment=True)

    graph_id: str = Field(..., description="图谱 ID")
    workspace: str = Field(..., description="工作空间名称")

    entity_count: int = Field(default=0, ge=0, description="实体总数")
    relationship_count: int = Field(default=0, ge=0, description="关系总数")
    document_count: int = Field(default=0, ge=0, description="文档总数")

    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphInfo":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            GraphInfo 实例
        """
        return cls.model_validate(data)


class GraphConfig(BaseModel):
    """图谱配置。

    定义知识图谱的构建和配置参数。

    Attributes:
        workspace: 工作空间名称
        chunk_size: 文本块大小（字符数）
        overlap: 文本块重叠大小
        entity_types: 医学实体类型列表
    """

    model_config = ConfigDict(validate_assignment=True)

    workspace: str = Field(default="medical", description="工作空间名称")

    chunk_size: int = Field(default=512, gt=0, description="文本块大小（字符数）")

    overlap: int = Field(default=50, ge=0, description="文本块重叠大小")

    entity_types: List[str] = Field(
        default=[
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

    @field_validator("entity_types")
    @classmethod
    def validate_and_normalize_entity_types(cls, v: List[str]) -> List[str]:
        """验证并规范化实体类型。

        确保实体类型列表不为空，并统一转换为大写格式。

        Args:
            v: 实体类型列表

        Returns:
            规范化后的实体类型列表（大写、去重）

        Raises:
            ValueError: 如果实体类型列表为空
        """
        if not v:
            raise ValueError("entity_types 不能为空")
        # 转换为大写并去重
        return list(set(et.upper() for et in v))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphConfig":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            GraphConfig 实例
        """
        return cls.model_validate(data)


# ========== 导出列表 ==========

__all__ = [
    "QueryMode",
    "SourceInfo",
    "GraphContext",
    "QueryResult",
    "DocumentInfo",
    "GraphInfo",
    "GraphConfig",
]
