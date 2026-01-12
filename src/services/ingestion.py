"""
文档摄入服务模块。

该模块封装 RAGAnythingAdapter 的文档摄入功能，提供：
- 单文档摄入
- 批量摄入
- 纯文本摄入
- 进度跟踪
- 错误处理
- 部分失败容错

基于 LangGraph 最佳实践实现异步批处理和并发控制。

使用示例：
    >>> from src.core.config import Settings
    >>> from src.core.adapters import RAGAnythingAdapter
    >>> from src.services.ingestion import IngestionService
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     config = Settings()
    >>>     adapter = RAGAnythingAdapter(config)
    >>>     await adapter.initialize()
    >>>     service = IngestionService(adapter)
    >>>
    >>>     # 单文档摄入
    >>>     result = await service.ingest_document("doc.txt", doc_id="doc-001")
    >>>
    >>>     # 批量摄入
    >>>     batch_result = await service.ingest_batch(
    >>>         ["doc1.txt", "doc2.txt"],
    >>>         progress_callback=lambda cur, total: print(f"进度: {cur}/{total}")
    >>>     )
    >>>
    >>> asyncio.run(main())
"""

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any, Set
from dataclasses import dataclass, field

from src.core.adapters import RAGAnythingAdapter, IngestResult
from src.core.exceptions import DocumentError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.ingestion")


# ========== 数据类 ==========


@dataclass
class BatchIngestResult:
    """批量摄入结果。

    Attributes:
        total: 总文档数
        succeeded: 成功摄入的文档数
        failed: 失败的文档数
        errors: 错误列表，每个错误包含文件路径、文档 ID 和错误信息
        duration_ms: 批量摄入总耗时（毫秒）
        results: 所有文档的摄入结果列表
    """

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    results: List[IngestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "success_rate": self.succeeded / self.total if self.total > 0 else 0.0,
        }

    def __str__(self) -> str:
        """返回字符串表示。"""
        return (
            f"BatchIngestResult(总计={self.total}, "
            f"成功={self.succeeded}, "
            f"失败={self.failed}, "
            f"成功率={self.succeeded / self.total * 100:.1f}%, "
            f"耗时={self.duration_ms}ms)"
        )


@dataclass
class DocumentStatus:
    """文档摄入状态。

    Attributes:
        doc_id: 文档 ID
        status: 状态（pending, processing, completed, failed）
        progress: 进度百分比（0-100）
        error: 错误信息（如果失败）
        created_at: 创建时间戳
        updated_at: 更新时间戳
    """

    doc_id: str
    status: str = "pending"
    progress: int = 0
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "doc_id": self.doc_id,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ========== 进度回调类型 ==========

ProgressCallback = Callable[[int, int, str], None]
"""进度回调函数类型。

Args:
    current: 当前完成的数量
    total: 总数量
    doc_id: 当前正在处理的文档 ID
"""


# ========== 摄入服务类 ==========


class IngestionService:
    """文档摄入服务。

    封装 RAGAnythingAdapter 的文档摄入功能，提供：
    - 单文档和批量文档摄入
    - 纯文本摄入
    - 并发控制和进度跟踪
    - 完善的错误处理和部分失败容错
    - 文档状态查询

    Attributes:
        _adapter: RAGAnythingAdapter 实例
        _logger: 日志记录器
        _status_cache: 文档状态缓存（doc_id -> DocumentStatus）
    """

    def __init__(self, adapter: RAGAnythingAdapter):
        """初始化摄入服务。

        Args:
            adapter: RAGAnythingAdapter 实例

        Raises:
            ValidationError: 如果 adapter 不是 RAGAnythingAdapter 实例
        """
        if not isinstance(adapter, RAGAnythingAdapter):
            raise ValidationError(
                f"adapter 必须是 RAGAnythingAdapter 实例，当前类型: {type(adapter)}",
                field="adapter",
                value=type(adapter).__name__,
            )

        self._adapter = adapter
        self._logger = logger
        self._status_cache: Dict[str, DocumentStatus] = {}

        logger.info("文档摄入服务初始化完成")

    async def ingest_document(
        self,
        file_path: str,
        doc_id: Optional[str] = None,
    ) -> IngestResult:
        """摄入单个文档。

        Args:
            file_path: 文档文件路径
            doc_id: 文档 ID（可选，如果不提供则使用文件名）

        Returns:
            IngestResult: 摄入结果

        Raises:
            DocumentError: 文档处理失败
            ValidationError: 文件路径无效

        Example:
            >>> result = await service.ingest_document("doc.txt", doc_id="doc-001")
            >>> print(f"摄入状态: {result.status}")
        """
        # 验证文件路径
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(
                f"文件不存在: {file_path}",
                field="file_path",
                value=file_path,
            )

        if not path.is_file():
            raise ValidationError(
                f"路径不是文件: {file_path}",
                field="file_path",
                value=file_path,
            )

        # 使用文件名作为默认 doc_id
        if doc_id is None:
            doc_id = path.stem

        self._logger.info(f"开始摄入文档 | 路径: {file_path} | ID: {doc_id}")

        # 更新状态缓存
        self._status_cache[doc_id] = DocumentStatus(
            doc_id=doc_id, status="processing", progress=0
        )

        try:
            # 调用适配器摄入
            result = await self._adapter.ingest_document(file_path, doc_id)

            # 更新状态为完成
            self._status_cache[doc_id].status = "completed"
            self._status_cache[doc_id].progress = 100
            self._status_cache[doc_id].updated_at = time.time()

            self._logger.info(f"文档摄入成功 | ID: {doc_id} | 状态: {result.status}")

            return result

        except (DocumentError, ValidationError):
            # 更新状态为失败
            self._status_cache[doc_id].status = "failed"
            self._status_cache[doc_id].error = str(
                self._status_cache.get(doc_id, DocumentStatus(doc_id)).error
            )
            self._status_cache[doc_id].updated_at = time.time()
            raise

        except Exception as e:
            # 更新状态为失败
            self._status_cache[doc_id].status = "failed"
            self._status_cache[doc_id].error = str(e)
            self._status_cache[doc_id].updated_at = time.time()

            self._logger.error(f"文档摄入失败 | ID: {doc_id} | 错误: {e}")

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
        """摄入纯文本。

        Args:
            text: 文本内容
            doc_id: 文档 ID（可选）

        Returns:
            IngestResult: 摄入结果

        Raises:
            DocumentError: 文本摄入失败
            ValidationError: 文本为空

        Example:
            >>> result = await service.ingest_text("糖尿病是一种代谢疾病...", doc_id="text-001")
        """
        if not text or not text.strip():
            raise ValidationError(
                "文本内容不能为空",
                field="text",
                value=text,
            )

        # 生成默认 doc_id
        if doc_id is None:
            import hashlib

            doc_id = f"text_{hashlib.md5(text.encode()).hexdigest()[:8]}"

        self._logger.debug(f"开始摄入文本 | ID: {doc_id} | 长度: {len(text)}")

        # 更新状态缓存
        self._status_cache[doc_id] = DocumentStatus(
            doc_id=doc_id, status="processing", progress=0
        )

        try:
            # 调用适配器摄入
            result = await self._adapter.ingest_text(text, doc_id)

            # 更新状态为完成
            self._status_cache[doc_id].status = "completed"
            self._status_cache[doc_id].progress = 100
            self._status_cache[doc_id].updated_at = time.time()

            self._logger.debug(f"文本摄入成功 | ID: {doc_id}")

            return result

        except (DocumentError, ValidationError):
            # 更新状态为失败
            self._status_cache[doc_id].status = "failed"
            self._status_cache[doc_id].updated_at = time.time()
            raise

        except Exception as e:
            # 更新状态为失败
            self._status_cache[doc_id].status = "failed"
            self._status_cache[doc_id].error = str(e)
            self._status_cache[doc_id].updated_at = time.time()

            self._logger.error(f"文本摄入失败 | ID: {doc_id} | 错误: {e}")

            raise DocumentError(
                f"文本摄入失败: {e}",
                doc_id=doc_id,
            ) from e

    async def ingest_batch(
        self,
        file_paths: List[str],
        doc_ids: Optional[List[str]] = None,
        max_concurrency: int = 5,
        progress_callback: Optional[ProgressCallback] = None,
        continue_on_error: bool = True,
    ) -> BatchIngestResult:
        """批量摄入文档。

        使用 asyncio.Semaphore 控制并发数量，支持：
        - 并发摄入多个文档
        - 进度回调通知
        - 部分失败容错
        - 详细的错误报告

        Args:
            file_paths: 文档文件路径列表
            doc_ids: 文档 ID 列表（可选，默认使用文件名）
            max_concurrency: 最大并发数（默认 5）
            progress_callback: 进度回调函数 (current, total, doc_id)
            continue_on_error: 遇到错误是否继续处理（默认 True）

        Returns:
            BatchIngestResult: 批量摄入结果

        Raises:
            ValidationError: 参数验证失败
            DocumentError: 所有文档都失败时抛出

        Example:
            >>> def on_progress(current, total, doc_id):
            ...     print(f"进度: {current}/{total} - 当前: {doc_id}")
            >>>
            >>> result = await service.ingest_batch(
            ...     ["doc1.txt", "doc2.txt", "doc3.txt"],
            ...     progress_callback=on_progress,
            ...     max_concurrency=3
            ... )
            >>> print(f"完成: {result.succeeded}/{result.total}")
        """
        # 验证输入
        if not file_paths:
            raise ValidationError(
                "文档路径列表不能为空",
                field="file_paths",
            )

        if max_concurrency < 1:
            raise ValidationError(
                f"最大并发数必须 >= 1，当前值: {max_concurrency}",
                field="max_concurrency",
                value=max_concurrency,
            )

        # 生成 doc_id（如果未提供）
        if doc_ids is None:
            doc_ids = [Path(p).stem for p in file_paths]

        # 验证 doc_ids 长度
        if len(doc_ids) != len(file_paths):
            raise ValidationError(
                f"文档 ID 数量与文件数量不匹配 | "
                f"文件数: {len(file_paths)} | ID数: {len(doc_ids)}",
                field="doc_ids",
                constraint="len(doc_ids) == len(file_paths)",
            )

        start_time = time.time()
        total = len(file_paths)
        result = BatchIngestResult(total=total)

        self._logger.info(
            f"开始批量摄入 | 总数: {total} | 并发数: {max_concurrency} | "
            f"容错: {continue_on_error}"
        )

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrency)

        # 用于跟踪已完成任务的集合
        completed_indices: Set[int] = set()

        async def ingest_one(
            file_path: str,
            doc_id: str,
            index: int,
        ) -> Optional[IngestResult]:
            """摄入单个文档（内部函数）。"""
            async with semaphore:
                try:
                    self._logger.debug(
                        f"开始摄入 [{index + 1}/{total}] | "
                        f"文件: {file_path} | ID: {doc_id}"
                    )

                    # 调用单文档摄入
                    ingest_result = await self.ingest_document(file_path, doc_id)

                    # 记录成功
                    result.succeeded += 1
                    result.results.append(ingest_result)

                    # 调用进度回调
                    completed_indices.add(index)
                    current_count = len(completed_indices)
                    if progress_callback:
                        try:
                            progress_callback(current_count, total, doc_id)
                        except Exception as e:
                            self._logger.warning(f"进度回调失败: {e}")

                    return ingest_result

                except Exception as e:
                    # 记录失败
                    result.failed += 1
                    error_info = {
                        "index": index,
                        "file": file_path,
                        "doc_id": doc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    result.errors.append(error_info)

                    self._logger.error(
                        f"文档摄入失败 [{index + 1}/{total}] | "
                        f"文件: {file_path} | ID: {doc_id} | 错误: {e}"
                    )

                    # 如果不继续处理，则抛出异常
                    if not continue_on_error:
                        raise

                    # 仍然记录为已完成（用于进度跟踪）
                    completed_indices.add(index)
                    if progress_callback:
                        try:
                            progress_callback(len(completed_indices), total, doc_id)
                        except Exception as cb_e:
                            self._logger.warning(f"进度回调失败: {cb_e}")

                    return None

        # 并发执行所有任务
        try:
            tasks = [
                ingest_one(fp, did, i)
                for i, (fp, did) in enumerate(zip(file_paths, doc_ids))
            ]

            # 使用 asyncio.gather 并发执行
            await asyncio.gather(*tasks, return_exceptions=continue_on_error)

        except Exception as e:
            self._logger.error(f"批量摄入过程中断 | 错误: {e}")

            # 如果不是容错模式，抛出异常
            if not continue_on_error:
                raise DocumentError(
                    f"批量摄入失败: {e}",
                    details={
                        "total": total,
                        "succeeded": result.succeeded,
                        "failed": result.failed,
                    },
                ) from e

        # 计算总耗时
        result.duration_ms = int((time.time() - start_time) * 1000)

        self._logger.info(
            f"批量摄入完成 | {result.succeeded}/{result.total} 成功 | "
            f"{result.failed} 失败 | 耗时 {result.duration_ms}ms | "
            f"平均 {result.duration_ms / total:.0f}ms/文档"
        )

        return result

    async def get_ingestion_status(
        self,
        doc_id: str,
    ) -> DocumentStatus:
        """获取文档的摄入状态。

        Args:
            doc_id: 文档 ID

        Returns:
            DocumentStatus: 文档状态

        Raises:
            NotFoundError: 文档状态不存在

        Example:
            >>> status = await service.get_ingestion_status("doc-001")
            >>> print(f"状态: {status.status} | 进度: {status.progress}%")
        """
        if doc_id not in self._status_cache:
            from src.core.exceptions import NotFoundError

            raise NotFoundError(
                f"文档状态不存在: {doc_id}",
                resource_type="document_status",
                resource_id=doc_id,
            )

        return self._status_cache[doc_id]

    async def list_documents(
        self,
        status_filter: Optional[str] = None,
    ) -> List[DocumentStatus]:
        """列出所有文档的摄入状态。

        Args:
            status_filter: 状态过滤（可选，如 "completed", "failed"）

        Returns:
            List[DocumentStatus]: 文档状态列表

        Example:
            >>> # 列出所有文档
            >>> all_docs = await service.list_documents()
            >>>
            >>> # 仅列出成功的文档
            >>> completed_docs = await service.list_documents(status_filter="completed")
        """
        statuses = list(self._status_cache.values())

        if status_filter:
            statuses = [s for s in statuses if s.status == status_filter]

        return statuses

    async def clear_cache(
        self,
        older_than: Optional[float] = None,
    ) -> int:
        """清理状态缓存。

        Args:
            older_than: 清理早于此时间戳的状态（可选）
                       如果不提供，则清理所有缓存

        Returns:
            int: 清理的状态数量

        Example:
            >>> # 清理所有缓存
            >>> count = await service.clear_cache()
            >>>
            >>> # 清理 1 小时前的缓存
            >>> import time
            >>> count = await service.clear_cache(older_than=time.time() - 3600)
        """
        if older_than is None:
            count = len(self._status_cache)
            self._status_cache.clear()
            self._logger.info(f"清理所有状态缓存 | 数量: {count}")
            return count

        # 清理早于指定时间的缓存
        to_remove = [
            doc_id
            for doc_id, status in self._status_cache.items()
            if status.created_at < older_than
        ]

        for doc_id in to_remove:
            del self._status_cache[doc_id]

        self._logger.info(
            f"清理过期状态缓存 | 阈值: {older_than} | 数量: {len(to_remove)}"
        )

        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """获取摄入服务的统计信息。

        Returns:
            Dict[str, Any]: 统计信息，包括：
                - total_cached: 缓存的文档总数
                - by_status: 按状态分组的文档数量
                - success_rate: 成功率（百分比）

        Example:
            >>> stats = service.get_stats()
            >>> print(f"缓存文档: {stats['total_cached']}")
            >>> print(f"成功率: {stats['success_rate']:.1f}%")
        """
        if not self._status_cache:
            return {
                "total_cached": 0,
                "by_status": {},
                "success_rate": 0.0,
            }

        total = len(self._status_cache)
        by_status: Dict[str, int] = {}

        for status in self._status_cache.values():
            by_status[status.status] = by_status.get(status.status, 0) + 1

        completed = by_status.get("completed", 0)
        failed = by_status.get("failed", 0)
        finished = completed + failed
        success_rate = (completed / finished * 100) if finished > 0 else 0.0

        return {
            "total_cached": total,
            "by_status": by_status,
            "success_rate": success_rate,
        }


# ========== 导出的公共接口 ==========

__all__ = [
    "IngestionService",
    "BatchIngestResult",
    "DocumentStatus",
    "ProgressCallback",
]
