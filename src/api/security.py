"""
API 安全认证模块。

本模块提供 API Key 认证功能，使用 FastAPI 的 APIKeyHeader 实现。
支持从环境变量加载有效 API Keys，并支持可选认证模式。

遵循 PEP 8 标准，包含完整的类型提示和 Google 风格文档字符串。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.core.logging import get_logger


logger = get_logger(__name__)

# 创建 API Key 方案
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_valid_api_keys() -> list[str]:
    """
    从环境变量获取有效的 API Keys 列表。

    从环境变量 API_KEYS 中读取逗号分隔的 API Keys，
    如果未设置则返回空列表（表示禁用认证）。

    Returns:
        list[str]: 有效的 API Keys 列表。如果环境变量未设置，返回空列表。

    Example:
        >>> # 设置环境变量: export API_KEYS=key1,key2,key3
        >>> keys = get_valid_api_keys()
        >>> assert "key1" in keys
    """
    api_keys_env = os.getenv("API_KEYS", "")
    if not api_keys_env:
        logger.warning("未设置 API_KEYS 环境变量，API Key 认证已禁用")
        return []

    # 解析逗号分隔的 API Keys
    valid_keys = [key.strip() for key in api_keys_env.split(",") if key.strip()]
    logger.info(f"已加载 {len(valid_keys)} 个有效 API Keys")

    return valid_keys


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> str | None:
    """
    验证 API Key。

    该函数验证请求头中的 X-API-Key 是否有效。
    如果未设置 API_KEYS 环境变量，则跳过认证（可选认证模式）。

    Args:
        api_key: 从请求头中提取的 API Key

    Returns:
        str | None: 验证通过的 API Key，如果跳过认证则返回 None

    Raises:
        HTTPException: 当 API Key 缺失或无效时抛出 401 或 403 错误

    Example:
        >>> from fastapi import Depends, APIRouter
        >>> from src.api.security import verify_api_key
        >>>
        >>> router = APIRouter()
        >>>
        >>> @router.get("/protected")
        >>> async def protected_route(
        >>>     key: str = Depends(verify_api_key)
        >>> ):
        >>>     return {"message": "访问成功", "api_key": key}
    """
    # 获取有效的 API Keys
    valid_keys = get_valid_api_keys()

    # 如果未配置有效的 API Keys，跳过认证
    if not valid_keys:
        logger.debug("API Key 认证已禁用，跳过验证")
        return None

    # 检查 API Key 是否存在
    if api_key is None:
        logger.warning("请求缺少 API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 缺失，请在请求头中提供 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 检查 API Key 是否有效
    if api_key not in valid_keys:
        logger.warning(f"无效的 API Key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key",
        )

    logger.debug(f"API Key 验证成功: {api_key[:8]}...")
    return api_key


async def verify_api_key_required(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> str:
    """
    验证 API Key（必需模式）。

    该函数验证请求头中的 X-API-Key 是否有效。
    与 verify_api_key 不同，该函数始终要求提供有效的 API Key，
    即使未配置 API_KEYS 环境变量也会要求认证。

    Args:
        api_key: 从请求头中提取的 API Key

    Returns:
        str: 验证通过的 API Key

    Raises:
        HTTPException: 当 API Key 缺失或无效时抛出 401 或 403 错误
        RuntimeError: 当未配置 API_KEYS 环境变量时抛出运行时错误

    Example:
        >>> from fastapi import Depends, APIRouter
        >>> from src.api.security import verify_api_key_required
        >>>
        >>> router = APIRouter()
        >>>
        >>> @router.get("/admin")
        >>> async def admin_route(
        >>>     key: str = Depends(verify_api_key_required)
        >>> ):
        >>>     return {"message": "管理员访问成功"}
    """
    # 获取有效的 API Keys
    valid_keys = get_valid_api_keys()

    # 如果未配置有效的 API Keys，抛出错误
    if not valid_keys:
        logger.error("必需认证的端点未配置 API_KEYS 环境变量")
        raise RuntimeError(
            "此端点需要 API Key 认证，但未配置 API_KEYS 环境变量。"
            "请在环境变量中设置有效的 API Keys。"
        )

    # 检查 API Key 是否存在
    if api_key is None:
        logger.warning("请求缺少 API Key（必需认证）")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 缺失，请在请求头中提供 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 检查 API Key 是否有效
    if api_key not in valid_keys:
        logger.warning(f"无效的 API Key（必需认证）: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key",
        )

    logger.debug(f"API Key 验证成功（必需认证）: {api_key[:8]}...")
    return api_key


__all__ = [
    "api_key_header",
    "get_valid_api_keys",
    "verify_api_key",
    "verify_api_key_required",
]
