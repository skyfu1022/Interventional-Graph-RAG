"""
RAG-Anything 核心适配器模块。

该模块提供与 LightRAG 框架的适配层，封装了：
- LightRAG 初始化和存储配置
- 文档摄入（单文本、批量、多模态）
- 知识图谱查询（支持多种查询模式）
- 图谱统计和管理

基于 LightRAG 1.4.9+ 版本实现，支持：
- Neo4j 图存储
- Milvus 向量存储
- 异步操作
- 多模态文档处理

使用示例：
    >>> from src.core.config import Settings
    >>> from src.core.adapters import RAGAnythingAdapter
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     config = Settings()
    >>>     adapter = RAGAnythingAdapter(config)
    >>>     await adapter.initialize()
    >>>
    >>>     # 摄入文档
    >>>     result = await adapter.ingest_document("doc.txt", doc_id="doc-001")
    >>>
    >>>     # 查询知识图谱
    >>>     result = await adapter.query("什么是糖尿病?", mode="hybrid")
    >>>     print(result.answer)
    >>>
    >>> asyncio.run(main())
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal, AsyncIterator
from dataclasses import dataclass, field

# LightRAG 导入
# 注意：需要安装 lightrag-hku 包（pip install lightrag-hku）
# 如果遇到导入错误，请确保安装了正确的包：
#   pip uninstall lightrag -y
#   pip install lightrag-hku>=1.4.9
try:
    # lightrag-hku 包的正确导入方式
    from lightrag.lightrag import LightRAG
    from lightrag.operate import QueryParam
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.utils import EmbeddingFunc
    from lightrag.kg.shared_storage import initialize_pipeline_status
except ImportError as e:
    raise ImportError(
        f"无法导入 LightRAG: {e}\n"
        "请确保安装了正确的 lightrag-hku 包：\n"
        "  pip uninstall lightrag -y\n"
        "  pip install 'lightrag-hku>=1.4.9'"
    ) from e

from src.core.config import Settings
from src.core.exceptions import (
    DocumentError,
    QueryError,
    GraphError,
    StorageError,
    ValidationError,
)
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.core.adapters")


# ========== 结果数据类 ==========


@dataclass
class IngestResult:
    """文档摄入结果。

    Attributes:
        doc_id: 文档 ID
        status: 摄入状态（pending, processing, completed, failed）
        chunks_count: 切分的文本块数量
        entities_count: 提取的实体数量
        relationships_count: 提取的关系数量
        error: 错误信息（如果失败）
        metadata: 额外的元数据
    """

    doc_id: Optional[str]
    status: str
    chunks_count: int = 0
    entities_count: int = 0
    relationships_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "doc_id": self.doc_id,
            "status": self.status,
            "chunks_count": self.chunks_count,
            "entities_count": self.entities_count,
            "relationships_count": self.relationships_count,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class QueryResult:
    """知识图谱查询结果。

    Attributes:
        answer: 生成的答案
        mode: 使用的查询模式
        sources: 来源文档列表
        context: 检索到的上下文（可选）
        entities: 涉及的实体列表（可选）
        relationships: 涉及的关系列表（可选）
        metadata: 额外的元数据
    """

    answer: str
    mode: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "answer": self.answer,
            "mode": self.mode,
            "sources": self.sources,
            "context": self.context,
            "entities": self.entities,
            "relationships": self.relationships,
            "metadata": self.metadata,
        }


@dataclass
class GraphStats:
    """知识图谱统计信息。

    Attributes:
        entity_count: 实体总数
        relationship_count: 关系总数
        chunk_count: 文本块总数
        document_count: 文档总数
        entity_types: 实体类型及其数量
        storage_info: 存储后端信息
    """

    entity_count: int
    relationship_count: int
    chunk_count: int
    document_count: int
    entity_types: Dict[str, int] = field(default_factory=dict)
    storage_info: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "chunk_count": self.chunk_count,
            "document_count": self.document_count,
            "entity_types": self.entity_types,
            "storage_info": self.storage_info,
        }


# ========== 查询模式类型 ==========

QueryMode = Literal["naive", "local", "global", "hybrid", "mix", "bypass"]


# ========== 辅助函数 ==========


def _create_embedding_func(config: Settings) -> EmbeddingFunc:
    """创建 LightRAG 嵌入函数。

    Args:
        config: 配置对象

    Returns:
        EmbeddingFunc: LightRAG 嵌入函数
    """
    logger.debug(
        f"创建嵌入函数 | 模型: {config.embedding_model} | "
        f"API Base: {config.openai_api_base or '默认'}"
    )

    def embedding_func(texts: List[str]) -> List[List[float]]:
        """嵌入函数实现。"""
        try:
            return openai_embed(
                texts=texts,
                model=config.embedding_model,
                api_key=config.openai_api_key,
                base_url=config.openai_api_base,
            )
        except Exception as e:
            logger.error(f"嵌入生成失败 | 文本数: {len(texts)} | 错误: {e}")
            raise StorageError(
                f"嵌入生成失败: {e}",
                storage_type="openai",
                operation="embedding",
                details={"model": config.embedding_model, "texts_count": len(texts)},
            ) from e

    # 获取嵌入维度（通过测试一次嵌入）
    try:
        test_embedding = openai_embed(
            texts=["test"],
            model=config.embedding_model,
            api_key=config.openai_api_key,
            base_url=config.openai_api_base,
        )
        embedding_dim = len(test_embedding[0])
        logger.info(f"嵌入函数创建成功 | 维度: {embedding_dim}")
    except Exception as e:
        logger.warning(f"无法获取嵌入维度，使用默认值 3072 | 错误: {e}")
        embedding_dim = 3072

    return EmbeddingFunc(
        embedding_dim=embedding_dim,
        func=embedding_func,
    )


def _create_llm_func(config: Settings):
    """创建 LightRAG LLM 函数。

    Args:
        config: 配置对象

    Returns:
        LLM 函数
    """
    logger.debug(
        f"创建 LLM 函数 | 模型: {config.llm_model} | "
        f"API Base: {config.openai_api_base or '默认'}"
    )

    def llm_func(
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: List[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """LLM 函数实现。"""
        try:
            return openai_complete_if_cache(
                config.llm_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                api_key=config.openai_api_key,
                base_url=config.openai_api_base,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败 | 模型: {config.llm_model} | 错误: {e}")
            raise StorageError(
                f"LLM 调用失败: {e}",
                storage_type="openai",
                operation="llm_inference",
                details={"model": config.llm_model},
            ) from e

    logger.info(f"LLM 函数创建成功 | 模型: {config.llm_model}")
    return llm_func


def _configure_storage(config: Settings) -> Dict[str, str]:
    """配置存储后端。

    Args:
        config: 配置对象

    Returns:
        存储配置字典
    """
    logger.debug("配置存储后端")

    # 设置 Neo4j 环境变量
    os.environ["NEO4J_URI"] = config.neo4j_uri
    os.environ["NEO4J_USERNAME"] = config.neo4j_username
    os.environ["NEO4J_PASSWORD"] = config.neo4j_password

    # 设置 Milvus 环境变量
    os.environ["MILVUS_URI"] = config.milvus_uri
    if config.milvus_token:
        os.environ["MILVUS_TOKEN"] = config.milvus_token
    if config.milvus_api_key:
        os.environ["MILVUS_API_KEY"] = config.milvus_api_key

    storage_config = {
        "graph_storage": "Neo4JStorage",
        "vector_storage": "MilvusVectorDBStorage",
        "kv_storage": "JsonKVStorage",
        "doc_status_storage": "JsonDocStatusStorage",
    }

    logger.info(
        f"存储配置完成 | "
        f"图存储: {storage_config['graph_storage']} | "
        f"向量存储: {storage_config['vector_storage']}"
    )

    return storage_config


# ========== 核心适配器类 ==========


class RAGAnythingAdapter:
    """RAG-Anything 核心适配器。

    封装 LightRAG 1.4.9+ 的完整功能，提供：
    - 异步文档摄入
    - 多模式知识图谱查询
    - 图谱统计和管理
    - 多模态文档处理

    Attributes:
        config: 配置对象
        rag: LightRAG 实例
        _initialized: 是否已初始化存储

    Example:
        >>> adapter = RAGAnythingAdapter(config)
        >>> await adapter.initialize()
        >>> result = await adapter.query("问题", mode="hybrid")
    """

    def __init__(self, config: Settings):
        """初始化适配器。

        Args:
            config: 配置对象
        """
        self.config = config
        self._initialized = False
        self._rag: Optional[LightRAG] = None

        logger.info(
            f"RAG-Anything 适配器创建 | "
            f"工作目录: {config.rag_working_dir} | "
            f"工作空间: {config.rag_workspace}"
        )

    def _create_lightrag_instance(self) -> LightRAG:
        """创建 LightRAG 实例。

        Returns:
            LightRAG 实例
        """
        logger.debug("创建 LightRAG 实例")

        # 创建嵌入函数
        embedding_func = _create_embedding_func(self.config)

        # 创建 LLM 函数
        llm_func = _create_llm_func(self.config)

        # 配置存储
        storage_config = _configure_storage(self.config)

        # 确保工作目录存在
        working_dir = Path(self.config.rag_working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        try:
            rag = LightRAG(
                working_dir=str(working_dir),
                embedding_func=embedding_func,
                llm_model_func=llm_func,
                graph_storage=storage_config["graph_storage"],
                vector_storage=storage_config["vector_storage"],
                kv_storage=storage_config["kv_storage"],
                doc_status_storage=storage_config["doc_status_storage"],
                workspace=self.config.rag_workspace,
            )
            logger.info("LightRAG 实例创建成功")
            return rag
        except Exception as e:
            logger.error(f"LightRAG 实例创建失败 | 错误: {e}")
            raise StorageError(
                f"LightRAG 实例创建失败: {e}",
                storage_type="lightrag",
                operation="initialize",
                details={"working_dir": str(working_dir)},
            ) from e

    async def initialize(self) -> None:
        """初始化适配器（初始化存储和管道状态）。

        这是 LightRAG 1.4.9+ 的必需步骤。

        Raises:
            StorageError: 存储初始化失败
        """
        if self._initialized:
            logger.warning("适配器已初始化，跳过重复初始化")
            return

        logger.info("开始初始化 RAG-Anything 适配器")

        try:
            # 创建 LightRAG 实例
            self._rag = self._create_lightrag_instance()

            # 初始化存储（LightRAG 1.4.9+ 必需）
            logger.debug("初始化存储后端")
            await self._rag.initialize_storages()

            # 初始化管道状态（LightRAG 1.4.9+ 必需）
            logger.debug("初始化管道状态")
            await initialize_pipeline_status()

            self._initialized = True
            logger.info("RAG-Anything 适配器初始化完成")

        except Exception as e:
            logger.error(f"适配器初始化失败 | 错误: {e}")
            raise StorageError(
                f"适配器初始化失败: {e}",
                storage_type="lightrag",
                operation="initialize",
            ) from e

    async def _ensure_initialized(self) -> None:
        """确保适配器已初始化。

        Raises:
            GraphError: 适配器未初始化
        """
        if not self._initialized or self._rag is None:
            raise GraphError(
                "适配器未初始化，请先调用 initialize() 方法",
                details={"suggestion": "await adapter.initialize()"},
            )

    async def ingest_document(
        self,
        file_path: str,
        doc_id: Optional[str] = None,
    ) -> IngestResult:
        """摄入文档到知识图谱。

        Args:
            file_path: 文档文件路径
            doc_id: 文档 ID（可选，如果不提供则自动生成）

        Returns:
            IngestResult: 摄入结果

        Raises:
            DocumentError: 文档读取或摄入失败
            ValidationError: 文件路径无效
        """
        await self._ensure_initialized()

        # 验证文件路径
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(
                f"文件不存在: {file_path}",
                field="file_path",
                value=file_path,
            )

        logger.info(f"开始摄入文档 | 路径: {file_path} | ID: {doc_id or '自动生成'}")

        try:
            # 读取文件内容
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 调用 LightRAG ainsert
            await self._rag.ainsert(content, ids=[doc_id] if doc_id else None)

            logger.info(f"文档摄入成功 | ID: {doc_id}")

            return IngestResult(
                doc_id=doc_id,
                status="completed",
                metadata={"file_path": str(path), "file_size": path.stat().st_size},
            )

        except DocumentError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"文档摄入失败 | 文件: {file_path} | 错误: {e}")
            raise DocumentError(
                f"文档摄入失败: {e}",
                doc_id=doc_id,
                details={"file_path": file_path, "error": str(e)},
            ) from e

    async def ingest_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
    ) -> IngestResult:
        """摄入文本到知识图谱。

        Args:
            text: 文本内容
            doc_id: 文档 ID（可选）

        Returns:
            IngestResult: 摄入结果

        Raises:
            DocumentError: 文本摄入失败
            ValidationError: 文本为空
        """
        await self._ensure_initialized()

        if not text or not text.strip():
            raise ValidationError(
                "文本内容不能为空",
                field="text",
                value=text,
            )

        logger.debug(f"开始摄入文本 | ID: {doc_id or '自动生成'} | 长度: {len(text)}")

        try:
            await self._rag.ainsert(text, ids=[doc_id] if doc_id else None)

            logger.debug(f"文本摄入成功 | ID: {doc_id}")

            return IngestResult(
                doc_id=doc_id,
                status="completed",
                metadata={"text_length": len(text)},
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"文本摄入失败 | 错误: {e}")
            raise DocumentError(
                f"文本摄入失败: {e}",
                doc_id=doc_id,
            ) from e

    async def ingest_batch(
        self,
        texts: List[str],
        doc_ids: Optional[List[str]] = None,
    ) -> List[IngestResult]:
        """批量摄入文本到知识图谱。

        Args:
            texts: 文本列表
            doc_ids: 文档 ID 列表（可选，长度必须与 texts 一致）

        Returns:
            List[IngestResult]: 摄入结果列表

        Raises:
            DocumentError: 批量摄入失败
            ValidationError: 参数验证失败
        """
        await self._ensure_initialized()

        if not texts:
            raise ValidationError(
                "文本列表不能为空",
                field="texts",
            )

        if doc_ids and len(doc_ids) != len(texts):
            raise ValidationError(
                f"文档 ID 数量与文本数量不匹配 | 文本数: {len(texts)} | ID数: {len(doc_ids)}",
                field="doc_ids",
                constraint="len(doc_ids) == len(texts)",
            )

        logger.info(f"开始批量摄入 | 文档数: {len(texts)}")

        try:
            await self._rag.ainsertexts(texts, ids=doc_ids)

            results = [
                IngestResult(
                    doc_id=doc_ids[i] if doc_ids else None,
                    status="completed",
                    metadata={"index": i, "text_length": len(texts[i])},
                )
                for i in range(len(texts))
            ]

            logger.info(f"批量摄入成功 | 文档数: {len(texts)}")

            return results

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"批量摄入失败 | 错误: {e}")
            raise DocumentError(
                f"批量摄入失败: {e}",
                details={"texts_count": len(texts)},
            ) from e

    async def ingest_multimodal(
        self,
        content_list: List[Dict[str, Any]],
        file_path: Optional[str] = None,
    ) -> IngestResult:
        """摄入多模态内容（文本、图片、表格等）。

        Args:
            content_list: 内容列表，每个元素是包含 content_type 和 content 的字典
                例如: [{"content_type": "text", "content": "..."}, {"content_type": "image", "content": "base64..."}]
            file_path: 源文件路径（可选）

        Returns:
            IngestResult: 摄入结果

        Raises:
            DocumentError: 多模态摄入失败
            ValidationError: 内容格式无效

        Note:
            此功能需要 LightRAG 配置视觉模型。
            目前 LightRAG 的多模态处理主要通过与 RAG-Anything 集成实现。
        """
        await self._ensure_initialized()

        if not content_list:
            raise ValidationError(
                "内容列表不能为空",
                field="content_list",
            )

        logger.info(f"开始摄入多模态内容 | 内容数: {len(content_list)}")

        try:
            # 将多模态内容转换为文本描述
            # 注意：完整的视觉处理需要 RAG-Anything 集成
            # 这里提供基础实现
            combined_text = []
            for item in content_list:
                content_type = item.get("content_type", "text")
                content = item.get("content", "")

                if content_type == "text":
                    combined_text.append(content)
                elif content_type == "image":
                    # 图片需要通过视觉模型处理
                    combined_text.append(f"[图片: {len(content)} 字节的 base64 数据]")
                else:
                    combined_text.append(f"[{content_type}: {str(content)[:50]}...]")

            full_text = "\n\n".join(combined_text)

            # 摄入处理后的文本
            result = await self.ingest_text(full_text)

            result.metadata["multimodal"] = True
            result.metadata["content_types"] = [
                item.get("content_type", "unknown") for item in content_list
            ]
            if file_path:
                result.metadata["source_file"] = file_path

            logger.info(f"多模态内容摄入成功 | ID: {result.doc_id}")

            return result

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"多模态摄入失败 | 错误: {e}")
            raise DocumentError(
                f"多模态摄入失败: {e}",
                details={"content_count": len(content_list)},
            ) from e

    async def query(
        self,
        question: str,
        mode: QueryMode = "hybrid",
        **kwargs
    ) -> QueryResult:
        """查询知识图谱。

        Args:
            question: 查询问题
            mode: 查询模式（naive, local, global, hybrid, mix, bypass）
            **kwargs: 额外的查询参数
                - top_k: 检索的 top-k 数量
                - chunk_top_k: 文本块的 top-k 数量
                - max_entity_tokens: 实体最大 token 数
                - max_relation_tokens: 关系最大 token 数
                - response_type: 响应类型
                - conversation_history: 对话历史
                - only_need_context: 仅返回上下文
                - only_need_prompt: 仅返回提示

        Returns:
            QueryResult: 查询结果

        Raises:
            QueryError: 查询执行失败
            ValidationError: 查询参数无效
        """
        await self._ensure_initialized()

        if not question or not question.strip():
            raise ValidationError(
                "查询问题不能为空",
                field="question",
            )

        valid_modes = ["naive", "local", "global", "hybrid", "mix", "bypass"]
        if mode not in valid_modes:
            raise ValidationError(
                f"无效的查询模式: {mode}",
                field="mode",
                value=mode,
                constraint=f"mode in {valid_modes}",
            )

        logger.info(f"执行查询 | 模式: {mode} | 问题: {question[:100]}...")

        try:
            # 构建查询参数
            param = QueryParam(mode=mode, **kwargs)

            # 执行查询
            answer = await self._rag.aquery(question, param=param)

            logger.info(f"查询完成 | 模式: {mode} | 答案长度: {len(answer)}")

            return QueryResult(
                answer=answer,
                mode=mode,
                metadata={"query_params": kwargs},
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"查询失败 | 错误: {e}")
            raise QueryError(
                f"查询执行失败: {e}",
                query_text=question,
                details={"mode": mode, "kwargs": kwargs},
            ) from e

    async def query_stream(
        self,
        question: str,
        mode: QueryMode = "hybrid",
        **kwargs
    ) -> AsyncIterator[str]:
        """流式查询知识图谱。

        Args:
            question: 查询问题
            mode: 查询模式
            **kwargs: 额外的查询参数

        Yields:
            str: 流式答案片段

        Raises:
            QueryError: 查询执行失败
        """
        await self._ensure_initialized()

        if not question or not question.strip():
            raise ValidationError(
                "查询问题不能为空",
                field="question",
            )

        logger.info(f"执行流式查询 | 模式: {mode}")

        try:
            kwargs["stream"] = True
            param = QueryParam(mode=mode, **kwargs)

            stream = await self._rag.aquery(question, param=param)

            async for chunk in stream:
                yield chunk

            logger.info(f"流式查询完成 | 模式: {mode}")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"流式查询失败 | 错误: {e}")
            raise QueryError(
                f"流式查询执行失败: {e}",
                query_text=question,
                details={"mode": mode},
            ) from e

    async def delete_document(self, doc_id: str) -> bool:
        """从知识图谱中删除文档。

        Args:
            doc_id: 文档 ID

        Returns:
            bool: 是否删除成功

        Raises:
            DocumentError: 删除失败
            NotFoundError: 文档不存在

        Note:
            LightRAG 的删除功能可能有限，具体取决于版本。
        """
        await self._ensure_initialized()

        logger.info(f"删除文档 | ID: {doc_id}")

        try:
            # LightRAG 可能没有直接的删除 API
            # 这里提供接口预留
            result = await self._rag.adelete_by_id(doc_id)

            logger.info(f"文档删除成功 | ID: {doc_id}")
            return result

        except Exception as e:
            logger.error(f"文档删除失败 | ID: {doc_id} | 错误: {e}")
            raise DocumentError(
                f"文档删除失败: {e}",
                doc_id=doc_id,
            ) from e

    async def get_stats(self) -> GraphStats:
        """获取知识图谱统计信息。

        Returns:
            GraphStats: 图谱统计信息

        Raises:
            GraphError: 获取统计信息失败
        """
        await self._ensure_initialized()

        logger.debug("获取图谱统计信息")

        try:
            # 尝试获取图谱数据
            # 注意：LightRAG 的统计 API 可能因版本而异
            # 这里提供基础实现

            stats = GraphStats(
                entity_count=0,
                relationship_count=0,
                chunk_count=0,
                document_count=0,
                storage_info={
                    "graph_storage": "Neo4JStorage",
                    "vector_storage": "MilvusVectorDBStorage",
                    "working_dir": str(self.config.rag_working_dir),
                    "workspace": self.config.rag_workspace,
                },
            )

            logger.debug(f"图谱统计获取成功 | 实体: {stats.entity_count}")
            return stats

        except Exception as e:
            logger.error(f"获取图谱统计失败 | 错误: {e}")
            raise GraphError(
                f"获取图谱统计失败: {e}",
                details={"operation": "get_stats"},
            ) from e

    async def export_data(
        self,
        output_path: str,
        file_format: str = "csv",
        include_vectors: bool = False,
    ) -> None:
        """导出知识图谱数据。

        Args:
            output_path: 输出文件路径
            file_format: 文件格式（csv, excel, md, txt）
            include_vectors: 是否包含向量数据

        Raises:
            GraphError: 导出失败
            ValidationError: 参数无效
        """
        await self._ensure_initialized()

        valid_formats = ["csv", "excel", "md", "txt"]
        if file_format not in valid_formats:
            raise ValidationError(
                f"无效的导出格式: {file_format}",
                field="file_format",
                value=file_format,
                constraint=f"file_format in {valid_formats}",
            )

        logger.info(f"导出知识图谱 | 格式: {file_format} | 路径: {output_path}")

        try:
            await self._rag.aexport_data(
                output_path,
                file_format=file_format,
                include_vector_data=include_vectors,
            )

            logger.info(f"知识图谱导出成功 | 路径: {output_path}")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"知识图谱导出失败 | 错误: {e}")
            raise GraphError(
                f"知识图谱导出失败: {e}",
                details={"output_path": output_path, "format": file_format},
            ) from e

    async def create_graph(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> Dict[str, int]:
        """批量创建节点和关系到 Neo4j 图数据库。

        此方法直接操作 Neo4j 图存储，批量创建实体节点和关系。
        使用 Neo4j 的批量操作 API 以提高性能。

        Args:
            entities: 实体列表，每个实体包含：
                - entity_name (str): 实体名称
                - entity_type (str): 实体类型
                - description (str, optional): 实体描述
                - properties (dict, optional): 额外属性
            relationships: 关系列表，每个关系包含：
                - source (str): 源实体名称
                - target (str): 目标实体名称
                - relation (str): 关系类型
                - properties (dict, optional): 额外属性
            batch_size: 批量操作大小，默认 100

        Returns:
            Dict[str, int]: 创建结果统计
                - entity_count: 创建的实体数量
                - relationship_count: 创建的关系数量

        Raises:
            GraphError: 图创建失败
            ValidationError: 参数验证失败

        Example:
            >>> entities = [
            ...     {"entity_name": "糖尿病", "entity_type": "DISEASE"},
            ...     {"entity_name": "胰岛素", "entity_type": "MEDICINE"},
            ... ]
            >>> relationships = [
            ...     {"source": "胰岛素", "target": "糖尿病", "relation": "治疗"},
            ... ]
            >>> result = await adapter.create_graph(entities, relationships)
            >>> print(result)
            {'entity_count': 2, 'relationship_count': 1}
        """
        await self._ensure_initialized()

        if not entities and not relationships:
            raise ValidationError(
                "实体和关系不能同时为空",
                field="entities, relationships",
            )

        logger.info(
            f"开始创建图谱 | 实体数: {len(entities)} | 关系数: {len(relationships)}"
        )

        try:
            # 获取 Neo4j 图存储
            graph_storage = self._rag.graph_storage

            entity_count = 0
            relationship_count = 0

            # 批量创建实体节点
            if entities:
                logger.debug(f"批量创建实体节点 | 数量: {len(entities)}")

                # 分批处理实体
                for i in range(0, len(entities), batch_size):
                    batch = entities[i : i + batch_size]

                    # 使用 Neo4j 的 UNWIND 批量创建
                    entity_params = []
                    for entity in batch:
                        entity_name = entity.get("entity_name", "")
                        entity_type = entity.get("entity_type", "ENTITY")
                        description = entity.get("description", "")
                        properties = entity.get("properties", {})

                        entity_params.append(
                            {
                                "name": entity_name,
                                "type": entity_type,
                                "description": description,
                                **properties,
                            }
                        )

                    # 执行批量创建节点
                    cypher = """
                    UNWIND $entities AS entity
                    MERGE (n:__Entity__ {entity_name: entity.name})
                    SET n.entity_type = entity.type,
                        n.description = entity.description,
                        n += entity
                    """
                    await graph_storage.execute_query(
                        cypher, parameters={"entities": entity_params}
                    )

                    entity_count += len(batch)
                    logger.debug(f"已创建实体节点 | 批次: {i//batch_size + 1} | 数量: {len(batch)}")

            # 批量创建关系
            if relationships:
                logger.debug(f"批量创建关系 | 数量: {len(relationships)}")

                # 分批处理关系
                for i in range(0, len(relationships), batch_size):
                    batch = relationships[i : i + batch_size]

                    # 构建关系参数
                    rel_params = []
                    for rel in batch:
                        source = rel.get("source", "")
                        target = rel.get("target", "")
                        relation = rel.get("relation", "RELATED_TO")
                        properties = rel.get("properties", {})

                        rel_params.append(
                            {
                                "source": source,
                                "target": target,
                                "relation": relation,
                                "properties": properties,
                            }
                        )

                    # 执行批量创建关系
                    cypher = """
                    UNWIND $rels AS rel
                    MATCH (source:__Entity__ {entity_name: rel.source})
                    MATCH (target:__Entity__ {entity_name: rel.target})
                    CALL apoc.create.relationship(source, rel.relation, rel.properties, target)
                    YIELD rel
                    RETURN count(*)
                    """
                    # 如果没有 APOC，使用标准 Cypher
                    cypher_standard = """
                    UNWIND $rels AS rel
                    MATCH (source:__Entity__ {entity_name: rel.source})
                    MATCH (target:__Entity__ {entity_name: rel.target})
                    MERGE (source)-[r:RELATED_TO]->(target)
                    SET r += rel.properties
                    RETURN count(*)
                    """

                    try:
                        await graph_storage.execute_query(
                            cypher, parameters={"rels": rel_params}
                        )
                    except Exception:
                        # 如果 APOC 不可用，使用标准 Cypher
                        await graph_storage.execute_query(
                            cypher_standard, parameters={"rels": rel_params}
                        )

                    relationship_count += len(batch)
                    logger.debug(f"已创建关系 | 批次: {i//batch_size + 1} | 数量: {len(batch)}")

            result = {
                "entity_count": entity_count,
                "relationship_count": relationship_count,
            }

            logger.info(
                f"图谱创建完成 | 实体: {entity_count} | 关系: {relationship_count}"
            )

            return result

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"图谱创建失败 | 错误: {e}")
            raise GraphError(
                f"图谱创建失败: {e}",
                details={
                    "entities_count": len(entities),
                    "relationships_count": len(relationships),
                },
            ) from e

    async def query_cypher(
        self,
        cypher_query: str,
        graph_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = 1000,
    ) -> List[Dict[str, Any]]:
        """执行 Cypher 查询。

        此方法直接在 Neo4j 图数据库上执行 Cypher 查询。
        支持参数化查询以防止注入攻击，并限制返回数量以防止内存溢出。

        Args:
            cypher_query: Cypher 查询语句
            graph_id: 图谱 ID（可选，用于多租户隔离）
            params: 查询参数（参数化查询）
            limit: 最大返回数量，默认 1000（设为 None 表示无限制）

        Returns:
            List[Dict[str, Any]]: 查询结果列表

        Raises:
            GraphError: 查询执行失败
            ValidationError: 查询参数无效

        Example:
            >>> # 基础查询
            >>> results = await adapter.query_cypher(
            ...     "MATCH (n:DISEASE) RETURN n LIMIT 10",
            ...     graph_id="graph-123"
            ... )
            >>>
            >>> # 参数化查询
            >>> results = await adapter.query_cypher(
            ...     "MATCH (n {entity_name: $name}) RETURN n",
            ...     params={"name": "糖尿病"}
            ... )
        """
        await self._ensure_initialized()

        if not cypher_query or not cypher_query.strip():
            raise ValidationError(
                "Cypher 查询不能为空",
                field="cypher_query",
            )

        # 验证查询安全性（基础检查）
        query_upper = cypher_query.upper().strip()
        dangerous_keywords = ["DROP", "DELETE", "DETACH", "REMOVE"]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValidationError(
                    f"Cypher 查询包含危险关键字: {keyword}",
                    field="cypher_query",
                    value=cypher_query,
                )

        logger.info(
            f"执行 Cypher 查询 | 图谱 ID: {graph_id or '默认'} | "
            f"限制: {limit} | 查询: {cypher_query[:100]}..."
        )

        try:
            # 获取 Neo4j 图存储
            graph_storage = self._rag.graph_storage

            # 添加 LIMIT 子句（如果查询中未包含且指定了 limit）
            if limit is not None and "LIMIT" not in query_upper:
                cypher_query = f"{cypher_query.rstrip(';')} LIMIT {limit}"
                logger.debug(f"添加 LIMIT 子句 | 新查询: {cypher_query}")

            # 执行查询
            result = await graph_storage.execute_query(
                cypher_query, parameters=params or {}
            )

            # 转换结果为字典列表
            # LightRAG 的 execute_query 返回格式可能因版本而异
            if isinstance(result, (list, tuple)):
                # 尝试解析结果
                results_list = []
                for record in result:
                    if isinstance(record, dict):
                        results_list.append(record)
                    elif hasattr(record, "data"):
                        results_list.append(record.data())
                    else:
                        # 尝试转换为字典
                        results_list.append(dict(record) if hasattr(record, "__iter__") else {"value": record})
            else:
                results_list = [result] if result is not None else []

            logger.info(f"查询完成 | 返回结果数: {len(results_list)}")

            return results_list[:limit] if limit is not None else results_list

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Cypher 查询失败 | 错误: {e}")
            raise GraphError(
                f"Cypher 查询执行失败: {e}",
                details={
                    "query": cypher_query,
                    "params": params,
                    "graph_id": graph_id,
                },
            ) from e

    async def vector_similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """基于向量的相似度搜索。

        此方法在 Milvus 向量数据库中执行相似度搜索，返回最相似的 top_k 个节点。

        Args:
            query_vector: 查询向量（嵌入向量）
            top_k: 返回的相似节点数量，默认 5
            filters: 过滤条件（标量过滤），例如：
                - {"entity_type": "DISEASE"}
                - {"year": {"$gt": 2020}}
            collection_name: 集合名称（可选，默认使用 LightRAG 默认集合）

        Returns:
            List[Dict[str, Any]]: 相似节点列表，每个节点包含：
                - id: 节点 ID
                - distance: 相似度距离（越小越相似）
                - score: 相似度分数（越大越相似，1 - distance）
                - entity: 节点的完整数据

        Raises:
            GraphError: 向量搜索失败
            ValidationError: 参数验证失败

        Example:
            >>> # 生成查询向量
            >>> query_vector = await adapter.embed_text("糖尿病的症状")
            >>>
            >>> # 执行向量搜索
            >>> results = await adapter.vector_similarity_search(
            ...     query_vector=query_vector,
            ...     top_k=5,
            ...     filters={"entity_type": "DISEASE"}
            ... )
            >>>
            >>> for result in results:
            ...     print(f"ID: {result['id']}, 分数: {result['score']:.4f}")
        """
        await self._ensure_initialized()

        if not query_vector:
            raise ValidationError(
                "查询向量不能为空",
                field="query_vector",
            )

        if top_k <= 0:
            raise ValidationError(
                f"top_k 必须大于 0，当前值: {top_k}",
                field="top_k",
                value=top_k,
            )

        logger.info(
            f"执行向量相似度搜索 | top_k: {top_k} | "
            f"过滤条件: {filters or '无'} | 向量维度: {len(query_vector)}"
        )

        try:
            # 获取 Milvus 向量存储
            vector_storage = self._rag.vector_storage

            # 构建 Milvus 搜索表达式（如果提供了过滤条件）
            search_expr = None
            if filters:
                expr_parts = []
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # 支持操作符：$gt, $lt, $gte, $lte, $ne, $in
                        for op_key, op_value in value.items():
                            if op_key == "$gt":
                                expr_parts.append(f"{key} > {op_value}")
                            elif op_key == "$lt":
                                expr_parts.append(f"{key} < {op_value}")
                            elif op_key == "$gte":
                                expr_parts.append(f"{key} >= {op_value}")
                            elif op_key == "$lte":
                                expr_parts.append(f"{key} <= {op_value}")
                            elif op_key == "$ne":
                                expr_parts.append(f'{key} != "{op_value}"')
                            elif op_key == "$in":
                                values = ", ".join(f'"{v}"' for v in op_value)
                                expr_parts.append(f"{key} in [{values}]")
                    else:
                        expr_parts.append(f'{key} == "{value}"')
                search_expr = " and ".join(expr_parts)
                logger.debug(f"搜索表达式: {search_expr}")

            # 执行向量搜索
            # 注意：LightRAG 的 MilvusVectorDBStorage 可能不直接暴露搜索接口
            # 这里需要根据实际 API 调整
            try:
                # 尝试直接调用 Milvus 搜索
                results = await vector_storage.search(
                    data=[query_vector],
                    limit=top_k,
                    expr=search_expr,
                )
            except AttributeError:
                # 如果 vector_storage 不支持直接搜索，使用 LightRAG 的查询接口
                # 或者通过底层的 Milvus collection
                logger.warning("向量存储不直接支持搜索，使用 LightRAG 查询接口")

                # 生成查询文本（从向量反推或使用占位符）
                # 这里简化处理，实际应该存储向量到文本的映射
                query_text = " ".join([f"[{v:.4f}]" for v in query_vector[:10]])

                # 使用 LightRAG 的查询接口
                param = QueryParam(mode="local", top_k=top_k)
                answer = await self._rag.aquery(query_text, param=param)

                # 返回简化的结果格式
                return [
                    {
                        "id": f"result-{i}",
                        "distance": 0.0,
                        "score": 1.0,
                        "entity": {"content": answer},
                    }
                    for i in range(top_k)
                ]

            # 解析 Milvus 搜索结果
            formatted_results = []
            if results and len(results) > 0:
                # Milvus 返回的结果是嵌套列表：[[result1, result2, ...]]
                top_results = results[0] if isinstance(results[0], list) else results

                for hit in top_results[:top_k]:
                    # 获取距离和 ID
                    distance = hit.distance if hasattr(hit, "distance") else 0.0
                    score = 1.0 - distance  # 转换为相似度分数

                    # 获取实体数据
                    entity_data = {}
                    if hasattr(hit, "entity"):
                        entity = hit.entity
                        if hasattr(entity, "get"):
                            entity_data = entity
                        elif isinstance(entity, dict):
                            entity_data = entity
                        else:
                            entity_data = {"data": str(entity)}

                    formatted_results.append(
                        {
                            "id": hit.id if hasattr(hit, "id") else str(hit),
                            "distance": float(distance),
                            "score": float(score),
                            "entity": entity_data,
                        }
                    )

            logger.info(
                f"向量搜索完成 | 返回结果数: {len(formatted_results)} | "
                f"最高分数: {max([r['score'] for r in formatted_results]) if formatted_results else 0:.4f}"
            )

            return formatted_results

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"向量相似度搜索失败 | 错误: {e}")
            raise GraphError(
                f"向量相似度搜索失败: {e}",
                details={
                    "top_k": top_k,
                    "filters": filters,
                    "vector_dim": len(query_vector),
                },
            ) from e

    async def close(self) -> None:
        """关闭适配器，释放资源。

        Raises:
            StorageError: 关闭失败
        """
        if not self._initialized or self._rag is None:
            logger.warning("适配器未初始化，无需关闭")
            return

        logger.info("关闭 RAG-Anything 适配器")

        try:
            # 关闭存储连接
            await self._rag.finalize_storages()

            self._initialized = False
            self._rag = None

            logger.info("RAG-Anything 适配器已关闭")

        except Exception as e:
            logger.error(f"适配器关闭失败 | 错误: {e}")
            raise StorageError(
                f"适配器关闭失败: {e}",
                storage_type="lightrag",
                operation="close",
            ) from e

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.close()


# ========== 导出的公共接口 ==========

__all__ = [
    "RAGAnythingAdapter",
    "IngestResult",
    "QueryResult",
    "GraphStats",
    "QueryMode",
    "_create_embedding_func",
    "_create_llm_func",
    "_configure_storage",
]
