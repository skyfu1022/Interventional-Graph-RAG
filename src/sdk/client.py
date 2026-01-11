"""
Medical Graph RAG Python SDK 客户端。

该模块提供 Medical Graph RAG 的 Python SDK 主要客户端接口，
用于与医疗知识图谱系统进行交互。

主要功能:
- 异步上下文管理器支持（自动初始化和清理资源）
- 文档摄入（文本、文件、批量、多模态）
- 知识图谱查询（支持多种查询模式）
- 图谱管理和统计
- 性能监控和指标收集
- 配置管理（环境变量、配置文件）

使用示例:
    >>> from src.sdk import MedGraphClient
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     # 使用异步上下文管理器（推荐）
    >>>     async with MedGraphClient(workspace="medical") as client:
    >>>         # 摄入文档
    >>>         await client.ingest_document("medical_doc.txt")
    >>>
    >>>         # 查询知识图谱
    >>>         result = await client.query("什么是糖尿病?")
    >>>         print(result.answer)
    >>>
    >>>         # 获取性能统计
    >>>         stats = client.get_stats()
    >>>         print(f"查询次数: {stats['total_queries']}")
    >>>
    >>> asyncio.run(main())

基于 LightRAG 1.4.9+ 版本实现，整合所有服务层功能。
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, field

from src.core.config import Settings, get_settings
from src.core.logging import setup_logging, get_logger
from src.core.exceptions import QueryError, DocumentError, ValidationError, ConfigError, NotFoundError
from src.core.adapters import (
    RAGAnythingAdapter,
    IngestResult,
    QueryResult as AdapterQueryResult,
    GraphStats,
    QueryMode as AdapterQueryMode,
)

# 导入服务层
from src.services.ingestion import IngestionService, BatchIngestResult
from src.services.query import QueryService as ServiceQueryService, QueryContext
from src.services.graph import GraphService

# 导入 SDK 层类型
from src.sdk.types import (
    QueryMode,
    QueryResult,
    DocumentInfo,
    GraphInfo,
    GraphConfig,
    SourceInfo,
    GraphContext,
)
from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError as SDKConfigError,
    DocumentNotFoundError,
    ConnectionError as SDKConnectionError,
    ValidationError as SDKValidationError,
)
from src.sdk.monitoring import PerformanceMonitor, QueryPerformanceTimer


# ========== 配置文件解析函数 ==========


def _load_yaml_config(path: str) -> Dict[str, Any]:
    """加载 YAML 配置文件。
    
    Args:
        path: YAML 文件路径
        
    Returns:
        配置字典
        
    Raises:
        SDKConfigError: 文件读取失败或格式错误
    """
    try:
        import yaml
    except ImportError:
        raise SDKConfigError(
            "缺少 YAML 依赖，请安装: pip install pyyaml",
            config_file=path
        )
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                return {}
            return config
    except FileNotFoundError:
        raise SDKConfigError(
            f"配置文件不存在: {path}",
            config_file=path
        )
    except yaml.YAMLError as e:
        raise SDKConfigError(
            f"YAML 格式错误: {str(e)}",
            config_file=path
        )
    except Exception as e:
        raise SDKConfigError(
            f"读取配置文件失败: {str(e)}",
            config_file=path
        )


def _load_json_config(path: str) -> Dict[str, Any]:
    """加载 JSON 配置文件。
    
    Args:
        path: JSON 文件路径
        
    Returns:
        配置字典
        
    Raises:
        SDKConfigError: 文件读取失败或格式错误
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        raise SDKConfigError(
            f"配置文件不存在: {path}",
            config_file=path
        )
    except json.JSONDecodeError as e:
        raise SDKConfigError(
            f"JSON 格式错误: {str(e)}",
            config_file=path
        )
    except Exception as e:
        raise SDKConfigError(
            f"读取配置文件失败: {str(e)}",
            config_file=path
        )


# ========== SDK 结果数据类 ==========


@dataclass
class DocumentInfo:
    """文档信息。

    Attributes:
        doc_id: 文档 ID
        status: 文档状态（pending, processing, completed, failed）
        file_path: 文件路径（如果从文件摄入）
        chunks_count: 文本块数量
        entities_count: 提取的实体数量
        error: 错误信息（如果失败）
        metadata: 额外的元数据
    """

    doc_id: Optional[str]
    status: str
    file_path: Optional[str] = None
    chunks_count: int = 0
    entities_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_ingest_result(cls, result: IngestResult, file_path: Optional[str] = None) -> "DocumentInfo":
        """从适配器摄入结果创建文档信息。

        Args:
            result: 适配器摄入结果
            file_path: 源文件路径

        Returns:
            DocumentInfo: 文档信息
        """
        return cls(
            doc_id=result.doc_id,
            status=result.status,
            file_path=file_path,
            chunks_count=result.chunks_count,
            entities_count=result.entities_count,
            error=result.error,
            metadata=result.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "doc_id": self.doc_id,
            "status": self.status,
            "file_path": self.file_path,
            "chunks_count": self.chunks_count,
            "entities_count": self.entities_count,
            "error": self.error,
            "metadata": self.metadata,
        }


# ========== SDK 客户端主类 ==========


class MedGraphClient:
    """Medical Graph RAG Python SDK 客户端。

    支持异步上下文管理器协议，自动处理资源的初始化和清理。
    提供简单易用的接口与医疗知识图谱系统进行交互。

    整合所有服务层功能：
    - IngestionService: 文档摄入
    - QueryService: 查询服务
    - GraphService: 图谱管理
    - PerformanceMonitor: 性能监控

    Attributes:
        workspace: 工作空间名称
        config: 配置对象
        _adapter: RAG 适配器实例
        _initialized: 是否已初始化
        _performance_monitor: 性能监控器

    Example:
        >>> # 基本使用（自动初始化）
        >>> async with MedGraphClient(workspace="medical") as client:
        ...     result = await client.query("测试")
        ...     print(result.answer)
        >>> # 退出时自动关闭连接
        >>>
        >>> # 手动管理
        >>> client = MedGraphClient(workspace="medical")
        >>> await client.initialize()
        >>> result = await client.query("问题")
        >>> await client.close()
        >>>
        >>> # 使用性能监控
        >>> async with MedGraphClient(enable_metrics=True) as client:
        ...     result = await client.query("测试")
        ...     stats = client.get_stats()
        ...     print(f"平均延迟: {stats['avg_latency_ms']}ms")
    """
    
    def __init__(
        self,
        workspace: str = "medical",
        log_level: str = "INFO",
        config: Optional[Settings] = None,
        enable_metrics: bool = True,
        **kwargs
    ):
        """初始化 SDK 客户端。

        Args:
            workspace: 工作空间名称，用于隔离不同的知识图谱
            log_level: 日志级别
            config: 配置对象（可选，如果不提供则从环境变量加载）
            enable_metrics: 是否启用性能监控
            **kwargs: 额外的配置参数（会覆盖 config 中的值）

        Raises:
            SDKConfigError: 配置无效
        """
        # 设置日志
        setup_logging(log_level=log_level)
        self.logger = get_logger("MedGraphClient")
        
        self.workspace = workspace
        self._config = config
        self._config_overrides = kwargs
        self._adapter: Optional[RAGAnythingAdapter] = None
        self._initialized = False
        
        # 性能监控
        self._enable_metrics = enable_metrics
        self._performance_monitor = PerformanceMonitor(enable_metrics=enable_metrics)
        
        # 服务层实例（延迟初始化）
        self._ingestion_service: Optional[IngestionService] = None
        self._query_service: Optional[ServiceQueryService] = None
        self._graph_service: Optional[GraphService] = None

        self.logger.debug(
            f"SDK 客户端创建 | 工作空间: {workspace} | "
            f"自定义配置: {len(kwargs)} 项 | 性能监控: {enable_metrics}"
        )

    @property
    def config(self) -> Settings:
        """获取配置对象（延迟加载）。

        Returns:
            Settings: 配置对象
        """
        if self._config is None:
            # 创建配置对象（合并参数）
            config_params = {"rag_workspace": self.workspace, **self._config_overrides}
            self._config = Settings(**config_params)

        return self._config

    def _create_adapter(self) -> RAGAnythingAdapter:
        """创建 RAG 适配器实例。

        Returns:
            RAGAnythingAdapter: 适配器实例

        Raises:
            SDKConfigError: 配置无效
        """
        try:
            # 确保配置包含工作空间
            config = self.config.model_copy(update={"rag_workspace": self.workspace})

            adapter = RAGAnythingAdapter(config)
            self.logger.debug(f"RAG 适配器创建成功 | 工作空间: {self.workspace}")
            return adapter

        except Exception as e:
            self.logger.error(f"RAG 适配器创建失败 | 错误: {e}")
            raise SDKConfigError(
                f"RAG 适配器创建失败: {e}",
                config_key="rag_adapter",
            ) from e

    def _init_services(self) -> None:
        """初始化服务层实例。"""
        if self._adapter is None:
            return
        
        # 创建服务层实例
        self._ingestion_service = IngestionService(self._adapter)
        self._query_service = ServiceQueryService(self._adapter)
        self._graph_service = GraphService(self._adapter)
        
        self.logger.debug("服务层初始化完成")

    async def __aenter__(self) -> "MedGraphClient":
        """进入异步上下文。

        自动初始化适配器和连接，支持初始化超时控制。

        Returns:
            MedGraphClient: 客户端实例

        Raises:
            SDKConfigError: 初始化超时或失败

        Example:
            >>> async with MedGraphClient(workspace="medical") as client:
            ...     result = await client.query("测试")
            ... # 退出时自动关闭连接
        """
        self.logger.info(f"进入 SDK 客户端上下文 | 工作空间: {self.workspace}")

        try:
            # 使用超时确保初始化不会无限等待
            await asyncio.wait_for(
                self._ensure_initialized(),
                timeout=30.0  # 30 秒超时
            )

            self.logger.info(f"SDK 客户端上下文就绪 | 工作空间: {self.workspace}")
            return self

        except asyncio.TimeoutError:
            self.logger.error(f"SDK 客户端初始化超时 | 工作空间: {self.workspace}")
            raise SDKConfigError(
                "SDK 客户端初始化超时（30秒）",
                config_key="initialization_timeout",
            )
        except Exception as e:
            self.logger.error(f"SDK 客户端上下文进入失败 | 错误: {e}")
            raise

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any]
    ) -> None:
        """退出异步上下文。

        自动关闭连接和释放资源，确保资源清理不会掩盖原始异常。

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪

        Example:
            >>> async with MedGraphClient() as client:
            ...     raise ValueError("测试异常")
            >>> # 异常会被正确传播，连接已关闭
        """
        self.logger.info(
            f"退出 SDK 客户端上下文 | 工作空间: {self.workspace} | "
            f"异常: {exc_type.__name__ if exc_type else '无'}"
        )

        try:
            await self.close()
        except Exception as e:
            self.logger.error(f"关闭客户端时发生错误 | 错误: {e}")
            # 不要在 __aexit__ 中抛出异常
            # 这会掩盖原始异常

        # 记录原始异常信息
        if exc_val:
            self.logger.error(
                f"上下文退出时发生异常: {exc_type.__name__}: {exc_val}"
            )

    async def _ensure_initialized(self) -> None:
        """确保客户端已初始化。

        LightRAG 1.4.9+ 要求在首次使用前调用初始化方法。
        此方法可以安全地多次调用（幂等性）。

        Raises:
            SDKConfigError: 初始化失败
        """
        if self._initialized:
            return

        self.logger.info(f"初始化 SDK 客户端 | 工作空间: {self.workspace}")

        try:
            # 创建适配器实例
            self._adapter = self._create_adapter()

            # 初始化适配器（包括存储和管道状态）
            await self._adapter.initialize()
            
            # 初始化服务层
            self._init_services()

            self._initialized = True
            self.logger.info(f"SDK 客户端初始化完成 | 工作空间: {self.workspace}")

        except SDKConfigError:
            # 重新抛出配置错误
            raise
        except Exception as e:
            self.logger.error(f"SDK 客户端初始化失败 | 错误: {e}")
            raise SDKConfigError(
                f"SDK 客户端初始化失败: {e}",
                config_key="client_initialization",
            ) from e

    async def close(self) -> None:
        """关闭客户端，释放资源。

        关闭适配器连接，清理缓存。可以安全地多次调用。

        Example:
            >>> client = MedGraphClient()
            >>> await client.initialize()
            >>> # ... 使用客户端 ...
            >>> await client.close()
        """
        if not self._initialized or self._adapter is None:
            self.logger.debug("SDK 客户端未初始化，无需关闭")
            return

        self.logger.info(f"关闭 SDK 客户端 | 工作空间: {self.workspace}")

        try:
            # 关闭适配器
            await self._adapter.close()

            self._initialized = False
            self._adapter = None
            self._ingestion_service = None
            self._query_service = None
            self._graph_service = None

            self.logger.info(f"SDK 客户端已关闭 | 工作空间: {self.workspace}")

        except Exception as e:
            self.logger.error(f"SDK 客户端关闭失败 | 错误: {e}")
            # 不抛出异常，确保清理完成

    async def initialize(self) -> None:
        """手动初始化客户端（如果不使用上下文管理器）。

        此方法是公开的，允许用户在不使用 async with 的情况下管理生命周期。

        Example:
            >>> client = MedGraphClient()
            >>> await client.initialize()
            >>> result = await client.query("问题")
            >>> await client.close()
        """
        await self._ensure_initialized()

    # ========== 文档摄入方法 ==========

    async def ingest_document(
        self,
        file_path: str,
        doc_id: Optional[str] = None,
    ) -> DocumentInfo:
        """摄入文档到知识图谱。

        支持各种文本格式（txt, md, json, csv 等）。
        自动进行文本切分、实体提取和关系构建。

        Args:
            file_path: 文档文件路径
            doc_id: 文档 ID（可选，如果不提供则自动生成）

        Returns:
            DocumentInfo: 文档信息

        Raises:
            SDKValidationError: 文件路径无效
            DocumentError: 文档读取或摄入失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     doc_info = await client.ingest_document("medical.txt")
            ...     print(f"摄入成功 | ID: {doc_info.doc_id}")
        """
        await self._ensure_initialized()

        self.logger.info(f"摄入文档 | 路径: {file_path} | ID: {doc_id or '自动生成'}")

        try:
            # 使用服务层摄入文档
            result = await self._ingestion_service.ingest_document(file_path, doc_id)

            # 转换为 SDK 格式
            doc_info = DocumentInfo.from_ingest_result(result, file_path=file_path)
            
            # 记录性能指标
            self._performance_monitor.record_document(success=True)

            self.logger.info(f"文档摄入成功 | ID: {doc_info.doc_id} | 状态: {doc_info.status}")

            return doc_info

        except (ValidationError, DocumentError):
            self._performance_monitor.record_document(success=False)
            # 重新抛出已知异常
            raise
        except Exception as e:
            self._performance_monitor.record_document(success=False)
            self.logger.error(f"文档摄入失败 | 文件: {file_path} | 错误: {e}")
            raise DocumentError(
                f"文档摄入失败: {e}",
                doc_id=doc_id,
                details={"file_path": file_path},
            ) from e

    async def ingest_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
    ) -> DocumentInfo:
        """摄入文本到知识图谱。

        适合处理程序生成的文本或 API 获取的文本内容。

        Args:
            text: 文本内容
            doc_id: 文档 ID（可选）

        Returns:
            DocumentInfo: 文档信息

        Raises:
            SDKValidationError: 文本为空
            DocumentError: 文本摄入失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     text = "糖尿病是一种慢性代谢性疾病..."
            ...     doc_info = await client.ingest_text(text, doc_id="doc-001")
        """
        await self._ensure_initialized()

        self.logger.debug(f"摄入文本 | ID: {doc_id or '自动生成'} | 长度: {len(text)}")

        try:
            result = await self._ingestion_service.ingest_text(text, doc_id)
            doc_info = DocumentInfo.from_ingest_result(result)
            
            # 记录性能指标
            self._performance_monitor.record_document(success=True)

            self.logger.debug(f"文本摄入成功 | ID: {doc_info.doc_id}")

            return doc_info

        except (ValidationError, DocumentError):
            self._performance_monitor.record_document(success=False)
            raise
        except Exception as e:
            self._performance_monitor.record_document(success=False)
            self.logger.error(f"文本摄入失败 | 错误: {e}")
            raise DocumentError(
                f"文本摄入失败: {e}",
                doc_id=doc_id,
            ) from e

    async def ingest_batch(
        self,
        file_paths: List[str],
        doc_ids: Optional[List[str]] = None,
        max_concurrency: int = 5,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BatchIngestResult:
        """批量摄入文档到知识图谱。

        适合批量处理多个文档，提高摄入效率。

        Args:
            file_paths: 文档文件路径列表
            doc_ids: 文档 ID 列表（可选，长度必须与 file_paths 一致）
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数

        Returns:
            BatchIngestResult: 批量摄入结果

        Raises:
            SDKValidationError: 参数验证失败
            DocumentError: 批量摄入失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     def on_progress(cur, total, doc_id):
            ...         print(f"进度: {cur}/{total} - {doc_id}")
            ...     
            ...     result = await client.ingest_batch(
            ...         ["doc1.txt", "doc2.txt", "doc3.txt"],
            ...         progress_callback=on_progress
            ...     )
            ...     print(f"完成: {result.succeeded}/{result.total}")
        """
        await self._ensure_initialized()

        self.logger.info(f"批量摄入 | 文档数: {len(file_paths)}")

        try:
            results = await self._ingestion_service.ingest_batch(
                file_paths=file_paths,
                doc_ids=doc_ids,
                max_concurrency=max_concurrency,
                progress_callback=progress_callback,
            )

            # 记录性能指标
            for result in results.results:
                if result.status == "completed":
                    self._performance_monitor.record_document(success=True)
                else:
                    self._performance_monitor.record_document(success=False)

            self.logger.info(f"批量摄入成功 | 文档数: {results.succeeded}/{results.total}")

            return results

        except (ValidationError, DocumentError):
            raise
        except Exception as e:
            self.logger.error(f"批量摄入失败 | 错误: {e}")
            raise DocumentError(
                f"批量摄入失败: {e}",
                details={"texts_count": len(file_paths)},
            ) from e

    async def ingest_multimodal(
        self,
        content_list: List[Dict[str, Any]],
        file_path: Optional[str] = None,
    ) -> DocumentInfo:
        """摄入多模态内容（文本、图片、表格等）。

        支持处理包含多种内容类型的复杂文档。

        Args:
            content_list: 内容列表，每个元素是包含 content_type 和 content 的字典
            file_path: 源文件路径（可选）

        Returns:
            DocumentInfo: 文档信息

        Raises:
            SDKValidationError: 内容格式无效
            DocumentError: 多模态摄入失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     contents = [
            ...         {"content_type": "text", "content": "报告文本"},
            ...         {"content_type": "image", "content": "base64..."}
            ...     ]
            ...     doc_info = await client.ingest_multimodal(contents)
        """
        await self._ensure_initialized()

        self.logger.info(f"摄入多模态内容 | 内容数: {len(content_list)}")

        try:
            result = await self._adapter.ingest_multimodal(content_list, file_path)
            doc_info = DocumentInfo.from_ingest_result(result, file_path=file_path)
            
            self._performance_monitor.record_document(success=True)

            self.logger.info(f"多模态摄入成功 | ID: {doc_info.doc_id}")

            return doc_info

        except (ValidationError, DocumentError):
            self._performance_monitor.record_document(success=False)
            raise
        except Exception as e:
            self._performance_monitor.record_document(success=False)
            self.logger.error(f"多模态摄入失败 | 错误: {e}")
            raise DocumentError(
                f"多模态摄入失败: {e}",
                details={"content_count": len(content_list)},
            ) from e

    # ========== 查询方法 ==========

    async def query(
        self,
        query_text: str,
        mode: str = "hybrid",
        graph_id: str = "default",
        **kwargs
    ) -> QueryResult:
        """执行知识图谱查询。

        支持多种查询模式，根据问题类型自动选择最佳检索策略。
        集成性能监控，自动记录查询延迟和成功率。

        Args:
            query_text: 查询问题
            mode: 查询模式（naive, local, global, hybrid, mix, bypass）
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Returns:
            QueryResult: 查询结果

        Raises:
            SDKValidationError: 查询参数无效
            QueryError: 查询执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     # 混合模式查询（推荐）
            ...     result = await client.query("什么是糖尿病?")
            ...     print(result.answer)
            ...     
            ...     # 局部模式查询（关注实体关系）
            ...     result = await client.query(
            ...         "糖尿病和高血压有什么关系?",
            ...         mode="local"
            ...     )
        """
        await self._ensure_initialized()

        if not query_text or not query_text.strip():
            raise ValidationError(
                "查询问题不能为空",
                field="query_text",
            )

        self.logger.info(f"执行查询 | 模式: {mode} | 问题: {query_text[:100]}...")

        # 使用性能计时器
        start_time = time.time()

        try:
            # 调用服务层查询
            from src.services.query import QueryResult as ServiceQueryResult
            service_result = await self._query_service.query(
                query_text=query_text,
                mode=mode,
                graph_id=graph_id,
                **kwargs
            )
            
            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)

            # 转换为 SDK QueryResult
            result = QueryResult(
                query=service_result.query,
                answer=service_result.answer,
                mode=QueryMode(service_result.mode.value),
                graph_id=service_result.graph_id,
                sources=[
                    SourceInfo(
                        doc_id=s.get("doc_id", ""),
                        chunk_id=s.get("chunk_id", ""),
                        content=s.get("content", ""),
                        relevance=s.get("relevance", 0.0),
                    )
                    for s in service_result.sources
                ],
                context=service_result.context,
                retrieval_count=service_result.retrieval_count,
                latency_ms=latency_ms,
            )

            # 记录性能指标
            self._performance_monitor.record_query(mode, latency_ms, success=True)

            self.logger.info(
                f"查询完成 | 模式: {mode} | "
                f"答案长度: {len(result.answer)} | 延迟: {latency_ms}ms"
            )

            return result

        except ValidationError:
            raise
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._performance_monitor.record_query(mode, latency_ms, success=False)
            self.logger.error(f"查询失败 | 错误: {e}")
            raise QueryError(
                f"查询执行失败: {e}",
                query_text=query_text,
                details={"mode": mode, "latency_ms": latency_ms},
            ) from e

    async def query_stream(
        self,
        query_text: str,
        mode: str = "hybrid",
        graph_id: str = "default",
        **kwargs
    ) -> AsyncIterator[str]:
        """流式查询知识图谱。

        逐块返回生成的答案，适合长文本或实时响应场景。

        Args:
            query_text: 查询问题
            mode: 查询模式
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Yields:
            str: 流式答案片段

        Raises:
            SDKValidationError: 查询参数无效
            QueryError: 查询执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     async for chunk in client.query_stream("详细说明糖尿病的病因"):
            ...         print(chunk, end="", flush=True)
        """
        await self._ensure_initialized()

        if not query_text or not query_text.strip():
            raise ValidationError(
                "查询问题不能为空",
                field="query_text",
            )

        self.logger.info(f"执行流式查询 | 模式: {mode}")

        try:
            async for chunk in self._query_service.query_stream(
                query_text=query_text,
                mode=mode,
                graph_id=graph_id,
                **kwargs
            ):
                yield chunk

            self.logger.info(f"流式查询完成 | 模式: {mode}")

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"流式查询失败 | 错误: {e}")
            raise QueryError(
                f"流式查询执行失败: {e}",
                query_text=query_text,
                details={"mode": mode},
            ) from e

    # ========== 文档管理方法 ==========

    async def delete_document(self, doc_id: str) -> bool:
        """从知识图谱中删除文档。

        Args:
            doc_id: 文档 ID

        Returns:
            bool: 是否删除成功

        Raises:
            NotFoundError: 文档不存在
            DocumentError: 删除失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     success = await client.delete_document("doc-123")
            ...     if success:
            ...         print("文档删除成功")
        """
        await self._ensure_initialized()

        self.logger.info(f"删除文档 | ID: {doc_id}")

        try:
            result = await self._adapter.delete_document(doc_id)
            self.logger.info(f"文档删除成功 | ID: {doc_id}")
            return result

        except Exception as e:
            self.logger.error(f"文档删除失败 | ID: {doc_id} | 错误: {e}")
            raise DocumentError(
                f"文档删除失败: {e}",
                doc_id=doc_id,
            ) from e

    # ========== 图谱管理方法 ==========

    async def list_graphs(self) -> List[GraphInfo]:
        """列出所有图谱。

        Returns:
            List[GraphInfo]: 图谱信息列表

        Raises:
            GraphError: 获取图谱列表失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     graphs = await client.list_graphs()
            ...     for graph in graphs:
            ...         print(f"{graph.graph_id}: {graph.entity_count} 实体")
        """
        await self._ensure_initialized()

        self.logger.debug("列出所有图谱")

        try:
            service_graphs = await self._graph_service.list_graphs()

            # 转换为 SDK GraphInfo
            return [
                GraphInfo(
                    graph_id=g.graph_id,
                    workspace=g.workspace,
                    entity_count=g.entity_count,
                    relationship_count=g.relationship_count,
                    document_count=g.document_count,
                    created_at=g.created_at or "",
                    updated_at=g.updated_at or "",
                )
                for g in service_graphs
            ]

        except Exception as e:
            self.logger.error(f"列出图谱失败 | 错误: {e}")
            raise QueryError(
                f"列出图谱失败: {e}",
                details={"operation": "list_graphs"},
            ) from e

    async def get_graph(self, graph_id: str) -> GraphInfo:
        """获取图谱详情。

        Args:
            graph_id: 图谱 ID

        Returns:
            GraphInfo: 图谱信息

        Raises:
            NotFoundError: 图谱不存在
            GraphError: 获取信息失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     info = await client.get_graph("medical")
            ...     print(f"实体数: {info.entity_count}")
        """
        await self._ensure_initialized()

        self.logger.debug(f"获取图谱详情: {graph_id}")

        try:
            g = await self._graph_service.get_graph_info(graph_id)

            return GraphInfo(
                graph_id=g.graph_id,
                workspace=g.workspace,
                entity_count=g.entity_count,
                relationship_count=g.relationship_count,
                document_count=g.document_count,
                created_at=g.created_at or "",
                updated_at=g.updated_at or "",
            )

        except Exception as e:
            self.logger.error(f"获取图谱详情失败 | 错误: {e}")
            raise QueryError(
                f"获取图谱详情失败: {e}",
                details={"graph_id": graph_id},
            ) from e

    async def delete_graph(self, graph_id: str, confirm: bool = False) -> bool:
        """删除图谱。

        Args:
            graph_id: 图谱 ID
            confirm: 是否确认删除（安全措施）

        Returns:
            bool: 是否成功删除

        Raises:
            SDKValidationError: 未确认删除操作
            NotFoundError: 图谱不存在
            GraphError: 删除失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     success = await client.delete_graph("test", confirm=True)
        """
        await self._ensure_initialized()

        self.logger.info(f"删除图谱: {graph_id}")

        try:
            result = await self._graph_service.delete_graph(graph_id, confirm=confirm)
            self.logger.info(f"图谱删除成功: {graph_id}")
            return result

        except Exception as e:
            self.logger.error(f"删除图谱失败 | 错误: {e}")
            raise QueryError(
                f"删除图谱失败: {e}",
                details={"graph_id": graph_id},
            ) from e

    async def export_graph(
        self,
        graph_id: str,
        output_path: str,
        format: str = "json",
    ) -> None:
        """导出图谱。

        Args:
            graph_id: 图谱 ID
            output_path: 输出文件路径
            format: 导出格式（json, csv, mermaid）

        Raises:
            SDKValidationError: 参数无效
            QueryError: 导出失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     await client.export_graph("medical", "output.json", "json")
        """
        await self._ensure_initialized()

        self.logger.info(f"导出图谱: {graph_id} -> {output_path} ({format})")

        try:
            await self._graph_service.export_graph(graph_id, output_path, format)
            self.logger.info(f"图谱导出成功: {output_path}")

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"导出图谱失败 | 错误: {e}")
            raise QueryError(
                f"导出图谱失败: {e}",
                details={"output_path": output_path, "format": format},
            ) from e

    async def merge_graph_nodes(
        self,
        graph_id: str,
        source_entities: List[str],
        target_entity: str,
        threshold: float = 0.7,
        merge_strategy: Optional[Dict[str, str]] = None,
    ) -> int:
        """合并知识图谱中的相似节点。

        基于语义相似度自动识别和合并相似实体节点。此功能对于
        清理重复实体、整合同义词、规范实体名称非常有用。

        Args:
            graph_id: 图谱 ID
            source_entities: 源实体列表（要合并的实体）
            target_entity: 目标实体（合并后的实体名称）
            threshold: 相似度阈值（0-1），默认 0.7。用于验证和识别相似实体
            merge_strategy: 合并策略字典
                - description: concatenate | keep_first | keep_latest
                  - concatenate: 拼接所有描述（默认）
                  - keep_first: 保留第一个实体的描述
                  - keep_latest: 保留最后一个实体的描述
                - entity_type: keep_first | majority
                  - keep_first: 保留第一个实体的类型（默认）
                  - majority: 使用出现最多的类型
                - source_id: join_unique | join_all
                  - join_unique: 合并去重的源 ID（默认）
                  - join_all: 合并所有源 ID（包括重复）

        Returns:
            int: 合并的节点数量

        Raises:
            SDKValidationError: 参数无效（阈值超出范围、源实体为空等）
            NotFoundError: 图谱或实体不存在
            QueryError: 合并操作失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> # 基本合并：合并糖尿病的同义词
            >>> async with MedGraphClient() as client:
            ...     count = await client.merge_graph_nodes(
            ...         "medical",
            ...         ["糖尿病", "糖尿病 mellitus", "DM"],
            ...         "糖尿病"
            ...     )
            ...     print(f"合并了 {count} 个节点")
            >>>
            >>> # 自定义合并策略：合并高血压变体
            >>> async with MedGraphClient() as client:
            ...     count = await client.merge_graph_nodes(
            ...         "medical",
            ...         ["高血压", "Hypertension", "BP"],
            ...         "高血压病",
            ...         threshold=0.8,
            ...         merge_strategy={
            ...             "description": "concatenate",
            ...             "entity_type": "keep_first",
            ...             "source_id": "join_unique"
            ...         }
            ...     )
            ...     print(f"合并了 {count} 个节点")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"合并图谱节点 | 图谱: {graph_id} | "
            f"源实体: {len(source_entities)} 个 | 目标: {target_entity} | "
            f"阈值: {threshold}"
        )

        try:
            # 调用服务层合并方法
            merged_count = await self._graph_service.merge_graph_nodes(
                graph_id=graph_id,
                source_entities=source_entities,
                target_entity=target_entity,
                threshold=threshold,
                merge_strategy=merge_strategy,
            )

            self.logger.info(
                f"节点合并成功 | 图谱: {graph_id} | "
                f"数量: {merged_count} | 目标: {target_entity}"
            )

            return merged_count

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"合并图谱节点失败 | 错误: {e}")
            raise QueryError(
                f"合并图谱节点失败: {e}",
                details={
                    "graph_id": graph_id,
                    "source_entities": source_entities,
                    "target_entity": target_entity,
                    "threshold": threshold,
                },
            ) from e

    async def find_similar_entities(
        self,
        graph_id: str,
        entity_name: str,
        threshold: float = 0.7,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """查找与指定实体相似的实体。

        基于语义相似度查找相似实体，用于辅助合并决策。此功能
        可以帮助识别图谱中的重复实体、同义词和别名。

        Args:
            graph_id: 图谱 ID
            entity_name: 参考实体名称
            threshold: 相似度阈值（0-1），默认 0.7
            top_k: 返回的最大相似实体数量，默认 10

        Returns:
            List[Dict[str, Any]]: 相似实体列表，每个字典包含：
                - entity_name: 实体名称
                - entity_type: 实体类型
                - similarity: 相似度分数（0-1）
                - description: 实体描述

        Raises:
            SDKValidationError: 参数无效
            NotFoundError: 图谱不存在
            QueryError: 查找失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with MedGraphClient() as client:
            ...     similar = await client.find_similar_entities(
            ...         "medical",
            ...         "糖尿病",
            ...         threshold=0.7,
            ...         top_k=5
            ...     )
            ...     for entity in similar:
            ...         print(f"{entity['entity_name']}: {entity['similarity']:.2f}")
        """
        await self._ensure_initialized()

        self.logger.debug(
            f"查找相似实体 | 图谱: {graph_id} | "
            f"实体: {entity_name} | 阈值: {threshold}"
        )

        try:
            similar_entities = await self._graph_service.find_similar_entities(
                graph_id=graph_id,
                entity_name=entity_name,
                threshold=threshold,
                top_k=top_k,
            )

            self.logger.info(
                f"找到 {len(similar_entities)} 个相似实体 | "
                f"参考: {entity_name}"
            )

            return similar_entities

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"查找相似实体失败 | 错误: {e}")
            raise QueryError(
                f"查找相似实体失败: {e}",
                details={
                    "graph_id": graph_id,
                    "entity_name": entity_name,
                    "threshold": threshold,
                },
            ) from e

    async def auto_merge_similar_entities(
        self,
        graph_id: str,
        entity_type: Optional[str] = None,
        threshold: float = 0.85,
        merge_strategy: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """自动合并相似实体。

        基于语义相似度自动识别和合并相似的实体节点。此功能
        适用于批量清理重复实体，建议先使用试运行模式预览。

        Args:
            graph_id: 图谱 ID
            entity_type: 实体类型过滤（可选），如 "DISEASE", "MEDICINE"
            threshold: 相似度阈值（0-1），默认 0.85。较高的阈值减少误合并
            merge_strategy: 合并策略（参见 merge_graph_nodes 方法）
            dry_run: 是否为试运行模式。如果为 True，只报告将要合并的实体对

        Returns:
            Dict[str, Any]: 合并结果摘要
                - merged_count: 实际合并的实体对数量
                - merged_entities: 合并的实体对列表
                - skipped_count: 跳过的实体数量
                - total_processed: 处理的实体总数
                - dry_run: 是否为试运行

        Raises:
            SDKValidationError: 参数无效
            NotFoundError: 图谱不存在
            QueryError: 自动合并失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> # 先试运行，查看将要合并的实体
            >>> async with MedGraphClient() as client:
            ...     result = await client.auto_merge_similar_entities(
            ...         "medical",
            ...         entity_type="DISEASE",
            ...         threshold=0.9,
            ...         dry_run=True
            ...     )
            ...     print(f"将合并 {result['merged_count']} 对实体")
            ...     for merge in result['merged_entities']:
            ...         print(f"  {merge['target_entity']} <- {merge['source_entities']}")
            >>>
            >>> # 确认后执行实际合并
            >>> async with MedGraphClient() as client:
            ...     result = await client.auto_merge_similar_entities(
            ...         "medical",
            ...         entity_type="DISEASE",
            ...         threshold=0.9,
            ...         dry_run=False
            ...     )
            ...     print(f"成功合并 {result['merged_count']} 对实体")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"自动合并相似实体 | 图谱: {graph_id} | "
            f"类型: {entity_type or '全部'} | 阈值: {threshold} | "
            f"试运行: {dry_run}"
        )

        try:
            result = await self._graph_service.auto_merge_similar_entities(
                graph_id=graph_id,
                entity_type=entity_type,
                threshold=threshold,
                merge_strategy=merge_strategy,
                dry_run=dry_run,
            )

            self.logger.info(
                f"自动合并完成 | 合并: {result['merged_count']} | "
                f"跳过: {result['skipped_count']} | "
                f"总计: {result['total_processed']}"
            )

            return result

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"自动合并失败 | 错误: {e}")
            raise QueryError(
                f"自动合并失败: {e}",
                details={
                    "graph_id": graph_id,
                    "entity_type": entity_type,
                    "threshold": threshold,
                    "dry_run": dry_run,
                },
            ) from e

    # ========== 性能监控方法 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息。

        Returns:
            包含性能指标的字典：
            - metrics_enabled: 是否启用指标收集
            - total_queries: 总查询次数
            - total_documents: 总文档数
            - avg_latency_ms: 平均查询延迟
            - p50_latency_ms: 中位数延迟（P50）
            - p95_latency_ms: P95 延迟
            - p99_latency_ms: P99 延迟
            - queries_by_mode: 各模式查询次数
            - errors: 错误次数
            - error_rate: 错误率

        Example:
            >>> stats = client.get_stats()
            >>> print(f"查询次数: {stats['total_queries']}")
            >>> print(f"平均延迟: {stats['avg_latency_ms']}ms")
        """
        return self._performance_monitor.get_stats()

    def reset_stats(self) -> None:
        """重置性能统计。

        Example:
            >>> client.reset_stats()
            >>> print("性能统计已重置")
        """
        self._performance_monitor.reset_stats()

    def get_performance_summary(self) -> str:
        """获取性能摘要（用于日志输出）。

        Returns:
            格式化的性能摘要字符串

        Example:
            >>> summary = client.get_performance_summary()
            >>> print(summary)
        """
        return self._performance_monitor.get_performance_summary()

    # ========== 配置管理方法 ==========

    @classmethod
    def from_env(
        cls,
        workspace: str = "medical",
        log_level: str = "INFO",
        enable_metrics: bool = True,
    ) -> "MedGraphClient":
        """从环境变量创建客户端。

        Args:
            workspace: 工作空间名称
            log_level: 日志级别
            enable_metrics: 是否启用性能监控

        Returns:
            MedGraphClient: 客户端实例

        Example:
            >>> client = MedGraphClient.from_env()
            >>> async with client:
            ...     result = await client.query("测试")
        """
        config = get_settings()

        return cls(
            workspace=workspace,
            log_level=log_level,
            enable_metrics=enable_metrics,
            config=config,
        )

    @classmethod
    def from_config(
        cls,
        config_path: str,
        workspace: Optional[str] = None,
        log_level: str = "INFO",
        enable_metrics: bool = True,
    ) -> "MedGraphClient":
        """从配置文件创建客户端。

        Args:
            config_path: 配置文件路径（支持 .json, .yaml, .yml）
            workspace: 工作空间名称（可选，覆盖配置文件中的值）
            log_level: 日志级别
            enable_metrics: 是否启用性能监控

        Returns:
            MedGraphClient: 客户端实例

        Raises:
            SDKConfigError: 配置文件格式错误或不存在

        Example:
            >>> client = MedGraphClient.from_config("config.json")
            >>> async with client:
            ...     result = await client.query("测试")
        """
        path = Path(config_path)

        # 检测文件格式
        if path.suffix in ['.yaml', '.yml']:
            config_data = _load_yaml_config(config_path)
        elif path.suffix == '.json':
            config_data = _load_json_config(config_path)
        else:
            raise SDKConfigError(
                f"不支持的配置文件格式: {path.suffix}",
                config_file=config_path,
            )

        # 覆盖工作空间
        if workspace is not None:
            config_data["rag_workspace"] = workspace

        # 创建客户端
        return cls(
            workspace=config_data.get("rag_workspace", "medical"),
            log_level=log_level,
            enable_metrics=enable_metrics,
            **config_data
        )

    # ========== 便捷方法 ==========

    async def ingest_and_query(
        self,
        text: str,
        query_text: str,
        mode: str = "hybrid",
    ) -> QueryResult:
        """便捷方法：摄入文本后立即查询。

        适合快速测试和单文档场景。

        Args:
            text: 要摄入的文本
            query_text: 查询问题
            mode: 查询模式

        Returns:
            QueryResult: 查询结果

        Example:
            >>> async with MedGraphClient() as client:
            ...     text = "糖尿病是一种慢性代谢性疾病..."
            ...     result = await client.ingest_and_query(
            ...         text,
            ...         "什么是糖尿病?"
            ...     )
            ...     print(result.answer)
        """
        self.logger.info("执行摄入和查询操作")

        # 摄入文本
        await self.ingest_text(text)

        # 稍作等待，确保索引完成
        await asyncio.sleep(0.5)

        # 执行查询
        result = await self.query(query_text, mode=mode)

        return result


# ========== 便捷函数 ==========


async def create_client(
    workspace: str = "default",
    **kwargs
) -> MedGraphClient:
    """创建并初始化客户端的便捷函数。

    Args:
        workspace: 工作空间名称
        **kwargs: 额外的配置参数

    Returns:
        MedGraphClient: 已初始化的客户端实例

    Example:
        >>> client = await create_client(workspace="medical")
        >>> result = await client.query("问题")
        >>> await client.close()
    """
    client = MedGraphClient(workspace=workspace, **kwargs)
    await client.initialize()
    return client


# ========== 导出的公共接口 ==========

__all__ = [
    "MedGraphClient",
    "DocumentInfo",
    "create_client",
]
