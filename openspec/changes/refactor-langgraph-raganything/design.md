# 架构设计文档

## 目录
1. [系统架构](#系统架构)
2. [模块设计](#模块设计)
   - [SDK 层 (sdk/)](#0-sdk-层-sdk) ⭐ 新增
   - [智能体层 (agents/)](#1-智能体层-agents)
   - [核心模块 (core/)](#2-核心模块-core)
   - [服务层 (services/)](#3-服务层-services)
   - [接口层 (api/ & cli/)](#4-接口层-api--cli)
3. [数据流](#数据流)
4. [RAG-Anything 适配层](#rag-anything-适配层)
5. [存储配置](#存储配置)
6. [SDK 设计](#sdk-设计) ⭐ 新增
7. [API 设计](#api-设计)
8. [CLI 设计](#cli-设计)
9. [与原设计的差异](#与原设计的差异)

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Medical Graph RAG                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐                          │
│  │     CLI      │    │   REST API   │                          │
│  │   (Typer)    │    │   (FastAPI)  │                          │
│  └──────┬───────┘    └──────┬───────┘                          │
│         │                   │                                   │
│         └─────────┬─────────┘                                   │
│                   ▼                                               │
│         ┌──────────────────┐                                     │
│         │   Python SDK     │ ◄─── 统一接口层                    │
│         │ (MedGraphClient) │                                     │
│         └─────────┬────────┘                                     │
│                   │                                               │
│                   ▼                                               │
│         ┌──────────────────┐                                     │
│         │   服务层          │                                     │
│         │  (Services)      │                                     │
│         └─────────┬────────┘                                     │
│                   │                                               │
│                   ▼                                               │
│         ┌──────────────────┐                                     │
│         │  LangGraph       │                                     │
│         │  智能体编排层     │                                     │
│         │  (Agent Layer)   │                                     │
│         └─────────┬────────┘                                     │
│                   │                                               │
│                   ▼                                               │
│         ┌──────────────────┐                                     │
│         │  RAG-Anything    │                                     │
│         │   适配层         │                                     │
│         └─────────┬────────┘                                     │
│                   │                                               │
│     ┌─────────────┼─────────────┐                                │
│     ▼             ▼             ▼                                │
│  ┌────────┐  ┌────────┐  ┌────────┐                              │
│  │ Milvus │  │ Neo4j  │  │LightRAG│                              │
│  │向量存储│  │ 图存储 │  │ 核心   │                              │
│  └────────┘  └────────┘  └────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 架构层次

```
┌────────────────────────────────────────────────────────────────┐
│                   Presentation Layer                          │
│  ┌─────────────────┐         ┌────────────────────────────┐   │
│  │  CLI (Typer)    │         │  REST API (FastAPI)        │   │
│  └────────┬────────┘         └────────────┬───────────────┘   │
│           │                               │                   │
│           └─────────────┬─────────────────┘                   │
│                         ▼                                     │
│           ┌───────────────────────────────┐                   │
│           │      Python SDK Layer         │ ◄─── 统一接口      │
│           │   (MedGraphClient + Types)    │                   │
│           └───────────────┬───────────────┘                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                      Service Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ Ingestion   │  │    Query    │  │     Graph           │    │
│  │  Service    │  │   Service   │  │     Service         │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   Agent Layer (LangGraph)                      │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           LangGraph 工作流编排                          │   │
│  │  - 查询路由工作流                                       │   │
│  │  - 图谱构建工作流                                       │   │
│  │  - 扩展点：介入手术智能体                               │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   Adapter Layer                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           RAGAnythingAdapter (核心适配器)              │   │
│  │  - 封装 LightRAG API                                   │   │
│  │  - 提供医学领域定制                                    │   │
│  │  - 管理多工作空间                                      │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                RAG-Anything (LightRAG)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ MilvusVector│  │  Neo4JGraph │  │    Document          │    │
│  │   Storage   │  │   Storage   │  │    Processor        │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

---

## 模块设计

### 0. SDK 层 (sdk/) ⭐ 新增

**设计目标**：提供类型安全、易用的 Python API，作为 CLI 和 REST API 的统一基础。

```
src/sdk/
├── __init__.py           # 导出 MedGraphClient
├── client.py             # MedGraphClient 主客户端
├── types.py              # 类型定义（QueryMode, GraphInfo 等）
├── exceptions.py         # SDK 专用异常
└── async_client.py       # 异步客户端（可选）
```

#### MedGraphClient 设计

```python
# src/sdk/client.py
from typing import Optional, List, AsyncIterator
from pydantic import BaseModel, Field
from .types import QueryMode, GraphInfo, QueryResult, DocumentInfo

class MedGraphClient:
    """Medical Graph RAG Python SDK 客户端

    提供类型安全、易用的 Python API，支持：
    - 文档摄入和管理
    - 知识图谱查询
    - 图谱管理（列表、删除、导出）
    """

    def __init__(
        self,
        workspace: str = "medical",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_username: str = "neo4j",
        neo4j_password: str = "password",
        milvus_uri: str = "http://localhost:19530",
        milvus_token: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o",
    ):
        """初始化客户端

        Args:
            workspace: 工作空间名称，用于隔离不同租户的图谱
            neo4j_uri: Neo4j 连接 URI（支持 bolt:// 和 neo4j:// 协议）
            neo4j_username: Neo4j 用户名
            neo4j_password: Neo4j 密码
            milvus_uri: Milvus 连接 URI
            milvus_token: Milvus 认证 Token（可选）
            openai_api_key: OpenAI API Key（默认从环境变量读取）
            embedding_model: 向量嵌入模型
            llm_model: LLM 模型

        注意：
            LightRAG 1.4.9+ 要求在首次使用前调用初始化方法。
            SDK 客户端会在首次调用任何方法时自动执行初始化。
        """
        self.workspace = workspace
        self._adapter = RAGAnythingAdapter(...)
        self._query_service = QueryService(...)
        self._graph_service = GraphService(...)
        self._initialized = False

    async def _ensure_initialized(self):
        """确保 SDK 客户端已初始化（LightRAG 1.4.9+ 要求）"""
        if not self._initialized:
            # 通过适配器初始化 LightRAG 存储和管道状态
            await self._adapter._ensure_initialized()
            self._initialized = True

    # ========== 文档管理 ==========

    async def ingest_document(
        self,
        file_path: str,
        graph_id: Optional[str] = None,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> DocumentInfo:
        """摄入单个文档到知识图谱

        Args:
            file_path: 文档路径（支持 PDF, TXT, MD, DOCX）
            graph_id: 目标图谱 ID（默认使用 workspace 作为 graph_id）
            chunk_size: 文本分块大小
            overlap: 分块重叠大小

        Returns:
            DocumentInfo: 文档信息（ID, 状态, 实体数等）
        """
        return await self._adapter.ingest_document(
            file_path=file_path,
            graph_id=graph_id or self.workspace,
            chunk_size=chunk_size,
            overlap=overlap,
        )

    async def ingest_documents(
        self,
        file_paths: List[str],
        graph_id: Optional[str] = None,
        show_progress: bool = True,
    ) -> List[DocumentInfo]:
        """批量摄入多个文档

        Args:
            file_paths: 文档路径列表
            graph_id: 目标图谱 ID
            show_progress: 是否显示进度条

        Returns:
            List[DocumentInfo]: 所有文档的信息
        """
        results = []
        for file_path in file_paths:
            result = await self.ingest_document(file_path, graph_id)
            results.append(result)
        return results

    async def get_document(self, doc_id: str) -> DocumentInfo:
        """获取文档详情"""
        # 实现细节...
        pass

    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        # 实现细节...
        pass

    # ========== 查询接口 ==========

    async def query(
        self,
        query: str,
        mode: QueryMode = QueryMode.HYBRID,
        graph_id: Optional[str] = None,
        top_k: int = 10,
        stream: bool = False,
    ) -> QueryResult:
        """执行查询

        Args:
            query: 查询文本
            mode: 检索模式（naive, local, global, hybrid, mix, bypass）
            graph_id: 图谱 ID（默认使用 workspace）
            top_k: 返回结果数量
            stream: 是否流式返回

        Returns:
            QueryResult: 查询结果（答案、来源、上下文等）
        """
        if stream:
            return self._query_stream(query, mode, graph_id, top_k)
        return await self._query_service.query(
            query=query,
            mode=mode,
            graph_id=graph_id or self.workspace,
            top_k=top_k,
        )

    async def _query_stream(
        self,
        query: str,
        mode: QueryMode,
        graph_id: str,
        top_k: int,
    ) -> AsyncIterator[str]:
        """流式查询"""
        # 实现细节...
        pass

    # ========== 图谱管理 ==========

    async def list_graphs(self) -> List[GraphInfo]:
        """列出所有图谱

        Returns:
            List[GraphInfo]: 图谱信息列表
        """
        return await self._graph_service.list_graphs(self.workspace)

    async def get_graph(self, graph_id: str) -> GraphInfo:
        """获取图谱详情"""
        # 实现细节...
        pass

    async def delete_graph(self, graph_id: str) -> bool:
        """删除图谱"""
        # 实现细节...
        pass

    async def merge_graph_nodes(
        self,
        graph_id: str,
        threshold: float = 0.7,
    ) -> int:
        """合并相似节点

        Args:
            graph_id: 图谱 ID
            threshold: 相似度阈值

        Returns:
            int: 合并的节点数量
        """
        return await self._graph_service.merge_nodes(graph_id, threshold)

    async def export_graph(
        self,
        graph_id: str,
        output_path: str,
        format: str = "json",
    ) -> None:
        """导出图谱

        Args:
            graph_id: 图谱 ID
            output_path: 输出路径
            format: 导出格式（json, csv, mermaid）
        """
        await self._graph_service.export(graph_id, output_path, format)

    # ========== 三层图谱关联 ==========

    async def link_trinity_graphs(
        self,
        top_graph_id: str,
        middle_graph_id: str,
        bottom_graph_id: str,
        similarity_threshold: float = 0.75,
    ) -> int:
        """创建三层图谱关联

        Args:
            top_graph_id: 顶层图 ID（患者数据）
            middle_graph_id: 中层图 ID（医学文献）
            bottom_graph_id: 底层图 ID（医学词典）
            similarity_threshold: 相似度阈值

        Returns:
            int: 创建的关联关系数量
        """
        return await self._graph_service.link_trinity(
            top_graph_id,
            middle_graph_id,
            bottom_graph_id,
            similarity_threshold,
        )
```

#### SDK 类型定义

```python
# src/sdk/types.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class QueryMode(str, Enum):
    """查询模式"""
    NAIVE = "naive"
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    MIX = "mix"
    BYPASS = "bypass"

class DocumentInfo(BaseModel):
    """文档信息"""
    doc_id: str
    file_name: str
    file_path: str
    status: str  # pending, processing, completed, failed
    entity_count: int = 0
    relationship_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

class SourceInfo(BaseModel):
    """来源信息"""
    doc_id: str
    chunk_id: str
    content: str
    relevance: float = 0.0

class GraphContext(BaseModel):
    """图谱上下文"""
    entities: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)

class QueryResult(BaseModel):
    """查询结果"""
    query: str
    answer: str
    sources: List[SourceInfo] = Field(default_factory=list)
    context: List[str] = Field(default_factory=list)
    graph_context: Optional[GraphContext] = None
    mode: QueryMode
    graph_id: str
    retrieval_count: int = 0
    latency_ms: int = 0

class GraphInfo(BaseModel):
    """图谱信息"""
    graph_id: str
    workspace: str
    entity_count: int = 0
    relationship_count: int = 0
    document_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

class GraphConfig(BaseModel):
    """图谱配置"""
    workspace: str = "medical"
    chunk_size: int = 512
    overlap: int = 50
    entity_types: List[str] = Field(
        default=[
            "DISEASE",
            "MEDICINE",
            "SYMPTOM",
            "ANATOMICAL_STRUCTURE",
            "BODY_FUNCTION",
            "LABORATORY_DATA",
            "PROCEDURE",
        ]
    )
```

#### SDK 异常定义

```python
# src/sdk/exceptions.py
class MedGraphError(Exception):
    """SDK 基础异常"""
    pass

class DocumentError(MedGraphError):
    """文档相关错误"""
    pass

class QueryError(MedGraphError):
    """查询相关错误"""
    pass

class GraphError(MedGraphError):
    """图谱相关错误"""
    pass

class ConfigError(MedGraphError):
    """配置相关错误"""
    pass

class AuthenticationError(MedGraphError):
    """认证错误"""
    pass
```

#### SDK 使用示例

```python
# 基本使用
from medgraph import MedGraphClient, QueryMode

# 初始化
client = MedGraphClient(
    workspace="medical-knowledge",
    neo4j_uri="bolt://localhost:7687",
    neo4j_password="your-password",
)

# 摄入文档
doc_info = await client.ingest_document("paper.pdf")
print(f"实体数量: {doc_info.entity_count}")

# 查询
result = await client.query(
    "糖尿病患者的主要症状是什么？",
    mode=QueryMode.HYBRID,
)
print(f"答案: {result.answer}")
print(f"来源: {result.sources}")

# 列出图谱
graphs = await client.list_graphs()
for graph in graphs:
    print(f"{graph.id}: {graph.entity_count} entities")
```

---

### 1. 智能体层 (agents/)

```
src/agents/
├── __init__.py
├── workflows/
│   ├── __init__.py
│   ├── query.py        # 查询工作流
│   └── build.py        # 图谱构建工作流
├── states.py           # LangGraph 状态定义
└── nodes.py            # 工作流节点定义
```

#### LangGraph 查询工作流

```python
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

class QueryState(TypedDict):
    query: str
    graph_id: str
    query_complexity: str  # simple, medium, complex
    context: List[Document]
    answer: str
    sources: List[str]
    retrieval_count: int
    max_retries: int

def create_query_workflow(rag_adapter):
    """创建查询工作流"""

    workflow = StateGraph(QueryState)

    # 添加节点
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("retrieve", retrieve_node(rag_adapter))
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("refine_query", refine_query_node)

    # 添加边
    workflow.add_edge(START, "analyze_query")
    workflow.add_conditional_edges(
        "analyze_query",
        should_retrieve,
        {
            "direct": "generate_answer",
            "retrieve": "retrieve"
        }
    )
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        check_relevance,
        {
            "relevant": "generate_answer",
            "refine": "refine_query",
            "end": END
        }
    )
    workflow.add_edge("refine_query", "retrieve")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()
```

#### 工作流节点设计

```python
async def analyze_query_node(state: QueryState) -> QueryState:
    """分析查询，确定检索策略"""
    # 简单查询直接生成答案
    # 复杂查询执行检索
    pass

async def retrieve_node(state: QueryState, rag_adapter) -> QueryState:
    """使用 RAG-Anything 检索上下文"""
    result = await rag_adapter.query(
        state["query"],
        mode="hybrid",
        graph_id=state["graph_id"]
    )
    state["context"] = result.documents
    state["sources"] = result.sources
    return state

async def grade_documents_node(state: QueryState) -> QueryState:
    """评估检索文档的相关性"""
    # 使用 LLM 评估相关性
    # 低相关性触发查询优化
    pass

async def generate_answer_node(state: QueryState) -> QueryState:
    """基于上下文生成答案"""
    # 使用 LLM 生成带引用的答案
    pass

async def refine_query_node(state: QueryState) -> QueryState:
    """优化查询以重试检索"""
    state["retrieval_count"] += 1
    # 使用 LLM 重写查询
    # 示例：扩展查询、添加上下文关键词
    pass

# ========== 路由函数 ==========

def should_retrieve(state: QueryState) -> str:
    """判断是否需要执行检索

    Returns:
        "direct": 简单查询，直接生成答案
        "retrieve": 复杂查询，需要检索
    """
    # 根据查询复杂度判断
    # simple → direct
    # medium/complex → retrieve
    if state.get("query_complexity") == "simple":
        return "direct"
    return "retrieve"

def check_relevance(state: QueryState) -> str:
    """检查检索结果的相关性

    Returns:
        "relevant": 相关性足够高，继续生成答案
        "refine": 相关性低，优化查询重试
        "end": 达到最大重试次数，结束
    """
    max_retries = state.get("max_retries", 3)
    retrieval_count = state.get("retrieval_count", 0)

    # 如果达到最大重试次数，结束
    if retrieval_count >= max_retries:
        return "end"

    # TODO: 使用 LLM 评估检索结果相关性
    # 这里需要根据实际的检索质量评估逻辑实现
    # 如果相关性分数 < 0.6，返回 "refine"
    # 否则返回 "relevant"
    return "relevant"  # 默认实现
```

#### 扩展点：介入手术智能体

```python
# 未来扩展：介入手术智能体
def create_interventional_agent(rag_adapter):
    """创建介入手术智能体工作流"""

    class InterventionalState(TypedDict):
        patient_data: Dict
        procedure_type: str
        devices: List[str]
        risks: List[str]
        recommendations: str

    workflow = StateGraph(InterventionalState)

    # 添加介入手术特定节点
    workflow.add_node("analyze_patient", analyze_patient_node)
    workflow.add_node("select_devices", select_devices_node)
    workflow.add_node("assess_risks", assess_risks_node)
    workflow.add_node("generate_plan", generate_plan_node)

    # ... 工作流编排

    return workflow.compile()
```

#### LangGraph 图谱构建工作流

```python
class BuildState(TypedDict):
    file_path: str
    graph_id: str
    merge_enabled: bool
    status: str
    entity_count: int
    relationship_count: int
    error: Optional[str]

def create_build_workflow(rag_adapter, merge_enabled: bool = False):
    """创建图谱构建工作流"""

    workflow = StateGraph(BuildState)

    # 添加节点
    workflow.add_node("load_document", load_document_node)
    workflow.add_node("extract_entities", extract_entities_node(rag_adapter))
    workflow.add_node("build_graph", build_graph_node)
    workflow.add_node("merge_nodes", merge_nodes_node)  # 可选节点
    workflow.add_node("create_summary", create_summary_node)

    # 添加边
    workflow.add_edge(START, "load_document")
    workflow.add_edge("load_document", "extract_entities")
    workflow.add_edge("extract_entities", "build_graph")

    # 条件边：根据 merge_enabled 决定是否执行 merge_nodes
    workflow.add_conditional_edges(
        "build_graph",
        lambda state: "merge" if state.get("merge_enabled") else "summary",
        {
            "merge": "merge_nodes",
            "summary": "create_summary"
        }
    )
    workflow.add_edge("merge_nodes", "create_summary")
    workflow.add_edge("create_summary", END)

    return workflow.compile()

# 节点实现
async def load_document_node(state: BuildState) -> BuildState:
    """加载文档并执行文本分块"""
    # 读取文档内容
    # 执行文本分块（chunk_size, overlap）
    # 提取多模态内容（图像、表格等）
    state["status"] = "loaded"
    return state

async def extract_entities_node(state: BuildState, rag_adapter) -> BuildState:
    """使用 RAG-Anything 提取实体和关系"""
    # 调用 rag_adapter.ingest_document()
    # 自动提取医学实体和关系
    state["status"] = "extracted"
    return state

async def build_graph_node(state: BuildState) -> BuildState:
    """在 Neo4j 和 Milvus 中构建图谱"""
    # 创建节点和关系
    # 存储向量嵌入
    state["status"] = "built"
    return state

async def merge_nodes_node(state: BuildState) -> BuildState:
    """合并相似节点（可选）"""
    # 基于语义相似度合并重复节点
    state["status"] = "merged"
    return state

async def create_summary_node(state: BuildState) -> BuildState:
    """创建社区摘要"""
    # 生成社区摘要以支持全局检索
    state["status"] = "completed"
    return state
```

### 2. 核心模块 (core/)

```
src/core/
├── __init__.py
├── config.py           # 配置管理 (Pydantic Settings)
├── adapters.py         # RAG-Anything 适配器
├── exceptions.py       # 自定义异常
└── logging.py          # 日志配置
```

#### 配置管理
```python
class Settings(BaseSettings):
    # LLM 配置
    openai_api_key: str
    openai_api_base: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-large"

    # Neo4j 配置 (图存储)
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    # Milvus 配置 (向量存储)
    milvus_uri: str = "http://localhost:19530"
    milvus_token: Optional[str] = None
    milvus_api_key: Optional[str] = None

    # RAG-Anything 配置
    rag_working_dir: str = "./data/rag_storage"
    rag_workspace: str = "medical"

    # 医学领域定制
    medical_entity_types: List[str] = [
        "DISEASE",               # 疾病/问题
        "MEDICINE",              # 药物
        "SYMPTOM",               # 症状
        "ANATOMICAL_STRUCTURE",  # 解剖结构
        "BODY_FUNCTION",         # 身体功能
        "LABORATORY_DATA",       # 实验室数据
        "PROCEDURE",             # 医疗程序
    ]
```

---

## RAG-Anything 适配层

### 核心适配器

```python
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.storage import Neo4JStorage, MilvusVectorDBStorage
from lightrag.kg.shared_storage import initialize_pipeline_status

class RAGAnythingAdapter:
    """RAG-Anything 核心适配器 (LightRAG 1.4.9+)"""

    def __init__(self, config: Settings):
        # 配置环境变量
        os.environ["NEO4J_URI"] = config.neo4j_uri
        os.environ["NEO4J_USERNAME"] = config.neo4j_username
        os.environ["NEO4J_PASSWORD"] = config.neo4j_password
        os.environ["MILVUS_URI"] = config.milvus_uri
        if config.milvus_token:
            os.environ["MILVUS_TOKEN"] = config.milvus_token

        # 初始化 LightRAG
        self.rag = LightRAG(
            working_dir=config.rag_working_dir,
            embedding_func=embedding_func(config),
            llm_model_func=llm_func(config),
            vector_storage="MilvusVectorDBStorage",
            graph_storage="Neo4JStorage",
            workspace=config.rag_workspace,
        )

        # 医学领域定制
        self.domain_config = {
            "entity_types": config.medical_entity_types
        }

        self._initialized = False

    async def _ensure_initialized(self):
        """确保 LightRAG 已初始化 (LightRAG 1.4.9+ 要求)"""
        if not self._initialized:
            # LightRAG 1.4.9+ 要求：必须先初始化存储
            await self.rag.initialize_storages()
            # LightRAG 1.4.9+ 要求：必须初始化管道状态
            await initialize_pipeline_status()
            self._initialized = True

    async def ingest_document(
        self,
        file_path: str,
        doc_id: Optional[str] = None
    ) -> IngestResult:
        """摄入文档 - 直接使用 LightRAG 的 ainsert"""
        # LightRAG 1.4.9+ 要求：确保已初始化
        await self._ensure_initialized()

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        await self.rag.ainsert(content, doc_id=doc_id)
        return IngestResult(doc_id=doc_id, status="completed")

    async def query(
        self,
        question: str,
        mode: str = "hybrid",
        **kwargs
    ) -> QueryResult:
        """查询 - 直接使用 LightRAG 的 aquery"""
        # LightRAG 1.4.9+ 要求：确保已初始化
        await self._ensure_initialized()

        param = QueryParam(mode=mode, **kwargs)
        result = await self.rag.aquery(question, param=param)
        return QueryResult(answer=result, sources=[])

    async def ingest_multimodal(
        self,
        content_list: List[Dict],
        file_path: str
    ):
        """多模态内容摄入 - 使用 LightRAG 的多模态支持"""
        # LightRAG 1.4.9+ 要求：确保已初始化
        await self._ensure_initialized()

        # LightRAG 原生支持多模态内容
        pass
```

---

## 存储配置

### Milvus 向量存储

RAG-Anything 原生支持 Milvus，无需额外配置：

```python
# 环境变量配置
MILVUS_URI=http://localhost:19530
MILVUS_TOKEN=username:password  # 可选
MILVUS_API_KEY=your-api-key      # 可选 (Zilliz Cloud)

# 或在代码中配置
from lightrag import LightRAG

rag = LightRAG(
    working_dir="./rag_storage",
    vector_storage="MilvusVectorDBStorage",  # 使用 Milvus
    graph_storage="Neo4JStorage",             # 使用 Neo4j
)
```

### Neo4j 图存储

```python
# 环境变量配置
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# 或在代码中配置
rag = LightRAG(
    graph_storage="Neo4JStorage",
)
```

### 混合存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG-Anything                             │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  MilvusVectorDB  │         │   Neo4JStorage    │          │
│  │  ┌────────────┐  │         │  ┌────────────┐  │          │
│  │  │ Embeddings │  │         │  │  Entities   │  │          │
│  │  │ Chunks     │  │         │  │ Relations   │  │          │
│  │  │ Documents  │  │         │  │ Communities │  │          │
│  │  └────────────┘  │         │  └────────────┘  │          │
│  └──────────────────┘         └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流

### 查询模式对比

系统提供两种查询模式，根据查询复杂度自动选择或由用户指定：

#### 简单查询模式（直接使用 RAG-Anything）

**适用场景**：单轮问答、简单事实查询、快速响应

```
┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
│  Query  │ -> │  CLI/API     │ -> │   Service   │ -> │   RAG      │
│         │    │  Interface   │    │   Layer     │    │  Adapter   │
└─────────┘    └──────────────┘    └─────────────┘    └─────┬──────┘
                                                           │
                                                           ▼
                                                    ┌──────────────┐
                                                    │  LightRAG    │
                                                    │   aquery()   │
                                                    └──────┬───────┘
                                                           │
                                             ┌─────────────┴─────────────┐
                                             ▼                           ▼
                                      ┌─────────────┐           ┌─────────────┐
                                      │   Milvus    │           │   Neo4j    │
                                      │ (Vector     │           │  (Graph     │
                                      │  Search)    │           │   Traversal)│
                                      └─────────────┘           └─────────────┘
                                             │
                                             ▼
                                      ┌─────────────┐
                                      │  LLM Generate│
                                      │     Answer   │
                                      └─────────────┘
```

#### 智能查询模式（使用 LangGraph 工作流）

**适用场景**：多轮对话、复杂推理、需要查询优化、介入手术智能体

```
┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  Query  │ -> │  CLI/API     │ -> │   Service   │ -> │  LangGraph   │
│         │    │  Interface   │    │   Layer     │    │  Workflow     │
└─────────┘    └──────────────┘    └─────────────┘    └──────┬───────┘
                                                           │
        ┌──────────────────────────────────────────────────┤
        │                                                  ▼
        │                                    ┌──────────────────────┐
        │              analyze_query   ──>  │  查询分析和路由        │
        │                                    └──────────┬───────────┘
        │                                               │
        │                                    ┌──────────▼───────────┐
        │              retrieve          ──>  │  检索上下文           │
        │                                    │  (调用 RAG Adapter)  │
        │                                    └──────────┬───────────┘
        │                                               │
        │                                    ┌──────────▼───────────┐
        │              grade_documents   ──>  │  评估文档相关性       │
        │                                    └──────────┬───────────┘
        │                                               │
        │              ┌──────────────────────┴─────────────┐
        │              │                                   │
        │              ▼                                   ▼
        │     ┌──────────────────┐               ┌──────────────────┐
        │     │  refine_query    │               │ generate_answer  │
        │     │  (优化并重试)     │               │  (生成答案)       │
        │     └─────────┬────────┘               └────────┬─────────┘
        │               │                                 │
        │               └─────────────┬───────────────────┘
        │                             │
        ▼                             ▼
  ┌─────────────┐             ┌─────────────┐
  │   Milvus    │             │   Neo4j    │
  │ (Embeddings)│             │  (Graph)   │
  └─────────────┘             └─────────────┘
```

### 文档摄入流程

```
┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐
│  Input  │ -> │  CLI/API     │ -> │   Service   │ -> │ LightRAG │
│  File   │    │  Interface   │    │   Layer     │    │  ainsert │
└─────────┘    └──────────────┘    └─────────────┘    └────┬─────┘
                                                           │
                                             ┌─────────────┴─────────────┐
                                             ▼                           ▼
                                      ┌─────────────┐           ┌─────────────┐
                                      │   Milvus    │           │   Neo4j    │
                                      │ (Embeddings)│           │  (Graph)   │
                                      └─────────────┘           └─────────────┘
```

---

## API 设计

### 端点列表

| 方法 | 端点 | 描述 | 实现 |
|------|------|------|------|
| `POST` | `/api/v1/documents` | 上传文档 | `adapter.ingest_document()` |
| `POST` | `/api/v1/query` | 简单查询（直接） | `adapter.query()` |
| `POST` | `/api/v1/query/intelligent` | 智能查询（LangGraph 工作流） | `query_workflow.run()` |
| `GET` | `/api/v1/graphs` | 列出图谱 | 遍历工作目录 |
| `DELETE` | `/api/v1/graphs/{id}` | 删除图谱 | 删除工作空间 |

**说明**：
- `/api/v1/query`：适用于简单查询，直接调用 RAG-Anything，响应快速
- `/api/v1/query/intelligent`：适用于复杂查询，使用 LangGraph 工作流，支持查询优化和多轮对话

---

## CLI 设计

### 命令列表

```
medgraph
├── ingest PATH           # 摄入文档
├── query QUERY           # 简单查询（直接使用 LightRAG）
├── query QUERY --intelligent  # 智能查询（使用 LangGraph 工作流）
├── build PATH            # 构建知识图谱（使用 LangGraph 工作流）
├── serve                 # 启动 API 服务器
└── export                # 导出图谱数据
```

**说明**：
- `query QUERY`：快速查询，直接调用 RAG-Anything
- `query QUERY --intelligent`：智能查询，使用 LangGraph 工作流，支持查询优化
- `build PATH`：使用 LangGraph 构建工作流，支持批量处理和错误恢复

---

## 与原设计的差异

### 架构策略：混合架构（保留 LangGraph + 复用 RAG-Anything）

本设计采用**混合架构策略**，结合两者的优势：

#### 保留的组件（基于 LangGraph）

| 组件 | 保留原因 | 实现方式 |
|------|----------|----------|
| LangGraph 编排层 | 提供复杂工作流编排能力，为介入手术智能体扩展做准备 | `agents/workflows/` |
| 查询路由工作流 | 支持多轮对话、查询优化和智能检索 | `agents/workflows/query.py` |
| 图谱构建工作流 | 支持异步批量处理、错误恢复和状态检查点 | `agents/workflows/build.py` |
| 扩展点机制 | 支持领域特定智能体（如介入手术智能体） | `agents/nodes.py` |

#### 复用的组件（基于 RAG-Anything）

| 原组件 | RAG-Anything 替代方案 | 说明 |
|--------|---------------------|------|
| 自定义实体提取器 | LightRAG 内置实体识别 | 保留医学实体类型定制 |
| 自定义关系提取器 | LightRAG 内置关系推理 | 通过领域提示词增强 |
| 自定义向量存储 | MilvusVectorDBStorage | 直接使用 RAG-Anything 集成 |
| 自定义图存储 | Neo4JStorage | 直接使用 RAG-Anything 集成 |
| 检索器实现 | LightRAG 6 种检索模式 | 通过 LangGraph 调用不同模式 |
| 节点合并逻辑 | LightRAG 内置实体链接 | 保留后处理定制能力 |

#### 新增的自定义组件

| 组件 | 说明 |
|------|------|
| CLI 接口 | Typer 命令行工具，支持简单/智能两种查询模式 |
| REST API | FastAPI Web 框架，提供智能查询端点 |
| RAGAnythingAdapter | 封装 RAG-Anything API，提供医学领域定制 |
| 医学领域配置 | 实体类型、提示词、后处理规则 |
| 多图谱管理 | 工作空间管理逻辑，支持多租户 |
