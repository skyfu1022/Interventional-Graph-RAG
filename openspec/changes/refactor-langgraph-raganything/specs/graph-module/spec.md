# 图构建模块规范

## 新增需求

### 需求：LangGraph 图谱构建工作流

系统**必须**使用 LangGraph 实现可组合的图谱构建工作流。

#### 场景：完整的图谱构建流程

**给定**：
- 一个医学文档
- 配置的 LangGraph 工作流

**当**：启动构建工作流

**那么**：工作流应按以下顺序执行：
1. **加载文档** (load_document)
   - 读取文档内容
   - 执行文本分块
   - 更新状态：`content_chunks`

2. **提取实体** (extract_entities)
   - 从每个分块提取医学实体
   - 识别实体间的关系
   - 更新状态：`entities`, `relationships`

3. **构建图谱** (build_graph)
   - 在 Neo4j 中创建节点和边
   - 添加向量嵌入
   - 生成唯一 `graph_id`

4. **合并节点** (merge_nodes) - 可选
   - 基于向量相似度合并相似节点
   - 使用 GDS 库计算余弦相似度
   - 阈值默认为 0.5

5. **创建摘要** (create_summary)
   - 生成文档摘要
   - 将摘要连接到所有节点

**验证**：
```python
workflow = create_build_workflow()
result = await workflow.ainvoke({
    "document_path": "medical_report.pdf",
})
assert result["graph_id"] is not None
assert len(result["entities"]) > 0
```

#### 场景：条件节点合并

**给定**：
- 构建工作流
- 配置 `merge=True`

**当**：工作流到达 `build_graph` 节点

**然后**：
- 应评估是否需要合并
- 如果启用，执行 `merge_nodes`
- 否则跳过到 `create_summary`

---

### 需求：Neo4j 适配器

系统**必须**提供类型安全的 Neo4j 操作接口。

#### 场景：创建节点和关系

**给定**：
- 一个 `graph_id`
- 实体和关系列表

**当**：调用 `create_graph()` 方法

**那么**：
- 每个实体应创建为 Neo4j 节点
- 每个关系应创建为 Neo4j 边
- 节点和边应包含 `gid` 属性
- 节点应包含向量嵌入

**验证**：
```python
adapter = Neo4jAdapter(url, username, password)
adapter.create_graph(
    graph_id="graph-123",
    entities=[Entity(id="e1", type="DISEASE", name="Diabetes")],
    relationships=[Relationship(source="e1", target="e2", type="CAUSES")],
)
```

#### 场景：向量相似度搜索

**给定**：
- 一个查询向量
- 相似度阈值

**当**：调用 `find_similar_nodes()` 方法

**那么**：
- 应返回相似度超过阈值的所有节点
- 结果应按相似度降序排列
- 每个结果应包含相似度分数

#### 场景：执行 Cypher 查询

**给定**：
- 一个 Cypher 查询字符串
- 可选的参数字典

**当**：调用 `query()` 方法

**那么**：
- 应返回查询结果
- 参数应被正确绑定
- 查询错误应抛出 `GraphError`

---

### 需求：图谱节点合并

系统**必须**基于语义相似度合并重复或高度相似的节点。

#### 场景：基于阈值合并节点

**给定**：
- 相似度阈值 `threshold=0.7`
- 同一 `graph_id` 中的节点

**当**：调用 `merge_similar_nodes()` 方法

**那么**：
- 应计算所有节点对的余弦相似度
- 相似度超过阈值的节点对应被合并
- 合并应保留更完整的属性
- 关系应被重新连接到合并后的节点

**验证**：
```python
merger = NodeMerger(adapter)
stats = merger.merge_similar_nodes("graph-123", threshold=0.7)
assert stats.merged_count > 0
assert stats.final_node_count < stats.initial_node_count
```

#### 场景：跨图节点关联

**给定**：
- 两个不同的 `graph_id`
- 配置的关联阈值

**当**：调用 `link_cross_graph_nodes()` 方法

**那么**：
- 应查找两个图中相似的节点
- 应创建 `REFERENCE` 类型的关系
- 关系方向应从源图指向目标图

---

### 需求：三层图谱关联 (Trinity)

系统**必须**支持跨图层的知识关联。

#### 场景：创建三层关联

**给定**：
- 顶层图 (患者数据)
- 中层图 (医学文献)
- 底层图 (医学词典)

**当**：调用 `create_trinity_links()` 方法

**那么**：
- 顶层节点应链接到相关的中层节点
- 中层节点应链接到相关的底层节点
- 链接应基于语义相似度
- 所有链接应使用 `REFERENCE` 关系类型

**验证**：
```python
trinity = TrinityLinker(adapter)
trinity.create_trinity_links(
    top_graph_id="patient-data",
    middle_graph_id="literature",
    bottom_graph_id="umls",
    threshold=0.6,
)
```

#### 场景：查询关联上下文

**给定**：
- 一个查询的 `graph_id`
- 存在的三层关联

**当**：调用 `get_linked_context()` 方法

**那么**：
- 应返回当前图的上下文
- 应返回所有关联图的引用上下文
- 结果应按图谱层级组织

---

### 需求：图谱可视化

系统**必须**支持将图谱导出为可视化格式。

#### 场景：导出为 Mermaid 图表

**给定**：
- 一个 `graph_id`

**当**：调用 `export_mermaid()` 方法

**那么**：
- 应生成 Mermaid 格式的图定义
- 节点应按类型使用不同形状
- 关系应有清晰的标签

**验证**：
```python
visualizer = GraphVisualizer(adapter)
mermaid_code = visualizer.export_mermaid("graph-123")
assert "graph TD" in mermaid_code
```

#### 场景：导出为 JSON

**给定**：一个 `graph_id`

**当**：调用 `export_json()` 方法

**那么**：应返回包含所有节点和边的 JSON 结构
