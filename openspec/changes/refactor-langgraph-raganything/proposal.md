# 提案：使用 LangGraph 和 RAG-Anything 重构 Medical Graph RAG

## 变更ID
`refactor-langgraph-raganything`

## 概述

将 Medical Graph RAG 项目从基于 CAMEL 和 Nano GraphRAG 的单体架构重构为基于 LangGraph 和 RAG-Anything 的模块化、易扩展架构。重构后将提供 CLI 命令和 RESTful API 接口，支持知识图谱构建和推理测试功能。

**术语说明**：
- **RAG-Anything**：基于 LightRAG 构建的医学知识图谱框架，提供多模态支持
- **LightRAG**：RAG-Anything 的底层引擎，代码中使用 `lightrag` 包
- 本文档在架构描述中使用 "RAG-Anything"，在代码示例中使用 "LightRAG"

## 动机

### 当前问题
1. **依赖过重**：项目依赖 CAMEL（多智能体框架）和 Nano GraphRAG，增加了复杂性和维护成本
2. **架构问题**：代码以单体脚本形式组织，缺乏模块化设计
3. **功能缺失**：缺少标准的 CLI 接口和 RESTful API
4. **扩展性差**：难以添加新功能或修改现有流程

### 重构收益
1. **简化依赖**：使用 RAG-Anything 替代 Nano GraphRAG，使用 LangGraph 替代 CAMEL
2. **模块化架构**：清晰的分层设计，SDK、API、CLI 各司其职，易于维护和扩展
3. **Python SDK**：提供类型安全、易用的 Python SDK，支持直接集成到其他应用
4. **标准化接口**：提供 CLI 和 RESTful API，两者都基于 SDK 构建，便于集成
5. **多模态支持**：RAG-Anything 原生支持图像、表格、公式等多模态内容
6. **工作流灵活性**：LangGraph 提供强大的状态管理和工作流编排能力
7. **三层图谱关联**：支持跨图层的知识关联，可以链接患者数据、医学文献和医学词典

## 技术选型

| 组件 | 当前技术 | 目标技术 | 理由 |
|------|----------|----------|------|
| 知识图谱核心 | CAMEL + Nano GraphRAG | **RAG-Anything (LightRAG)** | 原生支持 Milvus + Neo4j，内置实体关系提取，多模态支持 |
| 智能体编排 | CAMEL 多智能体 | **LangGraph** | 为介入手术智能体扩展提供工作流编排能力，支持状态管理和多步推理 |
| 向量存储 | 自定义 | **Milvus (RAG-Anything 原生)** | LightRAG 原生支持 MilvusVectorDBStorage |
| 图数据库 | Neo4j | **Neo4j (RAG-Anything 原生)** | LightRAG 原生支持 Neo4JStorage |
| 检索模式 | 自定义 | **LightRAG 6种模式** | naive, local, global, hybrid, mix, bypass |
| Web 框架 | 无 | **FastAPI** | 高性能，类型安全，自动文档生成 |
| CLI | argparse | **Typer + Rich** | 类型安全，美观的终端输出 |

## 混合架构设计

### 架构原则
**分层设计，各司其职**：
- **接口层**：CLI 和 RESTful API，都基于 SDK 构建
- **SDK 层**：提供类型安全、易用的 Python API，是所有接口的统一基础
- **LangGraph 层**：智能体工作流编排、状态管理、多步推理（为介入手术智能体做准备）
- **RAG-Anything 层**：核心 RAG 能力、向量存储、图存储、实体关系提取
- **服务层**：底层业务逻辑，被 SDK 调用

### 为什么保留 LangGraph
1. **介入手术智能体扩展**：LangGraph 提供的智能体编排能力将为未来的介入手术智能体提供基础
2. **复杂推理支持**：支持多步推理、循环、条件分支等复杂工作流
3. **状态管理**：LangGraph 的状态管理适合需要维护长期对话和上下文的场景
4. **可组合性**：LangGraph 的图结构可以方便地组合多个智能体

### 复用 RAG-Anything 的优势
1. **原生存储支持**：Milvus 向量存储 + Neo4j 图存储
2. **内置实体提取**：无需自定义实体关系提取器
3. **多种检索模式**：6 种检索模式开箱即用
4. **多模态支持**：原生支持图像、表格、公式等多模态内容

## 影响范围

### 代码组织变化
```
项目根目录/
├── src/
│   ├── agents/         # LangGraph 智能体层
│   │   ├── workflows/  # 工作流定义
│   │   ├── states.py   # 状态管理
│   │   └── nodes.py    # 节点实现
│   ├── core/           # 核心适配层
│   │   ├── config.py   # 配置管理
│   │   ├── adapters.py # RAG-Anything 适配器
│   │   ├── exceptions.py # 异常处理
│   │   └── logging.py  # 日志配置
│   ├── services/       # 底层业务服务
│   │   ├── ingestion.py # 摄入服务
│   │   ├── query.py    # 查询服务
│   │   └── graph.py    # 图谱服务
│   ├── sdk/            # Python SDK 层 ⭐ 新增
│   │   ├── __init__.py
│   │   ├── client.py   # MedGraphClient 主客户端
│   │   ├── types.py    # 类型定义
│   │   └── exceptions.py # SDK 异常
│   ├── cli/            # CLI 命令（基于 SDK）
│   └── api/            # RESTful API（基于 SDK）
├── tests/              # 测试套件
│   ├── test_sdk/       # SDK 测试
│   └── test_api/       # API 测试
└── docs/               # 文档
    ├── sdk/            # SDK 使用文档
    └── api/            # API 文档
```

### 依赖变更
**移除**：
- `camel` (整个 CAMEL 框架)
- `nano-graphrag` 及其依赖
- 自定义向量存储实现

**新增**：
- `lightrag-hku>=1.4.9` (RAG-Anything 核心，基于 LightRAG)
  - **Context7 Library ID**: `/hkuds/lightrag`
  - **Benchmark Score**: 81.6/100
  - **⚠️ 关键 API 变更**: 必须在首次使用前调用 `initialize_storages()` 和 `initialize_pipeline_status()`
- `lightrag>=1.4.9` (LightRAG 基础库)
- `langgraph>=1.0.3` (智能体工作流编排)
  - **Context7 Library ID**: `/langchain-ai/langgraph`
  - **Benchmark Score**: 88.5/100
  - **API 兼容性**: 主要变更是检查点相关，大部分 API 与 0.2.x 兼容
- `langchain>=0.3.0` (LangGraph 依赖)
- `langchain-openai>=0.2.0` (OpenAI 集成)
- `pymilvus>=2.4.0` (向量存储)
- `fastapi[standard]>=0.115.0`
- `typer>=0.12.0`
- `rich>=13.0.0`

**保留**：
- `neo4j>=5.0.0` (图存储)
- `openai`、`tiktoken` (LLM)

### 功能变更

#### 1. Python SDK ⭐ 新增
提供类型安全、易用的 Python API，支持直接集成到其他 Python 应用：

```python
from medgraph import MedGraphClient
from medgraph.types import QueryMode, GraphConfig

# 初始化客户端
client = MedGraphClient(
    workspace="medical-knowledge",
    neo4j_uri="bolt://localhost:7687",
    milvus_uri="http://localhost:19530"
)

# 摄入文档
doc_id = await client.ingest_document(
    file_path="medical_paper.pdf",
    graph_id="graph-001"
)

# 执行查询
result = await client.query(
    query="糖尿病患者的主要症状是什么？",
    mode=QueryMode.HYBRID,
    graph_id="graph-001"
)
print(result.answer)
print(result.sources)

# 列出图谱
graphs = await client.list_graphs()
for graph in graphs:
    print(f"{graph.id}: {graph.entity_count} entities")

# 导出图谱
await client.export_graph(
    graph_id="graph-001",
    output_path="graph_export.json"
)
```

#### 2. CLI 命令（基于 SDK）：
   - `medgraph build` - 构建知识图谱
   - `medgraph query` - 执行查询
   - `medgraph ingest` - 摄入文档
   - `medgraph serve` - 启动 API 服务器
   - `medgraph export` - 导出图谱数据

#### 3. RESTful API 端点（基于 SDK）：
   - `POST /api/v1/documents` - 上传并处理文档
   - `GET /api/v1/documents/{doc_id}` - 获取文档详情
   - `DELETE /api/v1/documents/{doc_id}` - 删除文档
   - `POST /api/v1/query` - 执行简单查询（直接使用 RAG-Anything）
   - `POST /api/v1/query/intelligent` - 执行智能查询（使用 LangGraph 工作流）
   - `GET /api/v1/graphs` - 列出所有图谱
   - `GET /api/v1/graphs/{graph_id}` - 获取图谱详情
   - `DELETE /api/v1/graphs/{graph_id}` - 删除图谱
   - `POST /api/v1/graphs/{graph_id}/merge` - 合并图谱节点
   - `GET /api/v1/graphs/{graph_id}/visualize` - 导出图谱可视化

## 向后兼容性

此重构为**破坏性变更**，不提供向后兼容性。主要变更：
1. 配置文件格式变更
2. 命令行接口完全重新设计
3. API 接口为新功能，不影响现有使用方式

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| RAG-Anything API 差异 | 高 | 创建适配层封装 LightRAG API |
| LangGraph 学习曲线 | 中 | 提供详细文档和示例 |
| 迁移成本 | 中 | 分阶段迁移，保留旧代码作为参考 |
| 性能下降 | 低 | 进行性能基准测试和优化 |

## 时间表

此提案仅涵盖设计和规范阶段。实施时间表将在 `apply` 阶段根据批准的规范确定。

## 参考资料

- [RAG-Anything 文档](https://github.com/hkuds/rag-anything)
- [LangGraph 文档](https://github.com/langchain-ai/langgraph)
  - **Context7 Library ID**: `/langchain-ai/langgraph`
  - **版本**: 1.0.3
- [LightRAG 文档](https://github.com/HKUDS/LightRAG)
  - **Context7 Library ID**: `/hkuds/lightrag`
  - **版本**: v1.4.9.8
- 当前项目结构分析

## 关键 API 变更说明

### LightRAG 1.4.9+ 初始化要求

**旧版本 (< 1.4.9)**:
```python
from lightrag import LightRAG
rag = LightRAG(working_dir="./rag_storage", ...)
await rag.ainsert("文档")
```

**新版本 (>= 1.4.9)**:
```python
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status

rag = LightRAG(
    working_dir="./rag_storage",
    graph_storage="Neo4JStorage",
    vector_storage="MilvusVectorDBStorage",
    ...
)
# ⚠️ 必须先执行初始化
await rag.initialize_storages()
await initialize_pipeline_status()
await rag.ainsert("文档")
```

### LangGraph 1.0.3 检查点变更

LangGraph 1.0.3 主要变更在检查点（checkpoint）相关 API：
- 检查点存储接口保持向后兼容
- 新增更多检查点后端选项
- 改进了检查点序列化机制
