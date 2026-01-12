"""
SDK 异常模块。

定义 Medical Graph RAG SDK 的异常类，提供更友好的错误信息。
"""

from typing import Optional, Dict, Any
import re


class MedGraphSDKError(Exception):
    """SDK 基础异常类。

    所有 SDK 异常的基类，提供统一的错误处理接口。

    Attributes:
        message: 错误消息
        error_code: 错误码
        details: 错误详情字典

    Example:
        >>> err = MedGraphSDKError("测试错误", error_code="TEST_001", details={"key": "value"})
        >>> print(err)
        [TEST_001] 测试错误
        >>> err.to_dict()
        {'error_type': 'MedGraphSDKError', 'error_code': 'TEST_001', 'message': '测试错误', 'details': {'key': 'value'}}
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """初始化 SDK 异常。

        Args:
            message: 错误消息
            error_code: 错误码，如果不提供则使用类名
            details: 错误详情字典
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 API 响应。

        Returns:
            包含错误信息的字典
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        """友好的字符串表示。"""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """开发者表示。"""
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r}, details={self.details!r})"


class ConfigError(MedGraphSDKError):
    """配置相关错误。

    当 SDK 配置缺失、无效或无法加载时抛出。

    Attributes:
        message: 错误消息
        config_key: 相关的配置键
        config_file: 配置文件路径（如果从文件加载）

    Example:
        >>> raise ConfigError("API Key 未配置", config_key="openai_api_key")
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
    ):
        """初始化配置错误。

        Args:
            message: 错误消息
            config_key: 相关的配置键
            config_file: 配置文件路径
        """
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file

        super().__init__(message=message, error_code="CONFIG_ERROR", details=details)
        self.config_key = config_key
        self.config_file = config_file


class DocumentNotFoundError(MedGraphSDKError):
    """文档未找到错误。

    当尝试访问不存在的文档时抛出。

    Attributes:
        message: 错误消息
        doc_id: 文档 ID

    Example:
        >>> raise DocumentNotFoundError("文档不存在", doc_id="doc-123")
    """

    def __init__(self, message: str, doc_id: Optional[str] = None):
        """初始化文档未找到错误。

        Args:
            message: 错误消息
            doc_id: 文档 ID
        """
        details = {}
        if doc_id:
            details["doc_id"] = doc_id

        super().__init__(
            message=message, error_code="DOCUMENT_NOT_FOUND", details=details
        )
        self.doc_id = doc_id


class ConnectionError(MedGraphSDKError):
    """连接错误。

    当无法连接到 Neo4j、Milvus 或其他服务时抛出。

    Attributes:
        message: 错误消息
        service: 服务名称（neo4j, milvus 等）
        uri: 连接 URI（不包含敏感信息）

    Example:
        >>> raise ConnectionError("无法连接到 Neo4j", service="neo4j", uri="bolt://localhost:7687")
    """

    def __init__(
        self, message: str, service: Optional[str] = None, uri: Optional[str] = None
    ):
        """初始化连接错误。

        Args:
            message: 错误消息
            service: 服务名称
            uri: 连接 URI
        """
        details = {}
        if service:
            details["service"] = service
        if uri:
            # 脱敏 URI，不暴露密码
            details["uri"] = self._sanitize_uri(uri)

        super().__init__(
            message=message, error_code="CONNECTION_ERROR", details=details
        )
        self.service = service
        self.uri = uri

    @staticmethod
    def _sanitize_uri(uri: str) -> str:
        """脱敏 URI，移除密码等敏感信息。

        Args:
            uri: 原始 URI

        Returns:
            脱敏后的 URI

        Example:
            >>> ConnectionError._sanitize_uri("bolt://neo4j:password@localhost:7687")
            'bolt://neo4j:****@localhost:7687'
        """
        # 移除 password 部分
        return re.sub(r":([^:@]+)@", ":****@", uri)


class ValidationError(MedGraphSDKError):
    """数据验证错误。

    当输入数据不符合要求时抛出。

    Attributes:
        message: 错误消息
        field: 字段名称
        value: 实际值
        constraint: 约束描述

    Example:
        >>> raise ValidationError(
        ...     "查询模式无效",
        ...     field="mode",
        ...     value="invalid",
        ...     constraint="必须是 naive, local, global, hybrid, mix, bypass 之一"
        ... )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
    ):
        """初始化验证错误。

        Args:
            message: 错误消息
            field: 字段名称
            value: 实际值
            constraint: 约束描述
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]  # 限制长度
        if constraint:
            details["constraint"] = constraint

        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=details
        )
        self.field = field
        self.value = value
        self.constraint = constraint


class QueryTimeoutError(MedGraphSDKError):
    """查询超时错误。

    当查询执行时间超过限制时抛出。

    Attributes:
        message: 错误消息
        timeout_seconds: 超时时间（秒）
        query: 查询文本

    Example:
        >>> raise QueryTimeoutError("查询超时", timeout_seconds=30.0, query="MATCH (n) RETURN n")
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        query: Optional[str] = None,
    ):
        """初始化查询超时错误。

        Args:
            message: 错误消息
            timeout_seconds: 超时时间（秒）
            query: 查询文本
        """
        details = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        if query:
            details["query"] = query[:100]  # 限制长度

        super().__init__(message=message, error_code="QUERY_TIMEOUT", details=details)
        self.timeout_seconds = timeout_seconds
        self.query = query


class RateLimitError(MedGraphSDKError):
    """速率限制错误。

    当请求超过 API 速率限制时抛出。

    Attributes:
        message: 错误消息
        limit: 限制次数
        window: 时间窗口（秒）
        retry_after: 重试等待时间（秒）

    Example:
        >>> raise RateLimitError("超出速率限制", limit=100, window=60, retry_after=30)
    """

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        """初始化速率限制错误。

        Args:
            message: 错误消息
            limit: 限制次数
            window: 时间窗口（秒）
            retry_after: 重试等待时间（秒）
        """
        details = {}
        if limit is not None:
            details["limit"] = limit
        if window is not None:
            details["window_seconds"] = window
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message, error_code="RATE_LIMIT_ERROR", details=details
        )
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


def convert_core_exception(e: Exception) -> MedGraphSDKError:
    """将核心层异常转换为 SDK 异常。

    这个函数用于在 SDK 层捕获核心层异常并转换为用户友好的 SDK 异常。

    Args:
        e: 核心层异常

    Returns:
        MedGraphSDKError: 转换后的 SDK 异常

    Example:
        >>> try:
        ...     # 调用核心层代码
        ...     raise Exception("核心层错误")
        ... except Exception as e:
        ...     sdk_error = convert_core_exception(e)
        ...     raise sdk_error from e
    """
    from src.core.exceptions import (
        DocumentError as CoreDocumentError,
        QueryError as CoreQueryError,
        GraphError as CoreGraphError,
        ConfigError as CoreConfigError,
        ValidationError as CoreValidationError,
        NotFoundError as CoreNotFoundError,
        StorageError as CoreStorageError,
        AuthenticationError as CoreAuthenticationError,
        RateLimitError as CoreRateLimitError,
    )

    # 映射核心异常到 SDK 异常
    exception_map = {
        CoreDocumentError: DocumentNotFoundError,
        CoreQueryError: ValidationError,
        CoreGraphError: ValidationError,
        CoreConfigError: ConfigError,
        CoreValidationError: ValidationError,
        CoreNotFoundError: DocumentNotFoundError,
        CoreStorageError: ConnectionError,
        CoreAuthenticationError: ConfigError,
        CoreRateLimitError: RateLimitError,
    }

    # 查找对应的 SDK 异常类
    for core_exc, sdk_exc_class in exception_map.items():
        if isinstance(e, core_exc):
            # 尝试从核心异常中提取详细信息
            kwargs = {}
            if hasattr(e, "message"):
                kwargs["message"] = str(e.message)
            else:
                kwargs["message"] = str(e)

            # 根据不同的异常类型添加特定参数
            if isinstance(e, CoreDocumentError) and hasattr(e, "doc_id"):
                kwargs["doc_id"] = e.doc_id
            elif isinstance(e, CoreConfigError):
                if hasattr(e, "config_key"):
                    kwargs["config_key"] = e.config_key
                if hasattr(e, "config_file"):
                    kwargs["config_file"] = e.config_file
            elif isinstance(e, CoreValidationError):
                if hasattr(e, "field"):
                    kwargs["field"] = e.field
                if hasattr(e, "value"):
                    kwargs["value"] = e.value
                if hasattr(e, "constraint"):
                    kwargs["constraint"] = e.constraint
            elif isinstance(e, CoreStorageError):
                if hasattr(e, "storage_type"):
                    kwargs["service"] = e.storage_type
            elif isinstance(e, CoreRateLimitError):
                if hasattr(e, "limit"):
                    kwargs["limit"] = e.limit
                if hasattr(e, "window"):
                    kwargs["window"] = e.window
                if hasattr(e, "retry_after"):
                    kwargs["retry_after"] = e.retry_after

            return sdk_exc_class(**kwargs)

    # 默认返回通用 SDK 异常
    return MedGraphSDKError(str(e))


# ========== 导出列表 ==========

__all__ = [
    "MedGraphSDKError",
    "ConfigError",
    "DocumentNotFoundError",
    "ConnectionError",
    "ValidationError",
    "QueryTimeoutError",
    "RateLimitError",
    "convert_core_exception",
]
