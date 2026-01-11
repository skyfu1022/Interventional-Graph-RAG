# LangGraph 节点函数使用指南

本文档展示如何使用已实现的 LangGraph 节点函数。

## 目录

1. [查询工作流节点](#查询工作流节点)
2. [图谱构建工作流节点](#图谱构建工作流节点)
3. [介入手术智能体节点](#介入手术智能体节点)
4. [参数传递方式](#参数传递方式)
5. [完整示例](#完整示例)

---

## 查询工作流节点

### 1. analyze_query_node

分析查询复杂度。

```python
from src.agents.nodes import analyze_query_node
from src.agents.states import QueryState

# 准备状态
state: QueryState = {
    "query": "什么是高血压？",
    "graph_id": "medical_graph_001",
}

# 调用节点函数
result = analyze_query_node(state)

# 结果
# {
#     "query_complexity": "simple",  # simple, medium, complex
#     "retrieval_count": 0,
#     "max_retries": 3
# }
```

### 2. retrieve_node

从知识图谱检索相关上下文。

```python
from src.agents.nodes import retrieve_node
from langgraph.types import RunnableConfig

# 准备状态
state: QueryState = {
    "query": "高血压的治疗方法",
    "graph_id": "medical_graph_001",
    "retrieval_count": 0,
}

# 准备配置（包含 RAG 适配器）
config = RunnableConfig(
    configurable={
        "rag_adapter": rag_adapter,  # RAGAnythingAdapter 实例
    }
)

# 异步调用节点函数
result = await retrieve_node(state, config)

# 结果
# {
#     "context": ["上下文1", "上下文2", ...],
#     "sources": ["来源1", "来源2", ...],
#     "retrieval_count": 1,
#     "error": None
# }
```

### 3. grade_documents_node

评估检索文档的相关性。

```python
from src.agents.nodes import grade_documents_node

# 准备状态（包含检索结果）
state: QueryState = {
    "query": "高血压的治疗方法",
    "context": [
        "高血压的药物治疗包括...",
        "高血压的非药物治疗包括...",
    ],
    "retrieval_count": 1,
    "max_retries": 3,
}

# 调用节点函数
result = await grade_documents_node(state)

# 结果
# {
#     "relevance": "relevant",  # relevant, refine, end
#     "error": None
# }
```

### 4. generate_answer_node

基于上下文生成答案。

```python
from src.agents.nodes import generate_answer_node

# 准备状态
state: QueryState = {
    "query": "高血压的治疗方法",
    "context": ["上下文1", "上下文2"],
    "sources": ["来源1", "来源2"],
    "query_complexity": "medium",
}

# 准备配置（包含 LLM）
config = RunnableConfig(
    configurable={
        "llm": llm,  # BaseChatModel 实例
    }
)

# 异步调用节点函数
result = await generate_answer_node(state, config)

# 结果
# {
#     "answer": "基于知识图谱检索结果，高血压的治疗方法包括...",
#     "error": None
# }
```

### 5. refine_query_node

优化查询表达式。

```python
from src.agents.nodes import refine_query_node

# 准备状态
state: QueryState = {
    "query": "高血压",
    "context": [],  # 检索结果不理想
    "retrieval_count": 1,
}

# 准备配置（包含 LLM）
config = RunnableConfig(
    configurable={
        "llm": llm,
    }
)

# 异步调用节点函数
result = await refine_query_node(state, config)

# 结果
# {
#     "query": "高血压 详细说明 临床表现 诊断 治疗",  # 优化后的查询
#     "error": None
# }
```

---

## 图谱构建工作流节点

### 1. load_document_node

加载文档文件。

```python
from src.agents.nodes import load_document_node
from src.agents.states import BuildState

# 准备状态
state: BuildState = {
    "file_path": "/path/to/medical_document.pdf",
    "graph_id": "medical_graph_001",
    "merge_enabled": False,
    "status": "pending",
    "document_count": 0,
}

# 准备配置（包含 RAG 适配器）
config = RunnableConfig(
    configurable={
        "rag_adapter": rag_adapter,
    }
)

# 异步调用节点函数
result = await load_document_node(state, config)

# 结果
# {
#     "status": "extracting",
#     "document_count": 1,
#     "error": None
# }
```

### 2. extract_entities_node

从文档中提取实体和关系。

```python
from src.agents.nodes import extract_entities_node

# 准备状态
state: BuildState = {
    "file_path": "/path/to/medical_document.pdf",
    "graph_id": "medical_graph_001",
    "status": "extracting",
}

# 异步调用节点函数
result = await extract_entities_node(state, config)

# 结果
# {
#     "status": "building",
#     "entity_count": 150,
#     "relationship_count": 200,
#     "error": None
# }
```

### 3. build_graph_node

在图数据库中构建图谱。

```python
from src.agents.nodes import build_graph_node

# 准备状态
state: BuildState = {
    "graph_id": "medical_graph_001",
    "merge_enabled": True,
    "status": "building",
}

# 异步调用节点函数
result = await build_graph_node(state, config)

# 结果（如果 merge_enabled=True）
# {
#     "status": "merging",
#     "error": None
# }
```

### 4. merge_nodes_node

合并相似节点。

```python
from src.agents.nodes import merge_nodes_node

# 准备状态
state: BuildState = {
    "graph_id": "medical_graph_001",
    "status": "merging",
}

# 异步调用节点函数
result = await merge_nodes_node(state, config)

# 结果
# {
#     "status": "completed",
#     "error": None
# }
```

### 5. create_summary_node

创建社区摘要。

```python
from src.agents.nodes import create_summary_node

# 准备状态
state: BuildState = {
    "graph_id": "medical_graph_001",
    "status": "completed",
}

# 异步调用节点函数
result = await create_summary_node(state, config)

# 结果
# {
#     "status": "completed",
#     "error": None
# }
```

---

## 介入手术智能体节点

### 1. analyze_patient_node

分析患者数据。

```python
from src.agents.nodes import analyze_patient_node

# 准备状态
state = {
    "patient_data": {
        "age": 65,
        "gender": "男",
        "diagnosis": "冠心病",
    },
    "procedure_type": "PCI",
}

# 异步调用节点函数
result = await analyze_patient_node(state)

# 结果
# {
#     "analysis": "患者数据分析结果"
# }
```

### 2. recommend_devices_node

推荐介入器械。

```python
from src.agents.nodes import recommend_devices_node

# 准备状态
state = {
    "patient_data": {...},
    "procedure_type": "PCI",
}

# 准备配置（包含 LLM）
config = RunnableConfig(
    configurable={
        "llm": llm,
    }
)

# 异步调用节点函数
result = await recommend_devices_node(state, config)

# 结果
# {
#     "devices": ["推荐器械1", "推荐器械2", ...],
#     "error": None
# }
```

### 3. assess_risks_node

评估手术风险。

```python
from src.agents.nodes import assess_risks_node

# 准备状态
state = {
    "patient_data": {...},
    "procedure_type": "PCI",
}

# 异步调用节点函数
result = await assess_risks_node(state, config)

# 结果
# {
#     "risks": ["风险1", "风险2", ...],
#     "error": None
# }
```

### 4. generate_recommendations_node

生成完整推荐方案。

```python
from src.agents.nodes import generate_recommendations_node

# 准备状态
state = {
    "patient_data": {...},
    "procedure_type": "PCI",
    "devices": ["器械1", "器械2"],
    "risks": ["风险1", "风险2"],
}

# 异步调用节点函数
result = await generate_recommendations_node(state, config)

# 结果
# {
#     "recommendations": "完整的手术推荐方案...",
#     "error": None
# }
```

---

## 参数传递方式

### 通过 RunnableConfig 传递参数

LangGraph 节点函数通过 `RunnableConfig` 的 `configurable` 字段接收外部依赖：

```python
from langgraph.types import RunnableConfig

# 准备配置
config = RunnableConfig(
    configurable={
        "rag_adapter": rag_adapter,  # RAG 适配器
        "llm": llm,                   # LLM 实例
        # 其他自定义参数...
    }
)

# 调用节点时传入 config
result = await retrieve_node(state, config)
```

### 节点函数内部访问参数

```python
async def retrieve_node(state: QueryState, config: Optional[RunnableConfig] = None):
    # 访问 rag_adapter
    if config and "configurable" in config:
        rag_adapter = config["configurable"].get("rag_adapter")
        llm = config["configurable"].get("llm")

        # 使用适配器和 LLM...
```

---

## 完整示例

### 示例 1: 创建查询工作流

```python
from langgraph.graph import StateGraph, START, END
from src.agents.states import QueryState
from src.agents.nodes import (
    analyze_query_node,
    retrieve_node,
    grade_documents_node,
    generate_answer_node,
    refine_query_node,
)
from langchain_openai import ChatOpenAI

# 创建 LLM 实例
llm = ChatOpenAI(model="gpt-4")

# 创建状态图
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
    lambda state: "retrieve" if state["query_complexity"] != "simple" else "generate_answer",
    {
        "retrieve": "retrieve",
        "generate_answer": "generate_answer",
    }
)
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    lambda state: state["relevance"],
    {
        "relevant": "generate_answer",
        "refine": "refine_query",
    }
)
workflow.add_edge("refine_query", "retrieve")
workflow.add_edge("generate_answer", END)

# 编译工作流
app = workflow.compile()

# 执行查询
config = {
    "configurable": {
        "rag_adapter": rag_adapter,
        "llm": llm,
    }
}

result = app.invoke(
    {
        "query": "什么是高血压？",
        "graph_id": "medical_graph_001",
    },
    config
)

print(result["answer"])
```

### 示例 2: 创建图谱构建工作流

```python
from langgraph.graph import StateGraph, START, END
from src.agents.states import BuildState
from src.agents.nodes import (
    load_document_node,
    extract_entities_node,
    build_graph_node,
    merge_nodes_node,
    create_summary_node,
)

# 创建状态图
workflow = StateGraph(BuildState)

# 添加节点
workflow.add_node("load_document", load_document_node)
workflow.add_node("extract_entities", extract_entities_node)
workflow.add_node("build_graph", build_graph_node)
workflow.add_node("merge_nodes", merge_nodes_node)
workflow.add_node("create_summary", create_summary_node)

# 添加边
workflow.add_edge(START, "load_document")
workflow.add_edge("load_document", "extract_entities")
workflow.add_edge("extract_entities", "build_graph")
workflow.add_conditional_edges(
    "build_graph",
    lambda state: "merge" if state["merge_enabled"] else "summary",
    {
        "merge": "merge_nodes",
        "summary": "create_summary",
    }
)
workflow.add_edge("merge_nodes", "create_summary")
workflow.add_edge("create_summary", END)

# 编译工作流
app = workflow.compile()

# 执行构建
config = {
    "configurable": {
        "rag_adapter": rag_adapter,
    }
}

result = app.invoke(
    {
        "file_path": "/path/to/document.pdf",
        "graph_id": "medical_graph_001",
        "merge_enabled": True,
    },
    config
)

print(f"构建状态: {result['status']}")
print(f"实体数: {result['entity_count']}")
print(f"关系数: {result['relationship_count']}")
```

---

## 注意事项

1. **异步调用**: 所有涉及外部服务（RAG 适配器、LLM）的节点都是异步函数，需要使用 `await` 调用。

2. **错误处理**: 所有节点函数都包含错误处理，出错时会设置 `error` 字段并返回安全值。

3. **配置传递**: 通过 `RunnableConfig` 的 `configurable` 字段传递 RAG 适配器和 LLM 实例。

4. **状态更新**: 节点函数返回字典，LangGraph 会自动合并到状态中。

5. **类型注解**: 所有节点函数都有完整的类型注解，建议使用类型检查工具（如 mypy）。

---

## 相关文档

- [LangGraph 官方文档](https://github.com/langchain-ai/langgraph)
- [状态定义](/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/agents/states.py)
- [工作流定义](/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/agents/workflows/)
