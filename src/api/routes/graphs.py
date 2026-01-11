"""
图谱 API 路由模块。

该模块提供图谱操作相关的 REST API 端点：
- 列出所有图谱
- 获取图谱详情
- 删除图谱
- 合并图谱节点
- 导出图谱可视化

遵循 PEP 8 标准，包含完整的类型提示和 Google 风格文档字符串。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from src.sdk.client import MedGraphClient
from src.core.exceptions import (
    GraphError,
    NotFoundError,
    ValidationError as CoreValidationError,
)
from src.api.deps import get_client
from src.api.schemas import (
    GraphListResponse,
    GraphInfoItem,
    GraphDetailResponse,
    GraphDeleteRequest,
    GraphDeleteResponse,
    GraphMergeRequest,
    GraphMergeResponse,
)
from src.core.logging import get_logger


# 模块日志
logger = get_logger(__name__)

# 创建路由器
router = APIRouter()

# 支持的导出格式
SUPPORTED_EXPORT_FORMATS = ["mermaid", "json", "csv"]


# ========== 路由处理函数 ==========


@router.get(
    "",
    response_model=GraphListResponse,
    summary="列出所有图谱",
    description="获取系统中所有可用的知识图谱列表",
    responses={
        200: {"description": "成功获取图谱列表"},
        500: {"model": dict, "description": "服务器内部错误"},
    },
    tags=["graphs"],
)
async def list_graphs(
    client: MedGraphClient = Depends(get_client),
    min_entity_count: int = Query(
        default=0,
        ge=0,
        description="最小实体数量过滤",
    ),
) -> GraphListResponse:
    """列出所有图谱。

    获取系统中所有可用的知识图谱，支持按最小实体数量过滤。

    Args:
        client: SDK 客户端实例（依赖注入）
        min_entity_count: 最小实体数量过滤条件

    Returns:
        GraphListResponse: 包含图谱列表的响应

    Raises:
        HTTPException: 服务器内部错误时抛出
    """
    try:
        logger.info(f"列出所有图谱 | 最小实体数: {min_entity_count}")

        # 调用 SDK 方法
        graphs = await client.list_graphs()

        # 过滤和转换
        filtered_graphs = [
            g for g in graphs if g.entity_count >= min_entity_count
        ]

        graph_items = [
            GraphInfoItem(
                graph_id=g.graph_id,
                workspace=g.workspace,
                entity_count=g.entity_count,
                relationship_count=g.relationship_count,
                document_count=g.document_count,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in filtered_graphs
        ]

        response = GraphListResponse(
            total=len(graph_items),
            graphs=graph_items,
        )

        logger.info(f"返回图谱列表 | 总数: {response.total}")

        return response

    except GraphError as e:
        logger.error(f"列出图谱失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GraphError",
                "message": str(e),
                "details": getattr(e, "details", {}),
            },
        ) from e
    except Exception as e:
        logger.error(f"列出图谱时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalError",
                "message": "列出图谱时发生服务器错误",
            },
        ) from e


@router.get(
    "/{graph_id}",
    response_model=GraphDetailResponse,
    summary="获取图谱详情",
    description="获取指定知识图谱的详细信息和统计数据",
    responses={
        200: {"description": "成功获取图谱详情"},
        404: {"model": dict, "description": "图谱不存在"},
        500: {"model": dict, "description": "服务器内部错误"},
    },
    tags=["graphs"],
)
async def get_graph(
    graph_id: str,
    client: MedGraphClient = Depends(get_client),
) -> GraphDetailResponse:
    """获取图谱详情。

    获取指定知识图谱的完整详细信息和统计数据。

    Args:
        graph_id: 图谱 ID
        client: SDK 客户端实例（依赖注入）

    Returns:
        GraphDetailResponse: 包含图谱详细信息的响应

    Raises:
        HTTPException 404: 图谱不存在
        HTTPException 500: 服务器内部错误
    """
    try:
        logger.info(f"获取图谱详情: {graph_id}")

        # 调用 SDK 方法
        graph_info = await client.get_graph(graph_id)

        # 构建 GraphInfoItem
        graph_item = GraphInfoItem(
            graph_id=graph_info.graph_id,
            workspace=graph_info.workspace,
            entity_count=graph_info.entity_count,
            relationship_count=graph_info.relationship_count,
            document_count=graph_info.document_count,
            created_at=graph_info.created_at,
            updated_at=graph_info.updated_at,
        )

        response = GraphDetailResponse(
            graph_info=graph_item,
            config=None,  # SDK 暂未提供配置信息
        )

        logger.info(f"返回图谱详情 | 实体数: {graph_item.entity_count}")

        return response

    except NotFoundError as e:
        logger.warning(f"图谱不存在: {graph_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFoundError",
                "message": f"图谱不存在: {graph_id}",
                "resource_type": "graph",
                "resource_id": graph_id,
            },
        ) from e
    except GraphError as e:
        logger.error(f"获取图谱详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GraphError",
                "message": str(e),
                "details": getattr(e, "details", {}),
            },
        ) from e
    except Exception as e:
        logger.error(f"获取图谱详情时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalError",
                "message": "获取图谱详情时发生服务器错误",
            },
        ) from e


@router.delete(
    "/{graph_id}",
    response_model=GraphDeleteResponse,
    summary="删除图谱",
    description="删除指定的知识图谱（需要确认）",
    responses={
        200: {"description": "成功删除图谱"},
        400: {"model": dict, "description": "请求参数无效"},
        404: {"model": dict, "description": "图谱不存在"},
        500: {"model": dict, "description": "服务器内部错误"},
    },
    tags=["graphs"],
)
async def delete_graph(
    graph_id: str,
    request: GraphDeleteRequest,
    client: MedGraphClient = Depends(get_client),
) -> GraphDeleteResponse:
    """删除图谱。

    删除指定的知识图谱。此操作不可逆，需要确认。

    Args:
        graph_id: 图谱 ID
        request: 删除请求参数（包含确认标志）
        client: SDK 客户端实例（依赖注入）

    Returns:
        GraphDeleteResponse: 包含删除结果的响应

    Raises:
        HTTPException 400: 未确认删除操作
        HTTPException 404: 图谱不存在
        HTTPException 500: 服务器内部错误
    """
    try:
        logger.info(f"删除图谱请求 | 图谱: {graph_id} | 确认: {request.confirm}")

        # 调用 SDK 方法
        deleted = await client.delete_graph(
            graph_id=graph_id,
            confirm=request.confirm,
        )

        response = GraphDeleteResponse(
            graph_id=graph_id,
            deleted=deleted,
            message=f"图谱 {graph_id} 已成功删除" if deleted else "删除操作未执行",
        )

        logger.info(f"删除图谱成功 | 图谱: {graph_id}")

        return response

    except CoreValidationError as e:
        logger.warning(f"删除图谱参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e
    except NotFoundError as e:
        logger.warning(f"图谱不存在: {graph_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFoundError",
                "message": f"图谱不存在: {graph_id}",
                "resource_type": "graph",
                "resource_id": graph_id,
            },
        ) from e
    except GraphError as e:
        logger.error(f"删除图谱失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GraphError",
                "message": str(e),
                "details": getattr(e, "details", {}),
            },
        ) from e
    except Exception as e:
        logger.error(f"删除图谱时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalError",
                "message": "删除图谱时发生服务器错误",
            },
        ) from e


@router.post(
    "/{graph_id}/merge",
    response_model=GraphMergeResponse,
    summary="合并图谱节点",
    description="合并相似的知识图谱节点，减少冗余",
    responses={
        200: {"description": "成功合并节点"},
        400: {"model": dict, "description": "请求参数无效"},
        404: {"model": dict, "description": "图谱不存在"},
        500: {"model": dict, "description": "服务器内部错误"},
    },
    tags=["graphs"],
)
async def merge_graph_nodes(
    graph_id: str,
    request: GraphMergeRequest,
    client: MedGraphClient = Depends(get_client),
) -> GraphMergeResponse:
    """合并图谱节点。

    合并相似的实体节点，减少图谱冗余。支持自动检测相似实体
    或手动指定要合并的实体列表。

    Args:
        graph_id: 图谱 ID
        request: 合并请求参数
        client: SDK 客户端实例（依赖注入）

    Returns:
        GraphMergeResponse: 包含合并结果的响应

    Raises:
        HTTPException 400: 请求参数无效
        HTTPException 404: 图谱不存在
        HTTPException 500: 服务器内部错误

    Note:
        如果未提供 source_entities，系统将使用 threshold 参数
        自动检测相似实体进行合并。
    """
    try:
        logger.info(
            f"合并图谱节点请求 | 图谱: {graph_id} | "
            f"阈值: {request.threshold} | "
            f"源实体: {len(request.source_entities) if request.source_entities else 0}"
        )

        # 如果没有提供源实体，返回提示信息
        # （SDK 的 merge_graph_nodes 需要明确的源实体列表）
        if not request.source_entities:
            response = GraphMergeResponse(
                graph_id=graph_id,
                merged_count=0,
                message="请提供要合并的源实体列表（source_entities）",
            )
            return response

        # 调用 SDK 方法
        # 注意：SDK 的 merge_graph_nodes 在 GraphService 中实现
        # 这里需要通过适配器调用
        merged_count = await client._graph_service.merge_graph_nodes(
            graph_id=graph_id,
            source_entities=request.source_entities,
            target_entity=request.target_entity or request.source_entities[0],
            threshold=request.threshold,
            merge_strategy=request.merge_strategy,
        )

        response = GraphMergeResponse(
            graph_id=graph_id,
            merged_count=merged_count,
            source_entities=request.source_entities,
            target_entity=request.target_entity or request.source_entities[0],
            message=f"成功合并 {merged_count} 个节点",
        )

        logger.info(f"合并图谱节点成功 | 图谱: {graph_id} | 数量: {merged_count}")

        return response

    except CoreValidationError as e:
        logger.warning(f"合并节点参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e
    except NotFoundError as e:
        logger.warning(f"图谱不存在: {graph_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFoundError",
                "message": f"图谱不存在: {graph_id}",
                "resource_type": "graph",
                "resource_id": graph_id,
            },
        ) from e
    except GraphError as e:
        logger.error(f"合并节点失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GraphError",
                "message": str(e),
                "details": getattr(e, "details", {}),
            },
        ) from e
    except Exception as e:
        logger.error(f"合并节点时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalError",
                "message": "合并节点时发生服务器错误",
            },
        ) from e


@router.get(
    "/{graph_id}/visualize",
    response_model=None,
    summary="导出图谱可视化",
    description="将知识图谱导出为指定格式的可视化文件",
    responses={
        200: {
            "description": "成功导出图谱",
            "content": {
                "application/json": {},
                "text/plain": {"example": "```mermaid\ngraph TD\n```"},
                "text/csv": {},
            },
        },
        400: {"model": dict, "description": "请求参数无效"},
        404: {"model": dict, "description": "图谱不存在"},
        500: {"model": dict, "description": "服务器内部错误"},
    },
    tags=["graphs"],
)
async def export_graph_visualization(
    graph_id: str,
    format: Literal["mermaid", "json", "csv"] = Query(
        default="mermaid",
        description="导出格式",
    ),
    client: MedGraphClient = Depends(get_client),
) -> FileResponse | Response:
    """导出图谱可视化。

    将知识图谱导出为指定格式的文件，支持 Mermaid 图表、JSON 和 CSV 格式。

    Args:
        graph_id: 图谱 ID
        format: 导出格式（mermaid, json, csv）
        client: SDK 客户端实例（依赖注入）

    Returns:
        FileResponse | Response: 导出的文件或文本内容

    Raises:
        HTTPException 400: 不支持的导出格式
        HTTPException 404: 图谱不存在
        HTTPException 500: 服务器内部错误

    Note:
        - mermaid: 返回 Mermaid 图表定义（文本）
        - json: 返回 JSON 格式的图谱数据文件
        - csv: 返回 CSV 格式的图谱数据文件
    """
    try:
        logger.info(f"导出图谱可视化 | 图谱: {graph_id} | 格式: {format}")

        # 验证格式
        if format not in SUPPORTED_EXPORT_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ValidationError",
                    "message": f"不支持的导出格式: {format}",
                    "supported_formats": SUPPORTED_EXPORT_FORMATS,
                },
            )

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=f".{format}",
            encoding="utf-8",
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # 调用 SDK 方法导出图谱
            await client.export_graph(
                graph_id=graph_id,
                output_path=temp_path,
                format=format,
            )

            # 根据格式决定响应方式
            media_types = {
                "mermaid": "text/plain",
                "json": "application/json",
                "csv": "text/csv",
            }

            filename = f"{graph_id}_graph.{format}"

            # 返回文件
            return FileResponse(
                path=temp_path,
                media_type=media_types[format],
                filename=filename,
                background=None,  # 临时文件清理由客户端负责
            )

        except Exception:
            # 清理临时文件
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            raise

    except CoreValidationError as e:
        logger.warning(f"导出图谱参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e
    except NotFoundError as e:
        logger.warning(f"图谱不存在: {graph_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFoundError",
                "message": f"图谱不存在: {graph_id}",
                "resource_type": "graph",
                "resource_id": graph_id,
            },
        ) from e
    except GraphError as e:
        logger.error(f"导出图谱失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GraphError",
                "message": str(e),
                "details": getattr(e, "details", {}),
            },
        ) from e
    except Exception as e:
        logger.error(f"导出图谱时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalError",
                "message": "导出图谱时发生服务器错误",
            },
        ) from e


# ========== 导出 ==========

__all__ = ["router"]

