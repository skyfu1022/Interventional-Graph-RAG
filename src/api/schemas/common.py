"""通用 API Schema 模型。

定义健康检查和错误响应等通用的 API 模型。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """健康检查响应模型。

    返回服务的健康状态。

    Attributes:
        status: 健康状态（healthy, unhealthy）
        service: 服务名称
        version: 服务版本
        timestamp: 检查时间

    Example:
        >>> response = HealthResponse(
        ...     status="healthy",
        ...     service="medical-graph-rag-api",
        ...     version="1.0.0"
        ... )
    """

    model_config = ConfigDict(validate_assignment=True)

    status: Literal["healthy", "unhealthy"] = Field(..., description="健康状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(default="1.0.0", description="服务版本")
    timestamp: Optional[str] = Field(default=None, description="检查时间")


class ErrorResponse(BaseModel):
    """错误响应模型。

    用于返回错误信息的标准格式。

    Attributes:
        error: 错误类型
        message: 错误消息
        detail: 详细错误信息（可选）
        code: 错误代码（可选）

    Example:
        >>> response = ErrorResponse(
        ...     error="ValidationError",
        ...     message="请求参数验证失败",
        ...     detail={"field": "query_text", "error": "不能为空"}
        ... )
    """

    model_config = ConfigDict(validate_assignment=True)

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[Dict[str, Any]] = Field(default=None, description="详细错误信息")
    code: Optional[str] = Field(default=None, description="错误代码")
