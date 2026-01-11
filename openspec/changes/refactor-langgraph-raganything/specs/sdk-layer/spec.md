# SDK 层规范

**依赖版本**：
- **LightRAG**: >= 1.4.9
  - **Context7 Library ID**: `/hkuds/lightrag`
  - **Benchmark Score**: 81.6/100
  - **⚠️ 关键 API 变更**: 必须在首次使用前调用 `initialize_storages()` 和 `initialize_pipeline_status()`
- **LangGraph**: >= 1.0.3
  - **Context7 Library ID**: `/langchain-ai/langgraph`
  - **Benchmark Score**: 88.5/100

## 新增需求

### 需求：Python SDK 客户端

系统**必须**提供类型安全、易用的 Python SDK，作为 CLI 和 REST API 的统一基础。

#### 场景：初始化 SDK 客户端

**给定**：
- 已安装 Medical Graph RAG SDK
- 配置了 Neo4j 和 Milvus 连接信息

**当**：创建 `MedGraphClient` 实例

**那么**：应成功初始化客户端，配置所有必需的服务

**验证**：
```python
from medgraph import MedGraphClient

client = MedGraphClient(
    workspace="medical-knowledge",
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    milvus_uri="http://localhost:19530",
    openai_api_key="sk-...",
)

assert client.workspace == "medical-knowledge"
assert client._adapter is not None
assert client._query_service is not None
assert client._graph_service is not None
```

**注意**：
- SDK 客户端会在首次调用任何方法时自动执行 LightRAG 1.4.9+ 所需的初始化
- 初始化过程包括调用 `initialize_storages()` 和 `initialize_pipeline_status()`
- 初始化是异步的，只会在首次调用时执行一次

---

#### 场景：摄入单个文档

**给定**：
- 已初始化的 SDK 客户端
- 一个 PDF 文档路径

**当**：调用 `client.ingest_document()`

**那么**：
- 应将文档添加到知识图谱
- 应返回 `DocumentInfo` 对象
- 应包含文档 ID、状态、实体数量等信息

**验证**：
```python
import asyncio

async def test_ingest_document():
    client = MedGraphClient(...)
    doc_info = await client.ingest_document(
        file_path="medical_paper.pdf",
        graph_id="graph-001",
        chunk_size=512,
        overlap=50,
    )

    assert doc_info.doc_id is not None
    assert doc_info.status == "completed"
    assert doc_info.entity_count > 0
    assert doc_info.file_name == "medical_paper.pdf"
```

---

#### 场景：批量摄入文档

**给定**：
- 多个文档路径
- 已初始化的 SDK 客户端

**当**：调用 `client.ingest_documents()`

**那么**：
- 应依次处理所有文档
- 应返回所有文档的 `DocumentInfo` 列表
- 应支持进度显示

**验证**：
```python
async def test_ingest_documents():
    client = MedGraphClient(...)
    file_paths = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

    results = await client.ingest_documents(
        file_paths=file_paths,
        graph_id="graph-001",
        show_progress=True,
    )

    assert len(results) == 3
    assert all(r.status == "completed" for r in results)
    assert sum(r.entity_count for r in results) > 0
```

---

#### 场景：执行查询

**给定**：
- 已初始化的 SDK 客户端
- 构建好的知识图谱
- 一个查询问题

**当**：调用 `client.query()`

**那么**：
- 应使用指定的检索模式执行查询
- 应返回 `QueryResult` 对象
- 应包含答案、来源、上下文等信息

**查询模式说明**：
- SDK 提供 6 种检索模式：naive, local, global, hybrid, mix, bypass
- 通过 `mode` 参数选择检索模式
- 默认使用 `hybrid` 模式

**简单查询 vs 智能查询**：
- **简单查询**：直接调用 RAG-Anything 适配器，执行检索
- **智能查询**：使用 LangGraph 工作流，包含查询分析、检索、评估、优化等步骤
- SDK 的 `query()` 方法默认使用简单查询（直接调用适配器）
- 如需使用智能查询，可通过参数指定（未来扩展）

**验证**：
```python
from medgraph.types import QueryMode

async def test_query():
    client = MedGraphClient(...)
    result = await client.query(
        query="糖尿病患者的主要症状是什么？",
        mode=QueryMode.HYBRID,
        graph_id="graph-001",
        top_k=10,
    )

    assert result.query == "糖尿病患者的主要症状是什么？"
    assert result.answer is not None
    assert len(result.answer) > 0
    assert len(result.sources) > 0
    # sources 是 SourceInfo 对象数组
    assert result.sources[0].doc_id is not None
    assert result.sources[0].relevance > 0
    assert result.graph_context is not None
    assert result.mode == QueryMode.HYBRID
    assert result.graph_id == "graph-001"
    assert result.latency_ms > 0
```

---

#### 场景：列出所有图谱

**给定**：
- 已初始化的 SDK 客户端
- 工作空间中有多个图谱

**当**：调用 `client.list_graphs()`

**那么**：
- 应返回所有图谱的 `GraphInfo` 列表
- 应包含图谱 ID、实体数、关系数等信息

**验证**：
```python
async def test_list_graphs():
    client = MedGraphClient(workspace="medical")
    graphs = await client.list_graphs()

    assert isinstance(graphs, list)
    assert len(graphs) > 0

    for graph in graphs:
        assert graph.workspace == "medical"
        assert graph.entity_count >= 0
        assert graph.relationship_count >= 0
        assert graph.graph_id is not None
```

---

#### 场景：导出图谱

**给定**：
- 已初始化的 SDK 客户端
- 一个图谱 ID
- 输出路径

**当**：调用 `client.export_graph()`

**那么**：
- 应将图谱数据导出到指定路径
- 应支持 JSON、CSV、Mermaid 格式

**验证**：
```python
async def test_export_graph():
    client = MedGraphClient(...)
    await client.export_graph(
        graph_id="graph-001",
        output_path="graph_export.json",
        format="json",
    )

    # 验证文件存在
    import os
    assert os.path.exists("graph_export.json")

    # 验证内容
    import json
    with open("graph_export.json") as f:
        data = json.load(f)
    assert "nodes" in data or "entities" in data
```

---

#### 场景：合并图谱节点

**给定**：
- 已初始化的 SDK 客户端
- 一个图谱 ID
- 相似度阈值

**当**：调用 `client.merge_graph_nodes()`

**那么**：
- 应查找相似度高于阈值的节点
- 应合并这些节点
- 应返回合并的节点数量

**验证**：
```python
async def test_merge_graph_nodes():
    client = MedGraphClient(...)
    merged_count = await client.merge_graph_nodes(
        graph_id="graph-001",
        threshold=0.7,
    )

    assert merged_count >= 0
    assert isinstance(merged_count, int)
```

---

#### 场景：三层图谱关联

**给定**：
- 三个图谱 ID（顶层、中层、底层）
- 已初始化的 SDK 客户端

**当**：调用 `client.link_trinity_graphs()`

**那么**：
- 应在三个图谱之间创建 REFERENCE 关系
- 应基于实体相似度建立关联
- 应返回创建的关联数量

**实现细节**：
- `link_trinity_graphs()` 调用 `_graph_service.link_trinity()` 方法
- `TrinityLinker` 类负责查找跨图层的相似实体
- 使用实体嵌入向量计算相似度
- 相似度超过阈值时创建 REFERENCE 关系
- 关系方向：顶层 → 中层 → 底层

**三层图谱定义**：
- **顶层图**（Top Layer）：患者数据、临床记录
- **中层图**（Middle Layer）：医学文献、临床指南
- **底层图**（Bottom Layer）：医学词典、基础医学知识

**验证**：
```python
async def test_link_trinity_graphs():
    client = MedGraphClient(...)
    link_count = await client.link_trinity_graphs(
        top_graph_id="patient-data",
        middle_graph_id="medical-literature",
        bottom_graph_id="medical-dictionary",
        similarity_threshold=0.75,
    )

    assert link_count >= 0
    assert isinstance(link_count, int)
```

---

#### 场景：流式查询

**给定**：
- 已初始化的 SDK 客户端
- 一个查询问题

**当**：调用 `client.query(stream=True)`

**那么**：
- 应返回异步迭代器
- 应逐块流式返回答案
- 应支持实时输出

**验证**：
```python
async def test_stream_query():
    client = MedGraphClient(...)
    stream = await client.query(
        query="详细说明糖尿病的病理机制",
        mode=QueryMode.HYBRID,
        stream=True,
    )

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
        print(chunk, end="")

    assert len(chunks) > 0
    full_answer = "".join(chunks)
    assert len(full_answer) > 0
```

---

### 需求：SDK 类型定义

系统**必须**提供完整的类型定义，确保类型安全。

#### 场景：QueryMode 枚举

**给定**：SDK 类型定义

**当**：使用 `QueryMode` 枚举

**那么**：应支持 6 种检索模式

**验证**：
```python
from medgraph.types import QueryMode

assert QueryMode.NAIVE.value == "naive"
assert QueryMode.LOCAL.value == "local"
assert QueryMode.GLOBAL.value == "global"
assert QueryMode.HYBRID.value == "hybrid"
assert QueryMode.MIX.value == "mix"
assert QueryMode.BYPASS.value == "bypass"
```

---

#### 场景：Pydantic 模型验证

**给定**：SDK 类型定义

**当**：创建 Pydantic 模型实例

**那么**：应自动验证字段类型

**验证**：
```python
from medgraph.types import DocumentInfo, QueryResult
from pydantic import ValidationError

import pytest

def test_document_info_validation():
    # 正常情况
    doc = DocumentInfo(
        doc_id="doc-001",
        file_name="paper.pdf",
        file_path="/path/to/paper.pdf",
        status="completed",
        entity_count=100,
        created_at="2024-01-01T00:00:00Z",
    )
    assert doc.doc_id == "doc-001"

    # 缺少必需字段应失败
    with pytest.raises(ValidationError):
        DocumentInfo(
            file_name="paper.pdf",
            # 缺少 doc_id
        )
```

---

### 需求：SDK 异常处理

系统**必须**提供结构化的异常处理机制。

#### 场景：捕获 SDK 异常

**给定**：SDK 操作失败

**当**：抛出异常

**那么**：应使用 SDK 定义的异常类型

**验证**：
```python
import pytest
from medgraph import MedGraphClient
from medgraph.exceptions import DocumentError, QueryError, GraphError

async def test_document_not_found():
    client = MedGraphClient(...)

    with pytest.raises(DocumentError):
        await client.get_document("nonexistent-doc-id")

async def test_invalid_query():
    client = MedGraphClient(...)

    with pytest.raises(QueryError):
        await client.query("")  # 空查询

async def test_graph_not_found():
    client = MedGraphClient(...)

    with pytest.raises(GraphError):
        await client.delete_graph("nonexistent-graph")
```

---

### 需求：SDK LightRAG 初始化

系统**必须**自动处理 LightRAG 1.4.9+ 的初始化要求。

#### 场景：自动初始化

**给定**：
- 已创建 SDK 客户端实例
- 尚未调用任何方法

**当**：首次调用任何 SDK 方法

**那么**：
- 应自动调用 `initialize_storages()`
- 应自动调用 `initialize_pipeline_status()`
- 后续调用不应重复初始化

**实现验证**：
```python
class MedGraphClient:
    def __init__(self, ...):
        self._adapter = RAGAnythingAdapter(...)
        self._initialized = False

    async def _ensure_initialized(self):
        """确保 LightRAG 已初始化 (1.4.9+ 要求)"""
        if not self._initialized:
            await self._adapter._ensure_initialized()
            self._initialized = True

    async def query(self, query: str, ...):
        # 首次调用时自动初始化
        await self._ensure_initialized()
        return await self._query_service.query(...)
```

**验证**：
```python
import pytest

async def test_auto_initialization():
    from medgraph import MedGraphClient

    client = MedGraphClient(...)

    # 首次调用应触发初始化
    result = await client.query("测试查询")

    # 验证初始化已执行
    assert client._initialized == True

    # 后续调用不应重复初始化
    result2 = await client.query("另一个查询")
    # 内部初始化方法应只被调用一次
```

---

### 需求：SDK 配置管理

系统**必须**支持灵活的配置方式。

#### 场景：从环境变量加载配置

**给定**：设置了环境变量

- `MEDGRAPH_WORKSPACE`
- `NEO4J_URI`
- `NEO4J_PASSWORD`
- `MILVUS_URI`
- `OPENAI_API_KEY`

**当**：创建 `MedGraphClient()` 不传参数

**那么**：应自动从环境变量读取配置

**验证**：
```python
import os
os.environ["MEDGRAPH_WORKSPACE"] = "medical"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_PASSWORD"] = "password"
os.environ["MILVUS_URI"] = "http://localhost:19530"
os.environ["OPENAI_API_KEY"] = "sk-..."

client = MedGraphClient()  # 不传参数
assert client.workspace == "medical"
```

---

#### 场景：从配置文件加载

**给定**：一个 YAML 配置文件

**当**：使用 `MedGraphClient.from_config()`

**那么**：应从配置文件加载所有配置

**验证**：
```python
# config.yaml
# workspace: medical
# neo4j:
#   url: bolt://localhost:7687
#   username: neo4j
#   password: password
# milvus:
#   uri: http://localhost:19530

from medgraph import MedGraphClient

client = MedGraphClient.from_config("config.yaml")
assert client.workspace == "medical"
```

---

### 需求：SDK 上下文管理器

系统**必须**支持上下文管理器，确保资源正确释放。

#### 场景：使用 with 语句

**给定**：SDK 客户端支持上下文管理

**当**：使用 `async with` 语句

**那么**：应自动关闭连接和释放资源

**验证**：
```python
async def test_context_manager():
    async with MedGraphClient(...) as client:
        result = await client.query("测试查询")
        assert result is not None

    # 退出上下文后，连接应关闭
    # 可以验证连接状态
```

---

### 需求：SDK 日志和监控

系统**必须**提供结构化的日志输出和监控指标。

#### 场景：启用调试日志

**给定**：SDK 客户端

**当**：设置 `log_level="DEBUG"`

**那么**：应输出详细的调试日志

**验证**：
```python
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)

client = MedGraphClient(
    ...,
    log_level="DEBUG",
)

# 所有 SDK 操作应输出详细日志
result = await client.query("测试查询")
# 日志应包含请求、响应、耗时等信息
```

---

#### 场景：收集性能指标

**给定**：SDK 客户端

**当**：执行操作

**那么**：应记录性能指标（延迟、Token 使用量等）

**验证**：
```python
client = MedGraphClient(...)

result = await client.query("测试查询")

# QueryResult 应包含性能指标
assert result.latency_ms > 0

# 可以从客户端获取统计信息
stats = client.get_stats()
assert stats["total_queries"] > 0
assert stats["total_latency_ms"] > 0
```

---

### 需求：SDK 与 CLI 和 API 的关系

系统**必须**确保 CLI 和 REST API 都基于 SDK 构建。

#### CLI 命令与 SDK 方法映射

| CLI 命令 | SDK 方法 | 说明 |
|---------|---------|------|
| `medgraph build PATH` | `ingest_document()` | 构建知识图谱 = 摄入文档（同一操作的不同命名） |
| `medgraph ingest PATH` | `ingest_document()` | 摄入文档 |
| `medgraph query QUERY` | `query()` | 执行查询 |
| `medgraph serve` | N/A | 启动 API 服务器（使用 SDK 客户端） |
| `medgraph export` | `export_graph()` | 导出图谱 |

**注意**：CLI 的 `build` 和 `ingest` 命令都映射到 SDK 的 `ingest_document()` 方法，两者是同一操作的不同命名约定。

#### 场景：CLI 使用 SDK

**给定**：CLI 命令

**当**：执行 `medgraph query "..."`

**那么**：CLI 应调用 SDK 的 `query()` 方法

**实现验证**：
```python
# src/cli/commands.py
from medgraph import MedGraphClient

async def query_command(query: str, mode: str):
    client = MedGraphClient.from_env()
    result = await client.query(query, mode=mode)
    print(result.answer)
```

---

#### 场景：API 使用 SDK

**给定**：REST API 端点

**当**：调用 `POST /api/v1/query`

**那么**：API 应调用 SDK 的 `query()` 方法

**实现验证**：
```python
# src/api/routes/query.py
from medgraph import MedGraphClient
from fastapi import APIRouter

router = APIRouter()
client = MedGraphClient.from_env()  # 共享客户端实例

@router.post("/query")
async def api_query(request: QueryRequest):
    result = await client.query(
        query=request.query,
        mode=request.mode,
        graph_id=request.graph_id,
    )
    return result
```
