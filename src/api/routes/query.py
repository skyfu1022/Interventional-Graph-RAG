"""
查询 API 路由模块。

该模块提供查询相关的 REST API 端点，包括：
- POST /api/v1/query - 执行普通查询
- POST /api/v1/query/stream - 流式查询（SSE）
- POST /api/v1/query/intelligent - 智能查询（使用 LangGraph 工作流）

所有端点都基于 SDK 的 MedGraphClient 实现。
"""

from typing import AsyncIterator
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi import status

from src.sdk.client import MedGraphClient
from src.sdk.types import QueryResult
from src.api.deps import get_client
from src.api.schemas import (
    QueryRequest,
    QueryResponse,
    StreamQueryRequest,
)
from src.core.logging import get_logger
from src.core.exceptions import QueryError, ValidationError as CoreValidationError

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


# ========== 辅助函数 ==========


def convert_sdk_result_to_response(sdk_result: QueryResult) -> QueryResponse:
    """将 SDK QueryResult 转换为 API QueryResponse。

    Args:
        sdk_result: SDK 查询结果

    Returns:
        API 查询响应
    """
    return QueryResponse(
        query=sdk_result.query,
        answer=sdk_result.answer,
        mode=sdk_result.mode.value,
        graph_id=sdk_result.graph_id,
        sources=sdk_result.sources,
        context=sdk_result.context,
        graph_context=sdk_result.graph_context,
        retrieval_count=sdk_result.retrieval_count,
        latency_ms=sdk_result.latency_ms,
    )


async def stream_query_response(
    query_text: str,
    mode: str,
    graph_id: str,
    client: MedGraphClient,
) -> AsyncIterator[str]:
    """流式查询响应生成器。

    该异步生成器将查询结果以 SSE 格式流式返回。

    Args:
        query_text: 查询文本
        mode: 查询模式
        graph_id: 图谱 ID
        client: MedGraphClient 实例

    Yields:
        str: SSE 格式的数据块
    """
    try:
        async for chunk in client.query_stream(
            query_text=query_text,
            mode=mode,
            graph_id=graph_id,
        ):
            # 发送文本块
            data = {"chunk": chunk}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 发送完成信号
        done_data = {"done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"流式查询错误: {e}", exc_info=True)
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


# ========== API 端点 ==========


@router.post(
    "",
    response_model=QueryResponse,
    summary="执行查询",
    description="执行知识图谱查询，返回完整结果。",
    tags=["query"],
)
async def execute_query(
    request: QueryRequest,
    client: MedGraphClient = Depends(get_client),
) -> QueryResponse:
    """执行查询。

    该端点接收查询请求，调用 SDK 的 query 方法，
    并返回完整的查询结果。

    Args:
        request: 查询请求
        client: MedGraphClient 实例（通过依赖注入）

    Returns:
        QueryResponse: 查询响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 查询执行失败

    Example:
        >>> POST /api/v1/query
        >>> {
        >>>     "query": "什么是糖尿病?",
        >>>     "mode": "hybrid",
        >>>     "graph_id": "medical"
        >>> }
    """
    logger.info(
        f"收到查询请求 | 模式: {request.mode} | "
        f"图谱: {request.graph_id} | 查询: {request.query[:100]}..."
    )

    try:
        # 调用 SDK 的 query 方法
        sdk_result = await client.query(
            query_text=request.query,
            mode=request.mode,
            graph_id=request.graph_id,
        )

        # 转换为 API 响应格式
        response = convert_sdk_result_to_response(sdk_result)

        logger.info(
            f"查询完成 | 耗时: {response.latency_ms}ms | "
            f"检索次数: {response.retrieval_count} | "
            f"答案长度: {len(response.answer)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"查询参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"查询执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
                "query_text": getattr(e, "query_text", None),
            },
        ) from e

    except Exception as e:
        logger.error(f"查询处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "查询处理失败，请稍后重试",
            },
        ) from e


@router.post(
    "/stream",
    summary="流式查询",
    description="执行流式查询，以 Server-Sent Events (SSE) 格式返回结果。",
    tags=["query"],
)
async def execute_stream_query(
    request: StreamQueryRequest,
    http_request: Request,
    client: MedGraphClient = Depends(get_client),
) -> StreamingResponse:
    """执行流式查询。

    该端点接收流式查询请求，以 Server-Sent Events (SSE) 格式
    逐块返回查询结果。

    SSE 格式：
    - data: {"chunk": "文本片段"}
    - data: {"done": true}

    Args:
        request: 流式查询请求
        http_request: FastAPI Request 对象
        client: MedGraphClient 实例（通过依赖注入）

    Returns:
        StreamingResponse: 流式响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 流式查询执行失败

    Example:
        >>> POST /api/v1/query/stream
        >>> {
        >>>     "query": "详细说明糖尿病的病因",
        >>>     "mode": "hybrid"
        >>> }
    """
    logger.info(
        f"收到流式查询请求 | 模式: {request.mode} | "
        f"图谱: {request.graph_id} | 查询: {request.query[:100]}..."
    )

    try:
        # 检查客户端是否断开连接
        if await http_request.is_disconnected():
            logger.info("客户端已断开连接")
            raise HTTPException(
                status_code=status.HTTP_499_REQUEST_CANCELLED,
                detail="客户端已断开连接",
            )

        # 创建流式响应
        return StreamingResponse(
            stream_query_response(
                query_text=request.query,
                mode=request.mode,
                graph_id=request.graph_id,
                client=client,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            },
        )

    except CoreValidationError as e:
        logger.warning(f"流式查询参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"流式查询处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "流式查询处理失败，请稍后重试",
            },
        ) from e


@router.post(
    "/intelligent",
    response_model=QueryResponse,
    summary="智能查询",
    description="使用 LangGraph 工作流执行智能查询，支持多轮对话和上下文管理。",
    tags=["query"],
)
async def execute_intelligent_query(
    request: QueryRequest,
    client: MedGraphClient = Depends(get_client),
) -> QueryResponse:
    """执行智能查询。

    该端点使用 LangGraph 工作流执行智能查询，支持：
    - 多轮对话（通过 conversation_history）
    - 上下文管理
    - 自定义参数

    Args:
        request: 智能查询请求
        client: MedGraphClient 实例（通过依赖注入）

    Returns:
        QueryResponse: 查询响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 智能查询执行失败

    Example:
        >>> POST /api/v1/query/intelligent
        >>> {
        >>>     "query": "它有哪些症状?",
        >>>     "mode": "hybrid",
        >>>     "conversation_history": [
        >>>         {"role": "user", "content": "什么是糖尿病?"},
        >>>         {"role": "assistant", "content": "糖尿病是..."}
        >>>     ]
        >>> }
    """
    history_count = (
        len(request.conversation_history) if request.conversation_history else 0
    )
    logger.info(
        f"收到智能查询请求 | 模式: {request.mode} | "
        f"图谱: {request.graph_id} | 对话历史: {history_count} 条"
    )

    try:
        # 准备额外的查询参数
        query_kwargs: dict[str, object] = {}

        # 添加对话历史
        if request.conversation_history:
            query_kwargs["conversation_history"] = request.conversation_history

        # 添加自定义参数
        if request.custom_params:
            query_kwargs.update(request.custom_params)

        # 调用 SDK 的 query 方法（智能查询使用相同的底层方法）
        sdk_result = await client.query(
            query_text=request.query,
            mode=request.mode,
            graph_id=request.graph_id,
            **query_kwargs,
        )

        # 转换为 API 响应格式
        response = convert_sdk_result_to_response(sdk_result)

        logger.info(
            f"智能查询完成 | 耗时: {response.latency_ms}ms | "
            f"答案长度: {len(response.answer)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"智能查询参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"智能查询执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
                "query_text": getattr(e, "query_text", None),
            },
        ) from e

    except Exception as e:
        logger.error(f"智能查询处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "智能查询处理失败，请稍后重试",
            },
        ) from e


# ========== 健康检查端点 ==========


@router.get(
    "/health",
    summary="查询服务健康检查",
    description="检查查询服务是否正常运行。",
    tags=["query"],
)
async def health_check() -> dict[str, str]:
    """查询服务健康检查。

    Returns:
        包含服务状态的字典
    """
    return {
        "service": "query",
        "status": "healthy",
    }


__all__ = ["router"]
