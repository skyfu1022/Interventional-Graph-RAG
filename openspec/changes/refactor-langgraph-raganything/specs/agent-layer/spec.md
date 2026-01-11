# LangGraph 智能体层规范

**依赖版本**：
- **LangGraph**: >= 1.0.3
  - **Context7 Library ID**: `/langchain-ai/langgraph`
  - **Benchmark Score**: 88.5/100
  - **API 兼容性**: 大部分 API 与 0.2.x 兼容，主要变更是检查点相关

## 新增需求

### 需求：LangGraph 工作流编排

系统**必须**使用 LangGraph 实现智能体工作流编排，为介入手术智能体扩展提供基础。

#### 场景：查询工作流执行

**给定**：
- 一个用户查询
- 配置的 LangGraph 查询工作流
- 现有的知识图谱

**当**：启动查询工作流

**那么**：工作流应按以下逻辑执行：

1. **分析查询** (analyze_query)
   - 判断查询复杂度
   - 识别关键实体
   - 确定检索策略

2. **路由决策** (route_query)
   - 简单查询 → 直接生成答案
   - 复杂查询 → 执行检索流程

3. **检索上下文** (retrieve)
   - 调用 RAG-Anything 适配器
   - 从 Milvus 和 Neo4j 检索相关内容
   - 合并检索结果

4. **评估文档** (grade_documents)
   - 使用 LLM 评估检索结果相关性
   - 低相关性 → 优化查询重试
   - 高相关性 → 继续生成

5. **生成答案** (generate_answer)
   - 使用 LLM 基于上下文生成答案
   - 添加引用和来源

**验证**：
```python
from src.agents.workflows.query import create_query_workflow

workflow = create_query_workflow(rag_adapter)
result = await workflow.ainvoke({
    "query": "糖尿病患者的主要症状是什么？",
    "graph_id": "graph-123",
})
assert result["answer"] is not None
assert len(result["sources"]) > 0
```

#### 场景：查询重试循环

**给定**：
- 检索到的文档相关性低
- 最大重试次数为 3

**当**：工作流到达 `grade_documents` 节点

**那么**：
- 应识别相关性不足
- 应转换到 `refine_query` 节点
- 应优化原始查询
- 应重新执行检索
- 最多重试 3 次

---

### 需求：图谱构建工作流

系统**必须**使用 LangGraph 实现图谱构建工作流。

#### 场景：完整的图谱构建流程

**给定**：
- 一个医学文档
- 配置的 LangGraph 构建工作流

**当**：启动构建工作流

**那么**：工作流应按以下逻辑执行：

1. **加载文档** (load_document)
   - 读取文档内容
   - 执行文本分块（chunk_size, overlap）
   - 提取多模态内容（图像、表格等）

2. **提取实体** (extract_entities)
   - 调用 RAG-Anything 的 `ainsert()`
   - RAG-Anything 自动提取医学实体
   - 识别实体类型（DISEASE, MEDICINE, SYMPTOM 等）

3. **构建图谱** (build_graph)
   - 在 Neo4j 中创建节点和关系
   - 存储向量嵌入到 Milvus

4. **合并节点** (merge_nodes) - 可选
   - 基于语义相似度合并重复节点
   - 仅在启用合并时执行

5. **创建摘要** (create_summary)
   - 生成社区摘要
   - 支持全局检索

**验证**：
```python
from src.agents.workflows.build import create_build_workflow

workflow = create_build_workflow(rag_adapter)
result = await workflow.ainvoke({
    "file_path": "/path/to/document.pdf",
    "graph_id": "graph-new",
})
assert result["status"] == "completed"
assert result["entity_count"] > 0
```

---

### 需求：状态管理

系统**必须**定义类型安全的状态类，用于 LangGraph 工作流的状态管理。

#### 场景：查询状态定义

**给定**：查询工作流需要管理状态

**当**：定义 `QueryState` 类

**那么**：状态应包含以下字段：
```python
class QueryState(TypedDict):
    query: str                    # 用户查询
    graph_id: str                 # 图谱 ID
    context: List[Document]       # 检索到的上下文
    answer: str                   # 生成的答案
    sources: List[str]            # 来源引用
    retrieval_count: int          # 检索次数
    max_retries: int              # 最大重试次数
    query_complexity: str         # 查询复杂度
```

**验证**：
```python
from src.agents.states import QueryState

state: QueryState = {
    "query": "糖尿病症状",
    "graph_id": "graph-123",
    "context": [],
    "answer": "",
    "sources": [],
    "retrieval_count": 0,
    "max_retries": 3,
    "query_complexity": "medium",
}
```

#### 场景：构建状态定义

**给定**：构建工作流需要管理状态

**当**：定义 `BuildState` 类

**那么**：状态应包含以下字段：
```python
class BuildState(TypedDict):
    file_path: str              # 文档路径
    graph_id: str               # 图谱 ID
    merge_enabled: bool         # 是否启用节点合并
    status: str                 # 构建状态
    entity_count: int           # 实体数量
    relationship_count: int     # 关系数量
    error: Optional[str]        # 错误信息
```

---

### 需求：节点实现

系统**必须**实现 LangGraph 工作流的所有节点函数。

#### 场景：检索节点实现

**给定**：
- 一个查询状态
- 配置的 RAG-Anything 适配器

**当**：执行 `retrieve_node`

**那么**：
- 应调用 `rag_adapter.query()`
- 应使用 `mode="hybrid"` 检索
- 应更新状态的 `context` 和 `sources` 字段
- 应处理检索错误

**验证**：
```python
from src.agents.nodes import retrieve_node

state = await retrieve_node(
    state={"query": "糖尿病症状", "graph_id": "graph-123"},
    rag_adapter=mock_adapter
)
assert len(state["context"]) > 0
assert len(state["sources"]) > 0
```

#### 场景：文档评估节点实现

**给定**：
- 包含检索上下文的状态
- 配置的 LLM

**当**：执行 `grade_documents_node`

**那么**：
- 应使用 LLM 评估每个文档的相关性
- 应计算平均相关性分数
- 应返回路由决策（relevant/refine/end）

**验证**：
```python
from src.agents.nodes import grade_documents_node

state = await grade_documents_node(
    state={"context": documents, "retrieval_count": 1}
)
assert "route" in state
assert state["route"] in ["relevant", "refine", "end"]
```

---

### 需求：介入手术智能体扩展点

系统**必须**为未来的介入手术智能体提供扩展点。

#### 场景：定义介入手术状态

**给定**：需要扩展介入手术智能体

**当**：定义 `InterventionalState` 类

**那么**：状态应包含介入手术特定字段：
```python
class InterventionalState(TypedDict):
    patient_data: Dict            # 患者数据
    procedure_type: str           # 手术类型
    available_devices: List[str]  # 可用设备
    selected_devices: List[str]   # 选择的设备
    risks: List[str]              # 风险评估
    recommendations: str          # 推荐方案
    step: str                     # 当前步骤
```

#### 场景：定义介入手术工作流节点

**给定**：介入手术智能体需要特定节点

**当**：定义工作流节点

**那么**：应包含以下节点：
- `analyze_patient` - 分析患者数据
- `select_devices` - 选择介入设备
- `assess_risks` - 评估手术风险
- `generate_plan` - 生成手术方案

**验证**：
```python
from src.agents.workflows.interventional import create_interventional_agent

workflow = create_interventional_agent(rag_adapter)
result = await workflow.ainvoke({
    "patient_data": {...},
    "procedure_type": "PCI",
})
assert result["recommendations"] is not None
assert len(result["selected_devices"]) > 0
```

---

### 需求：工作流可组合性

系统**必须**支持工作流的组合和嵌套。

#### 场景：组合多个工作流

**给定**：
- 查询工作流
- 构建工作流

**当**：创建复合工作流

**那么**：
- 应能将一个工作流作为节点嵌入另一个工作流
- 应支持状态传递和转换
- 应支持并行执行多个子工作流

**验证**：
```python
from langgraph.graph import StateGraph

# 创建复合工作流
composite = StateGraph(CompositeState)
composite.add_node("build", build_workflow)
composite.add_node("query", query_workflow)
composite.add_edge("build", "query")
```

---

### 需求：工作流检查点

系统**必须**支持工作流状态检查点，用于长时间运行的工作流恢复。

#### 场景：保存检查点

**给定**：
- 一个长时间运行的构建工作流
- 配置的检查点存储

**当**：工作流到达关键节点

**然后**：
- 应自动保存当前状态
- 应支持从检查点恢复
- 应支持检查点过期和清理

**验证**：
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
workflow = create_build_workflow(checkpointer=memory)

# 执行工作流
config = {"configurable": {"thread_id": "build-123"}}
result = await workflow.ainvoke(initial_state, config)

# 从检查点恢复
restored = await workflow.ainvoke(None, config)
assert restored["status"] == result["status"]
```

**注意**：
- LangGraph 1.0.3 的检查点 API 保持向后兼容
- 新增了更多检查点后端选项（如 Redis、PostgreSQL 等）
- 改进了检查点序列化机制，支持更复杂的状态类型

---

### 需求：工作流可视化

系统**必须**支持工作流图的可视化，便于调试和文档编写。

#### 场景：生成工作流图

**给定**：一个配置的 LangGraph 工作流

**当**：调用 `get_graph()` 方法

**然后**：
- 应返回工作流的 Mermaid 图表
- 应显示所有节点和边
- 应标注条件分支

**验证**：
```python
from src.agents.workflows.query import create_query_workflow

workflow = create_query_workflow(rag_adapter)
graph = workflow.get_graph()
mermaid_code = graph.print_mermaid()
assert "analyze_query" in mermaid_code
assert "retrieve" in mermaid_code
```
