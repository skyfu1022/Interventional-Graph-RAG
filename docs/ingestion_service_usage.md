# 摄入服务使用指南

本文档介绍如何使用 `IngestionService` 进行文档摄入。

## 目录
- [基础用法](#基础用法)
- [批量摄入](#批量摄入)
- [进度跟踪](#进度跟踪)
- [错误处理](#错误处理)
- [状态管理](#状态管理)
- [最佳实践](#最佳实践)

## 基础用法

### 1. 初始化服务

```python
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.ingestion import IngestionService
import asyncio

async def main():
    # 加载配置
    config = Settings()

    # 初始化适配器
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()

    # 创建摄入服务
    service = IngestionService(adapter)

    return service

service = asyncio.run(main())
```

### 2. 摄入单个文档

```python
# 从文件摄入
result = await service.ingest_document(
    file_path="path/to/document.txt",
    doc_id="doc-001"  # 可选，默认使用文件名
)

print(f"文档 ID: {result.doc_id}")
print(f"状态: {result.status}")
print(f"元数据: {result.metadata}")
```

### 3. 摄入纯文本

```python
# 直接摄入文本内容
text = """
糖尿病是一种代谢性疾病，主要特征是慢性高血糖。
常见症状包括多饮、多尿、多食和体重下降。
"""

result = await service.ingest_text(
    text=text,
    doc_id="text-001"  # 可选，默认使用 MD5 哈希
)

print(f"文本摄入成功: {result.doc_id}")
```

## 批量摄入

### 基础批量摄入

```python
# 准备文件列表
file_paths = [
    "documents/doc1.txt",
    "documents/doc2.txt",
    "documents/doc3.txt",
]

# 批量摄入
batch_result = await service.ingest_batch(
    file_paths=file_paths,
    max_concurrency=5  # 最大并发数
)

print(f"总计: {batch_result.total}")
print(f"成功: {batch_result.succeeded}")
print(f"失败: {batch_result.failed}")
print(f"耗时: {batch_result.duration_ms}ms")
```

### 带文档 ID 的批量摄入

```python
file_paths = ["doc1.txt", "doc2.txt", "doc3.txt"]
doc_ids = ["medical-doc-001", "medical-doc-002", "medical-doc-003"]

batch_result = await service.ingest_batch(
    file_paths=file_paths,
    doc_ids=doc_ids,
    max_concurrency=3
)
```

## 进度跟踪

### 使用进度回调

```python
def on_progress(current: int, total: int, doc_id: str):
    """进度回调函数"""
    percentage = (current / total) * 100
    print(f"进度: {current}/{total} ({percentage:.0f}%) - 当前: {doc_id}")

# 带进度跟踪的批量摄入
batch_result = await service.ingest_batch(
    file_paths=file_paths,
    progress_callback=on_progress,
    max_concurrency=5
)
```

### 自定义进度处理

```python
import time

class ProgressTracker:
    def __init__(self):
        self.start_time = time.time()
        self.last_update = self.start_time

    def __call__(self, current: int, total: int, doc_id: str):
        now = time.time()
        elapsed = now - self.start_time
        avg_time = elapsed / current if current > 0 else 0

        print(f"[{doc_id}] {current}/{total} | "
              f"平均耗时: {avg_time:.2f}秒/文档")

# 使用自定义跟踪器
tracker = ProgressTracker()
batch_result = await service.ingest_batch(
    file_paths=file_paths,
    progress_callback=tracker
)
```

## 错误处理

### 容错模式（默认）

```python
# 遇到错误继续处理
batch_result = await service.ingest_batch(
    file_paths=file_paths,
    continue_on_error=True  # 默认值
)

# 查看错误详情
for error in batch_result.errors:
    print(f"文件: {error['file']}")
    print(f"ID: {error['doc_id']}")
    print(f"错误: {error['error']}")
    print(f"类型: {error['error_type']}")
```

### 严格模式

```python
# 遇到错误立即停止
try:
    batch_result = await service.ingest_batch(
        file_paths=file_paths,
        continue_on_error=False  # 严格模式
    )
except Exception as e:
    print(f"批量摄入失败: {e}")
```

### 单文档错误处理

```python
from src.core.exceptions import DocumentError, ValidationError

try:
    result = await service.ingest_document("document.txt")
except ValidationError as e:
    print(f"验证失败: {e.message}")
    print(f"字段: {e.field}")
    print(f"值: {e.value}")
except DocumentError as e:
    print(f"文档处理失败: {e.message}")
    print(f"文档 ID: {e.doc_id}")
```

## 状态管理

### 查询文档状态

```python
# 查询单个文档状态
status = await service.get_ingestion_status("doc-001")

print(f"状态: {status.status}")  # pending, processing, completed, failed
print(f"进度: {status.progress}%")
print(f"创建时间: {status.created_at}")
print(f"更新时间: {status.updated_at}")

if status.error:
    print(f"错误: {status.error}")
```

### 列出所有文档

```python
# 列出所有文档
all_docs = await service.list_documents()
print(f"总文档数: {len(all_docs)}")

for doc in all_docs:
    print(f"{doc.doc_id}: {doc.status}")

# 按状态过滤
completed_docs = await service.list_documents(status_filter="completed")
failed_docs = await service.list_documents(status_filter="failed")
```

### 获取统计信息

```python
# 获取服务统计
stats = service.get_stats()

print(f"缓存文档总数: {stats['total_cached']}")
print(f"成功率: {stats['success_rate']:.1f}%")

# 按状态统计
for status, count in stats['by_status'].items():
    print(f"{status}: {count}")
```

### 清理缓存

```python
# 清理所有缓存
cleared_count = await service.clear_cache()
print(f"清理了 {cleared_count} 个状态")

# 清理过期缓存（例如 1 小时前）
import time
threshold = time.time() - 3600  # 1 小时前
cleared_count = await service.clear_cache(older_than=threshold)
print(f"清理了 {cleared_count} 个过期状态")
```

## 最佳实践

### 1. 合理设置并发数

```python
# 对于大量小文件，可以使用较高的并发数
batch_result = await service.ingest_batch(
    file_paths=small_files,
    max_concurrency=10  # 高并发
)

# 对于大文件，使用较低的并发数
batch_result = await service.ingest_batch(
    file_paths=large_files,
    max_concurrency=2  # 低并发，避免资源耗尽
)
```

### 2. 使用上下文管理器

```python
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.ingestion import IngestionService

async def ingest_documents():
    config = Settings()

    # 使用上下文管理器自动清理资源
    async with RAGAnythingAdapter(config) as adapter:
        await adapter.initialize()
        service = IngestionService(adapter)

        # 执行摄入操作
        result = await service.ingest_text("文档内容...")

        # 自动关闭适配器
```

### 3. 批量处理大文件集合

```python
async def ingest_large_collection(file_paths, batch_size=100):
    """分批处理大量文件"""

    total = len(file_paths)
    all_results = []

    for i in range(0, total, batch_size):
        batch = file_paths[i:i + batch_size]
        print(f"处理批次 {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")

        batch_result = await service.ingest_batch(
            file_paths=batch,
            max_concurrency=5
        )

        all_results.append(batch_result)

        # 可选：批次间休息
        await asyncio.sleep(1)

    return all_results
```

### 4. 实现重试机制

```python
import asyncio
from src.core.exceptions import DocumentError

async def ingest_with_retry(
    service,
    file_path: str,
    doc_id: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
):
    """带重试的文档摄入"""

    for attempt in range(max_retries):
        try:
            return await service.ingest_document(file_path, doc_id)
        except DocumentError as e:
            if attempt < max_retries - 1:
                print(f"摄入失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                print(f"重试 {max_retries} 次后仍失败")
                raise

# 使用
result = await ingest_with_retry(service, "doc.txt", "doc-001")
```

### 5. 监控和日志

```python
from src.core.logging import get_logger

logger = get_logger("my_ingestion_app")

async def monitored_ingestion(service, file_paths):
    """带监控的摄入过程"""

    logger.info(f"开始摄入 {len(file_paths)} 个文档")

    start_time = time.time()

    result = await service.ingest_batch(
        file_paths=file_paths,
        progress_callback=lambda c, t, d: logger.debug(f"进度: {c}/{t} - {d}")
    )

    duration = time.time() - start_time

    logger.info(
        f"摄入完成 | "
        f"成功: {result.succeeded}/{result.total} | "
        f"耗时: {duration:.2f}秒 | "
        f"平均: {duration/result.total:.2f}秒/文档"
    )

    if result.failed > 0:
        logger.warning(f"{result.failed} 个文档失败")
        for error in result.errors:
            logger.error(f"  {error['doc_id']}: {error['error']}")

    return result
```

## 完整示例

```python
import asyncio
from pathlib import Path
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.ingestion import IngestionService
from src.core.logging import setup_logging, get_logger

# 配置日志
setup_logging(log_level="INFO")
logger = get_logger("ingestion_example")

async def main():
    """完整的摄入示例"""

    logger.info("初始化服务...")
    config = Settings()

    async with RAGAnythingAdapter(config) as adapter:
        await adapter.initialize()
        service = IngestionService(adapter)

        # 1. 摄入单个文本
        logger.info("摄入医学文本...")
        text_result = await service.ingest_text(
            "高血压是心血管疾病的主要危险因素。",
            doc_id="medical-text-001"
        )
        logger.info(f"✓ 文本摄入成功: {text_result.doc_id}")

        # 2. 批量摄入文件
        logger.info("批量摄入文档...")
        file_paths = list(Path("documents").glob("*.txt"))

        if file_paths:
            batch_result = await service.ingest_batch(
                file_paths=[str(p) for p in file_paths],
                max_concurrency=3,
                progress_callback=lambda c, t, d: logger.info(f"进度: {c}/{t}")
            )

            logger.info(f"✓ 批量摄入完成: {batch_result}")

        # 3. 查看统计
        stats = service.get_stats()
        logger.info(f"服务统计: {stats}")

        # 4. 列出所有文档
        all_docs = await service.list_documents()
        logger.info(f"总文档数: {len(all_docs)}")

    logger.info("摄入完成！")

if __name__ == "__main__":
    asyncio.run(main())
```

## API 参考

### IngestionService

| 方法 | 说明 |
|------|------|
| `ingest_document(file_path, doc_id)` | 摄入单个文档 |
| `ingest_text(text, doc_id)` | 摄入纯文本 |
| `ingest_batch(file_paths, doc_ids, max_concurrency, progress_callback, continue_on_error)` | 批量摄入文档 |
| `get_ingestion_status(doc_id)` | 获取文档状态 |
| `list_documents(status_filter)` | 列出所有文档 |
| `clear_cache(older_than)` | 清理状态缓存 |
| `get_stats()` | 获取统计信息 |

### BatchIngestResult

| 属性 | 说明 |
|------|------|
| `total` | 总文档数 |
| `succeeded` | 成功数 |
| `failed` | 失败数 |
| `errors` | 错误列表 |
| `duration_ms` | 耗时（毫秒） |
| `results` | 所有摄入结果 |

### DocumentStatus

| 属性 | 说明 |
|------|------|
| `doc_id` | 文档 ID |
| `status` | 状态（pending/processing/completed/failed） |
| `progress` | 进度（0-100） |
| `error` | 错误信息 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

## 常见问题

### Q: 如何处理大量文档？

A: 使用批量摄入，分批处理，合理设置并发数（建议 5-10）。

### Q: 如何实现断点续传？

A: 使用状态缓存，记录已摄入的文档，下次跳过已完成文档。

### Q: 如何提高摄入速度？

A:
1. 增加并发数（但不要过高）
2. 使用 SSD 存储
3. 优化网络连接（如果使用云端服务）

### Q: 内存占用过高怎么办？

A:
1. 降低并发数
2. 分批处理文档
3. 定期清理状态缓存

## 相关资源

- [RAGAnythingAdapter 文档](./adapters.md)
- [异常处理指南](./exceptions.md)
- [配置管理](./configuration.md)
