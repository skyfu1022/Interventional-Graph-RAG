# Medical Graph RAG SDK 客户端

## 概述

Medical Graph RAG Python SDK 提供了一个类型安全、易用的 Python API，用于与医疗知识图谱系统进行交互。

### 主要特性

- ✅ **异步上下文管理器支持** - 自动初始化和清理资源
- ✅ **文档摄入** - 支持文本、文件、批量、多模态摄入
- ✅ **知识图谱查询** - 支持 6 种查询模式（naive, local, global, hybrid, mix, bypass）
- ✅ **图谱管理** - 列出、获取、删除、导出图谱
- ✅ **流式查询** - 实时流式返回答案
- ✅ **性能监控** - 自动记录查询延迟、错误率等指标
- ✅ **配置管理** - 支持环境变量和配置文件
- ✅ **异常处理** - 完善的异常类型和错误信息

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

## 快速开始

### 基本使用

```python
from src.sdk import MedGraphClient
import asyncio

async def main():
    # 使用异步上下文管理器（推荐）
    async with MedGraphClient(workspace="medical") as client:
        # 执行查询
        result = await client.query("什么是糖尿病?")
        print(result.answer)

asyncio.run(main())
```

### 文档摄入

```python
async with MedGraphClient(workspace="medical") as client:
    # 摄入单个文档
    doc_info = await client.ingest_document("medical.txt")
    print(f"文档已摄入: {doc_info.doc_id}")

    # 摄入文本
    text = "糖尿病是一种慢性代谢性疾病..."
    doc_info = await client.ingest_text(text, doc_id="diabetes_intro")
```

### 批量操作

```python
async with MedGraphClient(workspace="medical") as client:
    # 批量摄入文档
    def on_progress(current, total, doc_id):
        print(f"进度: {current}/{total} - {doc_id}")

    result = await client.ingest_batch(
        file_paths=["doc1.txt", "doc2.txt", "doc3.txt"],
        progress_callback=on_progress,
        max_concurrency=3
    )

    print(f"完成: {result.succeeded}/{result.total}")
```

### 流式查询

```python
async with MedGraphClient(workspace="medical") as client:
    # 流式查询
    async for chunk in client.query_stream("详细说明糖尿病的病因"):
        print(chunk, end="", flush=True)
```

## 配置管理

### 从环境变量创建客户端

```python
client = MedGraphClient.from_env(
    workspace="medical",
    log_level="INFO",
    enable_metrics=True
)

async with client:
    result = await client.query("测试")
```

### 从配置文件创建客户端

**config.json:**
```json
{
  "rag_workspace": "medical",
  "neo4j_uri": "neo4j://localhost:7687",
  "neo4j_username": "neo4j",
  "neo4j_password": "password",
  "milvus_uri": "http://localhost:19530",
  "openai_api_key": "sk-...",
  "llm_model": "gpt-4o-mini",
  "embedding_model": "text-embedding-3-large"
}
```

**Python 代码:**
```python
client = MedGraphClient.from_config("config.json")

async with client:
    result = await client.query("测试")
```

## 查询模式

SDK 支持 6 种查询模式：

| 模式 | 描述 | 使用场景 |
|------|------|----------|
| `naive` | 简单检索，直接返回答案 | 快速问答 |
| `local` | 局部社区检索，关注实体关系 | 实体关系查询 |
| `global` | 全局社区检索，关注图谱结构 | 全局概览 |
| `hybrid` | 混合检索，结合局部和全局 | 综合查询（推荐） |
| `mix` | 混合模式，动态调整策略 | 复杂查询 |
| `bypass` | 绕过图谱，直接检索向量 | 原始文档检索 |

```python
# 使用不同模式查询
result = await client.query("什么是糖尿病?", mode="hybrid")
result = await client.query("糖尿病和高血压的关系?", mode="local")
```

## 性能监控

SDK 内置性能监控功能，自动记录查询延迟、错误率等指标。

### 启用性能监控

```python
async with MedGraphClient(enable_metrics=True) as client:
    # 执行查询
    for i in range(10):
        await client.query(f"查询 {i}")

    # 获取统计信息
    stats = client.get_stats()
    print(f"查询次数: {stats['total_queries']}")
    print(f"平均延迟: {stats['avg_latency_ms']}ms")
    print(f"P95 延迟: {stats['p95_latency_ms']}ms")
    print(f"错误率: {stats['error_rate']:.2%}")
```

### 性能指标说明

| 指标 | 说明 |
|------|------|
| `total_queries` | 总查询次数 |
| `total_documents` | 总文档数 |
| `avg_latency_ms` | 平均查询延迟（毫秒） |
| `p50_latency_ms` | 中位数延迟（P50） |
| `p95_latency_ms` | P95 延迟 |
| `p99_latency_ms` | P99 延迟 |
| `queries_by_mode` | 各模式查询次数 |
| `errors` | 错误次数 |
| `error_rate` | 错误率 |

## 图谱管理

### 列出图谱

```python
async with MedGraphClient() as client:
    graphs = await client.list_graphs()
    for graph in graphs:
        print(f"{graph.graph_id}: {graph.entity_count} 实体")
```

### 获取图谱详情

```python
async with MedGraphClient() as client:
    info = await client.get_graph("medical")
    print(f"实体数: {info.entity_count}")
    print(f"关系数: {info.relationship_count}")
    print(f"文档数: {info.document_count}")
```

### 导出图谱

```python
async with MedGraphClient() as client:
    # 导出为 JSON
    await client.export_graph("medical", "output.json", "json")

    # 导出为 CSV
    await client.export_graph("medical", "output.csv", "csv")

    # 导出为 Mermaid
    await client.export_graph("medical", "output.mmd", "mermaid")
```

### 删除图谱

```python
async with MedGraphClient() as client:
    # 删除图谱（需要确认）
    success = await client.delete_graph("test", confirm=True)
```

## 异常处理

SDK 提供了完善的异常类型：

```python
from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError,
    DocumentNotFoundError,
    ConnectionError,
    ValidationError,
)

try:
    async with MedGraphClient() as client:
        result = await client.query("测试")
except ConfigError as e:
    print(f"配置错误: {e.message}")
    print(f"详情: {e.details}")
except ValidationError as e:
    print(f"验证错误: {e.message}")
    print(f"字段: {e.field}")
except MedGraphSDKError as e:
    print(f"SDK 错误: {e.message}")
```

## API 参考

### MedGraphClient

#### 初始化方法

- `__init__(workspace, log_level, config, enable_metrics, **kwargs)` - 初始化客户端
- `from_env(workspace, log_level, enable_metrics)` - 从环境变量创建客户端
- `from_config(config_path, workspace, log_level, enable_metrics)` - 从配置文件创建客户端

#### 生命周期方法

- `async initialize()` - 手动初始化客户端
- `async close()` - 关闭客户端
- `async __aenter__()` - 进入异步上下文
- `async __aexit__()` - 退出异步上下文

#### 文档摄入方法

- `async ingest_document(file_path, doc_id)` - 摄入单个文档
- `async ingest_text(text, doc_id)` - 摄入文本
- `async ingest_batch(file_paths, doc_ids, max_concurrency, progress_callback)` - 批量摄入
- `async ingest_multimodal(content_list, file_path)` - 摄入多模态内容
- `async delete_document(doc_id)` - 删除文档

#### 查询方法

- `async query(query_text, mode, graph_id, **kwargs)` - 执行查询
- `async query_stream(query_text, mode, graph_id, **kwargs)` - 流式查询

#### 图谱管理方法

- `async list_graphs()` - 列出所有图谱
- `async get_graph(graph_id)` - 获取图谱详情
- `async delete_graph(graph_id, confirm)` - 删除图谱
- `async export_graph(graph_id, output_path, format)` - 导出图谱

#### 性能监控方法

- `get_stats()` - 获取性能统计信息
- `reset_stats()` - 重置性能统计
- `get_performance_summary()` - 获取性能摘要

## 验证代码

运行验证代码以测试 SDK 客户端的各种功能：

```bash
python examples/sdk_client_example.py
```

该脚本包含以下示例：

1. **基本查询功能** - 演示如何执行简单的知识图谱查询
2. **文档摄入** - 演示如何摄入单个文档并查询
3. **批量操作** - 演示如何批量摄入文档并使用进度回调
4. **流式查询** - 演示如何使用流式查询实时获取答案
5. **配置管理** - 演示如何从环境变量和配置文件创建客户端
6. **性能监控** - 演示如何使用性能监控功能
7. **图谱管理** - 演示如何列出、获取和导出图谱
8. **异常处理** - 演示如何处理各种 SDK 异常

## 架构说明

SDK 客户端整合了所有服务层功能：

```
src/sdk/
├── client.py          # SDK 客户端主类
├── types.py           # 类型定义
├── exceptions.py      # 异常定义
├── monitoring.py      # 性能监控
└── __init__.py        # 导出接口

整合的服务层:
├── IngestionService   # 文档摄入服务
├── QueryService       # 查询服务
└── GraphService       # 图谱管理服务
```

## 最佳实践

### 1. 使用异步上下文管理器

```python
# 推荐：使用异步上下文管理器
async with MedGraphClient() as client:
    result = await client.query("测试")

# 不推荐：手动管理
client = MedGraphClient()
await client.initialize()
result = await client.query("测试")
await client.close()
```

### 2. 启用性能监控

```python
async with MedGraphClient(enable_metrics=True) as client:
    result = await client.query("测试")
    stats = client.get_stats()
    print(stats)
```

### 3. 使用批量操作提高效率

```python
# 推荐：批量摄入
await client.ingest_batch(file_paths, max_concurrency=5)

# 不推荐：逐个摄入
for path in file_paths:
    await client.ingest_document(path)
```

### 4. 选择合适的查询模式

```python
# 综合查询：使用 hybrid（推荐）
result = await client.query("什么是糖尿病?", mode="hybrid")

# 实体关系：使用 local
result = await client.query("糖尿病和高血压的关系?", mode="local")

# 快速问答：使用 naive
result = await client.query("血糖正常值是多少?", mode="naive")
```

### 5. 使用配置文件管理复杂配置

```python
# config.json
{
  "rag_workspace": "medical",
  "neo4j_uri": "neo4j://localhost:7687",
  "milvus_uri": "http://localhost:19530",
  "openai_api_key": "sk-..."
}

# Python 代码
client = MedGraphClient.from_config("config.json")
```

## 常见问题

### Q: 如何处理初始化超时？

```python
try:
    async with MedGraphClient() as client:
        result = await client.query("测试")
except ConfigError as e:
    if "超时" in e.message:
        print("初始化超时，请检查服务连接")
```

### Q: 如何禁用性能监控？

```python
async with MedGraphClient(enable_metrics=False) as client:
    result = await client.query("测试")
```

### Q: 如何使用不同的工作空间？

```python
# 创建不同工作空间的客户端
async with MedGraphClient(workspace="medical") as client1:
    result1 = await client1.query("医疗查询")

async with MedGraphClient(workspace="research") as client2:
    result2 = await client2.query("研究查询")
```

### Q: 如何调试查询问题？

```python
import logging
logging.basicConfig(level=logging.DEBUG)

async with MedGraphClient(log_level="DEBUG") as client:
    result = await client.query("测试")
```

## 参考资料

- [LightRAG 官方文档](https://github.com/HKUDS/LightRAG)
- [LangGraph 最佳实践](https://langchain-ai.github.io/langgraph/)
- [项目 README](../README.md)

## 版本历史

- **0.2.0** (2025-01-11)
  - 整合所有服务层功能
  - 添加性能监控
  - 添加配置管理
  - 完善异常处理

- **0.1.0** (2024-12-01)
  - 初始版本
  - 基本查询和文档摄入功能

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
