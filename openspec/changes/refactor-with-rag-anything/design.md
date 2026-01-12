# 设计文档：基于 RAG Anything 的重构架构

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         应用层 (不变)                              │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Web 服务 / LangGraph Agent 工作流                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG 接口适配层 (新增)                          │
├─────────────────────────────────────────────────────────────────┤
│  - MedicalRAG: 统一 RAG 接口                                      │
│  - ThreeLayerGraph: 三层图谱封装                                  │
│  - QueryAdapter: 查询适配器                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RAG Anything (新核心)                          │
├─────────────────────────────────────────────────────────────────┤
│  - 多模态文档解析 (MinerU/Docling)                                │
│  - 实体提取与关系识别                                             │
│  - 知识图谱构建                                                   │
│  - 向量检索与图谱查询                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    存储适配层 (新增)                              │
├─────────────────────────────────────────────────────────────────┤
│  - Neo4jAdapter: 将 LightRAG 存储适配到 Neo4j                     │
│  - MilvusAdapter: 保持现有 Milvus 集成                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      存储层 (保持不变)                            │
├─────────────────────────────────────────────────────────────────┤
│  Neo4j 图数据库         │         Milvus 向量数据库              │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. RAG 接口适配层

**目的**：保持现有 API 兼容，内部使用 RAG Anything 实现

```python
# 新增：medical_rag/adapter.py
class MedicalRAG:
    """统一的 RAG 接口，兼容原有 nano_graphrag 接口"""

    def __init__(self, config):
        # 初始化 RAG Anything
        self.rag_anything = RAGAnything(
            lightrag=...,
            vision_model_func=...,
            embedding_func=...
        )

    async def ainsert(self, documents):
        """兼容原接口的插入方法"""
        # 调用 RAG Anything 的文档处理
        pass

    async def aquery(self, query, mode="hybrid"):
        """兼容原接口的查询方法"""
        # 调用 RAG Anything 的查询
        pass
```

### 2. 三层图谱封装

**目的**：在 RAG Anything 之上实现项目的三层层次化结构

```python
# 新增：medical_rag/three_layer.py
class ThreeLayerGraph:
    """三层层次化图谱结构"""

    def __init__(self):
        self.top_layer = RAGAnything(...)    # 顶层：私有数据
        self.middle_layer = RAGAnything(...) # 中层：书籍和论文
        self.bottom_layer = RAGAnything(...) # 底层：字典数据

    async def query_all_layers(self, query):
        """跨层查询"""
        pass
```

### 3. 存储适配层

**Neo4j 适配器**

RAG Anything/LightRAG 默认使用基于文件的图存储。需要实现适配器将其映射到 Neo4j：

```python
# 新增：medical_rag/storage/neo4j_adapter.py
class Neo4jGraphStorage(BaseGraphStorage):
    """将 LightRAG 的图操作适配到 Neo4j"""

    def __init__(self, neo4j_config):
        self.neo4j = Neo4jGraph.from_config(neo4j_config)

    async def upsert_node(self, node_id, node_data):
        # 将节点写入 Neo4j
        pass

    async def upsert_edge(self, source, target, edge_data):
        # 将关系写入 Neo4j
        pass

    async def get_node(self, node_id):
        # 从 Neo4j 读取节点
        pass

    async def get_edges(self, node_id):
        # 从 Neo4j 读取相关边
        pass
```

## 数据流设计

### 文档处理流程

```
文档输入
    │
    ▼
┌───────────────────┐
│  RAG Anything     │
│  解析器 (MinerU)  │
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────────┐
│  多模态内容提取              │
│  - 文本                      │
│  - 图像                      │
│  - 表格                      │
│  - 公式                      │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  实体与关系提取              │
│  (LightRAG LLM)              │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  三层图谱存储                │
│  (Neo4j 适配层)             │
└─────────────────────────────┘
```

### 查询流程

```
用户查询
    │
    ▼
┌───────────────────┐
│  三层查询路由      │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌─────────┐ ┌──────────┐
│ 本地检索 │ │ 全局检索 │
└────┬────┘ └─────┬────┘
     │            │
     └─────┬──────┘
           ▼
┌─────────────────────────────┐
│  RAG Anything 查询          │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  Neo4j + Milvus 联合查询    │
└─────────┬───────────────────┘
          │
          ▼
    返回结果
```

## 兼容性保证

### 接口兼容

保持 `nano_graphrag` 的主要接口不变：

```python
# 原接口
rag = GraphRAG(...)
await rag.ainsert(documents)
result = await rag.aquery(query, mode="local")

# 新接口 (兼容)
rag = MedicalRAG(...)
await rag.ainsert(documents)
result = await rag.aquery(query, mode="local")
```

### 数据格式兼容

保持节点和边的数据结构：

```python
# 节点格式
{
    "entity_name": str,
    "entity_type": str,
    "description": str,
    "source_id": str
}

# 边格式
{
    "source": str,
    "target": str,
    "relationship": str,
    "weight": float
}
```

## 迁移策略

### 阶段 1：基础设施搭建
1. 添加 RAG Anything 依赖
2. 创建存储适配层
3. 创建接口适配层

### 阶段 2：核心功能迁移
1. 迁移文档处理功能
2. 迁移实体提取功能
3. 迁移图谱构建功能

### 阶段 3：查询功能迁移
1. 迁移本地查询
2. 迁移全局查询
3. 迁移混合查询

### 阶段 4：清理与优化
1. 删除旧的 `nano_graphrag` 代码
2. 更新测试用例
3. 性能对比和优化

## 技术选型

| 组件 | 当前实现 | 新实现 | 理由 |
|------|----------|--------|------|
| 文档解析 | 自实现 | MinerU/Docling | 更强的多模态支持 |
| 实体提取 | LightRAG API | LightRAG API | 保持一致 |
| 图存储 | NetworkX + Neo4j | LightRAG + Neo4j 适配 | 统一存储 |
| 向量存储 | Milvus | Milvus | 保持不变 |
| 多模态处理 | 有限 | ImageModalProcessor 等 | 增强能力 |
