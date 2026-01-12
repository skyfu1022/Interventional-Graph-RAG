"""
多模态查询 API 路由模块。

该模块提供多模态查询相关的 REST API 端点，包括：
- POST /api/v1/query/multimodal - 多模态查询（支持图像、表格）

支持文件上传（multipart/form-data），使用 FastAPI 的 UploadFile 处理。
基于 SDK 的 MedGraphClient 实现，使用依赖注入模式。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import base64
import tempfile
import os
from typing import Annotated, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, status

from src.sdk.client import MedGraphClient
from src.sdk.types import QueryResult, QueryMode
from src.api.deps import get_client
from src.api.schemas import QueryResponse
from src.core.logging import get_logger
from src.core.exceptions import QueryError, ValidationError as CoreValidationError


# ========== 日志配置 ==========

logger = get_logger(__name__)


# ========== 路由定义 ==========

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


async def process_upload_file(
    file: UploadFile,
    allowed_extensions: set[str],
    max_size_mb: int = 10,
) -> tuple[str, bytes]:
    """处理上传的文件。

    验证文件类型和大小，读取文件内容。

    Args:
        file: 上传的文件对象
        allowed_extensions: 允许的文件扩展名集合
        max_size_mb: 最大文件大小（MB）

    Returns:
        tuple[str, bytes]: (文件扩展名, 文件内容)

    Raises:
        HTTPException: 文件验证失败
    """
    # 验证文件名
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "文件名不能为空",
            },
        )

    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": f"不支持的文件类型: {file_ext}",
                "allowed_types": list(allowed_extensions),
            },
        )

    # 读取文件内容
    try:
        content = await file.read()

        # 验证文件大小
        max_size_bytes = max_size_mb * 1024 * 1024
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "FileTooLarge",
                    "message": f"文件大小超过限制: {max_size_mb}MB",
                    "file_size": len(content),
                    "max_size": max_size_bytes,
                },
            )

        logger.debug(
            f"文件读取成功 | 文件名: {file.filename} | "
            f"大小: {len(content)} 字节 | 类型: {file_ext}"
        )

        return file_ext, content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取文件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "FileReadError",
                "message": f"读取文件失败: {str(e)}",
            },
        ) from e


def encode_file_to_base64(content: bytes) -> str:
    """将文件内容编码为 Base64。

    Args:
        content: 文件内容（字节）

    Returns:
        str: Base64 编码的字符串
    """
    return base64.b64encode(content).decode("utf-8")


async def save_temp_file(
    content: bytes,
    suffix: str,
) -> str:
    """将内容保存到临时文件。

    Args:
        content: 文件内容
        suffix: 文件后缀名

    Returns:
        str: 临时文件路径

    Raises:
        HTTPException: 文件保存失败
    """
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            mode="wb",
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        logger.debug(f"临时文件创建成功 | 路径: {temp_file_path}")
        return temp_file_path

    except Exception as e:
        logger.error(f"创建临时文件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "TempFileError",
                "message": "创建临时文件失败",
            },
        ) from e


def cleanup_temp_file(file_path: str) -> None:
    """清理临时文件。

    Args:
        file_path: 临时文件路径
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"临时文件已删除 | 路径: {file_path}")
    except Exception as e:
        logger.warning(f"删除临时文件失败 | 路径: {file_path} | 错误: {e}")


# ========== API 端点 ==========


@router.post(
    "/multimodal",
    response_model=QueryResponse,
    summary="多模态查询",
    description="""
    执行多模态查询，支持文本查询结合图像或表格数据。

    支持的文件类型：
    - 图像: .jpg, .jpeg, .png, .gif
    - 表格: .csv, .xlsx, .xls

    最大文件大小: 10MB

    该端点使用多部分表单数据（multipart/form-data）上传文件。
    """,
    tags=["query", "multimodal"],
)
async def multimodal_query(
    query: Annotated[str, Form(description="查询文本")],
    image: Annotated[
        Optional[UploadFile],
        File(description="图像文件（可选）"),
    ] = None,
    table_data: Annotated[
        Optional[UploadFile],
        File(description="表格文件（可选）"),
    ] = None,
    mode: Annotated[
        QueryMode,
        Form(description="查询模式"),
    ] = QueryMode.HYBRID,
    graph_id: Annotated[
        Optional[str],
        Form(description="图谱 ID（可选）"),
    ] = None,
    client: MedGraphClient = Depends(get_client),
) -> QueryResponse:
    """执行多模态查询。

    该端点接收查询文本和可选的图像/表格文件，执行多模态查询。
    支持的场景包括：
    - 医学图像分析（X光片、CT片、MRI等）
    - 医学表格数据分析（实验室结果、病历数据等）
    - 结合文本和图像/表格的混合查询

    Args:
        query: 查询文本（必需）
        image: 图像文件（可选）
        table_data: 表格文件（可选）
        mode: 查询模式（默认：hybrid）
        graph_id: 图谱 ID（可选）
        client: MedGraphClient 实例（通过依赖注入）

    Returns:
        QueryResponse: 查询响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 413: 文件过大
        HTTPException 422: 文件处理失败
        HTTPException 500: 查询执行失败

    Example:
        >>> # 使用 curl 测试图像查询
        >>> curl -X POST "http://localhost:8000/api/v1/query/multimodal" \\
        >>>      -F "query=这张X光片显示什么？" \\
        >>>      -F "image=@xray.jpg" \\
        >>>      -F "mode=hybrid"
        >>>
        >>> # 使用 curl 测试表格查询
        >>> curl -X POST "http://localhost:8000/api/v1/query/multimodal" \\
        >>>      -F "query=分析这个血常规检查结果" \\
        >>>      -F "table_data=@blood_test.csv" \\
        >>>      -F "mode=hybrid"
    """
    logger.info(
        f"收到多模态查询请求 | 模式: {mode} | "
        f"图谱: {graph_id or '默认'} | 查询: {query[:100]}... | "
        f"图像: {image.filename if image else '无'} | "
        f"表格: {table_data.filename if table_data else '无'}"
    )

    # 验证至少有查询文本
    if not query or query.isspace():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "查询文本不能为空",
            },
        )

    # 验证至少上传了一个文件
    if not image and not table_data:
        logger.info("未上传文件，执行普通查询")
        # 如果没有上传文件，执行普通查询
        try:
            sdk_result = await client.query(
                query_text=query,
                mode=mode,
                graph_id=graph_id or "default",
            )
            response = convert_sdk_result_to_response(sdk_result)
            logger.info(f"查询完成 | 耗时: {response.latency_ms}ms")
            return response

        except CoreValidationError as e:
            logger.warning(f"查询参数验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ValidationError",
                    "message": str(e),
                },
            ) from e
        except QueryError as e:
            logger.error(f"查询执行失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "QueryError",
                    "message": str(e),
                },
            ) from e

    # 处理图像文件
    image_data_base64: Optional[str] = None
    image_type: Optional[str] = None
    temp_image_path: Optional[str] = None

    if image:
        allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif"}
        try:
            file_ext, content = await process_upload_file(
                file=image,
                allowed_extensions=allowed_image_extensions,
                max_size_mb=10,
            )

            # 保存到临时文件（供 SDK 使用）
            temp_image_path = await save_temp_file(content, file_ext)

            # 编码为 Base64（用于 Schema 验证）
            image_data_base64 = encode_file_to_base64(content)

            # 确定图像类型
            image_type_map = {
                ".jpg": "jpg",
                ".jpeg": "jpg",
                ".png": "png",
                ".gif": "gif",
            }
            image_type = image_type_map.get(file_ext, "jpg")

            logger.info(
                f"图像处理成功 | 类型: {image_type} | 大小: {len(content)} 字节"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"图像处理失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "ImageProcessingError",
                    "message": f"图像处理失败: {str(e)}",
                },
            ) from e

    # 处理表格文件
    table_data_dict: Optional[dict] = None
    temp_table_path: Optional[str] = None

    if table_data:
        allowed_table_extensions = {".csv", ".xlsx", ".xls"}
        try:
            file_ext, content = await process_upload_file(
                file=table_data,
                allowed_extensions=allowed_table_extensions,
                max_size_mb=10,
            )

            # 保存到临时文件（供 SDK 使用）
            temp_table_path = await save_temp_file(content, file_ext)

            # TODO: 解析表格数据为 JSON 格式
            # 这里可以添加表格解析逻辑，例如使用 pandas
            # table_data_dict = parse_table(content, file_ext)

            logger.info(f"表格处理成功 | 类型: {file_ext} | 大小: {len(content)} 字节")

        except HTTPException:
            # 清理已创建的临时文件
            if temp_image_path:
                cleanup_temp_file(temp_image_path)
            raise
        except Exception as e:
            logger.error(f"表格处理失败: {e}", exc_info=True)
            # 清理已创建的临时文件
            if temp_image_path:
                cleanup_temp_file(temp_image_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "TableProcessingError",
                    "message": f"表格处理失败: {str(e)}",
                },
            ) from e

    try:
        # 检查 SDK 是否支持多模态查询
        # 方法1: 检查是否有 multimodal_query 方法
        if hasattr(client, "multimodal_query"):
            logger.info("使用 SDK 的 multimodal_query 方法")
            sdk_result = await client.multimodal_query(
                query_text=query,
                image_data=image_data_base64,
                image_type=image_type,
                table_data=table_data_dict,
                mode=mode,
                graph_id=graph_id,
            )
        else:
            # 方法2: 使用普通 query 方法，添加提示信息
            logger.info("SDK 暂未实现多模态查询，使用普通查询方法")

            # 构建增强的查询文本
            enhanced_query = query
            if image:
                enhanced_query = f"[包含图像: {image.filename}] {query}"
            if table_data:
                enhanced_query = f"[包含表格: {table_data.filename}] {query}"

            sdk_result = await client.query(
                query_text=enhanced_query,
                mode=mode,
                graph_id=graph_id or "default",
            )

            # 添加提示信息到答案
            notice = (
                "\n\n[注意] SDK 暂未实现完整的多模态查询功能，"
                "已使用增强的文本查询。上传的文件仅供参考。"
            )
            sdk_result.answer = sdk_result.answer + notice

        # 转换为 API 响应格式
        response = convert_sdk_result_to_response(sdk_result)

        logger.info(
            f"多模态查询完成 | 耗时: {response.latency_ms}ms | "
            f"检索次数: {response.retrieval_count} | "
            f"答案长度: {len(response.answer)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"多模态查询参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
            },
        ) from e

    except QueryError as e:
        logger.error(f"多模态查询执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"多模态查询处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "多模态查询处理失败，请稍后重试",
            },
        ) from e

    finally:
        # 清理临时文件
        if temp_image_path:
            cleanup_temp_file(temp_image_path)
        if temp_table_path:
            cleanup_temp_file(temp_table_path)


# ========== 健康检查端点 ==========


@router.get(
    "/health",
    summary="多模态查询服务健康检查",
    description="检查多模态查询服务是否正常运行。",
    tags=["multimodal"],
)
async def health_check() -> dict[str, str]:
    """多模态查询服务健康检查。

    Returns:
        包含服务状态的字典
    """
    return {
        "service": "multimodal-query",
        "status": "healthy",
    }


__all__ = ["router"]
