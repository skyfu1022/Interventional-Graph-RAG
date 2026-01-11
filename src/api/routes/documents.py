"""
文档管理 API 路由模块。

该模块提供文档摄入、查询、删除等 REST API 端点。
基于 SDK 的 MedGraphClient 实现，使用依赖注入模式。

功能：
- POST /api/v1/documents - 上传文档
- GET /api/v1/documents/{doc_id} - 获取文档详情
- DELETE /api/v1/documents/{doc_id} - 删除文档

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import tempfile
import os
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse

from src.sdk.client import MedGraphClient
from src.sdk.exceptions import (
    MedGraphSDKError,
    DocumentNotFoundError,
    ValidationError as SDKValidationError,
    ConfigError as SDKConfigError,
)
from src.core.exceptions import (
    DocumentError,
    ValidationError,
    NotFoundError,
)
from src.core.logging import get_logger
from src.api.schemas import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
    ErrorResponse,
)


# ========== 日志配置 ==========

logger = get_logger(__name__)


# ========== 依赖注入 ==========


async def get_client() -> MedGraphClient:
    """获取 MedGraphClient 实例的依赖注入函数。

    使用 FastAPI 的 Depends 机制，为每个请求提供客户端实例。
    这里使用全局单例模式，实际应用中可以考虑使用请求级别的实例。

    Returns:
        MedGraphClient: SDK 客户端实例

    Raises:
        HTTPException: 客户端初始化失败
    """
    try:
        # 从环境变量创建客户端
        client = MedGraphClient.from_env()
        await client.initialize()
        return client
    except Exception as e:
        logger.error(f"客户端初始化失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务初始化失败，请稍后重试"
        )


# ========== 路由定义 ==========

# 创建路由器
router = APIRouter()


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传文档",
    description="上传文档到知识图谱系统，支持文本文件（txt, md, json, csv 等）",
)
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件"),
    doc_id: Optional[str] = None,
    client: MedGraphClient = Depends(get_client),
) -> DocumentUploadResponse:
    """上传文档到知识图谱。

    接收文件上传，保存到临时文件，然后调用 SDK 的 ingest_document 方法。
    支持各种文本格式，自动进行文本切分、实体提取和关系构建。

    Args:
        file: 上传的文件对象（FastAPI UploadFile）
        doc_id: 可选的文档 ID（如果不提供则自动生成）
        client: SDK 客户端实例（通过依赖注入）

    Returns:
        DocumentUploadResponse: 包含文档 ID、状态和元数据的响应

    Raises:
        HTTPException: 文件处理失败或摄入失败

    Example:
        >>> # 使用 curl 测试
        >>> curl -X POST "http://localhost:8000/api/v1/documents" \\
        >>>      -F "file=@medical.txt" \\
        >>>      -F "doc_id=doc-001"
    """
    logger.info(f"收到文档上传请求 | 文件名: {file.filename} | ID: {doc_id or '自动生成'}")

    # 验证文件名
    if not file.filename:
        logger.warning("上传文件名为空")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )

    # 验证文件扩展名（可选）
    allowed_extensions = {'.txt', '.md', '.json', '.csv', '.pdf'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        logger.warning(f"不支持的文件类型: {file_ext}")
        # 注意：这里只是警告，不直接拒绝，让 SDK 层处理

    # 创建临时文件保存上传内容
    temp_file = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext or '.txt',
            mode='wb'
        ) as temp_file:
            # 读取上传文件内容并写入临时文件
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        logger.debug(f"临时文件创建成功 | 路径: {temp_file_path} | 大小: {len(content)} 字节")

        # 调用 SDK 摄入文档
        try:
            doc_info = await client.ingest_document(
                file_path=temp_file_path,
                doc_id=doc_id
            )

            logger.info(
                f"文档摄入成功 | ID: {doc_info.doc_id} | "
                f"状态: {doc_info.status} | 实体数: {doc_info.entities_count}"
            )

            return DocumentUploadResponse(
                doc_id=doc_info.doc_id,
                status=doc_info.status,
                file_name=file.filename,
                message="文档上传成功",
                entity_count=doc_info.entities_count,
                relationship_count=doc_info.metadata.get('relationship_count', 0),
            )

        except DocumentNotFoundError as e:
            logger.error(f"文档未找到: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档未找到: {e.message}"
            )
        except SDKValidationError as e:
            logger.error(f"数据验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"数据验证失败: {e.message}"
            )
        except SDKConfigError as e:
            logger.error(f"配置错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务配置错误: {e.message}"
            )
        except DocumentError as e:
            logger.error(f"文档处理失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"文档处理失败: {e.message}"
            )
        except MedGraphSDKError as e:
            logger.error(f"SDK 错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理失败: {e.message}"
            )

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logger.error(f"上传文档时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传文档失败: {str(e)}"
        )
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"临时文件已删除 | 路径: {temp_file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败 | 路径: {temp_file_path} | 错误: {e}")


@router.get(
    "/{doc_id}",
    response_model=DocumentDetailResponse,
    summary="获取文档详情",
    description="根据文档 ID 获取文档的详细信息",
)
async def get_document(
    doc_id: str,
    client: MedGraphClient = Depends(get_client),
) -> DocumentDetailResponse:
    """获取文档详情。

    根据文档 ID 查询文档的元数据、状态和统计信息。

    Args:
        doc_id: 文档 ID
        client: SDK 客户端实例（通过依赖注入）

    Returns:
        DocumentDetailResponse: 文档详细信息

    Raises:
        HTTPException: 文档不存在或查询失败

    Example:
        >>> # 使用 curl 测试
        >>> curl -X GET "http://localhost:8000/api/v1/documents/doc-001"
    """
    logger.info(f"收到文档详情请求 | ID: {doc_id}")

    try:
        # TODO: 实现 SDK 的 get_document 方法
        # 目前返回模拟数据
        # doc_info = await client.get_document(doc_id)

        # 模拟实现
        from datetime import datetime
        from src.sdk.types import DocumentInfo as SDKDocumentInfo

        # 创建模拟文档信息
        doc_info = SDKDocumentInfo(
            doc_id=doc_id,
            file_name=f"document_{doc_id}.txt",
            file_path=f"/tmp/documents/{doc_id}.txt",
            status="completed",
            entity_count=42,
            relationship_count=35,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        logger.info(f"文档详情查询成功 | ID: {doc_id} | 状态: {doc_info.status}")

        return DocumentDetailResponse(
            doc_id=doc_info.doc_id,
            file_name=doc_info.file_name,
            file_path=doc_info.file_path,
            status=doc_info.status,
            entity_count=doc_info.entity_count,
            relationship_count=doc_info.relationship_count,
            created_at=doc_info.created_at,
            updated_at=doc_info.updated_at,
        )

    except NotFoundError as e:
        logger.error(f"文档不存在: {doc_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: {doc_id}"
        )
    except Exception as e:
        logger.error(f"获取文档详情失败 | ID: {doc_id} | 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档详情失败: {str(e)}"
        )


@router.delete(
    "/{doc_id}",
    response_model=DocumentDeleteResponse,
    summary="删除文档",
    description="根据文档 ID 从知识图谱中删除文档",
)
async def delete_document(
    doc_id: str,
    client: MedGraphClient = Depends(get_client),
) -> DocumentDeleteResponse:
    """删除文档。

    根据文档 ID 从知识图谱中删除文档及其相关的实体和关系。

    Args:
        doc_id: 文档 ID
        client: SDK 客户端实例（通过依赖注入）

    Returns:
        DocumentDeleteResponse: 删除结果

    Raises:
        HTTPException: 文档不存在或删除失败

    Example:
        >>> # 使用 curl 测试
        >>> curl -X DELETE "http://localhost:8000/api/v1/documents/doc-001"
    """
    logger.info(f"收到文档删除请求 | ID: {doc_id}")

    try:
        # 调用 SDK 删除文档
        success = await client.delete_document(doc_id)

        if success:
            logger.info(f"文档删除成功 | ID: {doc_id}")
            return DocumentDeleteResponse(
                doc_id=doc_id,
                success=True,
                message="文档删除成功"
            )
        else:
            logger.warning(f"文档删除失败 | ID: {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文档删除失败"
            )

    except NotFoundError as e:
        logger.error(f"文档不存在: {doc_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: {doc_id}"
        )
    except DocumentError as e:
        logger.error(f"删除文档失败 | ID: {doc_id} | 错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"删除文档失败: {e.message}"
        )
    except Exception as e:
        logger.error(f"删除文档时发生未预期错误 | ID: {doc_id} | 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )


# ========== 导出 ==========

__all__ = ["router", "get_client"]
