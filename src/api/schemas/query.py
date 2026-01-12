"""查询相关的 API Schema 模型。

定义知识图谱查询、流式查询等操作的请求和响应模型。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

# 从 SDK 导入类型定义，复用以确保一致性
from src.sdk.types import (
    QueryMode,
    SourceInfo,
    GraphContext,
    QueryResult as SDKQueryResult,
)


class QueryRequest(BaseModel):
    """查询请求模型。

    定义知识图谱查询 API 的请求参数。

    Attributes:
        query_text: 查询文本
        mode: 查询模式（naive, local, global, hybrid, mix, bypass）
        graph_id: 图谱 ID（可选，默认使用默认工作空间）
        top_k: 返回结果数量（可选）

    Example:
        >>> request = QueryRequest(
        ...     query_text="糖尿病的症状有哪些？",
        ...     mode="hybrid",
        ...     graph_id="graph-123",
        ...     top_k=5
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "query_text": "糖尿病的症状有哪些？",
                "mode": "hybrid",
                "graph_id": "graph-123",
                "top_k": 5,
            }
        },
    )

    query_text: str = Field(..., min_length=1, description="查询文本")
    mode: QueryMode = Field(default=QueryMode.HYBRID, description="查询模式")
    graph_id: Optional[str] = Field(default=None, description="图谱 ID（可选）")
    top_k: Optional[int] = Field(default=5, gt=0, le=20, description="返回结果数量")

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """验证查询文本。

        确保查询文本不为空且不全是空白字符。

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


class QueryResponse(BaseModel):
    """查询响应模型。

    返回知识图谱查询的结果，复用 SDK 的 QueryResult 类型。

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

    Example:
        >>> response = QueryResponse(
        ...     query="糖尿病的症状有哪些？",
        ...     answer="糖尿病的主要症状包括...",
        ...     mode="hybrid",
        ...     graph_id="graph-123"
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "query": "糖尿病的症状有哪些？",
                "answer": "糖尿病的主要症状包括多饮、多尿、多食...",
                "mode": "hybrid",
                "graph_id": "graph-123",
                "sources": [],
                "context": [],
                "graph_context": None,
                "retrieval_count": 3,
                "latency_ms": 250,
            }
        },
    )

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

    @classmethod
    def from_sdk_type(cls, result: SDKQueryResult) -> "QueryResponse":
        """从 SDK QueryResult 创建 API 响应模型。

        Args:
            result: SDK QueryResult 实例

        Returns:
            QueryResponse 实例
        """
        return cls(
            query=result.query,
            answer=result.answer,
            mode=result.mode,
            graph_id=result.graph_id,
            sources=result.sources,
            context=result.context,
            graph_context=result.graph_context,
            retrieval_count=result.retrieval_count,
            latency_ms=result.latency_ms,
        )


class StreamQueryRequest(BaseModel):
    """流式查询请求模型。

    定义流式查询 API 的请求参数，支持 Server-Sent Events (SSE)。

    Attributes:
        query_text: 查询文本
        mode: 查询模式
        graph_id: 图谱 ID（可选）

    Example:
        >>> request = StreamQueryRequest(
        ...     query_text="解释糖尿病的发病机制",
        ...     mode="global"
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "query_text": "解释糖尿病的发病机制",
                "mode": "global",
                "graph_id": "graph-123",
            }
        },
    )

    query_text: str = Field(..., min_length=1, description="查询文本")
    mode: QueryMode = Field(default=QueryMode.GLOBAL, description="查询模式")
    graph_id: Optional[str] = Field(default=None, description="图谱 ID（可选）")
