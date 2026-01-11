"""
Medical Graph RAG - FastAPI 应用主入口

本模块创建并配置 FastAPI 应用实例,包括:
- CORS 中间件配置
- 速率限制中间件配置
- 路由注册
- 全局异常处理
- 生命周期管理
- OpenAPI 文档增强
- API Key 认证方案

遵循 PEP 8 标准,包含完整的类型提示和 Google 风格文档字符串。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from rich.console import Console

from src.api.middleware import RateLimitMiddleware
from src.api.routes import documents, graphs, query, multimodal
from src.api.deps import close_client
from src.core.logging import get_logger


logger = get_logger(__name__)
console = Console()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理器。

    处理应用启动和关闭时的初始化和清理工作。

    Args:
        app: FastAPI 应用实例

    Yields:
        None

    Example:
        >>> app = FastAPI(lifespan=lifespan)
    """
    # 启动时执行
    console.print("[bold green]正在启动 Medical Graph RAG API 服务器...[/]")
    logger.info("Application startup initiated")

    # 检查是否启用了 API Key 认证
    api_keys = os.getenv("API_KEYS", "")
    if api_keys:
        key_count = len([k.strip() for k in api_keys.split(",") if k.strip()])
        console.print(f"[bold cyan]✓ API Key 认证已启用 ({key_count} 个有效密钥)[/]")
    else:
        console.print("[bold yellow]⚠ API Key 认证未启用 (开发模式)[/]")

    # 检查是否启用了速率限制
    rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    if rate_limit_enabled:
        requests = os.getenv("RATE_LIMIT_REQUESTS", "100")
        window = os.getenv("RATE_LIMIT_WINDOW", "60")
        console.print(f"[bold cyan]✓ 速率限制已启用 ({requests} 请求 / {window} 秒)[/]")
    else:
        console.print("[bold yellow]⚠ 速率限制已禁用[/]")

    # TODO: 初始化数据库连接
    # TODO: 初始化 Neo4j 连接
    # TODO: 初始化 Milvus 连接
    # TODO: 加载 LLM 模型

    console.print("[bold green]✓ API 服务器启动成功[/]")
    yield

    # 关闭时执行
    console.print("[bold yellow]正在关闭 Medical Graph RAG API 服务器...[/]")
    logger.info("Application shutdown initiated")

    # 关闭 SDK 客户端
    await close_client()

    # TODO: 关闭数据库连接
    # TODO: 释放资源

    console.print("[bold green]✓ API 服务器已安全关闭[/]")


def custom_openapi() -> dict[str, object]:
    """
    自定义 OpenAPI 架构。

    生成包含完整认证方案和详细 API 文档的 OpenAPI 架构。

    Returns:
        dict: OpenAPI 架构字典

    Example:
        >>> app = FastAPI()
        >>> app.openapi = custom_openapi
    """
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=app.servers,
            tags=app.openapi_tags,
        )

        # 添加认证方案
        app.openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": (
                    "API Key 认证。在请求头中添加 `X-API-Key: your-api-key`。"
                    "如果未配置 API_KEYS 环境变量，则不需要认证。"
                ),
            }
        }

        # 为所有需要认证的路径添加安全要求
        # 注意: 这里只是示例，实际应该在路由定义中使用 dependencies
        for path, path_item in app.openapi_schema["paths"].items():
            # 跳过不需要认证的端点
            if path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
                continue

            # 为其他端点添加认证要求（可选）
            # 如果设置了 API_KEYS 环境变量，则启用认证
            if os.getenv("API_KEYS"):
                for method in path_item.values():
                    if isinstance(method, dict) and "operationId" in method:
                        method.setdefault("security", [{"ApiKeyAuth": []}])

    return app.openapi_schema



def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例。

    该函数创建一个 FastAPI 应用,配置所有必要的中间件、
    路由和异常处理器。

    Returns:
        FastAPI: 配置好的应用实例

    Example:
        >>> app = create_app()
        >>> # 用于 uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    app = FastAPI(
        title="Medical Graph RAG API",
        description="""
        医学知识图谱 RAG (Retrieval-Augmented Generation) 系统的 REST API。

        ## 功能特性

        * **文档管理**: 上传、删除、更新医学文档
        * **知识图谱**: 构建和查询医学知识图谱
        * **智能问答**: 基于图谱的医学问答系统
        * **多模态查询**: 支持图像和表格的多模态查询
        * **可视化**: 图谱可视化接口

        ## 认证方式

        本 API 支持 API Key 认证。如果配置了 `API_KEYS` 环境变量，
        则需要在请求头中提供有效的 API Key:

        ```
        X-API-Key: your-api-key-here
        ```

        如果未配置 `API_KEYS` 环境变量，则不需要认证（开发模式）。

        ## 速率限制

        本 API 实现了基于 IP 的速率限制。默认配置为：
        - 每个 IP 地址在 60 秒内最多 100 个请求

        可通过环境变量配置：
        - `RATE_LIMIT_ENABLED`: 是否启用速率限制 (默认: true)
        - `RATE_LIMIT_REQUESTS`: 时间窗口内的最大请求数 (默认: 100)
        - `RATE_LIMIT_WINDOW`: 时间窗口长度（秒） (默认: 60)

        超过限制时，API 将返回 `429 Too Many Requests` 错误。

        ## 技术栈

        * **LangGraph** - 工作流编排
        * **Neo4j** - 图数据库
        * **Milvus** - 向量数据库
        * **RAG-Anything** - 多模态文档处理
        * **FastAPI** - Web 框架
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "health",
                "description": "健康检查和系统状态端点",
            },
            {
                "name": "documents",
                "description": "文档管理接口，支持上传、删除和查询文档信息",
            },
            {
                "name": "graphs",
                "description": "知识图谱管理接口，支持图谱构建、可视化和导出",
            },
            {
                "name": "query",
                "description": "查询接口，支持多种检索模式和智能问答",
            },
            {
                "name": "multimodal",
                "description": "多模态查询接口，支持图像和表格数据分析",
            },
        ],
    )

    # 设置自定义 OpenAPI 架构
    app.openapi = custom_openapi

    # 配置 CORS
    # 注意: 生产环境应该限制具体的 origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该指定具体的域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加速率限制中间件
    rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    if rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware, enabled=True)

    # 注册路由
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(graphs.router, prefix="/api/v1/graphs", tags=["graphs"])
    app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
    app.include_router(multimodal.router, prefix="/api/v1/query", tags=["multimodal"])

    # 根路径
    @app.get(
        "/",
        tags=["health"],
        summary="根路径",
        description="返回 API 的基本信息和文档链接",
    )
    async def root() -> dict[str, str]:
        """
        根路径端点。

        返回 API 的基本信息。

        Returns:
            包含 API 名称和版本的字典
        """
        return {
            "name": "Medical Graph RAG API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
        }

    # 健康检查端点
    @app.get(
        "/health",
        tags=["health"],
        summary="健康检查",
        description="用于监控服务是否正常运行",
    )
    async def health_check() -> dict[str, str]:
        """
        健康检查端点。

        用于监控服务是否正常运行。

        Returns:
            包含健康状态的字典
        """
        return {
            "status": "healthy",
            "service": "medical-graph-rag-api",
            "version": "1.0.0",
        }

    # 全局异常处理器
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        请求验证异常处理器。

        处理请求参数验证失败的异常。

        Args:
            request: 请求对象
            exc: 验证异常

        Returns:
            JSONResponse: 错误响应
        """
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        通用异常处理器。

        处理所有未捕获的异常。

        Args:
            request: 请求对象
            exc: 异常对象

        Returns:
            JSONResponse: 错误响应
        """
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
            },
        )

    return app


# 创建应用实例
app = create_app()


__all__ = ["app", "create_app", "lifespan"]
