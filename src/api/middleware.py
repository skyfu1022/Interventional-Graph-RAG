"""
API 中间件模块。

本模块提供速率限制中间件，基于 IP 地址实现简单的速率限制功能。
支持可配置的时间窗口和请求限制，使用内存存储（可扩展为 Redis）。

遵循 PEP 8 标准，包含完整的类型提示和 Google 风格文档字符串。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from src.core.logging import get_logger


logger = get_logger(__name__)


class RateLimiter:
    """
    基于内存的速率限制器。

    使用滑动窗口算法实现速率限制，支持多个 IP 地址独立限制。
    存储请求时间戳，并在时间窗口内计数请求次数。

    Attributes:
        requests_per_window: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口长度（秒）
        requests: 存储每个 IP 的请求时间戳的字典

    Example:
        >>> limiter = RateLimiter(requests_per_window=10, window_seconds=60)
        >>> limiter.is_allowed("192.168.1.1")
        True
    """

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
    ) -> None:
        """
        初始化速率限制器。

        Args:
            requests_per_window: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口长度（秒）
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

        logger.info(
            f"速率限制器已初始化: {requests_per_window} 请求 / {window_seconds} 秒"
        )

    def is_allowed(self, identifier: str) -> bool:
        """
        检查请求是否允许通过。

        使用滑动窗口算法检查指定标识符（通常是 IP 地址）
        是否超过速率限制。

        Args:
            identifier: 唯一标识符（通常是客户端 IP 地址）

        Returns:
            bool: 如果请求允许通过返回 True，否则返回 False

        Example:
            >>> limiter = RateLimiter(requests_per_window=10, window_seconds=60)
            >>> if limiter.is_allowed("192.168.1.1"):
            >>>     # 处理请求
            >>>     pass
            >>> else:
            >>>     # 返回 429 错误
            >>>     pass
        """
        current_time = time.time()

        # 获取该标识符的请求历史
        request_times = self.requests[identifier]

        # 移除时间窗口外的旧请求
        window_start = current_time - self.window_seconds
        self.requests[identifier] = [
            req_time for req_time in request_times if req_time > window_start
        ]

        # 检查是否超过限制
        if len(self.requests[identifier]) >= self.requests_per_window:
            logger.warning(
                f"速率限制触发: 标识符={identifier}, "
                f"请求数={len(self.requests[identifier])}, "
                f"限制={self.requests_per_window}"
            )
            return False

        # 记录当前请求
        self.requests[identifier].append(current_time)
        return True

    def get_remaining_requests(self, identifier: str) -> int:
        """
        获取指定标识符的剩余请求数。

        Args:
            identifier: 唯一标识符（通常是客户端 IP 地址）

        Returns:
            int: 剩余的请求数

        Example:
            >>> limiter = RateLimiter(requests_per_window=10, window_seconds=60)
            >>> remaining = limiter.get_remaining_requests("192.168.1.1")
        """
        current_time = time.time()
        request_times = self.requests[identifier]

        # 移除时间窗口外的旧请求
        window_start = current_time - self.window_seconds
        valid_requests = [
            req_time for req_time in request_times if req_time > window_start
        ]

        return max(0, self.requests_per_window - len(valid_requests))

    def reset(self, identifier: str) -> None:
        """
        重置指定标识符的请求计数。

        Args:
            identifier: 唯一标识符（通常是客户端 IP 地址）

        Example:
            >>> limiter = RateLimiter()
            >>> limiter.reset("192.168.1.1")
        """
        if identifier in self.requests:
            del self.requests[identifier]
            logger.debug(f"已重置标识符的速率限制: {identifier}")


def get_client_ip(request: Request) -> str:
    """
    获取客户端 IP 地址。

    优先从代理头部（X-Forwarded-For, X-Real-IP）获取真实 IP，
    如果没有则使用直接连接的 IP。

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 客户端 IP 地址

    Example:
        >>> ip = get_client_ip(request)
        >>> assert ip == "192.168.1.1"
    """
    # 检查代理头部
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()

    # 检查 X-Real-IP 头部
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 使用客户端地址
    if request.client:
        return request.client.host

    # 如果无法获取 IP，返回默认值
    return "unknown"


def create_rate_limiter_from_env() -> RateLimiter:
    """
    从环境变量创建速率限制器。

    从环境变量 RATE_LIMIT_REQUESTS 和 RATE_LIMIT_WINDOW
    读取速率限制配置。

    Returns:
        RateLimiter: 配置好的速率限制器实例

    Example:
        >>> # 设置环境变量:
        >>> # export RATE_LIMIT_REQUESTS=100
        >>> # export RATE_LIMIT_WINDOW=60
        >>> limiter = create_rate_limiter_from_env()
    """
    requests_per_window = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    window_seconds = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    return RateLimiter(
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )


class RateLimitMiddleware:
    """
    速率限制中间件。

    FastAPI 中间件，用于在请求处理前进行速率限制检查。
    超过限制的请求将返回 429 (Too Many Requests) 错误。

    Attributes:
        limiter: 速率限制器实例
        enabled: 是否启用速率限制

    Example:
        >>> app = FastAPI()
        >>> limiter = RateLimiter(requests_per_window=100, window_seconds=60)
        >>> middleware = RateLimitMiddleware(limiter=limiter, enabled=True)
        >>> app.middleware("http")(middleware)
    """

    def __init__(
        self,
        limiter: RateLimiter | None = None,
        enabled: bool = True,
    ) -> None:
        """
        初始化速率限制中间件。

        Args:
            limiter: 速率限制器实例，如果为 None 则从环境变量创建
            enabled: 是否启用速率限制
        """
        if limiter is None:
            self.limiter = create_rate_limiter_from_env()
        else:
            self.limiter = limiter

        self.enabled = enabled

        if enabled:
            logger.info("速率限制中间件已启用")
        else:
            logger.warning("速率限制中间件已禁用")

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        处理请求并应用速率限制。

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应对象

        Raises:
            HTTPException: 当超过速率限制时抛出 429 错误

        Example:
            >>> middleware = RateLimitMiddleware()
            >>> response = await middleware(request, call_next)
        """
        # 如果未启用速率限制，直接调用下一个处理器
        if not self.enabled:
            return await call_next(request)

        # 获取客户端 IP
        client_ip = get_client_ip(request)

        # 检查是否超过速率限制
        if not self.limiter.is_allowed(client_ip):
            remaining = self.limiter.get_remaining_requests(client_ip)
            logger.warning(f"速率限制: IP={client_ip}, 剩余请求={remaining}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "detail": (
                        f"超过速率限制。每个 IP 地址在 "
                        f"{self.limiter.window_seconds} 秒内最多 "
                        f"{self.limiter.requests_per_window} 个请求。"
                    ),
                    "remaining_requests": remaining,
                },
                headers={
                    "X-RateLimit-Limit": str(self.limiter.requests_per_window),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(
                        int(time.time()) + self.limiter.window_seconds
                    ),
                    "Retry-After": str(self.limiter.window_seconds),
                },
            )

        # 添加速率限制头信息
        remaining = self.limiter.get_remaining_requests(client_ip)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)

        return response


__all__ = [
    "RateLimiter",
    "RateLimitMiddleware",
    "get_client_ip",
    "create_rate_limiter_from_env",
]
