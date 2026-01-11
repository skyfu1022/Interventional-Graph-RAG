# Medical Graph RAG 开发者指南

本文档面向开发者，介绍 Medical Graph RAG 系统的架构设计、扩展指南和最佳实践。

## 目录

1. [系统架构](#系统架构)
2. [核心模块说明](#核心模块说明)
3. [智能体扩展指南](#智能体扩展指南)
4. [适配器扩展指南](#适配器扩展指南)
5. [服务层扩展](#服务层扩展)
6. [最佳实践](#最佳实践)

---

## 系统架构

### 整体架构图

```mermaid
graph TB
    subgraph "表现层"
        CLI[CLI 接口<br/>Typer]
        API[REST API<br/>FastAPI]
    end

    subgraph "SDK 层"
        SDK[Python SDK<br/>MedGraphClient]
    end

    subgraph "服务层"
        QuerySvc[QueryService<br/>查询服务]
        GraphSvc[GraphService<br/>图谱服务]
        IngestSvc[IngestionService<br/>摄入服务]
    end

    subgraph "智能体层"
        Workflow[LangGraph 工作流<br/>查询路由 | 图谱构建]
        Agents[智能体节点<br/>分析 | 检索 | 生成]
    end

    subgraph "适配器层"
        Adapter[RAGAnythingAdapter<br/>LightRAG 适配器]
    end

    subgraph "存储层"
        Neo4j[(Neo4j<br/>图存储)]
        Milvus[(Milvus<br/>向量存储)]
    end

    CLI --> SDK
    API --> SDK
    SDK --> QuerySvc
    SDK --> GraphSvc
    SDK --> IngestSvc

    QuerySvc --> Workflow
    GraphSvc --> Adapter
    IngestSvc --> Adapter

    Workflow --> Agents
    Agents --> Adapter

    Adapter --> Neo4j
    Adapter --> Milvus
```

### 架构层次说明

```
┌─────────────────────────────────────────────────────────────┐
│                      表现层 (Presentation Layer)            │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  CLI (Typer)     │         │  REST API        │         │
│  │  命令行接口       │         │  (FastAPI)       │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
├───────────┼──────────────────────────┼─────────────────────┤
│           │                          │                     │
├───────────┼──────────────────────────┼─────────────────────┤
│           ▼                          ▼                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            SDK 层 (Python SDK)                        │ │
│  │  MedGraphClient - 类型安全的 Python 客户端             │ │
│  └──────────────────────┬─────────────────────────────────┘ │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            服务层 (Service Layer)                      │ │
│  │  QueryService | GraphService | IngestionService       │ │
│  └──────────────────────┬─────────────────────────────────┘ │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         智能体层 (Agent Layer - LangGraph)             │ │
│  │  StateGraph 工作流编排                                  │ │
│  │  - 查询工作流 (分析→检索→评估→生成)                     │ │
│  │  - 构建工作流 (加载→提取→构建→合并)                     │ │
│  └──────────────────────┬─────────────────────────────────┘ │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        适配器层 (Adapter Layer)                        │ │
│  │  RAGAnythingAdapter - LightRAG 框架适配                │ │
│  └──────────────────────┬─────────────────────────────────┘ │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           存储层 (Storage Layer)                       │ │
│  │  Neo4j (图存储) + Milvus (向量存储)                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **分层解耦**：各层职责明确，通过接口通信
2. **依赖注入**：适配器和 LLM 通过构造函数注入
3. **异步优先**：所有 I/O 操作使用 async/await
4. **类型安全**：使用 TypedDict、dataclass 和 Pydantic
5. **错误处理**：统一的自定义异常体系

---

## 核心模块说明

### 1. 智能体层 (agents/)

智能体层基于 **LangGraph** 框架，负责工作流编排和智能决策。

#### 目录结构

```
src/agents/
├── states.py          # LangGraph 状态定义
├── nodes.py           # 工作流节点函数
├── workflows/         # 工作流定义
│   ├── query.py       # 查询工作流
│   └── build.py       # 图谱构建工作流
└── visualization.py   # 工作流可视化工具
```

#### 状态定义

```python
# src/agents/states.py

from typing import TypedDict, List, Optional, Annotated
from typing_extensions import Required
from operator import add

class QueryState(TypedDict):
    """查询工作流状态"""
    query: Required[str]                    # 用户查询
    graph_id: Required[str]                 # 目标图谱 ID
    query_complexity: str                   # 查询复杂度 (simple/medium/complex)
    context: Annotated[List[str], add]      # 检索上下文 (累加)
    answer: str                             # 生成的答案
    sources: List[str]                      # 答案来源
    retrieval_count: int                    # 检索次数
    max_retries: int                        # 最大重试次数
    error: Optional[str]                    # 错误信息
```

#### 节点函数

```python
# src/agents/nodes.py

from langchain_core.messages import HumanMessage, SystemMessage
from src.agents.states import QueryState

async def analyze_query_node(state: QueryState) -> dict:
    """分析查询复杂度节点"""
    query = state.get("query", "")

    # 启发式规则分析查询复杂度
    char_count = len(query)
    complex_indicators = ["比较", "分析", "原因", "如何"]

    has_complex = any(ind in query for ind in complex_indicators)

    if char_count <= 15 and not has_complex:
        complexity = "simple"
    elif char_count <= 50:
        complexity = "medium"
    else:
        complexity = "complex"

    return {"query_complexity": complexity}

async def retrieve_node(state: QueryState, config) -> dict:
    """检索节点 - 调用 RAG 适配器"""
    query = state.get("query", "")
    rag_adapter = config["configurable"].get("rag_adapter")

    result = await rag_adapter.query(query, mode="hybrid")

    return {
        "context": result.context,
        "sources": result.sources
    }
```

#### 工作流定义

```python
# src/agents/workflows/query.py

from langgraph.graph import StateGraph, START, END
from src.agents.states import QueryState
from src.agents.nodes import (
    analyze_query_node,
    retrieve_node,
    grade_documents_node,
    generate_answer_node,
    refine_query_node
)

def create_query_workflow(rag_adapter):
    """创建查询工作流"""

    workflow = StateGraph(QueryState)

    # 添加节点
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("refine_query", refine_query_node)

    # 添加边
    workflow.add_edge(START, "analyze_query")

    workflow.add_conditional_edges(
        "analyze_query",
        lambda state: "direct" if state.get("query_complexity") == "simple" else "retrieve",
        {
            "direct": "generate_answer",
            "retrieve": "retrieve"
        }
    )

    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        lambda state: "end" if state.get("retrieval_count", 0) >= state.get("max_retries", 3)
                        else state.get("relevance", "relevant"),
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

### 2. 适配器层 (core/adapters.py)

适配器层封装 **LightRAG** 框架，提供医学领域定制的 RAG 能力。

#### 核心适配器

```python
# src/core/adapters.py

from lightrag.lightrag import LightRAG
from lightrag.operate import QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

class RAGAnythingAdapter:
    """LightRAG 核心适配器"""

    def __init__(self, config: Settings):
        self.config = config
        self._rag: Optional[LightRAG] = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化适配器 (LightRAG 1.4.9+ 必需)"""
        # 创建 LightRAG 实例
        self._rag = LightRAG(
            working_dir=str(self.config.rag_working_dir),
            embedding_func=self._create_embedding_func(),
            llm_model_func=self._create_llm_func(),
            graph_storage="Neo4JStorage",
            vector_storage="MilvusVectorDBStorage",
            workspace=self.config.rag_workspace,
        )

        # 初始化存储 (LightRAG 1.4.9+ 必需)
        await self._rag.initialize_storages()
        await initialize_pipeline_status()

        self._initialized = True

    async def ingest_document(
        self,
        file_path: str,
        doc_id: Optional[str] = None
    ) -> IngestResult:
        """摄入文档"""
        await self._ensure_initialized()

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        await self._rag.ainsert(content, ids=[doc_id] if doc_id else None)

        return IngestResult(doc_id=doc_id, status="completed")

    async def query(
        self,
        question: str,
        mode: str = "hybrid",
        **kwargs
    ) -> QueryResult:
        """查询知识图谱"""
        await self._ensure_initialized()

        param = QueryParam(mode=mode, **kwargs)
        answer = await self._rag.aquery(question, param=param)

        return QueryResult(answer=answer, mode=mode)
```

### 3. 服务层 (services/)

服务层提供业务逻辑封装，供 SDK 层调用。

#### 查询服务

```python
# src/services/query.py

from src.core.adapters import RAGAnythingAdapter
from src.agents.workflows.query import create_query_workflow

class QueryService:
    """查询服务类"""

    def __init__(self, adapter: RAGAnythingAdapter):
        self._adapter = adapter
        self._workflow = create_query_workflow(adapter)

    async def query(
        self,
        query_text: str,
        mode: str = "hybrid",
        graph_id: str = "default",
        **kwargs
    ) -> QueryResult:
        """执行查询"""
        workflow_input = {
            "query": query_text,
            "graph_id": graph_id,
            "query_mode": mode,
            **kwargs
        }

        result = await self._workflow.ainvoke(workflow_input)

        return QueryResult(
            query=query_text,
            answer=result.get("answer", ""),
            mode=QueryMode.from_string(mode),
            graph_id=graph_id,
            sources=result.get("sources", []),
            context=result.get("context", []),
            retrieval_count=result.get("retrieval_count", 0),
        )
```

#### 图谱服务

```python
# src/services/graph.py

class GraphService:
    """图谱服务类"""

    def __init__(self, adapter: RAGAnythingAdapter):
        self._adapter = adapter

    async def list_graphs(self) -> List[GraphInfo]:
        """列出所有图谱"""
        # 遍历工作空间目录
        graphs = []
        for ws_path in Path(self._adapter.config.rag_working_dir).iterdir():
            if ws_path.is_dir() and not ws_path.name.startswith('.'):
                stats = await self._adapter.get_stats()
                graphs.append(GraphInfo(
                    graph_id=ws_path.name,
                    entity_count=stats.entity_count,
                    relationship_count=stats.relationship_count,
                ))
        return graphs

    async def export_graph(
        self,
        graph_id: str,
        output_path: str,
        format: str = "json"
    ) -> None:
        """导出图谱"""
        if format == "json":
            await self._export_json(graph_id, output_path)
        elif format == "csv":
            await self._export_csv(graph_id, output_path)
        elif format == "mermaid":
            await self._export_mermaid(graph_id, output_path)
```

---

## 智能体扩展指南

本指南介绍如何基于 LangGraph 扩展自定义智能体，以**介入手术智能体**为例。

### 扩展示例：介入手术智能体

#### 步骤 1：定义智能体状态

```python
# src/agents/states.py

class InterventionalState(TypedDict):
    """介入手术智能体工作流状态"""

    # 输入
    patient_data: Required[Dict]           # 患者数据 (年龄、病史、检查结果)
    procedure_type: Required[str]          # 手术类型 (PCI、支架植入等)

    # 中间状态
    analysis: str                          # 患者数据分析结果
    devices: Annotated[List[str], add]     # 推荐的器械列表 (累加)
    risks: Annotated[List[str], add]       # 识别的风险列表 (累加)
    context: Annotated[List[str], add]     # 检索到的相关上下文 (累加)

    # 输出
    recommendations: str                   # 推荐方案描述

    # 错误处理
    error: Optional[str]                   # 错误信息
```

#### 步骤 2：实现节点函数

```python
# src/agents/nodes.py

async def analyze_patient_node(
    state: InterventionalState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """分析患者数据节点"""

    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    # 获取 LLM (从 config)
    llm = config["configurable"].get("llm")

    prompt = f"""请分析以下患者数据，评估其是否适合进行 {procedure_type} 手术。

患者数据:
{patient_data}

请提供:
1. 患者基本信息摘要
2. 相关风险因素
3. 手术适应性评估
"""

    response = await llm.ainvoke([
        SystemMessage(content="你是介入手术分析专家。"),
        HumanMessage(content=prompt)
    ])

    return {"analysis": response.content.strip()}


async def recommend_devices_node(
    state: InterventionalState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """推荐器械节点"""

    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    llm = config["configurable"].get("llm")

    prompt = f"""基于患者数据和手术类型，推荐合适的介入器械。

手术类型: {procedure_type}
患者数据: {patient_data}

请推荐:
1. 导管类型和规格
2. 支架类型和规格 (如适用)
3. 其他必要器械
4. 器械使用注意事项
"""

    response = await llm.ainvoke([
        SystemMessage(content="你是介入器械推荐专家。"),
        HumanMessage(content=prompt)
    ])

    return {"devices": [response.content.strip()]}


async def assess_risks_node(
    state: InterventionalState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估风险节点"""

    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    llm = config["configurable"].get("llm")

    prompt = f"""评估介入手术的潜在风险。

手术类型: {procedure_type}
患者数据: {patient_data}

请评估:
1. 手术相关的主要风险
2. 可能的并发症
3. 风险等级 (高/中/低)
4. 风险预防和处理建议
"""

    response = await llm.ainvoke([
        SystemMessage(content="你是介入手术风险评估专家。"),
        HumanMessage(content=prompt)
    ])

    return {"risks": [response.content.strip()]}


async def generate_recommendations_node(
    state: InterventionalState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """生成推荐方案节点"""

    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    devices = state.get("devices", [])
    risks = state.get("risks", [])

    llm = config["configurable"].get("llm")

    devices_str = "\n".join([f"- {d}" for d in devices])
    risks_str = "\n".join([f"- {r}" for r in risks])

    prompt = f"""基于以下信息，为介入手术生成完整的推荐方案。

手术类型: {procedure_type}
患者数据: {patient_data}

推荐器械:
{devices_str}

风险评估:
{risks_str}

请生成:
1. 手术方案概述
2. 器械选择理由
3. 风险防控措施
4. 术后注意事项
5. 备选方案 (如适用)
"""

    response = await llm.ainvoke([
        SystemMessage(content="你是介入手术方案制定专家。"),
        HumanMessage(content=prompt)
    ])

    return {"recommendations": response.content.strip()}
```

#### 步骤 3：创建工作流

```python
# src/agents/workflows/interventional.py

from langgraph.graph import StateGraph, START, END
from src.agents.states import InterventionalState
from src.agents.nodes import (
    analyze_patient_node,
    recommend_devices_node,
    assess_risks_node,
    generate_recommendations_node,
)

def create_interventional_workflow(rag_adapter):
    """创建介入手术智能体工作流"""

    workflow = StateGraph(InterventionalState)

    # 添加节点
    workflow.add_node("analyze_patient", analyze_patient_node)
    workflow.add_node("recommend_devices", recommend_devices_node)
    workflow.add_node("assess_risks", assess_risks_node)
    workflow.add_node("generate_recommendations", generate_recommendations_node)

    # 添加边 (并行执行器械推荐和风险评估)
    workflow.add_edge(START, "analyze_patient")
    workflow.add_edge("analyze_patient", "recommend_devices")
    workflow.add_edge("analyze_patient", "assess_risks")
    workflow.add_edge("recommend_devices", "generate_recommendations")
    workflow.add_edge("assess_risks", "generate_recommendations")
    workflow.add_edge("generate_recommendations", END)

    return workflow.compile()
```

#### 步骤 4：集成到服务层

```python
# src/services/interventional.py

class InterventionalService:
    """介入手术智能体服务"""

    def __init__(self, adapter: RAGAnythingAdapter, llm: BaseChatModel):
        self._adapter = adapter
        self._llm = llm
        self._workflow = create_interventional_workflow(adapter)

    async def recommend(
        self,
        patient_data: Dict,
        procedure_type: str,
        graph_id: str = "medical"
    ) -> Dict[str, Any]:
        """执行介入手术推荐"""

        workflow_input = {
            "patient_data": patient_data,
            "procedure_type": procedure_type,
            "graph_id": graph_id,
        }

        config = {
            "configurable": {
                "rag_adapter": self._adapter,
                "llm": self._llm,
            }
        }

        result = await self._workflow.ainvoke(workflow_input, config)

        return {
            "analysis": result.get("analysis", ""),
            "devices": result.get("devices", []),
            "risks": result.get("risks", []),
            "recommendations": result.get("recommendations", ""),
        }
```

#### 使用示例

```python
# 使用介入手术智能体

from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.interventional import InterventionalService
from langchain_openai import ChatOpenAI

async def main():
    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    service = InterventionalService(adapter, llm)

    # 调用智能体
    result = await service.recommend(
        patient_data={
            "age": 65,
            "gender": "男",
            "history": ["高血压", "糖尿病"],
            "diagnosis": "冠心病",
        },
        procedure_type="PCI"
    )

    print(f"分析结果: {result['analysis']}")
    print(f"推荐器械: {result['devices']}")
    print(f"风险评估: {result['risks']}")
    print(f"推荐方案: {result['recommendations']}")

asyncio.run(main())
```

### 智能体可视化

使用内置工具生成工作流可视化图：

```python
from src.agents.visualization import visualize_workflow

# 生成 Mermaid 图表
mermaid_code = visualize_workflow(
    workflow=create_interventional_workflow(adapter),
    format="mermaid"
)

# 生成 PNG 图片
visualize_workflow(
    workflow=create_interventional_workflow(adapter),
    format="png",
    output_path="interventional_workflow.png"
)
```

---

## 适配器扩展指南

本指南介绍如何扩展 RAGAnythingAdapter 以支持自定义功能。

### 扩展场景 1：自定义实体提取器

为医学领域添加特定的实体提取规则。

```python
# src/core/adapters.py

class MedicalRAGAnythingAdapter(RAGAnythingAdapter):
    """医学领域定制的 RAG 适配器"""

    def __init__(self, config: Settings):
        super().__init__(config)

        # 医学实体类型定制
        self.medical_entity_types = [
            "DISEASE",               # 疾病
            "MEDICINE",              # 药物
            "SYMPTOM",               # 症状
            "ANATOMICAL_STRUCTURE",  # 解剖结构
            "BODY_FUNCTION",         # 身体功能
            "LABORATORY_DATA",       # 实验室数据
            "PROCEDURE",             # 医疗程序
            "DEVICE",                # 医疗器械 (新增)
            "INTERVENTION",          # 介入手术 (新增)
        ]

    async def extract_entities(
        self,
        text: str,
        domain: str = "medical"
    ) -> List[Dict[str, Any]]:
        """自定义实体提取"""

        # 调用父类的基础提取
        base_entities = await super().extract_entities(text)

        # 添加医学特定的后处理
        if domain == "medical":
            base_entities = self._merge_medical_entities(base_entities)
            base_entities = self._normalize_medical_terms(base_entities)

        return base_entities

    def _merge_medical_entities(
        self,
        entities: List[Dict]
    ) -> List[Dict]:
        """合并相似的医学实体"""

        # 医学术语同义词映射
        synonyms = {
            "高血压": ["高血压病", "原发性高血压"],
            "糖尿病": ["糖尿病 mellitus", "DM"],
            "冠心病": ["冠状动脉粥样硬化性心脏病"],
        }

        merged = []
        seen = set()

        for entity in entities:
            name = entity.get("entity_name", "")

            # 检查是否为同义词
            for canonical, variants in synonyms.items():
                if name in variants:
                    if canonical not in seen:
                        entity["entity_name"] = canonical
                        merged.append(entity)
                        seen.add(canonical)
                    break
            else:
                if name not in seen:
                    merged.append(entity)
                    seen.add(name)

        return merged

    def _normalize_medical_terms(
        self,
        entities: List[Dict]
    ) -> List[Dict]:
        """标准化医学术语"""

        # ICD-10 编码映射
        icd10_mapping = {
            "糖尿病": "E11",
            "高血压": "I10",
            "冠心病": "I25",
        }

        for entity in entities:
            name = entity.get("entity_name", "")
            if name in icd10_mapping:
                entity.setdefault("properties", {})["icd10"] = icd10_mapping[name]

        return entities
```

### 扩展场景 2：自定义查询模式

添加新的查询模式，如"三层图谱关联查询"。

```python
# src/core/adapters.py

class TrinityRAGAdapter(RAGAnythingAdapter):
    """支持三层图谱关联的适配器"""

    async def query_trinity(
        self,
        question: str,
        top_graph_id: str,      # 顶层：患者数据
        middle_graph_id: str,   # 中层：医学文献
        bottom_graph_id: str,   # 底层：医学词典
        mode: str = "hybrid"
    ) -> QueryResult:
        """三层图谱关联查询"""

        # 并行查询三个图谱
        import asyncio

        tasks = [
            self._query_single_graph(question, top_graph_id, mode),
            self._query_single_graph(question, middle_graph_id, mode),
            self._query_single_graph(question, bottom_graph_id, mode),
        ]

        results = await asyncio.gather(*tasks)

        # 合并结果
        combined_context = self._merge_trinity_results(results)

        # 生成最终答案
        answer = await self._generate_trinity_answer(
            question,
            combined_context
        )

        return QueryResult(
            answer=answer,
            mode="trinity",
            context=combined_context,
            metadata={
                "top_graph_id": top_graph_id,
                "middle_graph_id": middle_graph_id,
                "bottom_graph_id": bottom_graph_id,
            }
        )

    async def _query_single_graph(
        self,
        question: str,
        graph_id: str,
        mode: str
    ) -> str:
        """查询单个图谱"""
        result = await self.query(question, mode=mode)
        return result.answer

    def _merge_trinity_results(
        self,
        results: List[str]
    ) -> List[str]:
        """合并三层图谱的查询结果"""

        # 去重和排序
        unique_contexts = list(set(results))

        # 按相关性排序 (简化实现)
        return unique_contexts[:10]

    async def _generate_trinity_answer(
        self,
        question: str,
        context: List[str]
    ) -> str:
        """基于三层图谱上下文生成答案"""

        context_str = "\n\n".join([
            f"参考信息 {i+1}:\n{ctx}"
            for i, ctx in enumerate(context[:5])
        ])

        prompt = f"""请基于以下三层知识图谱的检索结果回答问题。

问题: {question}

三层图谱检索结果:
{context_str}

请提供准确、全面的答案，并注明信息来源。"""

        # 使用 LLM 生成答案
        from lightrag.llm.openai import openai_complete_if_cache

        answer = await openai_complete_if_cache(
            self.config.llm_model,
            prompt,
            api_key=self.config.openai_api_key,
        )

        return answer
```

### 扩展场景 3：自定义存储后端

添加对其他图数据库的支持，如 ArangoDB。

```python
# src/core/adapters.py

class ArangoDBStorage:
    """ArangoDB 图存储适配器"""

    def __init__(self, connection_string: str, database: str):
        from arango import ArangoClient

        self.client = ArangoClient(connection_string)
        self.db = self.db(database)

    async def execute_query(
        self,
        query: str,
        bind_vars: Optional[Dict] = None
    ) -> List[Dict]:
        """执行 AQL 查询"""
        cursor = self.db.aql.execute(
            query,
            bind_vars=bind_vars or {}
        )
        return [doc for doc in cursor]

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[Dict] = None
    ) -> str:
        """创建实体节点"""
        collection = self.db.collection(entity_type.lower())
        result = collection.insert({
            "name": name,
            "type": entity_type,
            **(properties or {})
        })
        return result["_id"]

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict] = None
    ) -> str:
        """创建关系边"""
        collection = self.db.collection(f"edge_{relation_type.lower()}")
        result = collection.insert({
            "_from": source_id,
            "_to": target_id,
            "type": relation_type,
            **(properties or {})
        })
        return result["_id"]


class ArangoDBRAGAdapter(RAGAnythingAdapter):
    """使用 ArangoDB 的 RAG 适配器"""

    def __init__(self, config: Settings, arango_connection: str):
        super().__init__(config)

        # 替换图存储为 ArangoDB
        self._arango_storage = ArangoDBStorage(
            arango_connection,
            "medical_graph"
        )

    async def query_arango(
        self,
        aql_query: str,
        bind_vars: Optional[Dict] = None
    ) -> List[Dict]:
        """直接执行 ArangoDB 查询"""
        return await self._arango_storage.execute_query(
            aql_query,
            bind_vars
        )
```

---

## 服务层扩展

### 创建自定义服务

```python
# src/services/analytics.py

class AnalyticsService:
    """图谱分析服务"""

    def __init__(self, adapter: RAGAnythingAdapter):
        self._adapter = adapter

    async def analyze_entity_cohort(
        self,
        graph_id: str,
        entity_type: str
    ) -> Dict[str, Any]:
        """分析实体群体"""

        # 执行 Cypher 查询
        cypher = f"""
        MATCH (n:{entity_type})
        RETURN
            count(n) as count,
            collect(n.entity_name)[0..10] as examples
        """

        results = await self._adapter.query_cypher(
            cypher,
            graph_id=graph_id
        )

        return {
            "entity_type": entity_type,
            "total_count": results[0]["count"] if results else 0,
            "examples": results[0]["examples"] if results else [],
        }

    async def find_shortest_path(
        self,
        graph_id: str,
        source_entity: str,
        target_entity: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """查找实体间最短路径"""

        cypher = f"""
        MATCH path = shortestPath(
            (source:__Entity__ {{entity_name: $source}})-[*..{max_depth}]-(target:__Entity__ {{entity_name: $target}})
        )
        RETURN [node in nodes(path) | node.entity_name] as path_names,
               [rel in relationships(path) | type(rel)] as rel_types
        """

        results = await self._adapter.query_cypher(
            cypher,
            graph_id=graph_id,
            params={"source": source_entity, "target": target_entity}
        )

        return results
```

---

## 最佳实践

### 1. 状态定义最佳实践

```python
# ✅ 推荐：使用类型注解和 reducer
from typing import TypedDict, List, Annotated
from operator import add

class GoodState(TypedDict):
    """使用累加器避免数据丢失"""
    context: Annotated[List[str], add]      # 自动累加
    retrieval_count: Annotated[int, add]    # 自动计数
    error: Optional[str]                     # 不需要累加

# ❌ 避免：使用普通列表会覆盖数据
class BadState(TypedDict):
    """每次更新都会覆盖之前的数据"""
    context: List[str]      # 错误：会被覆盖
    retrieval_count: int    # 错误：会丢失计数
```

### 2. 异步操作最佳实践

```python
# ✅ 推荐：使用 asyncio.gather 并行执行
async def parallel_retrieval(state):
    tasks = [
        retrieve_from_graph(state),
        retrieve_from_vector(state),
        retrieve_from_docs(state),
    ]
    results = await asyncio.gather(*tasks)
    return merge_results(results)

# ❌ 避免：顺序执行导致性能低下
async def sequential_retrieval(state):
    result1 = await retrieve_from_graph(state)      # 等待
    result2 = await retrieve_from_vector(state)     # 等待
    result3 = await retrieve_from_docs(state)       # 等待
    return merge_results([result1, result2, result3])
```

### 3. 错误处理最佳实践

```python
# ✅ 推荐：使用自定义异常和详细上下文
from src.core.exceptions import QueryError, ValidationError

async def safe_query(state):
    try:
        result = await adapter.query(state["query"])
        return {"answer": result}
    except ValidationError as e:
        # 参数错误，返回友好提示
        return {
            "error": f"查询参数错误: {e.message}",
            "suggestion": e.suggestion
        }
    except Exception as e:
        # 未知错误，记录日志并返回通用错误
        logger.error(f"查询失败: {e}", exc_info=True)
        raise QueryError(
            "查询执行失败",
            query_text=state["query"],
            details={"original_error": str(e)}
        ) from e
```

### 4. LLM 调用最佳实践

```python
# ✅ 推荐：使用系统提示和结构化输出
async def structured_llm_call(state):
    response = await llm.ainvoke([
        SystemMessage(content="""你是专业的医疗知识助手。

请按照以下 JSON 格式回答:
{
    "answer": "答案内容",
    "confidence": 0.95,
    "sources": ["来源1", "来源2"]
}"""),
        HumanMessage(content=f"问题: {state['query']}")
    ])

    # 解析 JSON 响应
    import json
    return json.loads(response.content)

# ❌ 避免：缺少结构化的自由文本输出
async def unstructured_llm_call(state):
    response = await llm.ainvoke([
        HumanMessage(content=f"回答: {state['query']}")
    ])

    # 难以解析和验证
    return {"answer": response.content}
```

### 5. 工作流设计最佳实践

```python
# ✅ 推荐：使用条件边实现智能路由
workflow.add_conditional_edges(
    "analyze_query",
    should_use_rag,  # 路由函数
    {
        "direct": "generate_answer",    # 简单查询直接生成
        "rag": "retrieve_context",       # 复杂查询使用 RAG
        "end": END                       # 无法处理的查询结束
    }
)

# ✅ 推荐：使用累加器收集多路径结果
workflow.add_node("merge_results", merge_node)
workflow.add_edge("rag_path", "merge_results")
workflow.add_edge("direct_path", "merge_results")
workflow.add_edge("merge_results", "generate_answer")

# ❌ 避免：复杂的嵌套条件逻辑
workflow.add_conditional_edges(
    "analyze_query",
    lambda s: "rag" if s["complex"] == "high"
              else "direct" if s["complex"] == "low"
              else "end",
    # 过多分支难以维护
)
```

### 6. 测试最佳实践

```python
# tests/interventional/test_agents.py

import pytest
from src.agents.workflows.interventional import create_interventional_workflow

@pytest.mark.asyncio
async def test_interventional_workflow_basic():
    """测试介入手术工作流基础功能"""

    # 准备
    adapter = create_mock_adapter()
    workflow = create_interventional_workflow(adapter)

    # 执行
    result = await workflow.ainvoke({
        "patient_data": {"age": 65},
        "procedure_type": "PCI",
    })

    # 验证
    assert "recommendations" in result
    assert len(result.get("devices", [])) > 0
    assert len(result.get("risks", [])) > 0

@pytest.mark.asyncio
async def test_interventional_workflow_with_llm_failure():
    """测试 LLM 失败时的处理"""

    adapter = create_mock_adapter()
    llm = create_failing_llm()  # 模拟失败的 LLM
    workflow = create_interventional_workflow(adapter)

    with pytest.raises(Exception):
        await workflow.ainvoke({
            "patient_data": {"age": 65},
            "procedure_type": "PCI",
        }, config={"configurable": {"llm": llm}})
```

### 7. 日志记录最佳实践

```python
# src/core/logging.py

import structlog

# 配置结构化日志
logger = structlog.get_logger()

# ✅ 推荐：使用结构化日志
logger.info(
    "query_executed",
    query_id=query_id,
    mode=mode,
    latency_ms=latency,
    retrieval_count=retrieval_count,
    entity_count=len(entities),
)

# ❌ 避免：使用非结构化日志
logger.info(
    f"查询 {query_id} 完成，"
    f"耗时 {latency}ms，"
    f"检索到 {retrieval_count} 次"
)
```

---

## 附录

### A. 相关文档链接

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [Neo4j Cypher 手册](https://neo4j.com/docs/cypher-manual/)
- [Milvus 文档](https://milvus.io/docs)

### B. 常见问题

#### Q1: LightRAG 初始化失败怎么办？

```python
# 确保调用初始化方法
adapter = RAGAnythingAdapter(config)
await adapter.initialize()  # 必需！

# 设置环境变量
os.environ["NEO4J_URI"] = config.neo4j_uri
os.environ["MILVUS_URI"] = config.milvus_uri
```

#### Q2: LangGraph 工作流如何调试？

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 使用 LangSmith 追踪
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"

# 可视化工作流
from src.agents.visualization import visualize_workflow
visualize_workflow(workflow, format="png", output_path="workflow.png")
```

#### Q3: 如何处理大文件摄入？

```python
# 分块摄入大文件
async def ingest_large_file(file_path: str, chunk_size: int = 10000):
    with open(file_path, 'r') as f:
        while True:
            chunk = f.readlines(chunk_size)
            if not chunk:
                break
            text = ''.join(chunk)
            await adapter.ingest_text(text)
```

---

**版本**: v1.0.0
**更新日期**: 2026-01-11
**维护者**: Medical Graph RAG Team
