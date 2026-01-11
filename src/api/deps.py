"""FastAPI 依赖注入模块。

该模块提供所有 API 路由所需的依赖项，包括：
- MedGraphClient 实例
- 认证/授权（未来）
- 请求上下文（未来）

使用 FastAPI 的 Depends 机制实现依赖注入。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import HTTPException
from fastapi import status

from src.sdk.client import MedGraphClient
from src.sdk.exceptions import MedGraphSDKError
from src.core.logging import get_logger


logger = get_logger(__name__)


# ========== 全局客户端实例 ==========

# 全局客户端实例（单例模式）
_global_client: MedGraphClient | None = None


async def get_client() -> AsyncGenerator[MedGraphClient, None]:
    """获取 MedGraphClient 实例的依赖注入函数。

    使用 FastAPI 的 Depends 机制，为每个请求提供客户端实例。
    采用单例模式，全局只维护一个客户端实例。

    Yields:
        MedGraphClient: SDK 客户端实例

    Raises:
        HTTPException: 客户端初始化失败

    Example:
        >>> @router.get("/test")
        >>> async def test_endpoint(
        >>>     client: MedGraphClient = Depends(get_client)
        >>> ):
        >>>     result = await client.query("测试查询")
        >>>     return result
    """
    global _global_client

    try:
        # 如果全局客户端不存在，则创建并初始化
        if _global_client is None:
            logger.info("初始化 MedGraphClient 实例")
            _global_client = MedGraphClient.from_env()
            await _global_client.initialize()
            logger.info("MedGraphClient 初始化成功")

        yield _global_client

    except MedGraphSDKError as e:
        logger.error(f"SDK 客户端错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SDKError",
                "message": "服务初始化失败，请稍后重试",
                "detail": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"客户端初始化失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InitializationError",
                "message": "服务初始化失败，请稍后重试",
                "detail": str(e),
            },
        ) from e


async def close_client() -> None:
    """关闭全局客户端实例。

    通常在应用关闭时调用。

    Example:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        >>>     yield
        >>>     await close_client()
    """
    global _global_client

    if _global_client is not None:
        try:
            await _global_client.close()
            logger.info("MedGraphClient 已关闭")
        except Exception as e:
            logger.error(f"关闭客户端失败: {e}", exc_info=True)
        finally:
            _global_client = None


__all__ = ["get_client", "close_client"]
