"""
SDK 监控和性能指标模块。

该模块为 SDK 客户端提供性能监控和指标收集功能。

核心功能：
- 查询性能监控（延迟、次数、分布）
- 文档摄入监控
- 错误率统计
- 百分位数计算（不依赖 numpy）
- 性能摘要生成

使用示例：
    >>> from src.sdk.monitoring import PerformanceMonitor
    >>>
    >>> # 创建监控器
    >>> monitor = PerformanceMonitor(enable_metrics=True)
    >>>
    >>> # 记录查询
    >>> monitor.record_query("hybrid", latency_ms=150)
    >>>
    >>> # 获取统计信息
    >>> stats = monitor.get_stats()
    >>> print(stats)
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


# ========== 辅助函数 ==========


def _calculate_percentile(values: List[float], percentile: float) -> float:
    """计算百分位数（不依赖 numpy）。

    使用线性插值方法计算百分位数，避免引入 numpy 依赖。

    Args:
        values: 数值列表
        percentile: 百分位数 (0-100)

    Returns:
        计算得到的百分位数值

    Example:
        >>> _calculate_percentile([1, 2, 3, 4, 5], 50)
        3.0
        >>> _calculate_percentile([1, 2, 3, 4, 5], 95)
        4.8
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)
    index = (percentile / 100) * (n - 1)

    # 线性插值
    lower = int(index)
    upper = min(lower + 1, n - 1)
    weight = index - lower

    if upper == lower:
        return sorted_values[lower]

    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


# ========== 性能监控类 ==========


@dataclass
class PerformanceMetrics:
    """性能指标数据类。

    存储各种性能相关的指标数据。

    Attributes:
        total_queries: 总查询次数
        total_documents: 总文档数
        total_latency_ms: 总延迟（毫秒）
        total_tokens: 总 Token 数
        queries_by_mode: 各查询模式的次数
        errors: 错误次数
    """

    total_queries: int = 0
    total_documents: int = 0
    total_latency_ms: int = 0
    total_tokens: int = 0
    queries_by_mode: Dict[str, int] = field(default_factory=dict)
    errors: int = 0


class PerformanceMonitor:
    """SDK 性能监控类。

    提供 SDK 客户端的性能监控和指标收集功能。

    核心功能：
    - 查询性能监控（延迟、次数、分布）
    - 文档摄入监控
    - 错误率统计
    - 百分位数计算
    - 性能摘要生成

    Attributes:
        _enable_metrics: 是否启用指标收集
        _metrics: 性能指标数据
        _query_times: 查询时间列表（用于计算百分位数）

    Example:
        >>> monitor = PerformanceMonitor(enable_metrics=True)
        >>>
        >>> # 记录查询
        >>> monitor.record_query("hybrid", latency_ms=150)
        >>>
        >>> # 获取统计信息
        >>> stats = monitor.get_stats()
        >>> print(f"平均延迟: {stats['avg_latency_ms']}ms")
    """

    def __init__(self, enable_metrics: bool = True):
        """初始化性能监控器。

        Args:
            enable_metrics: 是否启用指标收集
        """
        self._enable_metrics = enable_metrics
        self._metrics = PerformanceMetrics()
        self._query_times: List[float] = []

    def record_query(self, mode: str, latency_ms: int, success: bool = True) -> None:
        """记录查询指标。

        Args:
            mode: 查询模式
            latency_ms: 查询延迟（毫秒）
            success: 是否成功

        Example:
            >>> monitor.record_query("hybrid", latency_ms=150, success=True)
        """
        if not self._enable_metrics:
            return

        self._metrics.total_queries += 1
        self._metrics.total_latency_ms += latency_ms

        # 记录查询时间（用于计算百分位数）
        self._query_times.append(latency_ms)

        # 按模式统计
        if mode not in self._metrics.queries_by_mode:
            self._metrics.queries_by_mode[mode] = 0
        self._metrics.queries_by_mode[mode] += 1

        # 错误统计
        if not success:
            self._metrics.errors += 1

    def record_document(self, success: bool = True) -> None:
        """记录文档摄入指标。

        Args:
            success: 是否成功

        Example:
            >>> monitor.record_document(success=True)
        """
        if not self._enable_metrics:
            return

        self._metrics.total_documents += 1

        if not success:
            self._metrics.errors += 1

    def record_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """记录 Token 使用统计。

        Args:
            prompt_tokens: 提示词 Token 数
            completion_tokens: 完成 Token 数

        Example:
            >>> monitor.record_tokens(prompt_tokens=100, completion_tokens=200)
        """
        if not self._enable_metrics:
            return

        total_tokens = prompt_tokens + completion_tokens
        self._metrics.total_tokens += total_tokens

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息。

        Returns:
            包含以下字段的字典：
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
            >>> stats = monitor.get_stats()
            >>> print(f"总查询次数: {stats['total_queries']}")
            >>> print(f"平均延迟: {stats['avg_latency_ms']}ms")
        """
        if not self._enable_metrics:
            return {"metrics_enabled": False}

        stats = {
            "metrics_enabled": True,
            "total_queries": self._metrics.total_queries,
            "total_documents": self._metrics.total_documents,
            "queries_by_mode": self._metrics.queries_by_mode.copy(),
            "errors": self._metrics.errors,
        }

        # 计算延迟统计（不依赖 numpy）
        if self._query_times:
            stats["avg_latency_ms"] = int(
                sum(self._query_times) / len(self._query_times)
            )
            stats["p50_latency_ms"] = int(_calculate_percentile(self._query_times, 50))
            stats["p95_latency_ms"] = int(_calculate_percentile(self._query_times, 95))
            stats["p99_latency_ms"] = int(_calculate_percentile(self._query_times, 99))

        # 计算 Token 统计
        if self._metrics.total_tokens > 0:
            stats["total_tokens"] = self._metrics.total_tokens

        # 计算错误率
        total_ops = self._metrics.total_queries + self._metrics.total_documents
        if total_ops > 0:
            stats["error_rate"] = self._metrics.errors / total_ops
        else:
            stats["error_rate"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """重置性能统计信息。

        Example:
            >>> monitor.reset_stats()
            >>> print("性能统计已重置")
        """
        self._metrics = PerformanceMetrics()
        self._query_times = []

    def get_performance_summary(self) -> str:
        """获取性能摘要（用于日志输出）。

        Returns:
            格式化的性能摘要字符串

        Example:
            >>> summary = monitor.get_performance_summary()
            >>> print(summary)
        """
        stats = self.get_stats()

        if not stats.get("metrics_enabled"):
            return "性能指标收集已禁用"

        summary_parts = [
            "SDK 性能摘要:",
            f"- 总查询次数: {stats['total_queries']}",
            f"- 总文档数: {stats['total_documents']}",
        ]

        # 添加延迟统计（如果有）
        if "avg_latency_ms" in stats:
            summary_parts.extend(
                [
                    f"- 平均延迟: {stats['avg_latency_ms']}ms",
                    f"- P50 延迟: {stats.get('p50_latency_ms', 0)}ms",
                    f"- P95 延迟: {stats.get('p95_latency_ms', 0)}ms",
                    f"- P99 延迟: {stats.get('p99_latency_ms', 0)}ms",
                ]
            )

        # 添加 Token 统计（如果有）
        if "total_tokens" in stats:
            summary_parts.append(f"- 总 Token 数: {stats['total_tokens']}")

        # 添加错误统计
        summary_parts.extend(
            [
                f"- 错误次数: {stats['errors']}",
                f"- 错误率: {stats['error_rate']:.2%}",
                f"- 查询分布: {stats['queries_by_mode']}",
            ]
        )

        return "\n".join(summary_parts)


# ========== 性能上下文管理器 ==========


class QueryPerformanceTimer:
    """查询性能计时器上下文管理器。

    用于自动记录查询的性能指标。

    Example:
        >>> monitor = PerformanceMonitor()
        >>>
        >>> with QueryPerformanceTimer(monitor, "hybrid") as timer:
        >>>     result = execute_query()
        >>>     # 自动记录延迟
    """

    def __init__(
        self, monitor: PerformanceMonitor, mode: str, logger: Optional[Any] = None
    ):
        """初始化计时器。

        Args:
            monitor: 性能监控器
            mode: 查询模式
            logger: 日志记录器（可选）
        """
        self._monitor = monitor
        self._mode = mode
        self._logger = logger
        self._start_time = None
        self._success = True

    def __enter__(self) -> "QueryPerformanceTimer":
        """进入上下文，开始计时。"""
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，记录指标。"""
        if self._start_time is None:
            return

        latency_ms = int((time.time() - self._start_time) * 1000)
        success = exc_type is None

        # 记录指标
        self._monitor.record_query(self._mode, latency_ms, success)

        # 记录日志
        if self._logger:
            if success:
                self._logger.info(
                    f"查询完成 | mode={self._mode} | latency={latency_ms}ms"
                )
            else:
                self._logger.error(
                    f"查询失败 | mode={self._mode} | latency={latency_ms}ms"
                )

        return False


# ========== 导出的公共接口 ==========

__all__ = [
    "PerformanceMonitor",
    "PerformanceMetrics",
    "QueryPerformanceTimer",
    "_calculate_percentile",
]
