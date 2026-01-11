"""
核心异常处理模块。

该模块定义了 Medical Graph RAG 项目中使用的自定义异常类体系。
所有异常都继承自 MedGraphError 基类，提供统一的错误处理接口。

异常类特性:
- 支持错误码（error_code）用于精确识别错误类型
- 支持错误详情（details）字典用于携带上下文信息
- 提供 to_dict() 方法用于 API 响应
- 支持链式异常（保留原始异常信息）
- 支持中文错误消息
"""

from typing import Optional, Dict, Any


class MedGraphError(Exception):
    """SDK 基础异常类。

    所有项目自定义异常的基类，提供统一的错误处理接口。

    Attributes:
        message: 错误消息（中文）
        error_code: 错误码，默认为类名
        details: 错误详情字典，用于携带额外上下文信息

    Example:
        >>> err = MedGraphError("系统错误", error_code="SYS_001", details={"retry": True})
        >>> err.to_dict()
        {'error_type': 'MedGraphError', 'error_code': 'SYS_001', 'message': '系统错误', 'details': {'retry': True}}
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化异常。

        Args:
            message: 错误消息（中文）
            error_code: 错误码，如果不提供则使用类名
            details: 错误详情字典，可携带任意上下文信息
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式，用于 API 响应。

        Returns:
            包含异常信息的字典，包括错误类型、错误码、消息和详情
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        """返回异常的字符串表示。"""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """返回异常的开发者表示。"""
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r}, details={self.details!r})"


class DocumentError(MedGraphError):
    """文档相关错误。

    用于文档摄入、处理、删除等操作失败的场景。

    Attributes:
        message: 错误消息
        doc_id: 关联的文档 ID（可选）
        details: 错误详情

    Example:
        >>> raise DocumentError("文档摄入失败", doc_id="doc-123")
    """

    def __init__(
        self,
        message: str,
        doc_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化文档错误。

        Args:
            message: 错误消息
            doc_id: 关联的文档 ID
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if doc_id:
            details["doc_id"] = doc_id
        super().__init__(message, error_code="DOCUMENT_ERROR", details=details)
        self.doc_id = doc_id


class QueryError(MedGraphError):
    """查询相关错误。

    用于查询执行、解析、结果处理等操作失败的场景。

    Attributes:
        message: 错误消息
        query_id: 关联的查询 ID（可选）
        query_text: 查询文本（可选）
        details: 错误详情

    Example:
        >>> raise QueryError("查询语法错误", query_text="MATCH (n) RETURN")
    """

    def __init__(
        self,
        message: str,
        query_id: Optional[str] = None,
        query_text: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化查询错误。

        Args:
            message: 错误消息
            query_id: 关联的查询 ID
            query_text: 查询文本
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if query_id:
            details["query_id"] = query_id
        if query_text:
            details["query_text"] = query_text
        super().__init__(message, error_code="QUERY_ERROR", details=details)
        self.query_id = query_id
        self.query_text = query_text


class GraphError(MedGraphError):
    """图谱相关错误。

    用于图谱构建、遍历、更新等操作失败的场景。

    Attributes:
        message: 错误消息
        graph_id: 关联的图谱 ID（可选）
        entity_type: 涉及的实体类型（可选）
        details: 错误详情

    Example:
        >>> raise GraphError("图谱构建失败", graph_id="graph-456")
    """

    def __init__(
        self,
        message: str,
        graph_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化图谱错误。

        Args:
            message: 错误消息
            graph_id: 关联的图谱 ID
            entity_type: 涉及的实体类型
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if graph_id:
            details["graph_id"] = graph_id
        if entity_type:
            details["entity_type"] = entity_type
        super().__init__(message, error_code="GRAPH_ERROR", details=details)
        self.graph_id = graph_id
        self.entity_type = entity_type


class ConfigError(MedGraphError):
    """配置相关错误。

    用于配置加载、验证、解析等操作失败的场景。

    Attributes:
        message: 错误消息
        config_key: 关联的配置键（可选）
        config_file: 配置文件路径（可选）
        details: 错误详情

    Example:
        >>> raise ConfigError("配置项缺失", config_key="neo4j.uri")
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化配置错误。

        Args:
            message: 错误消息
            config_key: 关联的配置键
            config_file: 配置文件路径
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, error_code="CONFIG_ERROR", details=details)
        self.config_key = config_key
        self.config_file = config_file


class AuthenticationError(MedGraphError):
    """认证错误。

    用于身份验证、授权、令牌验证等操作失败的场景。

    Attributes:
        message: 错误消息
        auth_method: 认证方式（可选）
        user_id: 关联的用户 ID（可选）
        details: 错误详情

    Example:
        >>> raise AuthenticationError("认证失败", auth_method="token")
    """

    def __init__(
        self,
        message: str,
        auth_method: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化认证错误。

        Args:
            message: 错误消息
            auth_method: 认证方式（如 "token", "api_key" 等）
            user_id: 关联的用户 ID
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if auth_method:
            details["auth_method"] = auth_method
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, error_code="AUTH_ERROR", details=details)
        self.auth_method = auth_method
        self.user_id = user_id


class StorageError(MedGraphError):
    """存储相关错误。

    用于底层存储（Neo4j、Milvus 等）操作失败的场景。

    Attributes:
        message: 错误消息
        storage_type: 存储类型（如 "neo4j", "milvus"）（可选）
        operation: 执行的操作（如 "connect", "query", "insert"）（可选）
        details: 错误详情

    Example:
        >>> raise StorageError("Neo4j 连接失败", storage_type="neo4j", operation="connect")
    """

    def __init__(
        self,
        message: str,
        storage_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化存储错误。

        Args:
            message: 错误消息
            storage_type: 存储类型（如 "neo4j", "milvus"）
            operation: 执行的操作
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if storage_type:
            details["storage_type"] = storage_type
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="STORAGE_ERROR", details=details)
        self.storage_type = storage_type
        self.operation = operation


class ValidationError(MedGraphError):
    """数据验证错误。

    用于输入数据验证失败的场景。

    Attributes:
        message: 错误消息
        field: 验证失败的字段（可选）
        value: 验证失败的值（可选）
        constraint: 违反的约束条件（可选）
        details: 错误详情

    Example:
        >>> raise ValidationError("字段值无效", field="email", value="invalid", constraint="must be valid email")
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化验证错误。

        Args:
            message: 错误消息
            field: 验证失败的字段名
            value: 验证失败的值
            constraint: 违反的约束条件描述
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if constraint:
            details["constraint"] = constraint
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)
        self.field = field
        self.value = value
        self.constraint = constraint


class NotFoundError(MedGraphError):
    """资源未找到错误。

    用于请求的资源不存在的场景。

    Attributes:
        message: 错误消息
        resource_type: 资源类型（如 "document", "graph", "user"）（可选）
        resource_id: 资源 ID（可选）
        details: 错误详情

    Example:
        >>> raise NotFoundError("文档不存在", resource_type="document", resource_id="doc-999")
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化资源未找到错误。

        Args:
            message: 错误消息
            resource_type: 资源类型
            resource_id: 资源 ID
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, error_code="NOT_FOUND", details=details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class RateLimitError(MedGraphError):
    """API 速率限制错误。

    用于超出 API 调用频率限制的场景。

    Attributes:
        message: 错误消息
        limit: 速率限制值（可选）
        window: 时间窗口（可选）
        retry_after: 建议重试的秒数（可选）
        details: 错误详情

    Example:
        >>> raise RateLimitError("超出速率限制", limit=100, window=60, retry_after=30)
    """

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化速率限制错误。

        Args:
            message: 错误消息
            limit: 速率限制值（如请求数量）
            window: 时间窗口（秒）
            retry_after: 建议重试的等待时间（秒）
            details: 额外的错误详情
        """
        if details is None:
            details = {}
        if limit is not None:
            details["limit"] = limit
        if window is not None:
            details["window"] = window
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", details=details)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
