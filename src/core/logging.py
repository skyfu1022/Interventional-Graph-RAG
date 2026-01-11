"""
Medical Graph RAG 日志系统模块

本模块基于 loguru 提供完整的日志配置功能，支持：
- 控制台输出（带颜色）
- 文件输出（支持轮转和压缩）
- 结构化日志（JSON 格式）
- 请求 ID 跟踪
- 异常捕获
- 性能监控
"""

import sys
import logging
import uuid
import time
import json
from pathlib import Path
from typing import Optional, Any, Dict, Callable
from contextvars import ContextVar
from functools import wraps
from loguru import logger

# 上下文变量用于存储请求 ID
REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="")
SESSION_ID_CTX: ContextVar[str] = ContextVar("session_id", default="")


class LoggingConfig:
    """日志配置类

    用于集中管理日志配置参数
    """

    def __init__(
        self,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        log_dir: str = "./logs",
        rotation: str = "10 MB",
        retention: str = "30 days",
        compression: str = "zip",
        json_format: bool = False,
        enable_console: bool = True,
        enable_file: bool = True,
        console_level: str = "INFO",
        file_level: str = "DEBUG"
    ):
        """初始化日志配置

        Args:
            log_level: 默认日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: 日志文件名（默认使用 app.log）
            log_dir: 日志目录路径
            rotation: 日志轮转大小或时间
            retention: 日志保留时间
            compression: 压缩格式
            json_format: 是否使用 JSON 格式输出
            enable_console: 是否启用控制台输出
            enable_file: 是否启用文件输出
            console_level: 控制台日志级别
            file_level: 文件日志级别
        """
        self.log_level = log_level
        self.log_file = log_file or "app.log"
        self.log_dir = log_dir
        self.rotation = rotation
        self.retention = retention
        self.compression = compression
        self.json_format = json_format
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.console_level = console_level
        self.file_level = file_level

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """从环境变量创建配置

        Returns:
            LoggingConfig 实例
        """
        import os

        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            log_dir=os.getenv("LOG_DIR", "./logs"),
            rotation=os.getenv("LOG_ROTATION", "10 MB"),
            retention=os.getenv("LOG_RETENTION", "30 days"),
            compression=os.getenv("LOG_COMPRESSION", "zip"),
            json_format=os.getenv("LOG_JSON", "false").lower() == "true",
            enable_console=os.getenv("LOG_CONSOLE", "true").lower() == "true",
            enable_file=os.getenv("LOG_FILE_ENABLED", "true").lower() == "true",
            console_level=os.getenv("LOG_CONSOLE_LEVEL", "INFO"),
            file_level=os.getenv("LOG_FILE_LEVEL", "DEBUG")
        )


class RequestIdFilter:
    """请求 ID 过滤器

    为每条日志添加请求 ID 和会话 ID
    """

    def __init__(self):
        self.request_id = ""
        self.session_id = ""

    def __call__(self, record: "dict") -> bool:
        """为日志记录添加上下文信息

        Args:
            record: 日志记录字典

        Returns:
            True（始终返回 True 以允许所有日志通过）
        """
        request_id = REQUEST_ID_CTX.get()
        session_id = SESSION_ID_CTX.get()

        record["extra"]["request_id"] = request_id
        record["extra"]["session_id"] = session_id

        return True


def setup_logging(config: Optional[LoggingConfig] = None, **kwargs) -> None:
    """配置日志系统

    Args:
        config: 日志配置对象（可选）
        **kwargs: 直接传递的配置参数（优先级高于 config）

    Examples:
        >>> # 使用默认配置
        >>> setup_logging()

        >>> # 使用自定义配置
        >>> config = LoggingConfig(log_level="DEBUG", json_format=True)
        >>> setup_logging(config)

        >>> # 使用关键字参数
        >>> setup_logging(log_level="DEBUG", log_dir="./my_logs")
    """
    # 合并配置
    if config is None:
        config = LoggingConfig.from_env()

    # 更新配置（kwargs 优先级更高）
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    # 移除默认处理器
    logger.remove()

    # 创建请求 ID 过滤器
    request_filter = RequestIdFilter()

    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<yellow>Req:{extra[request_id]}</yellow> | "
        "<level>{message}</level>"
    )

    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "Req:{extra[request_id]} | "
        "Sess:{extra[session_id]} | "
        "{message}"
    )

    # JSON 格式化函数
    def json_formatter(record):
        """格式化日志记录为 JSON"""
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "request_id": record["extra"].get("request_id", ""),
            "session_id": record["extra"].get("session_id", ""),
            "message": record["message"],
        }

        # 添加异常信息（如果有）
        if record["exception"]:
            log_entry["exception"] = str(record["exception"])

        # 添加额外的上下文信息
        for key, value in record["extra"].items():
            if key not in ["request_id", "session_id"]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False) + "\n"

    json_format_str = json_formatter

    # 添加控制台处理器
    if config.enable_console:
        logger.add(
            sys.stdout,
            level=config.console_level,
            format=console_format,
            colorize=True,
            backtrace=True,
            diagnose=True,
            filter=request_filter
        )

    # 添加文件处理器
    if config.enable_file:
        log_path = Path(config.log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        full_log_path = log_path / config.log_file

        logger.add(
            full_log_path,
            level=config.file_level,
            format=json_format_str if config.json_format else file_format,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            enqueue=True,  # 异步写入
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
            filter=request_filter
        )

        # 添加错误日志文件（单独存储 ERROR 和 CRITICAL）
        error_log_path = log_path / f"{config.log_file.rsplit('.', 1)[0]}_error.log"
        logger.add(
            error_log_path,
            level="ERROR",
            format=json_format_str if config.json_format else file_format,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
            filter=request_filter
        )

    logger.info(f"日志系统初始化完成 | 级别: {config.log_level} | 目录: {config.log_dir}")


def get_logger(name: str, **extra):
    """获取指定名称的 logger

    Args:
        name: logger 名称（通常使用模块名）
        **extra: 额外的上下文信息

    Returns:
        绑定了名称和上下文的 logger 实例

    Examples:
        >>> logger = get_logger("my_module")
        >>> logger.info("这是一条日志")

        >>> # 添加额外上下文
        >>> logger = get_logger("my_module", user_id="123")
        >>> logger.info("用户操作日志")
    """
    return logger.bind(name=name, **extra)


def set_request_id(request_id: Optional[str] = None) -> str:
    """设置当前请求的 ID

    Args:
        request_id: 请求 ID（如果不提供，则自动生成 UUID）

    Returns:
        请求 ID

    Examples:
        >>> request_id = set_request_id()
        >>> logger.info("处理请求")

        >>> # 使用自定义 ID
        >>> request_id = set_request_id("req-12345")
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]

    REQUEST_ID_CTX.set(request_id)
    return request_id


def get_request_id() -> str:
    """获取当前请求的 ID

    Returns:
        当前请求 ID
    """
    return REQUEST_ID_CTX.get()


def set_session_id(session_id: Optional[str] = None) -> str:
    """设置当前会话的 ID

    Args:
        session_id: 会话 ID（如果不提供，则自动生成 UUID）

    Returns:
        会话 ID
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    SESSION_ID_CTX.set(session_id)
    return session_id


def get_session_id() -> str:
    """获取当前会话的 ID

    Returns:
        当前会话 ID
    """
    return SESSION_ID_CTX.get()


def intercept_standard_logging(level: int = logging.INFO) -> None:
    """拦截标准库 logging 的日志输出

    将使用标准 logging 库的第三方库（如 requests、httpx 等）的
    日志重定向到 loguru

    Args:
        level: 拦截的日志级别

    Examples:
        >>> intercept_standard_logging()
    """
    logging.basicConfig(level=level, handlers=[])

    class InterceptHandler(logging.Handler):
        """标准日志拦截处理器"""

        def emit(self, record: logging.LogRecord) -> None:
            """将标准日志转换为 loguru 日志"""
            # 获取对应的 loguru 日志级别
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # 查找调用者
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # 配置所有标准日志记录器
    for name in logging.root.manager.loggerDict.keys():
        if name.startswith("uvicorn.") or name.startswith("fastapi."):
            continue

        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


def log_execution_time(func: Optional[Callable] = None, *, level: str = "DEBUG") -> Callable:
    """装饰器：记录函数执行时间

    Args:
        func: 被装饰的函数
        level: 日志级别

    Returns:
        装饰后的函数

    Examples:
        >>> @log_execution_time
        >>> def my_function():
        ...     pass

        >>> @log_execution_time(level="INFO")
        >>> def slow_function():
        ...     time.sleep(1)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            logger_local = logger.bind(function=f.__name__)
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time

                logger_local.opt(depth=1).log(
                    level,
                    f"函数执行完成 | 耗时: {execution_time:.4f}秒"
                )

                return result
            except Exception as e:
                execution_time = time.time() - start_time

                logger_local.opt(depth=1, exception=e).error(
                    f"函数执行失败 | 耗时: {execution_time:.4f}秒"
                )

                raise

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def log_async_execution_time(func: Optional[Callable] = None, *, level: str = "DEBUG") -> Callable:
    """装饰器：记录异步函数执行时间

    Args:
        func: 被装饰的异步函数
        level: 日志级别

    Returns:
        装饰后的异步函数

    Examples:
        >>> @log_async_execution_time
        >>> async def my_async_function():
        ...     await asyncio.sleep(1)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def wrapper(*args, **kwargs):
            logger_local = logger.bind(function=f.__name__)
            start_time = time.time()

            try:
                result = await f(*args, **kwargs)
                execution_time = time.time() - start_time

                logger_local.opt(depth=1).log(
                    level,
                    f"异步函数执行完成 | 耗时: {execution_time:.4f}秒"
                )

                return result
            except Exception as e:
                execution_time = time.time() - start_time

                logger_local.opt(depth=1, exception=e).error(
                    f"异步函数执行失败 | 耗时: {execution_time:.4f}秒"
                )

                raise

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


class LogContext:
    """日志上下文管理器

    用于临时设置请求 ID 和会话 ID

    Examples:
        >>> with LogContext(request_id="req-123", session_id="sess-456"):
        ...     logger.info("这条日志会包含上下文信息")
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **extra
    ):
        """初始化日志上下文

        Args:
            request_id: 请求 ID
            session_id: 会话 ID
            **extra: 其他上下文信息
        """
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.session_id = session_id or str(uuid.uuid4())
        self.extra = extra
        self.token_request = None
        self.token_session = None

    def __enter__(self):
        """进入上下文"""
        self.token_request = REQUEST_ID_CTX.set(self.request_id)
        self.token_session = SESSION_ID_CTX.set(self.session_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.token_request:
            REQUEST_ID_CTX.reset(self.token_request)
        if self.token_session:
            SESSION_ID_CTX.reset(self.token_session)
        return False


# 导出的公共接口
__all__ = [
    "setup_logging",
    "get_logger",
    "LoggingConfig",
    "set_request_id",
    "get_request_id",
    "set_session_id",
    "get_session_id",
    "intercept_standard_logging",
    "log_execution_time",
    "log_async_execution_time",
    "LogContext",
    "logger",
]
