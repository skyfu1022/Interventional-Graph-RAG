# Medical Graph RAG SDK 使用文档

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
  - [安装](#安装)
  - [初始化](#初始化)
  - [基本使用](#基本使用)
- [API 参考](#api-参考)
  - [客户端类](#客户端类)
  - [文档摄入方法](#文档摄入方法)
  - [查询方法](#查询方法)
  - [图谱管理方法](#图谱管理方法)
  - [性能监控方法](#性能监控方法)
  - [配置管理方法](#配置管理方法)
- [类型定义](#类型定义)
- [异常处理](#异常处理)
- [完整示例](#完整示例)
- [最佳实践](#最佳实践)

---

## 概述

Medical Graph RAG SDK 是一个用于构建和查询医疗知识图谱的 Python SDK。它基于 LightRAG 和 LangGraph 构建，支持多模态文档处理、多种查询模式和图谱管理功能。

### 核心特性

- **异步架构**：完全异步设计，支持高并发操作
- **多模态支持**：支持文本、图像、表格等多种内容类型
- **多种查询模式**：6 种查询模式（naive、local、global、hybrid、mix、bypass）
- **图谱管理**：支持节点合并、相似实体查找、图谱导出等功能
- **性能监控**：内置性能指标收集和统计
- **上下文管理器**：支持 `async with` 自动资源管理

### 技术栈

- Python 3.10+
- LightRAG 1.4.9+（RAG 框架）
- LangGraph（智能体编排）
- Neo4j（图数据库）
- Milvus（向量数据库）

---

## 快速开始

### 安装

#### 使用 pip 安装

```bash
pip install medical-graph-rag
```

#### 从源码安装

```bash
git clone https://github.com/your-org/Medical-Graph-RAG.git
cd Medical-Graph-RAG
pip install -e .
```

### 配置环境变量

创建 `.env` 文件：

```bash
# OpenAI 配置
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Milvus 配置
MILVUS_URI=localhost:19530
MILVUS_TOKEN=

# 可选配置
RAG_WORKSPACE=medical
LOG_LEVEL=INFO
```

### 初始化

#### 方式 1：使用异步上下文管理器（推荐）

```python
from src.sdk import MedGraphClient
import asyncio

async def main():
    async with MedGraphClient(workspace="medical") as client:
        # 使用客户端
        result = await client.query("什么是糖尿病?")
        print(result.answer)

asyncio.run(main())
```

#### 方式 2：从环境变量创建

```python
client = MedGraphClient.from_env()

async with client:
    result = await client.query("什么是糖尿病?")
    print(result.answer)
```

#### 方式 3：从配置文件创建

```python
# config.yaml
workspace: medical
log_level: INFO
openai_api_key: sk-...
neo4j_uri: bolt://localhost:7687

client = MedGraphClient.from_config("config.yaml")

async with client:
    result = await client.query("什么是糖尿病?")
    print(result.answer)
```

### 基本使用

```python
from src.sdk import MedGraphClient
import asyncio

async def main():
    # 初始化客户端
    async with MedGraphClient(workspace="medical") as client:

        # 1. 摄入文档
        doc_info = await client.ingest_document("medical_report.txt")
        print(f"文档 ID: {doc_info.doc_id}")
        print(f"状态: {doc_info.status}")

        # 2. 查询知识图谱
        result = await client.query(
            "糖尿病的主要症状有哪些?",
            mode="hybrid"
        )

        # 3. 输出结果
        print(f"答案: {result.answer}")
        print(f"查询模式: {result.mode}")
        print(f"延迟: {result.latency_ms}ms")

asyncio.run(main())
```

---

## API 参考

### 客户端类

#### `MedGraphClient`

SDK 的主客户端类，提供所有功能的统一接口。

**初始化参数：**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `workspace` | str | "medical" | 工作空间名称，用于隔离不同的知识图谱 |
| `log_level` | str | "INFO" | 日志级别（DEBUG, INFO, WARNING, ERROR） |
| `config` | Settings | None | 配置对象（可选，如果不提供则从环境变量加载） |
| `enable_metrics` | bool | True | 是否启用性能监控 |
| `**kwargs` | - | - | 额外的配置参数（会覆盖 config 中的值） |

**示例：**

```python
# 使用默认配置
client = MedGraphClient()

# 自定义工作空间和日志级别
client = MedGraphClient(
    workspace="my_graph",
    log_level="DEBUG",
    enable_metrics=True
)

# 使用自定义配置
from src.core.config import Settings
config = Settings(
    openai_api_key="sk-...",
    neo4j_uri="bolt://localhost:7687"
)
client = MedGraphClient(config=config)
```

#### 异步上下文管理器方法

##### `async def __aenter__(self) -> MedGraphClient`

进入异步上下文，自动初始化客户端。

**返回：**
- `MedGraphClient`: 客户端实例

**示例：**

```python
async with MedGraphClient() as client:
    # 客户端已自动初始化
    result = await client.query("测试")
```

##### `async def __aexit__(self, exc_type, exc_val, exc_tb) -> None`

退出异步上下文，自动关闭连接和释放资源。

**示例：**

```python
# 即使发生异常，资源也会被正确清理
try:
    async with MedGraphClient() as client:
        await client.ingest_document("doc.txt")
        raise ValueError("测试异常")
except ValueError:
    print("异常被捕获，连接已自动关闭")
```

#### 客户端生命周期方法

##### `async def initialize(self) -> None`

手动初始化客户端（如果不使用上下文管理器）。

**示例：**

```python
client = MedGraphClient()
await client.initialize()
# ... 使用客户端 ...
await client.close()
```

##### `async def close(self) -> None`

关闭客户端，释放资源。可以安全地多次调用。

**示例：**

```python
async with MedGraphClient() as client:
    await client.query("测试")
# 退出时自动调用 close()
```

---

### 文档摄入方法

#### `async def ingest_document(self, file_path: str, doc_id: Optional[str] = None) -> DocumentInfo`

摄入文档到知识图谱。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `file_path` | str | 是 | 文档文件路径 |
| `doc_id` | Optional[str] | 否 | 文档 ID（可选，如果不提供则自动生成） |

**返回：**
- `DocumentInfo`: 文档信息对象

**抛出异常：**
- `ValidationError`: 文件路径无效
- `DocumentError`: 文档读取或摄入失败
- `ConfigError`: 客户端未初始化

**示例：**

```python
# 摄入单个文件
doc_info = await client.ingest_document("medical_report.txt")
print(f"文档 ID: {doc_info.doc_id}")
print(f"状态: {doc_info.status}")
print(f"实体数: {doc_info.entities_count}")

# 指定文档 ID
doc_info = await client.ingest_document(
    "report.txt",
    doc_id="custom-doc-id"
)
```

---

#### `async def ingest_text(self, text: str, doc_id: Optional[str] = None) -> DocumentInfo`

摄入文本到知识图谱。适合处理程序生成的文本或 API 获取的文本内容。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `text` | str | 是 | 文本内容 |
| `doc_id` | Optional[str] | 否 | 文档 ID（可选） |

**返回：**
- `DocumentInfo`: 文档信息对象

**示例：**

```python
text = """
糖尿病是一种慢性代谢性疾病，特征是血糖水平升高。
主要症状包括多饮、多尿、多食和体重下降。
"""

doc_info = await client.ingest_text(text, doc_id="text-001")
print(f"摄入成功: {doc_info.doc_id}")
```

---

#### `async def ingest_batch(self, file_paths: List[str], doc_ids: Optional[List[str]] = None, max_concurrency: int = 5, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> BatchIngestResult`

批量摄入文档到知识图谱。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `file_paths` | List[str] | 是 | 文档文件路径列表 |
| `doc_ids` | Optional[List[str]] | 否 | 文档 ID 列表（长度必须与 file_paths 一致） |
| `max_concurrency` | int | 否 | 最大并发数（默认 5） |
| `progress_callback` | Optional[Callable] | 否 | 进度回调函数 |

**返回：**
- `BatchIngestResult`: 批量摄入结果

**示例：**

```python
# 基本批量摄入
result = await client.ingest_batch([
    "doc1.txt",
    "doc2.txt",
    "doc3.txt"
])
print(f"完成: {result.succeeded}/{result.total}")

# 带进度回调
def on_progress(current, total, doc_id):
    print(f"进度: {current}/{total} - {doc_id}")

result = await client.ingest_batch(
    file_paths=["doc1.txt", "doc2.txt"],
    progress_callback=on_progress
)

# 指定文档 ID
result = await client.ingest_batch(
    file_paths=["doc1.txt", "doc2.txt"],
    doc_ids=["custom-id-1", "custom-id-2"],
    max_concurrency=3
)
```

---

#### `async def ingest_multimodal(self, content_list: List[Dict[str, Any]], file_path: Optional[str] = None) -> DocumentInfo`

摄入多模态内容（文本、图片、表格等）。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `content_list` | List[Dict[str, Any]] | 是 | 内容列表，每个元素是包含 content_type 和 content 的字典 |
| `file_path` | Optional[str] | 否 | 源文件路径（可选） |

**返回：**
- `DocumentInfo`: 文档信息对象

**示例：**

```python
# 多模态内容
contents = [
    {
        "content_type": "text",
        "content": "患者胸部 X 光片显示左下肺有阴影"
    },
    {
        "content_type": "image",
        "content": "base64_encoded_image_data..."
    }
]

doc_info = await client.ingest_multimodal(contents)
print(f"多模态摄入成功: {doc_info.doc_id}")
```

---

#### `async def delete_document(self, doc_id: str) -> bool`

从知识图谱中删除文档。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `doc_id` | str | 是 | 文档 ID |

**返回：**
- `bool`: 是否删除成功

**示例：**

```python
success = await client.delete_document("doc-123")
if success:
    print("文档删除成功")
```

---

### 查询方法

#### `async def query(self, query_text: str, mode: str = "hybrid", graph_id: str = "default", **kwargs) -> QueryResult`

执行知识图谱查询。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `query_text` | str | 是 | 查询问题 |
| `mode` | str | 否 | 查询模式（默认 "hybrid"） |
| `graph_id` | str | 否 | 图谱 ID（默认 "default"） |
| `**kwargs` | - | 否 | 额外的查询参数 |

**查询模式：**

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| `naive` | 直接使用 LLM（不使用知识图谱） | 简单问答、快速响应 |
| `local` | 仅使用局部上下文（实体邻居） | 实体关系查询 |
| `global` | 仅使用全局上下文（社区摘要） | 全局概览、主题分类 |
| `hybrid` | 结合局部和全局（推荐） | 复杂推理、综合分析 |
| `mix` | 混合模式，动态调整策略 | 不确定场景 |
| `bypass` | 绕过图谱，直接检索原始文档 | 文档检索 |

**返回：**
- `QueryResult`: 查询结果对象

**示例：**

```python
# 基本查询（使用 hybrid 模式）
result = await client.query("什么是糖尿病?")
print(result.answer)

# 指定查询模式
result = await client.query(
    "糖尿病和高血压有什么关系?",
    mode="local"
)

# 带额外参数
result = await client.query(
    "糖尿病的症状",
    mode="hybrid",
    top_k=10,
    max_entity_tokens=2000
)

# 访问结果详情
print(f"查询: {result.query}")
print(f"答案: {result.answer}")
print(f"模式: {result.mode}")
print(f"图谱 ID: {result.graph_id}")
print(f"检索次数: {result.retrieval_count}")
print(f"延迟: {result.latency_ms}ms")
print(f"来源数量: {len(result.sources)}")
```

---

#### `async def query_stream(self, query_text: str, mode: str = "hybrid", graph_id: str = "default", **kwargs) -> AsyncIterator[str]`

流式查询知识图谱。逐块返回生成的答案，适合长文本或实时响应场景。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `query_text` | str | 是 | 查询问题 |
| `mode` | str | 否 | 查询模式 |
| `graph_id` | str | 否 | 图谱 ID |
| `**kwargs` | - | 否 | 额外的查询参数 |

**返回：**
- `AsyncIterator[str]`: 流式答案片段

**示例：**

```python
# 流式查询
async for chunk in client.query_stream("详细说明糖尿病的病因"):
    print(chunk, end="", flush=True)

# 处理流式结果
full_answer = ""
async for chunk in client.query_stream("长问题..."):
    full_answer += chunk
    # 实时处理或显示
```

---

### 图谱管理方法

#### `async def list_graphs(self) -> List[GraphInfo]`

列出所有图谱。

**返回：**
- `List[GraphInfo]`: 图谱信息列表

**示例：**

```python
graphs = await client.list_graphs()
for graph in graphs:
    print(f"{graph.graph_id}: {graph.entity_count} 实体")
```

---

#### `async def get_graph(self, graph_id: str) -> GraphInfo`

获取图谱详情。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |

**返回：**
- `GraphInfo`: 图谱信息对象

**示例：**

```python
info = await client.get_graph("medical")
print(f"实体数: {info.entity_count}")
print(f"关系数: {info.relationship_count}")
print(f"文档数: {info.document_count}")
```

---

#### `async def delete_graph(self, graph_id: str, confirm: bool = False) -> bool`

删除图谱。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |
| `confirm` | bool | 否 | 是否确认删除（安全措施） |

**返回：**
- `bool`: 是否成功删除

**示例：**

```python
# 删除图谱（需要确认）
success = await client.delete_graph("test", confirm=True)
```

---

#### `async def export_graph(self, graph_id: str, output_path: str, format: str = "json") -> None`

导出图谱。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |
| `output_path` | str | 是 | 输出文件路径 |
| `format` | str | 否 | 导出格式（json, csv, mermaid） |

**示例：**

```python
# 导出为 JSON
await client.export_graph("medical", "output.json", "json")

# 导出为 CSV
await client.export_graph("medical", "output.csv", "csv")

# 导出为 Mermaid
await client.export_graph("medical", "output.mmd", "mermaid")
```

---

#### `async def merge_graph_nodes(self, graph_id: str, source_entities: List[str], target_entity: str, threshold: float = 0.7, merge_strategy: Optional[Dict[str, str]] = None) -> int`

合并知识图谱中的相似节点。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |
| `source_entities` | List[str] | 是 | 源实体列表（要合并的实体） |
| `target_entity` | str | 是 | 目标实体（合并后的实体名称） |
| `threshold` | float | 否 | 相似度阈值（0-1），默认 0.7 |
| `merge_strategy` | Optional[Dict[str, str]] | 否 | 合并策略字典 |

**合并策略：**

```python
merge_strategy = {
    "description": "concatenate",  # concatenate | keep_first | keep_latest
    "entity_type": "keep_first",   # keep_first | majority
    "source_id": "join_unique"     # join_unique | join_all
}
```

**返回：**
- `int`: 合并的节点数量

**示例：**

```python
# 基本合并
count = await client.merge_graph_nodes(
    "medical",
    ["糖尿病", "糖尿病 mellitus", "DM"],
    "糖尿病"
)
print(f"合并了 {count} 个节点")

# 自定义合并策略
count = await client.merge_graph_nodes(
    "medical",
    ["高血压", "Hypertension", "BP"],
    "高血压病",
    threshold=0.8,
    merge_strategy={
        "description": "concatenate",
        "entity_type": "keep_first",
        "source_id": "join_unique"
    }
)
```

---

#### `async def find_similar_entities(self, graph_id: str, entity_name: str, threshold: float = 0.7, top_k: int = 10) -> List[Dict[str, Any]]`

查找与指定实体相似的实体。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |
| `entity_name` | str | 是 | 参考实体名称 |
| `threshold` | float | 否 | 相似度阈值（0-1），默认 0.7 |
| `top_k` | int | 否 | 返回的最大相似实体数量，默认 10 |

**返回：**
- `List[Dict[str, Any]]`: 相似实体列表

**示例：**

```python
similar = await client.find_similar_entities(
    "medical",
    "糖尿病",
    threshold=0.7,
    top_k=5
)
for entity in similar:
    print(f"{entity['entity_name']}: {entity['similarity']:.2f}")
```

---

#### `async def auto_merge_similar_entities(self, graph_id: str, entity_type: Optional[str] = None, threshold: float = 0.85, merge_strategy: Optional[Dict[str, str]] = None, dry_run: bool = False) -> Dict[str, Any]`

自动合并相似实体。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `graph_id` | str | 是 | 图谱 ID |
| `entity_type` | Optional[str] | 否 | 实体类型过滤（可选），如 "DISEASE", "MEDICINE" |
| `threshold` | float | 否 | 相似度阈值（0-1），默认 0.85 |
| `merge_strategy` | Optional[Dict[str, str]] | 否 | 合并策略 |
| `dry_run` | bool | 否 | 是否为试运行模式 |

**返回：**
- `Dict[str, Any]`: 合并结果摘要

**示例：**

```python
# 先试运行，查看将要合并的实体
result = await client.auto_merge_similar_entities(
    "medical",
    entity_type="DISEASE",
    threshold=0.9,
    dry_run=True
)
print(f"将合并 {result['merged_count']} 对实体")

# 确认后执行实际合并
result = await client.auto_merge_similar_entities(
    "medical",
    entity_type="DISEASE",
    threshold=0.9,
    dry_run=False
)
print(f"成功合并 {result['merged_count']} 对实体")
```

---

### 性能监控方法

#### `def get_stats(self) -> Dict[str, Any]`

获取性能统计信息。

**返回：**
- `Dict[str, Any]`: 包含性能指标的字典

**性能指标：**

| 指标 | 描述 |
|------|------|
| `metrics_enabled` | 是否启用指标收集 |
| `total_queries` | 总查询次数 |
| `total_documents` | 总文档数 |
| `avg_latency_ms` | 平均查询延迟 |
| `p50_latency_ms` | 中位数延迟（P50） |
| `p95_latency_ms` | P95 延迟 |
| `p99_latency_ms` | P99 延迟 |
| `queries_by_mode` | 各模式查询次数 |
| `errors` | 错误次数 |
| `error_rate` | 错误率 |

**示例：**

```python
stats = client.get_stats()
print(f"查询次数: {stats['total_queries']}")
print(f"平均延迟: {stats['avg_latency_ms']}ms")
print(f"P95 延迟: {stats['p95_latency_ms']}ms")
print(f"错误率: {stats['error_rate']:.2%}")
```

---

#### `def reset_stats(self) -> None`

重置性能统计。

**示例：**

```python
client.reset_stats()
print("性能统计已重置")
```

---

#### `def get_performance_summary(self) -> str`

获取性能摘要（用于日志输出）。

**返回：**
- `str`: 格式化的性能摘要字符串

**示例：**

```python
summary = client.get_performance_summary()
print(summary)
# 输出类似：
# 查询次数: 100, 平均延迟: 250ms, P95: 450ms, 错误率: 2%
```

---

### 配置管理方法

#### `@classmethod def from_env(cls, workspace: str = "medical", log_level: str = "INFO", enable_metrics: bool = True) -> MedGraphClient`

从环境变量创建客户端。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `workspace` | str | 否 | 工作空间名称 |
| `log_level` | str | 否 | 日志级别 |
| `enable_metrics` | bool | 否 | 是否启用性能监控 |

**返回：**
- `MedGraphClient`: 客户端实例

**示例：**

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["NEO4J_URI"] = "neo4j://localhost:7687"

client = MedGraphClient.from_env()
async with client:
    result = await client.query("测试")
```

---

#### `@classmethod def from_config(cls, config_path: str, workspace: Optional[str] = None, log_level: str = "INFO", enable_metrics: bool = True) -> MedGraphClient`

从配置文件创建客户端。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `config_path` | str | 是 | 配置文件路径（支持 .json, .yaml, .yml） |
| `workspace` | Optional[str] | 否 | 工作空间名称（可选，覆盖配置文件中的值） |
| `log_level` | str | 否 | 日志级别 |
| `enable_metrics` | bool | 否 | 是否启用性能监控 |

**返回：**
- `MedGraphClient`: 客户端实例

**示例：**

```python
# config.yaml
# workspace: "medical"
# openai_api_key: "sk-..."
# neo4j_uri: "neo4j://localhost:7687"

client = MedGraphClient.from_config("config.yaml")
async with client:
    result = await client.query("测试")
```

---

### 便捷方法

#### `async def ingest_and_query(self, text: str, query_text: str, mode: str = "hybrid") -> QueryResult`

便捷方法：摄入文本后立即查询。适合快速测试和单文档场景。

**参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `text` | str | 是 | 要摄入的文本 |
| `query_text` | str | 是 | 查询问题 |
| `mode` | str | 否 | 查询模式 |

**返回：**
- `QueryResult`: 查询结果

**示例：**

```python
text = "糖尿病是一种慢性代谢性疾病，特征是血糖水平升高..."
result = await client.ingest_and_query(
    text,
    "什么是糖尿病?"
)
print(result.answer)
```

---

## 类型定义

### `QueryMode` 枚举

查询模式枚举。

| 值 | 描述 |
|-----|------|
| `NAIVE` | 简单检索，直接返回相关内容 |
| `LOCAL` | 局部社区检索，关注实体局部关系 |
| `GLOBAL` | 全局社区检索，关注图谱全局结构 |
| `HYBRID` | 混合检索，结合局部和全局优势 |
| `MIX` | 混合模式，动态调整检索策略 |
| `BYPASS` | 绕过图谱，直接检索原始文档 |

---

### `SourceInfo` 类

来源信息对象。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `doc_id` | str | 文档 ID |
| `chunk_id` | str | 内容块 ID |
| `content` | str | 内容片段 |
| `relevance` | float | 相关性评分（0-1） |

**方法：**

- `to_dict() -> Dict[str, Any]`: 转换为字典
- `to_json() -> str`: 转换为 JSON 字符串
- `from_dict(data: Dict[str, Any]) -> SourceInfo`: 从字典创建实例

---

### `GraphContext` 类

图谱上下文对象。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `entities` | List[str] | 实体列表 |
| `relationships` | List[str] | 关系列表 |
| `communities` | List[str] | 社区列表 |

---

### `QueryResult` 类

查询结果对象。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `query` | str | 查询文本 |
| `answer` | str | 生成的答案 |
| `mode` | QueryMode | 查询模式 |
| `graph_id` | str | 图谱 ID |
| `sources` | List[SourceInfo] | 来源列表 |
| `context` | List[str] | 上下文列表 |
| `graph_context` | Optional[GraphContext] | 图谱上下文 |
| `retrieval_count` | int | 检索次数 |
| `latency_ms` | int | 查询延迟（毫秒） |

---

### `DocumentInfo` 类

文档信息对象。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `doc_id` | str | 文档 ID |
| `file_name` | str | 文件名 |
| `file_path` | str | 文件路径 |
| `status` | str | 文档状态（pending, processing, completed, failed） |
| `entity_count` | int | 提取的实体数量 |
| `relationship_count` | int | 提取的关系数量 |
| `created_at` | str | 创建时间（ISO 8601） |
| `updated_at` | Optional[str] | 更新时间（ISO 8601） |

---

### `GraphInfo` 类

图谱信息对象。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `graph_id` | str | 图谱 ID |
| `workspace` | str | 工作空间名称 |
| `entity_count` | int | 实体总数 |
| `relationship_count` | int | 关系总数 |
| `document_count` | int | 文档总数 |
| `created_at` | str | 创建时间 |
| `updated_at` | Optional[str] | 更新时间 |

---

### `GraphConfig` 类

图谱配置对象。

**属性：**

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `workspace` | str | "medical" | 工作空间名称 |
| `chunk_size` | int | 512 | 文本块大小（字符数） |
| `overlap` | int | 50 | 文本块重叠大小 |
| `entity_types` | List[str] | [...] | 医学实体类型列表 |

**默认实体类型：**

```python
[
    "DISEASE",
    "MEDICINE",
    "SYMPTOM",
    "ANATOMICAL_STRUCTURE",
    "BODY_FUNCTION",
    "LABORATORY_DATA",
    "PROCEDURE",
]
```

---

## 异常处理

### 异常层次结构

```
MedGraphSDKError
├── ConfigError
├── DocumentNotFoundError
├── ConnectionError
├── ValidationError
├── QueryTimeoutError
└── RateLimitError
```

### 异常类

#### `MedGraphSDKError`

SDK 基础异常类。所有 SDK 异常的基类。

**属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `message` | str | 错误消息 |
| `error_code` | str | 错误码 |
| `details` | Dict[str, Any] | 错误详情字典 |

**方法：**

- `to_dict() -> Dict[str, Any]`: 转换为字典格式

**示例：**

```python
try:
    async with MedGraphClient() as client:
        result = await client.query("测试")
except MedGraphSDKError as e:
    error_dict = e.to_dict()
    print(f"错误类型: {error_dict['error_type']}")
    print(f"错误码: {error_dict['error_code']}")
    print(f"错误消息: {error_dict['message']}")
```

---

#### `ConfigError`

配置相关错误。当 SDK 配置缺失、无效或无法加载时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `config_key` | Optional[str] | 相关的配置键 |
| `config_file` | Optional[str] | 配置文件路径 |

**示例：**

```python
try:
    client = MedGraphClient.from_config("missing.yaml")
except ConfigError as e:
    print(f"配置错误: {e.message}")
    print(f"配置文件: {e.config_file}")
```

---

#### `DocumentNotFoundError`

文档未找到错误。当尝试访问不存在的文档时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `doc_id` | Optional[str] | 文档 ID |

**示例：**

```python
try:
    await client.delete_document("non-existent-doc")
except DocumentNotFoundError as e:
    print(f"文档未找到: {e.doc_id}")
```

---

#### `ConnectionError`

连接错误。当无法连接到 Neo4j、Milvus 或其他服务时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `service` | Optional[str] | 服务名称（neo4j, milvus 等） |
| `uri` | Optional[str] | 连接 URI（脱敏） |

**示例：**

```python
try:
    async with MedGraphClient() as client:
        result = await client.query("测试")
except ConnectionError as e:
    print(f"连接失败: {e.service}")
    print(f"URI: {e.uri}")  # 脱敏后的 URI
```

---

#### `ValidationError`

数据验证错误。当输入数据不符合要求时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `field` | Optional[str] | 字段名称 |
| `value` | Optional[Any] | 实际值 |
| `constraint` | Optional[str] | 约束描述 |

**示例：**

```python
try:
    await client.query("", mode="invalid")
except ValidationError as e:
    print(f"验证失败: {e.message}")
    print(f"字段: {e.field}")
    print(f"值: {e.value}")
    print(f"约束: {e.constraint}")
```

---

#### `QueryTimeoutError`

查询超时错误。当查询执行时间超过限制时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `timeout_seconds` | Optional[float] | 超时时间（秒） |
| `query` | Optional[str] | 查询文本 |

**示例：**

```python
try:
    await client.query("非常复杂的问题...")
except QueryTimeoutError as e:
    print(f"查询超时: {e.timeout_seconds}秒")
    print(f"查询: {e.query}")
```

---

#### `RateLimitError`

速率限制错误。当请求超过 API 速率限制时抛出。

**额外属性：**

| 属性 | 类型 | 描述 |
|------|------|------|
| `limit` | Optional[int] | 限制次数 |
| `window` | Optional[int] | 时间窗口（秒） |
| `retry_after` | Optional[int] | 重试等待时间（秒） |

**示例：**

```python
try:
    await client.query("测试")
except RateLimitError as e:
    print(f"速率限制: {e.limit} 次 / {e.window} 秒")
    print(f"请 {e.retry_after} 秒后重试")
```

---

## 完整示例

### 示例 1：完整的文档摄入和查询流程

```python
import asyncio
from src.sdk import MedGraphClient
from src.sdk.exceptions import (
    ConfigError,
    DocumentNotFoundError,
    ValidationError,
)

async def main():
    try:
        # 初始化客户端
        async with MedGraphClient(
            workspace="medical",
            log_level="INFO"
        ) as client:

            # 1. 摄入文档
            print("=== 摄入文档 ===")
            doc_files = [
                "docs/diabetes.txt",
                "docs/hypertension.txt",
                "docs/cardiology.txt"
            ]

            for file_path in doc_files:
                doc_info = await client.ingest_document(file_path)
                print(f"✓ {file_path}")
                print(f"  ID: {doc_info.doc_id}")
                print(f"  状态: {doc_info.status}")
                print(f"  实体数: {doc_info.entities_count}")

            # 2. 查询知识图谱
            print("\n=== 查询知识图谱 ===")
            questions = [
                "什么是糖尿病?",
                "糖尿病的主要症状有哪些?",
                "糖尿病和高血压有什么关系?"
            ]

            for question in questions:
                result = await client.query(question, mode="hybrid")
                print(f"\n问题: {question}")
                print(f"答案: {result.answer}")
                print(f"模式: {result.mode}")
                print(f"延迟: {result.latency_ms}ms")

            # 3. 获取性能统计
            print("\n=== 性能统计 ===")
            stats = client.get_stats()
            print(f"总查询次数: {stats['total_queries']}")
            print(f"平均延迟: {stats['avg_latency_ms']:.2f}ms")
            print(f"P95 延迟: {stats['p95_latency_ms']:.2f}ms")

    except ConfigError as e:
        print(f"配置错误: {e}")
    except DocumentNotFoundError as e:
        print(f"文档未找到: {e.doc_id}")
    except ValidationError as e:
        print(f"验证错误: {e.message}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 示例 2：图谱节点合并

```python
import asyncio
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient() as client:

        # 1. 查找相似实体
        print("=== 查找相似实体 ===")
        similar = await client.find_similar_entities(
            graph_id="medical",
            entity_name="糖尿病",
            threshold=0.7,
            top_k=5
        )

        for entity in similar:
            print(f"{entity['entity_name']}: {entity['similarity']:.2f}")

        # 2. 合并相似节点
        print("\n=== 合并相似节点 ===")
        merged_count = await client.merge_graph_nodes(
            graph_id="medical",
            source_entities=["糖尿病", "糖尿病 mellitus", "DM"],
            target_entity="糖尿病",
            threshold=0.7,
            merge_strategy={
                "description": "concatenate",
                "entity_type": "keep_first",
                "source_id": "join_unique"
            }
        )
        print(f"合并了 {merged_count} 个节点")

        # 3. 自动合并（先试运行）
        print("\n=== 自动合并（试运行） ===")
        result = await client.auto_merge_similar_entities(
            graph_id="medical",
            entity_type="DISEASE",
            threshold=0.9,
            dry_run=True
        )
        print(f"将合并 {result['merged_count']} 对实体")

        for merge in result['merged_entities']:
            print(f"  {merge['target_entity']} <- {merge['source_entities']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 示例 3：多模态查询

```python
import asyncio
import base64
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient() as client:

        # 1. 读取图像文件
        with open("xray.jpg", "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # 2. 摄入多模态内容
        contents = [
            {
                "content_type": "text",
                "content": "患者胸部 X 光片显示左下肺有阴影"
            },
            {
                "content_type": "image",
                "content": image_data
            }
        ]

        doc_info = await client.ingest_multimodal(contents)
        print(f"多模态摄入成功: {doc_info.doc_id}")

        # 3. 查询
        result = await client.query(
            "X 光片显示了什么异常?",
            mode="hybrid"
        )
        print(f"答案: {result.answer}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 示例 4：流式查询

```python
import asyncio
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient() as client:

        question = "请详细说明糖尿病的病因、症状、诊断和治疗方案"

        print(f"问题: {question}\n")
        print("答案: ", end="", flush=True)

        # 流式查询
        async for chunk in client.query_stream(question):
            print(chunk, end="", flush=True)

        print()  # 换行

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 示例 5：批量摄入和进度跟踪

```python
import asyncio
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient() as client:

        # 定义进度回调
        def on_progress(current: int, total: int, doc_id: str):
            percentage = (current / total) * 100
            print(f"进度: {current}/{total} ({percentage:.1f}%) - {doc_id}")

        # 批量摄入
        files = [
            f"docs/doc_{i}.txt" for i in range(1, 11)
        ]

        result = await client.ingest_batch(
            file_paths=files,
            max_concurrency=3,
            progress_callback=on_progress
        )

        print(f"\n完成: {result.succeeded}/{result.total}")
        print(f"失败: {result.failed}")

        if result.errors:
            print("\n错误列表:")
            for error in result.errors:
                print(f"  - {error['doc_id']}: {error['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 示例 6：图谱导出和可视化

```python
import asyncio
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient() as client:

        graph_id = "medical"

        # 1. 导出为 JSON
        print("=== 导出为 JSON ===")
        await client.export_graph(graph_id, "output.json", "json")
        print("✓ output.json")

        # 2. 导出为 CSV
        print("\n=== 导出为 CSV ===")
        await client.export_graph(graph_id, "output.csv", "csv")
        print("✓ output.csv")

        # 3. 导出为 Mermaid
        print("\n=== 导出为 Mermaid ===")
        await client.export_graph(graph_id, "output.mmd", "mermaid")
        print("✓ output.mmd")

        # 4. 读取并显示 Mermaid 内容
        with open("output.mmd", "r") as f:
            mermaid_content = f.read()
        print("\nMermaid 图表:")
        print(mermaid_content[:500] + "...")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 最佳实践

### 1. 使用异步上下文管理器

```python
# ✓ 推荐：使用 async with
async with MedGraphClient() as client:
    result = await client.query("问题")

# ✗ 不推荐：手动管理（容易出错）
client = MedGraphClient()
await client.initialize()
# ... 如果这里抛出异常，close() 不会被调用
await client.close()
```

### 2. 合理使用工作空间

```python
# 为不同的数据集使用不同的工作空间
async with MedGraphClient(workspace="dataset_a") as client_a:
    # 处理数据集 A
    pass

async with MedGraphClient(workspace="dataset_b") as client_b:
    # 处理数据集 B
    pass
```

### 3. 批量操作优化

```python
# ✓ 推荐：批量摄入
result = await client.ingest_batch([
    "doc1.txt",
    "doc2.txt",
    "doc3.txt"
])

# ✗ 不推荐：逐个摄入
for file in ["doc1.txt", "doc2.txt", "doc3.txt"]:
    await client.ingest_document(file)  # 效率较低
```

### 4. 选择合适的查询模式

```python
# 简单问题：使用 naive（快速）
result = await client.query("简单问题", mode="naive")

# 复杂推理：使用 hybrid（准确）
result = await client.query("复杂问题", mode="hybrid")

# 实体关系：使用 local（关注局部）
result = await client.query("实体关系", mode="local")
```

### 5. 错误处理

```python
from src.sdk.exceptions import (
    ConfigError,
    DocumentNotFoundError,
    ValidationError,
    ConnectionError,
)

try:
    async with MedGraphClient() as client:
        result = await client.query("问题")
except ConfigError as e:
    print(f"配置错误: {e}")
    print(f"配置键: {e.config_key}")
except DocumentNotFoundError as e:
    print(f"文档未找到: {e.doc_id}")
except ValidationError as e:
    print(f"验证错误: {e.message}")
    print(f"字段: {e.field}")
except ConnectionError as e:
    print(f"连接失败: {e.service}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 6. 性能监控

```python
async with MedGraphClient(enable_metrics=True) as client:
    # 执行操作
    await client.query("问题1")
    await client.query("问题2")
    await client.query("问题3")

    # 获取性能统计
    stats = client.get_stats()
    print(f"平均延迟: {stats['avg_latency_ms']:.2f}ms")
    print(f"P95 延迟: {stats['p95_latency_ms']:.2f}ms")
    print(f"错误率: {stats['error_rate']:.2%}")
```

### 7. 使用流式查询处理长答案

```python
# 长答案使用流式查询
async for chunk in client.query_stream("详细说明..."):
    print(chunk, end="", flush=True)
```

---

## 常见问题

### Q: 如何处理初始化超时？

A: 检查 Neo4j 和 Milvus 是否正常运行，网络连接是否稳定。

```python
try:
    async with MedGraphClient() as client:
        result = await client.query("测试")
except Exception as e:
    if "timeout" in str(e).lower():
        print("初始化超时，请检查:")
        print("1. Neo4j 是否正常运行")
        print("2. Milvus 是否正常运行")
        print("3. 网络连接是否稳定")
```

### Q: 如何提高查询速度？

A:
1. 使用 `naive` 模式（最快，但不使用知识图谱）
2. 减少 `top_k` 参数
3. 限制 `max_entity_tokens`
4. 使用流式查询改善用户体验

### Q: 如何处理大量文档？

A: 使用批量摄入，并控制并发数。

```python
result = await client.ingest_batch(
    file_paths=large_file_list,
    max_concurrency=5,  # 控制并发数
    progress_callback=on_progress
)
```

### Q: 如何导出图谱数据？

A: 使用 `export_graph` 方法。

```python
# 导出为 JSON
await client.export_graph("medical", "output.json", "json")

# 导出为 CSV
await client.export_graph("medical", "output.csv", "csv")

# 导出为 Mermaid（用于可视化）
await client.export_graph("medical", "output.mmd", "mermaid")
```

---

## 更多资源

- **GitHub 仓库**: [https://github.com/your-org/Medical-Graph-RAG](https://github.com/your-org/Medical-Graph-RAG)
- **API 文档**: [https://docs.medical-graph-rag.com](https://docs.medical-graph-rag.com)
- **示例代码**: [examples/](https://github.com/your-org/Medical-Graph-RAG/tree/main/examples)
- **问题反馈**: [https://github.com/your-org/Medical-Graph-RAG/issues](https://github.com/your-org/Medical-Graph-RAG/issues)

---

**版本**: 1.0.0
**更新日期**: 2026-01-11
**许可证**: MIT
