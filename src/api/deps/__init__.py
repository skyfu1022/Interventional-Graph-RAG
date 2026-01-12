"""
API 依赖注入模块。

该模块提供 FastAPI 依赖注入函数，用于获取 MedGraphClient 实例。
"""

from typing import AsyncGenerator

from src.sdk.client import MedGraphClient
from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 全局客户端实例（单例模式）
_client: MedGraphClient | None = None


async def get_client() -> AsyncGenerator[MedGraphClient, None]:
    """获取 MedGraphClient 实例的依赖注入函数。

    该函数创建并返回一个 MedGraphClient 实例，使用单例模式
    确保整个应用生命周期中只有一个客户端实例。

    Yields:
        MedGraphClient: 客户端实例

    Example:
        >>> from fastapi import APIRouter, Depends
        >>> from src.api.deps import get_client
        >>>
        >>> router = APIRouter()
        >>>
        >>> @router.post("/query")
        >>> async def query(
        >>>     request: QueryRequest,
        >>>     client: MedGraphClient = Depends(get_client)
        >>> ):
        >>>     result = await client.query(request.query, mode=request.mode)
        >>>     return result
    """
    global _client

    if _client is None:
        logger.info("初始化 MedGraphClient 实例")
        try:
            # 从环境变量加载配置
            settings = get_settings()

            # 创建客户端实例
            _client = MedGraphClient(
                workspace=settings.rag_workspace,
                config=settings,
                enable_metrics=True,
            )

            # 初始化客户端
            await _client.initialize()

            logger.info(
                f"MedGraphClient 初始化成功 | 工作空间: {settings.rag_workspace}"
            )

        except Exception as e:
            logger.error(f"MedGraphClient 初始化失败: {e}", exc_info=True)
            raise RuntimeError(f"无法初始化 MedGraphClient: {e}") from e

    try:
        yield _client
    except Exception as e:
        logger.error(f"获取客户端实例时发生错误: {e}", exc_info=True)
        raise


async def close_client() -> None:
    """关闭 MedGraphClient 实例。

    该函数在应用关闭时调用，用于释放资源。

    Example:
        >>> from fastapi import FastAPI
        >>> from src.api.deps import close_client
        >>>
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("shutdown")
        >>> async def shutdown():
        >>>     await close_client()
    """
    global _client

    if _client is not None:
        logger.info("关闭 MedGraphClient 实例")
        try:
            await _client.close()
            _client = None
            logger.info("MedGraphClient 已关闭")
        except Exception as e:
            logger.error(f"关闭 MedGraphClient 时发生错误: {e}", exc_info=True)


__all__ = ["get_client", "close_client"]
