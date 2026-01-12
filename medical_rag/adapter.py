"""
RAG Adapter - RAG 系统适配器

此模块提供基于 LightRAG 的 Medical RAG 适配器实现。
支持：
1. 文档插入（文本、PDF、多模态）
2. 多种查询模式（local、global、hybrid）
3. 自定义存储后端（Neo4j、Milvus）
4. LLM 和 Embedding 函数配置
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

from medical_rag.config import MedicalRAGConfig
from medical_rag.storage.factory import StorageFactory

logger = logging.getLogger(__name__)


class MedicalRAG:
    """
    Medical RAG 适配器

    基于 LightRAG-HKU 实现的医疗 RAG 系统适配器。
    提供统一的接口用于文档处理和知识查询。

    Attributes:
        config: Medical RAG 配置对象
        lightrag: LightRAG 实例
        storage_factory: 存储工厂实例
    """

    def __init__(
        self,
        config: Optional[MedicalRAGConfig] = None,
        working_dir: Optional[str] = None,
        namespace: str = "default"
    ):
        """
        初始化 Medical RAG 适配器

        Args:
            config: Medical RAG 配置对象，如果为 None 则从环境变量加载
            working_dir: 工作目录，覆盖配置中的设置
            namespace: 存储命名空间，用于多租户隔离
        """
        # 加载配置
        if config is None:
            config = MedicalRAGConfig.from_env()
        self.config = config

        # 设置工作目录
        if working_dir:
            self.config.rag.working_dir = working_dir

        # 确保工作目录存在
        Path(self.config.rag.working_dir).mkdir(parents=True, exist_ok=True)

        self.namespace = namespace
        self.lightrag: Optional[LightRAG] = None
        self.storage_factory: Optional[StorageFactory] = None
        self._initialized = False

        logger.info(
            f"Medical RAG 适配器已创建: "
            f"working_dir={self.config.rag.working_dir}, "
            f"namespace={namespace}"
        )

    def _create_llm_func(self):
        """
        创建 LLM 函数

        根据配置创建适用于 LightRAG 的 LLM 函数。
        复用 CAMEL 框架的 OpenAI 配置。

        Returns:
            LLM 函数
        """
        from lightrag.llm.openai import openai_complete_if_cache

        # 获取配置
        llm_config = self.config.llm
        api_key = llm_config.api_key or os.getenv("OPENAI_API_KEY")
        base_url = llm_config.base_url or os.getenv("OPENAI_API_BASE_URL")

        if not api_key:
            raise ValueError("LLM API key 未配置，请设置 LLM__API_KEY 环境变量或在配置中指定")

        # 创建 LLM 函数闭包
        def llm_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: List = [],
            **kwargs
        ) -> str:
            """LLM 函数包装器"""
            return openai_complete_if_cache(
                model=llm_config.model,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=api_key,
                base_url=base_url,
                **kwargs
            )

        logger.info(f"LLM 函数已创建: model={llm_config.model}")
        return llm_func

    def _create_embedding_func(self) -> EmbeddingFunc:
        """
        创建 Embedding 函数

        根据配置创建适用于 LightRAG 的嵌入函数。

        Returns:
            包装后的嵌入函数
        """
        from lightrag.llm.openai import openai_embed

        # 获取配置
        embed_config = self.config.embedding
        api_key = embed_config.api_key or os.getenv("OPENAI_API_KEY")
        base_url = embed_config.base_url or os.getenv("OPENAI_API_BASE_URL")

        if not api_key:
            raise ValueError("Embedding API key 未配置")

        # 创建异步嵌入函数
        async def embedding_func(texts: List[str]) -> List[List[float]]:
            """嵌入函数包装器"""
            return await openai_embed(
                texts=texts,
                model=embed_config.model,
                api_key=api_key,
                base_url=base_url,
            )

        # 使用 EmbeddingFunc 包装
        wrapped_func = EmbeddingFunc(
            embedding_dim=embed_config.embedding_dim,
            max_token_size=self.config.rag.max_token_size,
            func=embedding_func
        )

        logger.info(
            f"Embedding 函数已创建: "
            f"model={embed_config.model}, "
            f"dim={embed_config.embedding_dim}"
        )
        return wrapped_func

    def _create_vision_func(self):
        """
        创建 Vision 函数（多模态支持）

        用于处理图像内容的 LLM 函数。

        Returns:
            Vision 函数
        """
        from lightrag.llm.openai import openai_complete_if_cache

        # 获取配置（使用 GPT-4 Vision 模型）
        llm_config = self.config.llm
        api_key = llm_config.api_key or os.getenv("OPENAI_API_KEY")
        base_url = llm_config.base_url or os.getenv("OPENAI_API_BASE_URL")

        # 使用支持视觉的模型
        vision_model = "gpt-4o" if llm_config.model.startswith("gpt-4") else llm_config.model

        def vision_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: List = [],
            image_data: Optional[str] = None,
            **kwargs
        ) -> str:
            """Vision 函数包装器"""
            # 如果有图像数据，构建包含图像的消息
            if image_data:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                messages.extend(history_messages)

                # 添加包含图像的用户消息
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                        }
                    ]
                })

                return openai_complete_if_cache(
                    model=vision_model,
                    prompt="",
                    system_prompt=None,
                    history_messages=[],
                    messages=messages,
                    api_key=api_key,
                    base_url=base_url,
                    **kwargs
                )
            else:
                # 没有图像时使用普通模式
                return openai_complete_if_cache(
                    model=vision_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_key=api_key,
                    base_url=base_url,
                    **kwargs
                )

        logger.info(f"Vision 函数已创建: model={vision_model}")
        return vision_func

    async def initialize(self) -> None:
        """
        初始化 RAG 系统

        创建并初始化所有必要的组件：
        1. 创建 LLM、Embedding、Vision 函数
        2. 初始化存储适配器（Neo4j、Milvus）
        3. 创建 LightRAG 实例
        4. 初始化存储后端
        """
        if self._initialized:
            logger.warning("RAG 系统已初始化，跳过")
            return

        logger.info("正在初始化 Medical RAG 系统...")

        try:
            # 1. 创建函数
            llm_func = self._create_llm_func()
            embedding_func = self._create_embedding_func()
            vision_func = self._create_vision_func()

            # 2. 构建存储配置
            storage_config = {
                "neo4j_config": {
                    "uri": self.config.neo4j.uri,
                    "username": self.config.neo4j.username,
                    "password": self.config.neo4j.password,
                    "database": self.config.neo4j.database,
                },
                "milvus_config": {
                    "host": self.config.milvus.host,
                    "port": self.config.milvus.port,
                    "collection_name": f"{self.namespace}_{self.config.milvus.collection_name}",
                    "index_type": self.config.milvus.index_type,
                    "metric_type": self.config.milvus.metric_type,
                    "embedding_dim": self.config.milvus.embedding_dim,
                },
                "embedding_func": embedding_func,
                "embedding_batch_num": self.config.embedding.batch_size,
                "cosine_better_than_threshold": 0.2,
            }

            # 3. 创建存储工厂并初始化存储
            logger.info("正在创建存储适配器...")
            graph_storage, vector_storage = await StorageFactory.create_all_storages(
                config=storage_config,
                namespace=self.namespace,
                embedding_func=embedding_func
            )

            # 4. 创建 LightRAG 实例
            logger.info("正在创建 LightRAG 实例...")
            self.lightrag = LightRAG(
                working_dir=self.config.rag.working_dir,
                llm_model_func=llm_func,
                embedding_func=embedding_func,
                # 存储配置
                graph_storage=graph_storage,
                vector_storage=vector_storage,
                # RAG 参数
                chunk_token_size=self.config.rag.chunk_token_size,
                chunk_overlap_token_size=self.config.rag.chunk_overlap_token_size,
                tiktoken_model_name=self.config.rag.tiktoken_model_name,
                entity_extract_max_gleaning=self.config.rag.entity_extract_max_gleaning,
                # 缓存配置
                enable_llm_cache=self.config.rag.enable_llm_cache,
            )

            # 5. 初始化 LightRAG 存储
            await self.lightrag.initialize_storages()

            self._initialized = True
            logger.info("Medical RAG 系统初始化完成")

        except Exception as e:
            logger.error(f"初始化 Medical RAG 系统失败: {e}")
            raise

    async def finalize(self) -> None:
        """
        清理 RAG 系统资源

        关闭所有连接和存储。
        """
        if not self._initialized:
            return

        logger.info("正在清理 Medical RAG 系统资源...")

        try:
            # 关闭 LightRAG
            if self.lightrag:
                await self.lightrag.finalize_storages()

            # 关闭存储工厂
            await StorageFactory.close_storage(self.namespace)

            self._initialized = False
            logger.info("Medical RAG 系统资源已清理")

        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    async def ainsert(self, documents: Union[str, List[str]]) -> None:
        """
        异步插入文档

        支持：
        - 纯文本字符串
        - 文本列表
        - 文件路径（自动检测 PDF）

        Args:
            documents: 文档内容或文件路径

        Raises:
            ValueError: 文档格式不支持
            RuntimeError: RAG 系统未初始化
        """
        if not self._initialized:
            raise RuntimeError("RAG 系统未初始化，请先调用 initialize()")

        logger.info(f"开始插入文档...")

        try:
            # 处理单个文档
            if isinstance(documents, str):
                # 检查是否是文件路径
                if os.path.isfile(documents):
                    logger.info(f"检测到文件路径: {documents}")
                    with open(documents, 'r', encoding='utf-8') as f:
                        content = f.read()
                    await self.lightrag.ainsert(content)
                else:
                    # 直接作为文本内容
                    await self.lightrag.ainsert(documents)

            # 处理文档列表
            elif isinstance(documents, list):
                for doc in documents:
                    if isinstance(doc, str):
                        if os.path.isfile(doc):
                            with open(doc, 'r', encoding='utf-8') as f:
                                content = f.read()
                            await self.lightrag.ainsert(content)
                        else:
                            await self.lightrag.ainsert(doc)
                    else:
                        raise ValueError(f"不支持的文档类型: {type(doc)}")

            else:
                raise ValueError(f"不支持的文档格式: {type(documents)}")

            logger.info("文档插入完成")

        except Exception as e:
            logger.error(f"插入文档失败: {e}")
            raise

    def insert(self, documents: Union[str, List[str]]) -> None:
        """
        同步插入文档

        Args:
            documents: 文档内容或文件路径
        """
        asyncio.run(self.ainsert(documents))

    async def aquery(
        self,
        query: str,
        mode: str = "hybrid",
        only_need_context: bool = False,
        **kwargs
    ) -> str:
        """
        异步查询

        支持多种查询模式：
        - local: 本地实体检索
        - global: 全局社区摘要
        - hybrid: 混合检索（推荐）
        - naive: 简单向量检索

        Args:
            query: 查询问题
            mode: 查询模式
            only_need_context: 是否只返回上下文（不调用 LLM 生成）
            **kwargs: 其他查询参数

        Returns:
            查询结果字符串

        Raises:
            RuntimeError: RAG 系统未初始化
            ValueError: 不支持的查询模式
        """
        if not self._initialized:
            raise RuntimeError("RAG 系统未初始化，请先调用 initialize()")

        # 验证查询模式
        valid_modes = ["local", "global", "hybrid", "naive", "mix"]
        if mode not in valid_modes:
            raise ValueError(
                f"不支持的查询模式: {mode}，支持的模式: {valid_modes}"
            )

        logger.info(f"执行查询: mode={mode}, query={query[:50]}...")

        try:
            # 构建查询参数
            param = QueryParam(
                mode=mode,
                only_need_context=only_need_context,
                **kwargs
            )

            # 执行查询
            result = await self.lightrag.aquery(query, param=param)

            logger.info(f"查询完成: 返回 {len(result)} 个字符")
            return result

        except Exception as e:
            logger.error(f"查询失败: {e}")
            raise

    def query(
        self,
        query: str,
        mode: str = "hybrid",
        only_need_context: bool = False,
        **kwargs
    ) -> str:
        """
        同步查询

        Args:
            query: 查询问题
            mode: 查询模式
            only_need_context: 是否只返回上下文
            **kwargs: 其他查询参数

        Returns:
            查询结果字符串
        """
        return asyncio.run(self.aquery(query, mode, only_need_context, **kwargs))

    def __enter__(self):
        """上下文管理器入口"""
        asyncio.run(self.initialize())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        asyncio.run(self.finalize())

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.finalize()
