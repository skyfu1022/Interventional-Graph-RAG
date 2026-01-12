# 规范：Neo4j 集成和三层架构支持

**所有者**: Medical-Graph-RAG 团队
**创建日期**: 2026-01-12
**状态**: 提案中

---

## 新增需求

### 需求：Neo4j 图存储后端

**编号**: NEO4J-001

**描述**:
系统必须提供 `Neo4jGraphStorage` 类,实现 LightRAG 的 `BaseGraphStorage` 接口,用于将图数据存储到 Neo4j 数据库并支持 `gid` 机制。

**验收标准**:
1. 实现 `BaseGraphStorage` 接口的所有必需方法
2. 所有节点和边自动包含 `gid` 属性
3. 支持节点的 CRUD 操作
4. 支持边的 CRUD 操作
5. 支持基于 `gid` 的数据隔离

#### 场景：创建和获取节点

**前提条件**:
- Neo4j 数据库运行中
- `Neo4jGraphStorage` 已初始化

**步骤**:
1. 创建节点存储实例
2. 插入一个节点
3. 通过 ID 获取节点
4. 验证节点数据

**预期结果**:
- 节点成功创建
- 节点包含 `gid` 属性
- 获取的节点数据与插入的一致

**示例代码**:
```python
from medgraphrag.neo4j_storage import Neo4jGraphStorage
from camel.storages import Neo4jGraph

neo4j = Neo4jGraph(url="bolt://localhost:7687", username="neo4j", password="password")

storage = Neo4jGraphStorage(
    namespace="test",
    global_config={},
    neo4j_graph=neo4j,
    gid="test_gid_001"
)

# 插入节点
node_data = {
    "entity_name": "DIABETES",
    "entity_type": "Disease",
    "description": "A metabolic disorder",
    "embedding": [0.1, 0.2, 0.3]
}

await storage.upsert_node("DIABETES", node_data)

# 获取节点
node = await storage.get_node("DIABETES")

assert node is not None
assert node["id"] == "DIABETES"
assert node["gid"] == "test_gid_001"
assert node["description"] == "A metabolic disorder"
```

#### 场景：创建和获取关系

**前提条件**:
- 两个节点已存在
- `Neo4jGraphStorage` 已初始化

**步骤**:
1. 创建两个节点
2. 在节点间创建关系
3. 获取关系
4. 验证关系数据

**预期结果**:
- 关系成功创建
- 关系包含描述和强度信息
- 关系类型根据描述正确推断

**示例代码**:
```python
# 创建两个节点
await storage.upsert_node("DIABETES", {
    "entity_name": "DIABETES",
    "entity_type": "Disease",
    "description": "A metabolic disorder"
})

await storage.upsert_node("INSULIN", {
    "entity_name": "INSULIN",
    "entity_type": "Medication",
    "description": "A hormone used to treat diabetes"
})

# 创建关系
edge_data = {
    "description": "Insulin is used to treat diabetes",
    "strength": "high"
}

await storage.upsert_edge("INSULIN", "DIABETES", edge_data)

# 获取关系
edge = await storage.get_edge("INSULIN", "DIABETES")

assert edge is not None
assert edge["description"] == "Insulin is used to treat diabetes"
```

---

### 需求：关系类型自动推断

**编号**: NEO4J-002

**描述**:
系统必须根据关系描述自动推断合适的关系类型,以提供更语义化的图结构。

**验收标准**:
1. 包含 "treat" 或 "cure" 的描述推断为 `TREATS`
2. 包含 "cause" 或 "lead" 的描述推断为 `CAUSES`
3. 包含 "diagnose" 或 "indicate" 的描述推断为 `INDICATES`
4. 包含 "symptom" 或 "manifest" 的描述推断为 `HAS_SYMPTOM`
5. 其他情况默认为 `RELATED_TO`

#### 场景：治疗关系推断

**步骤**:
1. 创建药物和疾病节点
2. 创建包含 "treat" 的关系描述
3. 验证关系类型

**预期结果**:
- 关系类型为 `TREATS`

**示例代码**:
```python
edge_data = {
    "description": "This medication treats the condition",
    "strength": "high"
}

await storage.upsert_edge("ASPIRIN", "HEADACHE", edge_data)

# 验证关系类型
query = """
MATCH (a {id: 'ASPIRIN'})-[r:TREATS]->(b {id: 'HEADACHE'})
RETURN r
"""
result = neo4j.query(query)
assert len(result) == 1
```

#### 场景：因果关系推断

**步骤**:
1. 创建原因和结果节点
2. 创建包含 "cause" 的关系描述
3. 验证关系类型

**预期结果**:
- 关系类型为 `CAUSES`

---

### 需求：基于 gid 的数据隔离

**编号**: NEO4J-003

**描述**:
系统必须确保不同 `gid` 的数据相互隔离,查询时只返回匹配 `gid` 的节点和关系。

**验收标准**:
1. 创建节点时自动添加 `gid` 属性
2. 查询节点时自动过滤 `gid`
3. 创建关系时验证两端节点的 `gid` 匹配
4. 获取邻居节点时只返回相同 `gid` 的节点

#### 场景：不同 gid 的数据隔离

**前提条件**:
- 两个不同 `gid` 的存储实例

**步骤**:
1. 创建 gid1 的存储实例,插入节点 A
2. 创建 gid2 的存储实例,插入节点 B
3. 使用 gid1 查询,验证只能看到节点 A
4. 使用 gid2 查询,验证只能看到节点 B

**预期结果**:
- 每个 `gid` 只能访问自己的数据
- 跨 `gid` 访问返回 None 或空列表

**示例代码**:
```python
storage1 = Neo4jGraphStorage(
    namespace="test",
    global_config={},
    neo4j_graph=neo4j,
    gid="patient_001"
)

storage2 = Neo4jGraphStorage(
    namespace="test",
    global_config={},
    neo4j_graph=neo4j,
    gid="patient_002"
)

# 插入不同 gid 的节点
await storage1.upsert_node("FEVER", {"entity_name": "FEVER", "entity_type": "Symptom"})
await storage2.upsert_node("FEVER", {"entity_name": "FEVER", "entity_type": "Symptom"})

# 验证隔离
node1 = await storage1.get_node("FEVER")
node2 = await storage2.get_node("FEVER")

assert node1["gid"] == "patient_001"
assert node2["gid"] == "patient_002"
assert node1 != node2  # 是不同的节点
```

---

### 需求：跨层级链接

**编号**: NEO4J-004

**描述**:
系统必须支持在不同 `gid` 的图之间创建链接关系,以实现三层架构的跨层查询。

**验收标准**:
1. `link_context()` 函数接受两个 `gid` 参数
2. 识别两个图中的相似实体（基于嵌入相似度）
3. 创建跨 `gid` 的 `LINKS_TO` 关系
4. 保留原有图的数据完整性

#### 场景：患者图链接到医学词典

**前提条件**:
- 患者图（gid: patient_001）已构建
- UMLS 词典图（gid: umls_dict）已构建

**步骤**:
1. 调用 `link_context(neo4j, "patient_001", "umls_dict")`
2. 查询跨层链接
3. 验证链接的实体语义相关

**预期结果**:
- 创建了多个 `LINKS_TO` 关系
- 链接的实体对语义相似
- 可以通过链接进行跨层查询

**示例代码**:
```python
from utils import link_context

# 执行跨层链接
link_context(neo4j, "patient_001", "umls_dict")

# 验证链接
query = """
MATCH (p {gid: 'patient_001'})-[r:LINKS_TO]->(u {gid: 'umls_dict'})
RETURN p.id AS patient_entity, u.id AS umls_entity, u.description AS definition
LIMIT 10
"""

results = neo4j.query(query)
assert len(results) > 0

# 验证语义相关性
for result in results:
    patient_entity = result["patient_entity"]
    umls_entity = result["umls_entity"]
    # 应该是相同或相似的医学术语
    assert patient_entity.lower() in umls_entity.lower() or \
           umls_entity.lower() in patient_entity.lower()
```

---

### 需求：图内合并

**编号**: NEO4J-005

**描述**:
系统必须支持在同一 `gid` 内合并相似的节点,以减少冗余并提高图质量。

**验收标准**:
1. `merge_similar_nodes()` 函数接受 `gid` 参数
2. 识别语义相似的节点（基于嵌入）
3. 合并节点时保留所有关系
4. 合并节点时合并描述信息
5. 相似度阈值可配置（默认 0.9）

#### 场景：合并同义实体

**前提条件**:
- 图中存在语义相似的节点（如 "HEADACHE" 和 "HEAD_PAIN"）

**步骤**:
1. 构建包含相似实体的图
2. 调用 `merge_similar_nodes(neo4j, "test_gid")`
3. 验证相似节点已合并

**预期结果**:
- 相似节点合并为一个
- 合并后的节点保留所有关系
- 合并后的描述是两者的组合

**示例代码**:
```python
from utils import merge_similar_nodes

# 创建相似节点
await storage.upsert_node("HEADACHE", {
    "entity_name": "HEADACHE",
    "entity_type": "Symptom",
    "description": "Pain in the head region",
    "embedding": [0.8, 0.1, 0.1]
})

await storage.upsert_node("HEAD_PAIN", {
    "entity_name": "HEAD_PAIN",
    "entity_type": "Symptom",
    "description": "Painful sensation in head",
    "embedding": [0.81, 0.09, 0.11]  # 非常相似的向量
})

# 执行合并
merge_similar_nodes(neo4j, "test_gid", similarity_threshold=0.9)

# 验证合并结果
query = """
MATCH (n:Symptom {gid: 'test_gid'})
WHERE n.id IN ['HEADACHE', 'HEAD_PAIN']
RETURN count(n) AS count
"""
result = neo4j.query(query)
assert result[0]["count"] == 1  # 只剩一个节点
```

---

## 修改需求

### 需求：支持向量索引优化

**编号**: NEO4J-006

**修改内容**:
Neo4j 存储**必须**支持向量索引,以加速基于嵌入的相似度查询。

**验收标准**:
1. 自动创建向量索引（如果 Neo4j 版本支持）
2. 相似度查询使用索引加速
3. 向后兼容不支持向量索引的 Neo4j 版本

#### 场景：快速相似度查询

**步骤**:
1. 插入大量带嵌入的节点
2. 执行相似度查询
3. 验证查询速度

**预期结果**:
- 查询返回最相似的 K 个节点
- 查询时间显著快于暴力计算

---

## 技术约束

1. **Neo4j 版本**: 需要 Neo4j >= 5.0.0
2. **向量维度**: 支持可配置的嵌入维度（默认 1536）
3. **并发**: 支持多个 `gid` 的并发写入
4. **事务**: 关键操作（如合并）应在事务中执行

---

## 非功能需求

1. **性能**:
   - 单节点插入 < 100ms
   - 相似度查询（1000 节点）< 1s

2. **数据完整性**:
   - 合并操作不丢失任何关系
   - 跨层链接不破坏原有图结构

3. **可维护性**:
   - Cypher 查询应参数化,防止注入
   - 错误处理要明确和友好

---

## 参考资料

- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [LightRAG Storage Interface](https://github.com/HKUDS/LightRAG)
