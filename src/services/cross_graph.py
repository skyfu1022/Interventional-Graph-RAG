"""
跨图谱查询服务模块。

该模块提供跨多个知识图谱的联合查询功能，包括：
- 并行查询多个图谱（patient/literature/dictionary）
- 支持不同检索模式（local/global/hybrid）
- 结构化的检索结果聚合
- 来源图谱信息追踪

基于 LightRAG 和 RAGAnythingAdapter 实现，支持：
- 异步并行查询
- 结果去重和排序
- 多模式检索组合
- 性能监控

使用示例：
    >>> from src.services.cross_graph import cross_graph_query, CrossGraphResult
    >>> from src.core.config import Settings
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     result = await cross_graph_query(
    >>>         query="糖尿病的治疗方法",
    >>>         mode="hybrid",
    >>>         graphs=["patient", "literature", "dictionary"]
    >>>     )
    >>>     print(f"答案: {result.answer}")
    >>>     print(f"来源: {result.sources}")
    >>>
    >>> asyncio.run(main())
"""

import time
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from collections import OrderedDict
import asyncio

from src.core.adapters import RAGAnythingAdapter, QueryResult as AdapterQueryResult
from src.core.config import Settings
from src.core.exceptions import QueryError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.cross_graph")


# ========== 枚举和常量 ==========


GraphType = Literal["patient", "literature", "dictionary"]
QueryModeType = Literal["naive", "local", "global", "hybrid", "mix", "bypass"]

# 支持的图谱类型
SUPPORTED_GRAPHS: List[GraphType] = ["patient", "literature", "dictionary"]

# 默认查询模式
DEFAULT_QUERY_MODE: QueryModeType = "hybrid"


# ========== 数据类 ==========


@dataclass
class GraphSource:
    """图谱来源信息。

    表示检索结果来自哪个图谱。

    Attributes:
        graph_type: 图谱类型（patient/literature/dictionary）
        graph_id: 图谱 ID
        result_count: 该图谱返回的结果数量
        relevance: 相关性评分（0-1）
        latency_ms: 查询延迟（毫秒）
    """

    graph_type: GraphType
    graph_id: str
    result_count: int = 0
    relevance: float = 0.0
    latency_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含来源信息的字典
        """
        return {
            "graph_type": self.graph_type,
            "graph_id": self.graph_id,
            "result_count": self.result_count,
            "relevance": self.relevance,
            "latency_ms": self.latency_ms,
        }


@dataclass
class CrossGraphResult:
    """跨图谱查询结果。

    存储跨图谱查询的完整结果，包括答案、来源、性能指标等。

    Attributes:
        query: 原始查询文本
        answer: 聚合后的答案
        mode: 使用的查询模式
        sources: 来源图谱信息列表
        context: 聚合后的上下文列表
        retrieval_count: 总检索次数
        latency_ms: 总查询延迟（毫秒）
        graph_results: 各图谱的原始结果
        metadata: 额外的元数据
    """

    query: str
    answer: str
    mode: QueryModeType
    sources: List[GraphSource] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    retrieval_count: int = 0
    latency_ms: int = 0
    graph_results: Dict[GraphType, AdapterQueryResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含查询结果的字典
        """
        return {
            "query": self.query,
            "answer": self.answer,
            "mode": self.mode,
            "sources": [s.to_dict() for s in self.sources],
            "context": self.context,
            "retrieval_count": self.retrieval_count,
            "latency_ms": self.latency_ms,
            "graph_results": {k: v.to_dict() for k, v in self.graph_results.items()},
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """转换为 JSON 格式字符串。

        Returns:
            JSON 字符串
        """
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def __str__(self) -> str:
        """返回结果的字符串表示。"""
        return (
            f"CrossGraphResult(query='{self.query[:50]}...', "
            f"mode={self.mode}, "
            f"graphs={len(self.sources)}, "
            f"latency={self.latency_ms}ms)"
        )


# ========== 跨图谱查询函数 ==========


async def cross_graph_query(
    query: str,
    mode: QueryModeType = DEFAULT_QUERY_MODE,
    graphs: Optional[List[GraphType]] = None,
    adapter: Optional[RAGAnythingAdapter] = None,
    top_k: int = 5,
    max_tokens: int = 3000,
    deduplicate: bool = True,
    **kwargs,
) -> CrossGraphResult:
    """跨图谱查询函数。

    并行查询多个知识图谱，聚合结果并返回结构化的答案。

    Args:
        query: 查询文本
        mode: 查询模式（naive, local, global, hybrid, mix, bypass）
        graphs: 要查询的图谱列表（patient/literature/dictionary）
            如果为 None，则查询所有图谱
        adapter: RAGAnything 适配器实例（可选，如果不提供则自动创建）
        top_k: 每个图谱检索的 top-k 数量
        max_tokens: 最大 token 数量限制
        deduplicate: 是否对结果去重
        **kwargs: 额外的查询参数
            - patient_graph_id: 患者图谱 ID
            - literature_graph_id: 文献图谱 ID
            - dictionary_graph_id: 字典图谱 ID
            - timeout: 单个查询的超时时间（秒）

    Returns:
        CrossGraphResult: 跨图谱查询结果

    Raises:
        ValidationError: 参数验证失败
        QueryError: 查询执行失败

    Example:
        >>> result = await cross_graph_query(
        ...     query="糖尿病的治疗方法",
        ...     mode="hybrid",
        ...     graphs=["patient", "literature", "dictionary"]
        ... )
        >>> print(f"答案: {result.answer}")
        >>> print(f"患者图谱贡献: {result.graph_results.get('patient')}")
    """
    # ========== 参数验证 ==========

    if not query or not query.strip():
        raise ValidationError(
            "查询文本不能为空",
            field="query",
            value=query,
        )

    # 验证查询模式
    valid_modes = ["naive", "local", "global", "hybrid", "mix", "bypass"]
    if mode not in valid_modes:
        raise ValidationError(
            f"无效的查询模式: {mode}",
            field="mode",
            value=mode,
            constraint=f"mode in {valid_modes}",
        )

    # 确定要查询的图谱
    if graphs is None:
        graphs_to_query = SUPPORTED_GRAPHS
    else:
        # 验证图谱类型
        for graph_type in graphs:
            if graph_type not in SUPPORTED_GRAPHS:
                raise ValidationError(
                    f"无效的图谱类型: {graph_type}",
                    field="graphs",
                    value=graph_type,
                    constraint=f"graph_type in {SUPPORTED_GRAPHS}",
                )
        graphs_to_query = list(set(graphs))  # 去重

    if not graphs_to_query:
        raise ValidationError(
            "至少需要指定一个图谱",
            field="graphs",
            value=graphs,
        )

    logger.info(
        f"跨图谱查询 | 查询: {query[:50]}... | 模式: {mode} | 图谱: {graphs_to_query}"
    )

    # ========== 创建适配器 ==========

    if adapter is None:
        try:
            config = Settings()
            adapter = RAGAnythingAdapter(config)
            await adapter.initialize()
        except Exception as e:
            raise QueryError(
                f"无法创建适配器: {e}",
                query_text=query,
                details={"error": str(e)},
            ) from e

    # ========== 定义图谱 ID ==========

    graph_ids = {
        "patient": kwargs.get("patient_graph_id", "patient_graph"),
        "literature": kwargs.get("literature_graph_id", "literature_graph"),
        "dictionary": kwargs.get("dictionary_graph_id", "dictionary_graph"),
    }

    # ========== 执行并行查询 ==========

    start_time = time.time()
    query_tasks = []
    timeout = kwargs.get("timeout", 30)

    # 创建查询任务
    for graph_type in graphs_to_query:
        task = _query_single_graph(
            adapter=adapter,
            graph_type=graph_type,
            graph_id=graph_ids[graph_type],
            query=query,
            mode=mode,
            top_k=top_k,
            timeout=timeout,
        )
        query_tasks.append(task)

    # 并行执行查询
    try:
        results = await asyncio.gather(*query_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"并行查询失败: {e}", exc_info=True)
        raise QueryError(
            f"并行查询失败: {e}",
            query_text=query,
            details={"graphs": graphs_to_query},
        ) from e

    # ========== 处理查询结果 ==========

    graph_results: Dict[GraphType, AdapterQueryResult] = {}
    sources: List[GraphSource] = []
    total_retrieval_count = 0
    all_contexts: List[str] = []

    for i, result in enumerate(results):
        graph_type = graphs_to_query[i]

        # 处理异常
        if isinstance(result, Exception):
            logger.warning(f"图谱 {graph_type} 查询失败: {result}")
            sources.append(
                GraphSource(
                    graph_type=graph_type,
                    graph_id=graph_ids[graph_type],
                    result_count=0,
                    relevance=0.0,
                    latency_ms=0,
                )
            )
            continue

        # 处理正常结果
        if result is not None:
            graph_results[graph_type] = result
            total_retrieval_count += result.retrieval_count

            # 添加来源信息
            sources.append(
                GraphSource(
                    graph_type=graph_type,
                    graph_id=graph_ids[graph_type],
                    result_count=result.retrieval_count,
                    relevance=_calculate_relevance(result),
                    latency_ms=result.latency_ms,
                )
            )

            # 收集上下文
            if result.context:
                all_contexts.extend(result.context)

    # ========== 聚合答案 ==========

    # 去重上下文
    if deduplicate:
        all_contexts = _deduplicate_contexts(all_contexts)

    # 限制 token 数量
    if max_tokens > 0:
        all_contexts = _truncate_by_tokens(all_contexts, max_tokens)

    # 聚合答案
    answer = _aggregate_answers(graph_results, mode)

    # 计算总延迟
    total_latency_ms = int((time.time() - start_time) * 1000)

    # ========== 构建结果 ==========

    cross_result = CrossGraphResult(
        query=query,
        answer=answer,
        mode=mode,
        sources=sources,
        context=all_contexts,
        retrieval_count=total_retrieval_count,
        latency_ms=total_latency_ms,
        graph_results=graph_results,
        metadata={
            "graphs_queried": graphs_to_query,
            "graphs_succeeded": list(graph_results.keys()),
            "deduplicated": deduplicate,
            "max_tokens": max_tokens,
            "top_k": top_k,
        },
    )

    logger.info(
        f"跨图谱查询完成 | 图谱: {len(graph_results)}/{len(graphs_to_query)} | "
        f"检索: {total_retrieval_count} | 耗时: {total_latency_ms}ms"
    )

    return cross_result


# ========== 辅助函数 ==========


async def _query_single_graph(
    adapter: RAGAnythingAdapter,
    graph_type: GraphType,
    graph_id: str,
    query: str,
    mode: QueryModeType,
    top_k: int,
    timeout: float,
) -> Optional[AdapterQueryResult]:
    """查询单个图谱。

    Args:
        adapter: 适配器实例
        graph_type: 图谱类型
        graph_id: 图谱 ID
        query: 查询文本
        mode: 查询模式
        top_k: top-k 数量
        timeout: 超时时间

    Returns:
        AdapterQueryResult: 查询结果，如果失败则返回 None
    """
    logger.debug(
        f"查询图谱 | 类型: {graph_type} | ID: {graph_id} | 查询: {query[:50]}..."
    )

    try:
        # 使用超时执行查询
        result = await asyncio.wait_for(
            adapter.query(
                question=query,
                mode=mode,
                top_k=top_k,
            ),
            timeout=timeout,
        )

        logger.debug(
            f"图谱查询成功 | 类型: {graph_type} | 答案长度: {len(result.answer)}"
        )

        return result

    except asyncio.TimeoutError:
        logger.warning(f"图谱查询超时 | 类型: {graph_type} | 超时: {timeout}秒")
        return None
    except Exception as e:
        logger.warning(f"图谱查询失败 | 类型: {graph_type} | 错误: {e}")
        return None


def _calculate_relevance(result: AdapterQueryResult) -> float:
    """计算结果的相关性评分。

    基于答案长度、检索数量等指标估算相关性。

    Args:
        result: 查询结果

    Returns:
        float: 相关性评分（0-1）
    """
    # 简单启发式：基于答案长度和检索数量
    answer_score = min(1.0, len(result.answer) / 500)
    retrieval_score = min(1.0, result.retrieval_count / 10)

    return (answer_score + retrieval_score) / 2


def _deduplicate_contexts(contexts: List[str]) -> List[str]:
    """去除重复的上下文。

    Args:
        contexts: 上下文列表

    Returns:
        去重后的上下文列表
    """
    seen = OrderedDict()
    unique_contexts = []

    for context in contexts:
        # 使用前 100 个字符作为去重键
        key = context[:100] if context else ""
        if key and key not in seen:
            seen[key] = True
            unique_contexts.append(context)

    return unique_contexts


def _truncate_by_tokens(
    contexts: List[str],
    max_tokens: int,
) -> List[str]:
    """按 token 数量截断上下文列表。

    Args:
        contexts: 上下文列表
        max_tokens: 最大 token 数量

    Returns:
        截断后的上下文列表
    """
    if max_tokens <= 0:
        return []

    result = []
    current_tokens = 0

    # 简单估算：2 字符 = 1 token
    for context in contexts:
        context_tokens = len(context) // 2

        if current_tokens + context_tokens <= max_tokens:
            result.append(context)
            current_tokens += context_tokens
        else:
            # 尝试截断当前上下文
            remaining_tokens = max_tokens - current_tokens
            if remaining_tokens > 10:  # 至少保留 10 个 token
                truncated_chars = remaining_tokens * 2
                result.append(context[:truncated_chars])
            break

    return result


def _aggregate_answers(
    graph_results: Dict[GraphType, AdapterQueryResult],
    mode: QueryModeType,
) -> str:
    """聚合多个图谱的答案。

    Args:
        graph_results: 各图谱的查询结果
        mode: 查询模式

    Returns:
        聚合后的答案
    """
    if not graph_results:
        return "未找到相关答案。"

    # 如果只有一个图谱有结果，直接返回
    if len(graph_results) == 1:
        return list(graph_results.values())[0].answer

    # 多个图谱结果聚合
    aggregated_parts = []

    # 按图谱类型排序（优先级：dictionary > literature > patient）
    priority_order = ["dictionary", "literature", "patient"]

    for graph_type in priority_order:
        if graph_type in graph_results:
            result = graph_results[graph_type]
            graph_name = {
                "patient": "患者数据",
                "literature": "文献资料",
                "dictionary": "医学词典",
            }.get(graph_type, graph_type)

            # 添加图谱来源标记
            if result.answer:
                aggregated_parts.append(f"【{graph_name}】\n{result.answer}")

    # 如果 hybrid 模式，尝试融合答案
    if mode == "hybrid" and len(aggregated_parts) > 1:
        # 简单融合：将各部分用分隔符连接
        return "\n\n---\n\n".join(aggregated_parts)
    else:
        # 其他模式：直接连接
        return "\n\n".join(aggregated_parts)


async def get_graph_statistics(
    adapter: Optional[RAGAnythingAdapter] = None,
) -> Dict[str, Any]:
    """获取所有图谱的统计信息。

    Args:
        adapter: 适配器实例（可选）

    Returns:
        包含各图谱统计信息的字典

    Raises:
        QueryError: 获取统计信息失败
    """
    if adapter is None:
        try:
            config = Settings()
            adapter = RAGAnythingAdapter(config)
            await adapter.initialize()
        except Exception as e:
            raise QueryError(
                f"无法创建适配器: {e}",
                details={"error": str(e)},
            ) from e

    logger.info("获取图谱统计信息")

    statistics = {}

    # 获取每个图谱的统计信息
    for graph_type in SUPPORTED_GRAPHS:
        try:
            stats = await adapter.get_stats()
            statistics[graph_type] = {
                "entity_count": stats.entity_count,
                "relationship_count": stats.relationship_count,
                "chunk_count": stats.chunk_count,
                "document_count": stats.document_count,
                "storage_info": stats.storage_info,
            }
        except Exception as e:
            logger.warning(f"获取 {graph_type} 图谱统计失败: {e}")
            statistics[graph_type] = {
                "error": str(e),
            }

    return statistics


# ========== 导出的公共接口 ==========

__all__ = [
    "cross_graph_query",
    "get_graph_statistics",
    "CrossGraphResult",
    "GraphSource",
    "GraphType",
    "QueryModeType",
    "SUPPORTED_GRAPHS",
    "DEFAULT_QUERY_MODE",
]
