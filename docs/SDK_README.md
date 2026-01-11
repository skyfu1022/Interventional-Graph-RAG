# Medical Graph RAG Python SDK

Medical Graph RAG Python SDK 是一个类型安全、易用的 Python SDK，用于构建和管理医学知识图谱。

## 特性

- **异步支持**: 基于 asyncio 的异步 API，支持高并发操作
- **类型安全**: 使用 Pydantic 提供完整的类型定义和数据验证
- **易用性**: 提供异步上下文管理器，自动处理资源管理
- **性能监控**: 内置性能监控和指标收集
- **多种查询模式**: 支持 6 种知识图谱查询模式
- **完整的错误处理**: 提供友好的异常类和错误信息

## 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/medical-graph-rag.git
cd medical-graph-rag

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### 基本使用

```python
from src.sdk import MedGraphClient
import asyncio

async def main():
    # 使用异步上下文管理器（推荐）
    async with MedGraphClient(workspace="medical") as client:
        # 摄入文档
        await client.ingest_document("medical_doc.txt")

        # 查询知识图谱
        result = await client.query("什么是糖尿病?")
        print(result.answer)

asyncio.run(main())
```

### 摄入文本

```python
async with MedGraphClient(workspace="medical") as client:
    medical_text = """
    糖尿病是一种慢性代谢性疾病，主要特征是高血糖。
    糖尿病分为 1 型和 2 型，2 型糖尿病最为常见。
    """

    doc_info = await client.ingest_text(
        text=medical_text,
        doc_id="diabetes-doc"
    )

    print(f"文档 ID: {doc_info.doc_id}")
    print(f"状态: {doc_info.status}")
    print(f"实体数: {doc_info.entities_count}")
```

### 查询知识图谱

```python
async with MedGraphClient(workspace="medical") as client:
    # 混合模式查询（推荐）
    result = await client.query(
        query_text="糖尿病有哪些并发症？",
        mode="hybrid"
    )

    print(f"答案: {result.answer}")
    print(f"延迟: {result.latency_ms}ms")
    print(f"来源数: {len(result.sources)}")
```

### 批量摄入文档

```python
async with MedGraphClient(workspace="medical") as client:
    def progress_callback(current, total, doc_id):
        print(f"进度: {current}/{total} - {doc_id}")

    result = await client.ingest_batch(
        file_paths=["doc1.txt", "doc2.txt", "doc3.txt"],
        progress_callback=progress_callback
    )

    print(f"成功: {result.succeeded}/{result.total}")
```

### 流式查询

```python
async with MedGraphClient(workspace="medical") as client:
    async for chunk in client.query_stream(
        query_text="详细说明糖尿病的病因",
        mode="hybrid"
    ):
        print(chunk, end="", flush=True)
```

## API 参考

### MedGraphClient

主要的 SDK 客户端类。

#### 初始化

```python
client = MedGraphClient(
    workspace="medical",      # 工作空间名称
    log_level="INFO",         # 日志级别
    enable_metrics=True,      # 启用性能监控
    **kwargs                  # 其他配置参数
)
```

#### 文档摄入方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `ingest_document(file_path, doc_id)` | 摄入文档文件 | `DocumentInfo` |
| `ingest_text(text, doc_id)` | 摄入文本内容 | `DocumentInfo` |
| `ingest_batch(file_paths, doc_ids, max_concurrency, progress_callback)` | 批量摄入文档 | `BatchIngestResult` |
| `ingest_multimodal(content_list, file_path)` | 摄入多模态内容 | `DocumentInfo` |

#### 查询方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `query(query_text, mode, graph_id)` | 执行查询 | `QueryResult` |
| `query_stream(query_text, mode, graph_id)` | 流式查询 | `AsyncIterator[str]` |

#### 图谱管理方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `list_graphs()` | 列出所有图谱 | `List[GraphInfo]` |
| `get_graph(graph_id)` | 获取图谱详情 | `GraphInfo` |
| `delete_graph(graph_id, confirm)` | 删除图谱 | `bool` |
| `export_graph(graph_id, output_path, format)` | 导出图谱 | `None` |

#### 性能监控方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_stats()` | 获取性能统计 | `Dict[str, Any]` |
| `reset_stats()` | 重置性能统计 | `None` |
| `get_performance_summary()` | 获取性能摘要 | `str` |

### 查询模式

SDK 支持 6 种查询模式：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `naive` | 简单检索，直接返回相关内容 | 快速获取信息 |
| `local` | 局部社区检索，关注实体局部关系 | 实体关系查询 |
| `global` | 全局社区检索，关注图谱全局结构 | 全局概览查询 |
| `hybrid` | 混合检索，结合局部和全局优势 | 通用查询（推荐） |
| `mix` | 混合模式，动态调整检索策略 | 复杂查询 |
| `bypass` | 绕过图谱，直接检索原始文档 | 原始文档查询 |

```python
from src.sdk import QueryMode

# 使用枚举值
result = await client.query(
    query_text="糖尿病的治疗方法",
    mode=QueryMode.HYBRID
)

# 或使用字符串
result = await client.query(
    query_text="糖尿病的治疗方法",
    mode="hybrid"
)
```

### 类型定义

#### QueryResult

查询结果类型。

```python
from src.sdk import QueryResult

result: QueryResult = await client.query("问题")

# 访问结果字段
print(result.query)      # 查询文本
print(result.answer)     # 生成的答案
print(result.mode)       # 查询模式
print(result.sources)    # 来源列表
print(result.context)    # 上下文列表
```

#### DocumentInfo

文档信息类型。

```python
from src.sdk import DocumentInfo

doc_info: DocumentInfo = await client.ingest_text("文本内容")

# 访问文档信息
print(doc_info.doc_id)           # 文档 ID
print(doc_info.status)           # 状态
print(doc_info.entities_count)   # 实体数
```

#### GraphInfo

图谱信息类型。

```python
from src.sdk import GraphInfo

graphs: List[GraphInfo] = await client.list_graphs()

for graph in graphs:
    print(f"图谱: {graph.graph_id}")
    print(f"实体数: {graph.entity_count}")
    print(f"关系数: {graph.relationship_count}")
```

### 异常处理

SDK 提供了完整的异常类层次结构：

```python
from src.sdk import (
    MedGraphSDKError,
    ConfigError,
    DocumentNotFoundError,
    ValidationError,
    QueryTimeoutError,
    RateLimitError,
)

try:
    result = await client.query("问题")
except ValidationError as e:
    print(f"验证错误: {e}")
    print(f"字段: {e.field}")
    print(f"约束: {e.constraint}")
except DocumentNotFoundError as e:
    print(f"文档不存在: {e.doc_id}")
except MedGraphSDKError as e:
    print(f"SDK 错误: {e}")
    print(f"错误码: {e.error_code}")
    print(f"详情: {e.to_dict()}")
```

### 性能监控

SDK 内置性能监控功能：

```python
async with MedGraphClient(enable_metrics=True) as client:
    # 执行一些操作
    await client.ingest_text("文本")
    await client.query("问题")

    # 获取性能统计
    stats = client.get_stats()
    print(f"总查询次数: {stats['total_queries']}")
    print(f"平均延迟: {stats['avg_latency_ms']}ms")
    print(f"P95 延迟: {stats['p95_latency_ms']}ms")
    print(f"错误率: {stats['error_rate']:.2%}")

    # 获取性能摘要
    summary = client.get_performance_summary()
    print(summary)
```

### 配置管理

#### 从环境变量创建

```python
client = MedGraphClient.from_env(
    workspace="medical",
    log_level="INFO",
    enable_metrics=True
)
```

#### 从配置文件创建

```python
# JSON 配置文件
client = MedGraphClient.from_config(
    config_path="config.json",
    workspace="medical"  # 可选，覆盖配置文件中的值
)

# YAML 配置文件
client = MedGraphClient.from_config(
    config_path="config.yaml",
    workspace="medical"
)
```

## 高级用法

### 自定义日志

```python
from src.core.logging import setup_logging, get_logger

# 设置日志级别
setup_logging(log_level="DEBUG")

# 获取日志记录器
logger = get_logger("my_app")
logger.info("应用启动")
```

### 使用性能计时器

```python
from src.sdk import QueryPerformanceTimer

async with MedGraphClient() as client:
    monitor = client._performance_monitor

    # 自动记录查询性能
    with QueryPerformanceTimer(monitor, "hybrid", logger=logger):
        result = await client.query("问题")
        # 自动记录延迟和成功率
```

### 转换核心异常

```python
from src.sdk.exceptions import convert_core_exception
from src.core.exceptions import QueryError

try:
    # 调用核心层代码
    raise QueryError("核心层错误")
except Exception as e:
    # 转换为 SDK 异常
    sdk_error = convert_core_exception(e)
    raise sdk_error from e
```

## 示例

查看 `examples/sdk_usage_example.py` 获取更多使用示例：

```bash
python examples/sdk_usage_example.py
```

## 验证安装

运行验证脚本确保 SDK 正确安装：

```bash
python test_sdk_exports.py
```

## 版本信息

```python
from src.sdk import get_version, get_info

print(f"SDK 版本: {get_version()}")
print(f"SDK 信息: {get_info()}")
```

## 许可证

MIT License

## 支持

- GitHub Issues: https://github.com/your-org/medical-graph-rag/issues
- 文档: https://github.com/your-org/medical-graph-rag/docs
