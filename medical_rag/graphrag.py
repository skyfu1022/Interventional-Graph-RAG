"""
Medical RAG - GraphRAG 兼容接口

提供与 nano_graphrag.GraphRAG 兼容的接口，便于迁移现有代码。
内部使用 LightRAG-HKU 作为底层实现。
"""

import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

try:
    from lightrag import LightRAG, QueryParam as LightRAGQueryParam
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    LightRAGQueryParam = None

from .config import MedicalRAGConfig


@dataclass
class QueryParam:
    """
    查询参数（兼容 nano_graphrag.QueryParam）

    支持三种查询模式：
    - local: 本地实体查询
    - global: 全局社区查询
    - hybrid: 混合查询
    """
    mode: str = "local"  # local, global, hybrid
    top_k: int = 60
    max_token_for_text_unit: int = 4000
    max_token_for_global_context: int = 4000
    max_token_for_local_context: int = 4000

    def to_lightrag_param(self) -> Optional[Any]:
        """转换为 LightRAG 查询参数"""
        if not LIGHTRAG_AVAILABLE or not LightRAGQueryParam:
            return None
        return LightRAGQueryParam(mode=self.mode)


class MedicalRAG:
    """
    Medical RAG 主类（兼容 nano_graphrag.GraphRAG 接口）

    这是一个适配器类，提供与 nano_graphrag.GraphRAG 相同的接口，
    但内部使用 LightRAG-HKU 作为底层实现。

    主要方法：
    - insert(text): 插入文档
    - query(question, param): 执行查询
    - ainsert(text): 异步插入文档
    - aquery(question, param): 异步查询
    """

    def __init__(
        self,
        working_dir: str = "./nano_graphrag_cache",
        config: Optional[MedicalRAGConfig] = None,
        **kwargs
    ):
        """
        初始化 Medical RAG

        Args:
            working_dir: 工作目录
            config: MedicalRAGConfig 配置对象
            **kwargs: 其他配置参数
        """
        self.working_dir = working_dir

        # 创建工作目录
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        # 配置
        if config is None:
            config = MedicalRAGConfig()
            config.rag.working_dir = working_dir
        self.config = config

        # 初始化底层 RAG
        self._rag = None
        if LIGHTRAG_AVAILABLE:
            self._init_lightrag(**kwargs)
        else:
            print("警告: lightrag-hku 未安装，RAG 功能不可用")
            print("请运行: pip install lightrag-hku")

    def _init_lightrag(self, **kwargs):
        """初始化 LightRAG 实例"""
        try:
            # 准备 LightRAG 初始化参数（移除不支持的参数）
            lightrag_kwargs = {
                "working_dir": self.working_dir,
                "chunk_token_size": self.config.rag.chunk_token_size,
                "chunk_overlap_token_size": self.config.rag.chunk_overlap_token_size,
                "tiktoken_model_name": self.config.rag.tiktoken_model_name,
                "enable_llm_cache": self.config.rag.enable_llm_cache,
                **kwargs  # 允许覆盖参数
            }

            # 创建 LightRAG 实例
            self._rag = LightRAG(**lightrag_kwargs)
            print(f"LightRAG 初始化成功: {self.working_dir}")
        except Exception as e:
            print(f"LightRAG 初始化失败: {e}")
            self._rag = None

    def insert(self, text: Union[str, List[str]]) -> None:
        """
        插入文档（同步）

        Args:
            text: 文档内容（字符串或字符串列表）
        """
        if self._rag is None:
            raise RuntimeError("RAG 未初始化，请检查 lightrag-hku 是否已安装")

        # 转换为字符串
        if isinstance(text, list):
            text = "\n\n".join(text)

        # 调用 LightRAG insert
        self._rag.insert(text)

    async def ainsert(self, text: Union[str, List[str]]) -> None:
        """
        插入文档（异步）

        Args:
            text: 文档内容（字符串或字符串列表）
        """
        if self._rag is None:
            raise RuntimeError("RAG 未初始化，请检查 lightrag-hku 是否已安装")

        # 转换为字符串
        if isinstance(text, list):
            text = "\n\n".join(text)

        # 调用 LightRAG ainsert
        await self._rag.ainsert(text)

    def query(
        self,
        question: str,
        param: Optional[QueryParam] = None
    ) -> str:
        """
        执行查询（同步）

        Args:
            question: 查询问题
            param: 查询参数

        Returns:
            查询结果（字符串）
        """
        if self._rag is None:
            raise RuntimeError("RAG 未初始化，请检查 lightrag-hku 是否已安装")

        # 默认参数
        if param is None:
            param = QueryParam()

        # 转换为 LightRAG 参数
        lightrag_param = param.to_lightrag_param()

        # 调用 LightRAG query
        result = self._rag.query(question, param=lightrag_param)

        return result

    async def aquery(
        self,
        question: str,
        param: Optional[QueryParam] = None
    ) -> str:
        """
        执行查询（异步）

        Args:
            question: 查询问题
            param: 查询参数

        Returns:
            查询结果（字符串）
        """
        if self._rag is None:
            raise RuntimeError("RAG 未初始化，请检查 lightrag-hku 是否已安装")

        # 默认参数
        if param is None:
            param = QueryParam()

        # 转换为 LightRAG 参数
        lightrag_param = param.to_lightrag_param()

        # 调用 LightRAG aquery
        result = await self._rag.aquery(question, param=lightrag_param)

        return result

    def __repr__(self) -> str:
        return f"MedicalRAG(working_dir='{self.working_dir}')"


# 别名，用于兼容性
GraphRAG = MedicalRAG
