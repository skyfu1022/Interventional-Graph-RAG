# 规范：存储适配层

## 功能 ID
`storage-adapter`

## 新增需求

### 需求：Neo4j 图存储适配器

系统应实现将 LightRAG 的图操作适配到 Neo4j 数据库的适配器。

#### 场景：创建图节点

**给定** 已连接的 Neo4j 实例
**当** 调用 `await adapter.upsert_node(entity_id, entity_data)`
**那么** 应在 Neo4j 中创建或更新节点
**并且** 节点应包含实体名称、类型、描述等属性
**并且** 应使用 `MedicalEntity` 作为节点标签

```python
# 示例
await adapter.upsert_node(
    entity_id="epd_device_001",
    entity_data={
        "entity_name": "远端栓塞保护装置",
        "entity_type": "DEVICE",
        "description": "用于捕获介入治疗过程中脱落的栓子..."
    }
)
```

#### 场景：创建图关系

**给定** 已存在的源节点和目标节点
**当** 调用 `await adapter.upsert_edge(source, target, edge_data)`
**那么** 应在两节点间创建关系
**并且** 关系类型应为 `RELATES_TO` 或指定类型
**并且** 关系应包含权重和描述属性

```python
# 示例
await adapter.upsert_edge(
    source="epd_device_001",
    target="carotid_artery",
    edge_data={
        "relationship": "USED_IN",
        "weight": 0.9,
        "description": "EPD 装置用于颈动脉介入治疗"
    }
)
```

#### 场景：查询节点邻居

**给定** 已存在的节点
**当** 调用 `await adapter.get_node_neighbors(node_id, depth=1)`
**那么** 应返回直接相连的节点和边
**并且** 结果应包含节点详情和关系详情

#### 场景：批量操作

**给定** 多个节点和边需要写入
**当** 调用 `await adapter.batch_upsert(nodes, edges)`
**那么** 应使用事务批量写入
**并且** 失败时应回滚所有更改

#### 场景：节点删除

**给定** 需要删除的节点
**当** 调用 `await adapter.delete_node(node_id)`
**那么** 应删除指定节点
**并且** 应删除与该节点相关的所有边

---

### 需求：Milvus 向量存储适配器

系统应保持与现有 Milvus 向量数据库的兼容。

#### 场景：插入向量

**给定** 已连接的 Milvus 实例
**当** 调用 `await adapter.insert(vectors)`
**那么** 应将向量插入到 `medical_entities` collection
**并且** 应关联元数据（实体 ID、类型等）

```python
# 示例
await adapter.insert([
    {
        "id": "epd_device_001",
        "vector": [0.1, 0.2, ...],  # 1536 维向量
        "metadata": {
            "entity_name": "远端栓塞保护装置",
            "entity_type": "DEVICE"
        }
    }
])
```

#### 场景：相似度搜索

**给定** 查询向量
**当** 调用 `await adapter.search(query_vector, top_k=10)`
**那么** 应返回最相似的 k 个实体
**并且** 结果应按相似度排序
**并且** 结果应包含实体元数据

#### 场景：删除向量

**给定** 需要删除的实体 ID
**当** 调用 `await adapter.delete(entity_ids)`
**那么** 应从 collection 中删除指定向量

---

### 需求：存储工厂

系统应提供统一的存储创建接口。

#### 场景：创建 Neo4j 适配器

**给定** 包含 Neo4j 配置的参数
**当** 调用 `StorageFactory.create_graph_storage(config)`
**那么** 应返回配置好的 `Neo4jGraphStorageAdapter` 实例
**并且** 应验证连接成功

#### 场景：创建 Milvus 适配器

**给定** 包含 Milvus 配置的参数
**当** 调用 `StorageFactory.create_vector_storage(config)`
**那么** 应返回配置好的 `MilvusVectorStorageAdapter` 实例
**并且** 应验证 collection 存在

---

## 接口定义

### Neo4j 适配器接口

```python
class Neo4jGraphStorageAdapter:
    """Neo4j 图存储适配器"""

    async def upsert_node(
        self,
        entity_id: str,
        entity_data: dict
    ) -> None:
        """创建或更新节点"""

    async def upsert_edge(
        self,
        source: str,
        target: str,
        edge_data: dict
    ) -> None:
        """创建或更新边"""

    async def get_node(self, entity_id: str) -> dict | None:
        """获取节点详情"""

    async def get_node_neighbors(
        self,
        entity_id: str,
        depth: int = 1
    ) -> list[dict]:
        """获取节点的邻居"""

    async def delete_node(self, entity_id: str) -> None:
        """删除节点及其关系"""

    async def batch_upsert(
        self,
        nodes: list[dict],
        edges: list[dict]
    ) -> None:
        """批量写入"""
```

### Milvus 适配器接口

```python
class MilvusVectorStorageAdapter:
    """Milvus 向量存储适配器"""

    async def insert(self, records: list[dict]) -> None:
        """插入向量记录"""

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10
    ) -> list[dict]:
        """相似度搜索"""

    async def delete(self, entity_ids: list[str]) -> None:
        """删除向量记录"""
```

---

## Neo4j Schema 定义

### 节点标签

```
MedicalEntity
  - entity_id: STRING (唯一)
  - entity_name: STRING
  - entity_type: STRING  (DEVICE, DISEASE, TREATMENT, etc.)
  - description: STRING
  - source_id: STRING
  - created_at: DATETIME
```

### 关系类型

```
(:MedicalEntity)-[:RELATES_TO]->(:MedicalEntity)
  - weight: FLOAT
  - description: STRING
  - source_id: STRING
```
