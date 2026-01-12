# 设计文档：基于 RAG-Anything 重构架构

## 目录

1. [架构概览](#架构概览)
2. [模块设计](#模块设计)
3. [数据流](#数据流)
4. [接口设计](#接口设计)
5. [技术决策](#技术决策)
6. [迁移路径](#迁移路径)

---

## 架构概览

### 当前架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Medical-Graph-RAG                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Top-Level   │      │ Mid-Level    │      │ Bot-Level    │  │
│  │ (Patient)    │◄────►│ (Books/Papers)│◄────►│ (UMLS Dict)  │  │
│  │  Neo4j GID1  │      │  Neo4j GID2  │      │  Neo4j GID3  │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         ▲                     ▲                     ▲          │
│         │                     │                     │          │
│         └─────────────────────┴─────────────────────┘          │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │  nano_graphrag      │                     │
│                    │  (自定义实现)        │                     │
│                    │  - 实体提取          │                     │
│                    │  - 图构建 (NetworkX) │                     │
│                    │  - 向量存储 (Milvus) │                     │
│                    │  - 社区检测          │                     │
│                    └─────────────────────┘                     │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │  agentic_chunker    │                     │
│                    │  (智能分块)          │                     │
│                    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### 目标架构（重构后）

```
┌─────────────────────────────────────────────────────────────────┐
│                    Medical-Graph-RAG v2.0                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Top-Level   │      │ Mid-Level    │      │ Bot-Level    │  │
│  │ (Patient)    │◄────►│ (Books/Papers)│◄────►│ (UMLS Dict)  │  │
│  │  Neo4j GID1  │      │  Neo4j GID2  │      │  Neo4j GID3  │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         ▲                     ▲                     ▲          │
│         │                     │                     │          │
│         └─────────────────────┴─────────────────────┘          │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │  RAGAdapter         │                     │
│                    │  (适配器层)          │                     │
│                    │  - 封装 RAGAnything  │                     │
│                    │  - gid 管理          │                     │
│                    │  - 医学领域定制       │                     │
│                    └─────────────────────┘                     │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │  RAG-Anything       │                     │
│                    │  (LightRAG 核心)     │                     │
│                    │  - 实体提取          │                     │
│                    │  - 图构建            │                     │
│                    │  - 向量存储          │                     │
│                    │  - 社区检测          │                     │
│                    │  - 多模态支持        │                     │
│                    └─────────────────────┘                     │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │  存储后端            │                     │
│                    │  - Neo4j (图)        │                     │
│                    │  - Milvus (向量)     │                     │
│                    │  - JSON (KV)         │                     │
│                    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 模块设计

### 1. 核心适配器模块 (`medgraphrag/rag_adapter.py`)

**职责**: 封装 RAG-Anything 功能，提供与现有系统兼容的接口

```python
from raganything import RAGAnything, RAGAnythingConfig
from camel.storages import Neo4jGraph
from typing import Dict, List, Optional
import asyncio

class RAGAdapter:
    """
    RAG-Anything 适配器，用于 Medical GraphRAG 系统。

    主要功能：
    1. 封装 RAGAnything 的初始化和配置
    2. 处理医学领域特定的实体类型
    3. 管理 gid（graph ID）用于三层架构
    4. 与 Neo4j 图数据库集成
    """

    def __init__(
        self,
        working_dir: str,
        gid: str,
        neo4j_graph: Neo4jGraph,
        llm_model_func: callable,
        embedding_func: callable,
        entity_types: Optional[List[str]] = None
    ):
        """
        初始化 RAG 适配器

        Args:
            working_dir: 工作目录，用于存储临时文件和缓存
            gid: Graph ID，用于区分三层架构中的不同层级
            neo4j_graph: Neo4j 图数据库连接
            llm_model_func: LLM 模型函数
            embedding_func: 嵌入函数
            entity_types: 医学实体类型列表
        """
        self.gid = gid
        self.neo4j_graph = neo4j_graph

        # 默认医学实体类型
        if entity_types is None:
            self.entity_types = [
                "Disease", "Symptom", "Treatment", "Medication", "Test",
                "Anatomy", "Procedure", "Condition", "Measurement", "Hormone",
                "Diagnostic_Criteria", "Clinical_Guideline", "Patient", "Doctor"
            ]
        else:
            self.entity_types = entity_types

        # 配置 RAGAnything
        self.config = RAGAnythingConfig(
            working_dir=working_dir,
            enable_image_processing=False,  # 默认关闭，可配置
            enable_table_processing=False,
            enable_equation_processing=False,
        )

        # 初始化 RAGAnything
        self.rag = RAGAnything(
            config=self.config,
            llm_model_func=llm_model_func,
            embedding_func=embedding_func,
        )

    async def process_content(
        self,
        content: str,
        use_grained_chunking: bool = False
    ) -> Dict[str, List]:
        """
        处理内容，提取实体和关系

        Args:
            content: 文本内容
            use_grained_chunking: 是否使用细粒度分块

        Returns:
            包含 entities 和 relationships 的字典
        """
        # 使用 RAGAnything 的 insert 功能
        # 这将自动进行分块、实体提取、关系构建
        await self.rag.ainsert(content)

        # 获取提取的实体和关系
        # 通过 RAGAnything 的查询接口获取
        entities, relationships = await self._extract_entities_and_relationships()

        return {
            "entities": entities,
            "relationships": relationships
        }

    async def _extract_entities_and_relationships(self) -> tuple:
        """
        从 RAGAnything 的内部存储中提取实体和关系

        Returns:
            (entities, relationships) 元组
        """
        # 这里需要根据 RAG-Anything 的实际 API 实现
        # 可能需要直接访问其内部存储或使用特定的查询方法
        pass

    async def insert_to_neo4j(
        self,
        entities: List[Dict],
        relationships: List[Dict]
    ):
        """
        将提取的实体和关系插入 Neo4j

        Args:
            entities: 实体列表
            relationships: 关系列表
        """
        # 实现与现有 Neo4j 模式的兼容插入
        pass

    async def query(
        self,
        question: str,
        mode: str = "hybrid"
    ) -> str:
        """
        执行查询

        Args:
            question: 查询问题
            mode: 查询模式 (local/global/hybrid)

        Returns:
            查询结果
        """
        return await self.rag.aquery(question, mode=mode)

    async def link_to_other_graph(self, other_gid: str):
        """
        链接到其他层级的图谱

        Args:
            other_gid: 要链接的其他图 ID
        """
        # 实现跨层级链接逻辑
        pass
```

### 2. Neo4j 存储后端 (`medgraphrag/neo4j_storage.py`)

**职责**: 为 LightRAG 提供 Neo4j 存储后端

```python
from lightrag.base import BaseGraphStorage, BaseKVStorage, BaseVectorStorage
from camel.storages import Neo4jGraph
from typing import Dict, List, Optional, Any
import numpy as np

class Neo4jGraphStorage(BaseGraphStorage):
    """
    Neo4j 图存储实现，支持三层架构的 gid 机制
    """

    def __init__(
        self,
        namespace: str,
        global_config: Dict[str, Any],
        neo4j_graph: Neo4jGraph,
        gid: str
    ):
        """
        初始化 Neo4j 图存储

        Args:
            namespace: 命名空间
            global_config: 全局配置
            neo4j_graph: Neo4j 连接
            gid: Graph ID，用于区分层级
        """
        super().__init__(namespace, global_config)
        self.neo4j_graph = neo4j_graph
        self.gid = gid

    async def upsert_node(
        self,
        node_id: str,
        node_data: Dict[str, Any]
    ):
        """
        插入或更新节点

        节点数据结构：
        {
            "entity_name": "实体名称",
            "entity_type": "实体类型",
            "description": "描述",
            "embedding": [向量]
        }
        """
        entity_name = node_data.get("entity_name", node_id)
        entity_type = node_data.get("entity_type", "Entity")
        description = node_data.get("description", "")
        embedding = node_data.get("embedding")

        # 创建或更新节点的 Cypher 查询
        query = f"""
        MERGE (n:`{entity_type}` {{id: $id, gid: $gid}})
        ON CREATE SET
            n.description = $description,
            n.embedding = $embedding,
            n.source = 'rag_anything'
        ON MATCH SET
            n.description = CASE WHEN n.description IS NULL OR n.description = ''
                                 THEN $description
                                 ELSE n.description END,
            n.embedding = CASE WHEN n.embedding IS NULL
                               THEN $embedding
                               ELSE n.embedding END
        RETURN n
        """

        params = {
            "id": entity_name.upper(),
            "gid": self.gid,
            "description": description,
            "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        }

        self.neo4j_graph.query(query, params)

    async def upsert_edge(
        self,
        source_id: str,
        target_id: str,
        edge_data: Dict[str, Any]
    ):
        """
        插入或更新关系
        """
        source_id = source_id.upper()
        target_id = target_id.upper()

        # 根据描述推断关系类型
        edge_type = "RELATED_TO"
        description = edge_data.get("description", "").lower()

        if "treat" in description or "cure" in description:
            edge_type = "TREATS"
        elif "cause" in description or "lead" in description:
            edge_type = "CAUSES"
        elif "diagnose" in description or "indicate" in description:
            edge_type = "INDICATES"
        elif "symptom" in description or "manifest" in description:
            edge_type = "HAS_SYMPTOM"

        query = f"""
        MATCH (a {{id: $source_id, gid: $gid}})
        MATCH (b {{id: $target_id, gid: $gid}})
        MERGE (a)-[r:{edge_type}]->(b)
        ON CREATE SET
            r.description = $description,
            r.strength = $strength
        RETURN r
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "gid": self.gid,
            "description": edge_data.get("description", ""),
            "strength": edge_data.get("strength", "")
        }

        self.neo4j_graph.query(query, params)

    async def get_node(self, node_id: str) -> Optional[Dict]:
        """获取节点"""
        query = """
        MATCH (n {id: $id, gid: $gid})
        RETURN n
        """
        result = self.neo4j_graph.query(query, {"id": node_id.upper(), "gid": self.gid})
        if result:
            return result[0]["n"]
        return None

    async def get_edge(
        self,
        source_id: str,
        target_id: str
    ) -> Optional[Dict]:
        """获取关系"""
        query = """
        MATCH (a {id: $source_id, gid: $gid})-[r]->(b {id: $target_id, gid: $gid})
        RETURN r
        """
        result = self.neo4j_graph.query(query, {
            "source_id": source_id.upper(),
            "target_id": target_id.upper(),
            "gid": self.gid
        })
        if result:
            return result[0]["r"]
        return None

    async def node_exists(self, node_id: str) -> bool:
        """检查节点是否存在"""
        node = await self.get_node(node_id)
        return node is not None

    async def edge_exists(
        self,
        source_id: str,
        target_id: str
    ) -> bool:
        """检查关系是否存在"""
        edge = await self.get_edge(source_id, target_id)
        return edge is not None

    async def get_node_neighbors(
        self,
        node_id: str,
        direction: str = "both"
    ) -> List[Dict]:
        """获取节点的邻居"""
        if direction == "both":
            pattern = "(n)-[r]-(neighbor)"
        elif direction == "out":
            pattern = "(n)-[r]->(neighbor)"
        else:  # in
            pattern = "(n)<-[r]-(neighbor)"

        query = f"""
        MATCH (n {{id: $id, gid: $gid}})
        MATCH {pattern}
        RETURN neighbor, r
        """
        result = self.neo4j_graph.query(query, {"id": node_id.upper(), "gid": self.gid})
        return result

    async def index_done_callback(self):
        """索引完成回调"""
        pass
```

### 3. 配置模块 (`medgraphrag/config.py`)

**职责**: 管理医学领域特定的配置

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class MedicalRAGConfig:
    """
    Medical GraphRAG 配置
    """
    # 医学实体类型
    entity_types: List[str] = field(default_factory=lambda: [
        "Disease", "Symptom", "Treatment", "Medication", "Test",
        "Anatomy", "Procedure", "Condition", "Measurement", "Hormone",
        "Diagnostic_Criteria", "Clinical_Guideline", "Patient", "Doctor"
    ])

    # 实体提取参数
    entity_extract_max_gleaning: int = 1
    entity_summary_max_tokens: int = 500

    # 分块参数
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100

    # 图聚类参数
    graph_cluster_algorithm: str = "leiden"
    max_graph_cluster_size: int = 10

    # 查询模式
    default_query_mode: str = "hybrid"

    # 三层架构配置
    top_level_gid: str = "top_level"
    mid_level_gid: str = "mid_level"
    bot_level_gid: str = "bot_level"

    # 多模态处理
    enable_image_processing: bool = False
    enable_table_processing: bool = False
    enable_equation_processing: bool = False

    # 存储配置
    use_neo4j_for_graph: bool = True
    use_milvus_for_vectors: bool = True
```

---

## 数据流

### 1. 图构建流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        图构建流程                                │
└──────────────────────────────────────────────────────────────────┘

输入数据 (PDF/TXT/Excel)
        │
        ▼
┌───────────────────┐
│  数据加载         │  dataloader.py
│  load_high()      │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐      ┌───────────────────┐
│  分块处理         │◄─────│  可选: 细粒度分块  │
│  - RAGAnything    │      │  agentic_chunker  │
│    内置分块       │      │                   │
└─────────┬─────────┘      └───────────────────┘
          │
          ▼
┌───────────────────┐
│  实体提取         │  RAG-Anything (LightRAG)
│  - 使用医学提示词 │
│  - 提取实体类型   │
│  - 提取关系       │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  图构建           │  LightRAG
│  - 创建节点       │
│  - 创建关系       │
│  - 社区检测       │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  写入 Neo4j       │  Neo4jGraphStorage
│  - 添加 gid 标签  │
│  - 保留医学模式   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  后处理           │
│  - 图内合并       │  merge_similar_nodes()
│  - 跨图链接       │  link_context()
│  - 摘要节点       │  add_sum()
└───────────────────┘
```

### 2. 查询流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        查询流程                                  │
└──────────────────────────────────────────────────────────────────┘

用户问题
    │
    ▼
┌───────────────────┐
│  问题预处理       │
│  - 摘要生成       │  summerize.py
│  - 关键词提取     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  图遍历           │  seq_ret()
│  - 从摘要节点开始 │
│  - 遍历相关子图   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐      ┌───────────────────┐
│  RAG 查询        │◄─────│  跨层级查询       │
│  - local 模式    │      │  trinity 模式     │
│  - global 模式   │      │                   │
│  - hybrid 模式   │      │                   │
└─────────┬─────────┘      └───────────────────┘
          │
          ▼
┌───────────────────┐
│  上下文收集       │
│  - 实体信息       │
│  - 关系信息       │
│  - 社区报告       │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  生成回答         │  LLM
│  - 结合上下文     │
│  - 引用来源       │
└───────────────────┘
```

---

## 接口设计

### 1. 命令行接口（保持兼容）

```bash
# 简单模式（单文档 RAG）
python run.py -simple

# 构建图谱
python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -construct_graph -grained_chunk -ingraphmerge

# 三层架构
python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -construct_graph -trinity -trinity_gid1 <mid_gid> -trinity_gid2 <bot_gid>

# 推理
python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -inference
```

### 2. Python API

```python
from medgraphrag import MedicalGraphRAG
from camel.storages import Neo4jGraph
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
import os

# 初始化
neo4j = Neo4jGraph(
    url=os.getenv("NEO4J_URL"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

# 创建 LLM 函数
llm_func = lambda prompt, **kwargs: openai_complete_if_cache(
    "gpt-4o-mini", prompt, api_key=os.getenv("OPENAI_API_KEY"), **kwargs
)

# 创建嵌入函数
embedding_func = EmbeddingFunc(
    embedding_dim=1536,
    max_token_size=8192,
    func=lambda texts: openai_embed(
        texts, model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
    )
)

# 初始化 MedicalGraphRAG
mgr = MedicalGraphRAG(
    working_dir="./medgraph_storage",
    gid="patient_001",
    neo4j_graph=neo4j,
    llm_model_func=llm_func,
    embedding_func=embedding_func
)

# 插入文档
await_mgr.ainsert("患者病历内容...")

# 查询
result = await_mgr.aquery("患者的主要症状是什么？", mode="hybrid")
print(result)

# 链接到其他层级
await_mgr.link_to_other_graph("umls_dict")
```

---

## 技术决策

### 决策 1: 使用适配器模式而非直接替换

**问题**: 是否直接替换 `nano_graphrag` 还是使用适配器？

**决策**: 使用适配器模式

**理由**:
1. 保留对三层架构的完整控制
2. 可以逐步迁移，降低风险
3. 保持现有 API 的兼容性
4. 便于添加医学领域特定的逻辑

### 决策 2: Neo4j 存储后端的实现方式

**问题**: 如何实现 Neo4j 存储后端？

**决策**: 实现 LightRAG 的 `BaseGraphStorage` 接口

**理由**:
1. 符合 LightRAG 的扩展机制
2. 可以完全控制 Neo4j 的查询和存储逻辑
3. 保留现有的 `gid` 机制
4. 支持三层架构的特殊需求

### 决策 3: 分块策略

**问题**: 使用 RAG-Anything 的分块还是保留 `agentic_chunker`？

**决策**: 提供配置选项，默认使用 RAG-Anything 的分块

**理由**:
1. RAG-Anything 的分块与实体提取紧密集成
2. 减少系统复杂度
3. 保留 `agentic_chunker` 作为高级选项
4. 用户可以根据需求选择

### 决策 4: 多模态支持

**问题**: 是否启用多模态功能？

**决策**: 作为可选功能，默认关闭

**理由**:
1. 当前项目主要处理文本医学数据
2. 多模态处理需要额外的资源（VLM 模型）
3. 作为可选功能，未来可以启用
4. 不增加当前部署的复杂度

---

## 迁移路径

### 阶段 1: 并行运行（验证阶段）

```
┌────────────────────────────────────────────────────────┐
│                     迁移阶段 1                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────┐         ┌──────────────┐            │
│  │ 旧实现       │         │ 新实现       │            │
│  │ nano_graphrag│         │ RAG-Anything │            │
│  └──────────────┘         └──────────────┘            │
│         │                       │                      │
│         └──────────┬────────────┘                      │
│                    ▼                                   │
│         ┌──────────────────┐                          │
│         │   结果对比        │                          │
│         │   - 实体数量      │                          │
│         │   - 关系数量      │                          │
│         │   - 查询质量      │                          │
│         └──────────────────┘                          │
└────────────────────────────────────────────────────────┘
```

### 阶段 2: 逐步切换

```
┌────────────────────────────────────────────────────────┐
│                     迁移阶段 2                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────┐         │
│  │          MedicalGraphRAG                │         │
│  │  ┌─────────────────────────────────┐    │         │
│  │  │  RAGAdapter (适配器)            │    │         │
│  │  └────────────┬────────────────────┘    │         │
│  │               │                          │         │
│  │  ┌────────────▼────────────────────┐    │         │
│  │  │  backend = "lightrag" (新)      │    │         │
│  │  │  backend = "legacy" (旧)        │    │         │
│  │  └─────────────────────────────────┘    │         │
│  └──────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────┘
```

### 阶段 3: 完全迁移

```
┌────────────────────────────────────────────────────────┐
│                     迁移阶段 3                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────┐         │
│  │          MedicalGraphRAG v2.0           │         │
│  │                                          │         │
│  │  ┌─────────────────────────────────┐    │         │
│  │  │  RAGAdapter                     │    │         │
│  │  └────────────┬────────────────────┘    │         │
│  │               │                          │         │
│  │  ┌────────────▼────────────────────┐    │         │
│  │  │  RAG-Anything (LightRAG)        │    │         │
│  │  └─────────────────────────────────┘    │         │
│  └──────────────────────────────────────────┘         │
│                                                        │
│  ~~ nano_graphrag (已移除) ~~                          │
└────────────────────────────────────────────────────────┘
```

---

## 向后兼容性

### 保证的兼容性

1. **命令行参数**: 所有现有参数保持不变
2. **输入格式**: 数据输入格式不变
3. **Neo4j 模式**: 节点和关系结构保持兼容
4. **查询输出**: 输出格式保持一致

### 需要的迁移步骤

对于现有用户：

1. 更新依赖：`pip install -r requirements.txt`
2. 运行测试确保兼容性
3. 可选：重新构建图以获得更好的实体提取质量

---

## 性能考虑

### 预期性能变化

| 操作 | 当前实现 | 新实现 | 预期变化 |
|------|---------|--------|---------|
| 实体提取 | GPT-4o-mini | GPT-4o-mini | 相似 |
| 图构建 | NetworkX (内存) | NetworkX/Milvus | 相似或更好 |
| 向量搜索 | MilvusLite | Milvus | 相似 |
| 社区检测 | Leiden | Leiden | 相同 |
| 查询响应 | local/global | local/global/hybrid | 相似或更好 |

### 优化点

1. 使用 RAG-Anything 的缓存机制减少 LLM 调用
2. 利用 LightRAG 的批处理能力
3. 可选使用更快的向量数据库

---

## 安全性考虑

1. **API 密钥管理**: 继续使用环境变量
2. **数据隐私**: 医疗数据仍然只在本地/私有云处理
3. **访问控制**: Neo4j 的认证机制保持不变

---

## 总结

本重构通过引入 RAG-Anything 框架，实现了以下目标：

1. **简化代码库**: 移除约 1500+ 行自定义 GraphRAG 代码
2. **利用成熟库**: 使用经过验证的开源实现
3. **保持兼容性**: 通过适配器模式保持现有接口
4. **保留特色**: 三层架构、医学领域定制等特色功能
5. **未来扩展**: 获得多模态处理等新能力
