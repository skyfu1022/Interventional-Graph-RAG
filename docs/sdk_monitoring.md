# SDK 日志和监控功能使用指南

本文档介绍如何使用 Medical Graph RAG SDK 的日志记录和性能监控功能。

## 概述

SDK 提供了完整的日志记录和性能监控功能，帮助您：

- **记录查询性能**：跟踪查询延迟、次数、分布
- **监控文档摄入**：统计文档摄入数量和状态
- **错误追踪**：记录错误次数和错误率
- **Token 使用统计**：跟踪 LLM Token 消耗
- **性能分析**：计算 P50、P95、P99 延迟百分位数

## 核心组件

### 1. PerformanceMonitor

性能监控器是 SDK 的核心监控组件。

```python
from src.sdk import PerformanceMonitor

# 创建监控器
monitor = PerformanceMonitor(enable_metrics=True)

# 记录查询
monitor.record_query("hybrid", latency_ms=150, success=True)

# 获取统计信息
stats = monitor.get_stats()
print(stats)
```

### 2. QueryPerformanceTimer

计时器上下文管理器，用于自动记录查询性能。

```python
from src.sdk import QueryPerformanceTimer, PerformanceMonitor
from src.core.logging import get_logger

monitor = PerformanceMonitor(enable_metrics=True)
logger = get_logger("my_app")

# 自动计时和记录
with QueryPerformanceTimer(monitor, "hybrid", logger):
    result = await execute_query()
    # 自动记录延迟和日志
```

## 使用示例

### 基本用法

```python
from src.sdk import PerformanceMonitor

# 创建监控器
monitor = PerformanceMonitor(enable_metrics=True)

# 记录查询指标
monitor.record_query("hybrid", latency_ms=150, success=True)
monitor.record_query("local", latency_ms=100, success=True)

# 记录文档摄入
monitor.record_document(success=True)

# 记录 Token 使用
monitor.record_tokens(prompt_tokens=1000, completion_tokens=2000)

# 获取统计信息
stats = monitor.get_stats()
print(f"总查询次数: {stats['total_queries']}")
print(f"平均延迟: {stats['avg_latency_ms']}ms")
print(f"P95 延迟: {stats['p95_latency_ms']}ms")
print(f"错误率: {stats['error_rate']:.2%}")
```

### 使用计时器上下文管理器

```python
import asyncio
from src.sdk import PerformanceMonitor, QueryPerformanceTimer
from src.core.logging import get_logger

async def query_with_monitoring():
    monitor = PerformanceMonitor(enable_metrics=True)
    logger = get_logger("my_app")

    # 使用计时器
    with QueryPerformanceTimer(monitor, "hybrid", logger):
        await asyncio.sleep(0.1)  # 模拟查询
        # 自动记录延迟和日志

    # 查看统计
    stats = monitor.get_stats()
    print(f"查询次数: {stats['total_queries']}")
    print(f"平均延迟: {stats['avg_latency_ms']}ms")

asyncio.run(query_with_monitoring())
```

### 性能摘要

```python
from src.sdk import PerformanceMonitor

monitor = PerformanceMonitor(enable_metrics=True)

# 执行一些操作...
monitor.record_query("hybrid", 150)
monitor.record_query("hybrid", 200)
monitor.record_query("local", 100)

# 获取性能摘要
summary = monitor.get_performance_summary()
print(summary)

# 输出:
# SDK 性能摘要:
# - 总查询次数: 3
# - 总文档数: 0
# - 平均延迟: 150ms
# - P50 延迟: 150ms
# - P95 延迟: 200ms
# - P99 延迟: 200ms
# - 错误次数: 0
# - 错误率: 0.00%
# - 查询分布: {'hybrid': 2, 'local': 1}
```

### 错误跟踪

```python
from src.sdk import PerformanceMonitor

monitor = PerformanceMonitor(enable_metrics=True)

# 记录成功的操作
monitor.record_query("hybrid", 150, success=True)

# 记录失败的操作
monitor.record_query("hybrid", 100, success=False)

# 查看错误统计
stats = monitor.get_stats()
print(f"错误次数: {stats['errors']}")
print(f"错误率: {stats['error_rate']:.2%}")
```

### 重置统计

```python
from src.sdk import PerformanceMonitor

monitor = PerformanceMonitor(enable_metrics=True)

# 执行一些操作...
monitor.record_query("hybrid", 150)

# 重置统计
monitor.reset_stats()

# 验证重置
stats = monitor.get_stats()
print(f"查询次数（重置后）: {stats['total_queries']}")  # 0
```

## 性能指标说明

### 查询指标

| 指标 | 说明 |
|------|------|
| `total_queries` | 总查询次数 |
| `avg_latency_ms` | 平均查询延迟（毫秒） |
| `p50_latency_ms` | 中位数延迟（P50） |
| `p95_latency_ms` | P95 延迟（95% 的查询低于此值） |
| `p99_latency_ms` | P99 延迟（99% 的查询低于此值） |
| `queries_by_mode` | 各查询模式的次数分布 |

### 文档指标

| 指标 | 说明 |
|------|------|
| `total_documents` | 总文档摄入数 |

### Token 指标

| 指标 | 说明 |
|------|------|
| `total_tokens` | 总 Token 使用量 |

### 错误指标

| 指标 | 说明 |
|------|------|
| `errors` | 错误次数 |
| `error_rate` | 错误率（错误次数 / 总操作数） |

## 百分位数计算

SDK 使用纯 Python 实现百分位数计算，不依赖 numpy。

```python
from src.sdk.monitoring import _calculate_percentile

data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# 计算各种百分位数
p50 = _calculate_percentile(data, 50)  # 55.0
p95 = _calculate_percentile(data, 95)  # 95.5
p99 = _calculate_percentile(data, 99)  # 99.1

print(f"P50: {p50}, P95: {p95}, P99: {p99}")
```

## 禁用指标收集

如果不需要性能监控，可以禁用它：

```python
from src.sdk import PerformanceMonitor

# 创建禁用指标的监控器
monitor = PerformanceMonitor(enable_metrics=False)

# 记录操作（会被忽略）
monitor.record_query("hybrid", 150)

# 获取统计
stats = monitor.get_stats()
print(stats)  # {'metrics_enabled': False}
```

## 最佳实践

### 1. 使用上下文管理器自动计时

```python
from src.sdk import QueryPerformanceTimer, PerformanceMonitor

monitor = PerformanceMonitor(enable_metrics=True)

async def execute_query():
    with QueryPerformanceTimer(monitor, "hybrid"):
        # 执行查询
        result = await service.query("问题")
        return result
```

### 2. 定期获取性能摘要

```python
import asyncio

async def monitor_performance():
    monitor = PerformanceMonitor(enable_metrics=True)

    while True:
        await asyncio.sleep(60)  # 每分钟

        summary = monitor.get_performance_summary()
        logger.info(summary)
```

### 3. 重置统计以获取周期性指标

```python
import asyncio

async def periodic_monitoring():
    monitor = PerformanceMonitor(enable_metrics=True)

    while True:
        await asyncio.sleep(3600)  # 每小时

        # 获取并记录上一小时的统计
        stats = monitor.get_stats()
        logger.info(f"上一小时统计: {stats}")

        # 重置统计以开始新一轮
        monitor.reset_stats()
```

### 4. 与日志系统集成

```python
from src.sdk import PerformanceMonitor
from src.core.logging import get_logger

monitor = PerformanceMonitor(enable_metrics=True)
logger = get_logger("my_app")

# 记录操作
monitor.record_query("hybrid", 150)

# 同时记录日志和监控
logger.info("查询完成", extra={
    "latency_ms": 150,
    "mode": "hybrid"
})
```

## 性能考虑

- **内存使用**：监控器会保存所有查询时间用于计算百分位数。对于高负载场景，考虑定期重置统计。
- **计算开销**：百分位数计算的时间复杂度为 O(n log n)，对于大量查询可能会有一定开销。
- **线程安全**：当前实现不是线程安全的，如需在多线程环境中使用，请添加锁。

## 故障排查

### 统计信息为空

如果 `get_stats()` 返回 `{'metrics_enabled': False}`，请确保：

```python
# 创建监控器时启用指标
monitor = PerformanceMonitor(enable_metrics=True)
```

### 百分位数不准确

对于小样本量，百分位数可能不够准确。建议至少有 10 个以上的查询样本。

### 内存占用过高

定期重置统计以释放内存：

```python
monitor.reset_stats()
```

## 验证测试

运行验证脚本以测试监控功能：

```bash
source venv/bin/activate
python test_sdk_metrics.py
```

测试覆盖：
- 性能监控器的基本功能
- 计时器上下文管理器
- 百分位数计算
- 禁用指标收集
- 错误跟踪

## API 参考

### PerformanceMonitor

```python
class PerformanceMonitor:
    def __init__(self, enable_metrics: bool = True)
    def record_query(self, mode: str, latency_ms: int, success: bool = True) -> None
    def record_document(self, success: bool = True) -> None
    def record_tokens(self, prompt_tokens: int, completion_tokens: int) -> None
    def get_stats(self) -> Dict[str, Any]
    def reset_stats(self) -> None
    def get_performance_summary(self) -> str
```

### QueryPerformanceTimer

```python
class QueryPerformanceTimer:
    def __init__(self, monitor: PerformanceMonitor, mode: str, logger: Optional[Any] = None)
    def __enter__(self) -> "QueryPerformanceTimer"
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool
```

### 辅助函数

```python
def _calculate_percentile(values: List[float], percentile: float) -> float
```

## 总结

SDK 的监控功能提供了完整的性能追踪能力，帮助您：

1. 监控查询性能和延迟
2. 跟踪文档摄入状态
3. 统计错误率和失败情况
4. 分析 Token 使用
5. 生成性能报告

使用这些工具，您可以更好地了解应用的性能表现，及时发现和解决问题。
