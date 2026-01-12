# 规范：RAG 适配器核心功能

**所有者**: Medical-Graph-RAG 团队
**创建日期**: 2026-01-12
**状态**: 提案中

---

## 新增需求

### 需求：RAGAdapter 类初始化

**编号**: RAG-ADAPTER-001

**描述**:
系统必须提供 `RAGAdapter` 类,用于封装 RAG-Anything 功能并与 Medical-Graph-RAG 的三层架构集成。

**验收标准**:
1. `RAGAdapter` 可以使用指定的 `working_dir`、`gid`、`neo4j_graph`、`llm_model_func` 和 `embedding_func` 进行初始化
2. 初始化时自动配置医学领域特定的实体类型列表
3. 正确配置 RAG-Anything 的底层实例

#### 场景：基本初始化

**前提条件**:
- Neo4j 数据库可访问
- OpenAI API 密钥已配置

**步骤**:
1. 创建 Neo4j 连接
2. 准备 LLM 函数和嵌入函数
3. 使用这些参数初始化 `RAGAdapter`

**预期结果**:
- `RAGAdapter` 实例成功创建
- 内部 `RAGAnything` 实例已配置
- `gid` 属性正确设置
- 默认的医学实体类型列表已加载

**示例代码**:
```python
from medgraphrag.rag_adapter import RAGAdapter
from camel.storages import Neo4jGraph
import os

neo4j = Neo4jGraph(
    url=os.getenv("NEO4J_URL"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

def llm_func(prompt, **kwargs):
    # LLM 实现
    pass

def embedding_func(texts):
    # 嵌入实现
    pass

adapter = RAGAdapter(
    working_dir="./test_storage",
    gid="test_graph_001",
    neo4j_graph=neo4j,
    llm_model_func=llm_func,
    embedding_func=embedding_func
)

assert adapter.gid == "test_graph_001"
assert len(adapter.entity_types) > 0
```

---

### 需求：内容处理和实体提取

**编号**: RAG-ADAPTER-002

**描述**:
`RAGAdapter` 必须能够处理医学文本内容,提取实体和关系,并将结果格式化为标准结构。

**验收标准**:
1. `process_content()` 方法接受文本内容作为输入
2. 返回包含 `entities` 和 `relationships` 的字典
3. 实体包含 `entity_name`、`entity_type` 和 `description` 字段
4. 关系包含 `src`、`tgt`、`description` 和 `strength` 字段
5. 支持可选的细粒度分块模式

#### 场景：处理简单医学文本

**前提条件**:
- `RAGAdapter` 已正确初始化
- LLM 服务可用

**步骤**:
1. 准备包含医学实体和关系的文本
2. 调用 `process_content()` 方法
3. 检查返回的实体和关系

**预期结果**:
- 返回的字典包含 `entities` 和 `relationships` 键
- 医学实体（如疾病、症状）被正确提取
- 实体之间的关系被正确识别
- 所有实体和关系都包含必需的字段

**示例代码**:
```python
content = """
患者主诉头痛和发热三天。体温 39°C。
初步诊断为流感,建议口服奥司他韦进行治疗。
"""

result = await adapter.process_content(content)

assert "entities" in result
assert "relationships" in result
assert len(result["entities"]) > 0

# 验证实体结构
entity = result["entities"][0]
assert "entity_name" in entity
assert "entity_type" in entity
assert "description" in entity

# 验证关系结构
if len(result["relationships"]) > 0:
    rel = result["relationships"][0]
    assert "src" in rel
    assert "tgt" in rel
    assert "description" in rel
```

#### 场景：使用细粒度分块

**前提条件**:
- `RAGAdapter` 已正确初始化
- 长文本内容准备就绪

**步骤**:
1. 准备较长的医学文档
2. 调用 `process_content(content, use_grained_chunking=True)`
3. 验证分块和提取结果

**预期结果**:
- 文本被分成多个语义相关的块
- 每个块的实体被正确提取
- 跨块的实体被合并或链接

---

### 需求：Neo4j 数据写入

**编号**: RAG-ADAPTER-003

**描述**:
`RAGAdapter` 必须能够将提取的实体和关系写入 Neo4j 图数据库,并自动添加 `gid` 标签以支持三层架构。

**验收标准**:
1. `insert_to_neo4j()` 方法接受实体和关系列表
2. 实体作为节点插入,关系作为边插入
3. 所有节点和边都包含 `gid` 属性
4. 支持实体合并（相同实体不重复创建）
5. 实体类型作为节点标签
6. 关系类型根据描述自动推断

#### 场景：写入实体和关系到 Neo4j

**前提条件**:
- `RAGAdapter` 已初始化
- 实体和关系已提取
- Neo4j 数据库可访问

**步骤**:
1. 获取提取的实体和关系
2. 调用 `insert_to_neo4j(entities, relationships)`
3. 查询 Neo4j 验证数据

**预期结果**:
- 所有实体作为节点存在于 Neo4j
- 所有关系作为边存在于 Neo4j
- 节点包含正确的 `gid` 属性
- 节点的标签为实体类型
- 关系类型被正确推断

**示例代码**:
```python
entities = [
    {
        "entity_name": "INFLUENZA",
        "entity_type": "Disease",
        "description": "A viral infection affecting the respiratory system"
    },
    {
        "entity_name": "FEVER",
        "entity_type": "Symptom",
        "description": "Elevated body temperature"
    }
]

relationships = [
    {
        "src": "INFLUENZA",
        "tgt": "FEVER",
        "description": "Influenza causes fever",
        "strength": "high"
    }
]

await adapter.insert_to_neo4j(entities, relationships)

# 验证节点
query = "MATCH (n:Disease {id: 'INFLUENZA', gid: $gid}) RETURN n"
result = neo4j.query(query, {"gid": "test_graph_001"})
assert len(result) == 1

# 验证关系
query = """
MATCH (a {id: 'INFLUENZA', gid: $gid})-[r]->(b {id: 'FEVER', gid: $gid})
RETURN r
"""
result = neo4j.query(query, {"gid": "test_graph_001"})
assert len(result) == 1
```

---

### 需求：查询功能

**编号**: RAG-ADAPTER-004

**描述**:
`RAGAdapter` 必须提供查询接口,支持 local、global 和 hybrid 三种查询模式。

**验收标准**:
1. `query()` 方法接受问题字符串和查询模式
2. 支持 `local`、`global` 和 `hybrid` 三种模式
3. 返回基于上下文的回答字符串
4. 查询结果包含相关的实体和关系信息

#### 场景：Local 模式查询

**前提条件**:
- 图数据已构建并存储在 Neo4j
- 相关实体的社区报告已生成

**步骤**:
1. 提出与特定实体相关的问题
2. 使用 `local` 模式查询
3. 验证返回的答案

**预期结果**:
- 返回基于局部上下文的准确答案
- 答案包含相关实体的详细信息
- 查询速度快于 global 模式

**示例代码**:
```python
question = "患者的主要症状是什么?"
result = await adapter.query(question, mode="local")

assert isinstance(result, str)
assert len(result) > 0
# 验证答案包含症状相关信息
```

#### 场景：Hybrid 模式查询

**前提条件**:
- 图数据已构建
- 需要综合局部和全局信息的问题

**步骤**:
1. 提出需要综合分析的问题
2. 使用 `hybrid` 模式查询
3. 验证返回的答案质量

**预期结果**:
- 返回结合局部和全局上下文的答案
- 答案更全面,涵盖多个角度
- 包含引用和支持证据

---

### 需求：跨层级图链接

**编号**: RAG-ADAPTER-005

**描述**:
`RAGAdapter` 必须支持将当前层级的图与其他层级的图进行链接,以实现三层架构的跨层查询。

**验收标准**:
1. `link_to_other_graph()` 方法接受目标 `gid`
2. 识别两个图中的相同或相似实体
3. 创建跨 `gid` 的链接关系
4. 支持语义相似度匹配（基于嵌入）

#### 场景：链接患者图与医学词典图

**前提条件**:
- 患者图（Top-level）已构建,`gid = "patient_001"`
- UMLS 词典图（Bottom-level）已构建,`gid = "umls_dict"`
- 两个图都在同一个 Neo4j 实例中

**步骤**:
1. 初始化患者图的 `RAGAdapter`
2. 调用 `link_to_other_graph("umls_dict")`
3. 验证跨层链接已创建

**预期结果**:
- 患者图中的实体与 UMLS 词典中的标准术语建立链接
- 链接关系类型为 `LINKS_TO` 或类似
- 可以通过跨层查询获取更权威的医学定义

**示例代码**:
```python
# 假设两个图都已构建
patient_adapter = RAGAdapter(
    working_dir="./patient_storage",
    gid="patient_001",
    neo4j_graph=neo4j,
    llm_model_func=llm_func,
    embedding_func=embedding_func
)

await patient_adapter.link_to_other_graph("umls_dict")

# 验证链接
query = """
MATCH (p {gid: 'patient_001'})-[r:LINKS_TO]->(u {gid: 'umls_dict'})
RETURN p, r, u
LIMIT 5
"""
result = neo4j.query(query)
assert len(result) > 0
```

---

## 修改需求

### 需求：支持自定义实体类型

**编号**: RAG-ADAPTER-006

**修改内容**:
系统**必须**允许通过配置参数指定自定义的医学实体类型列表,替代原有的硬编码实体类型。

**验收标准**:
1. `RAGAdapter` 初始化时接受可选的 `entity_types` 参数
2. 如果未提供,使用默认的医学实体类型
3. 自定义类型在实体提取中生效

#### 场景：使用自定义实体类型

**步骤**:
1. 定义自定义实体类型列表
2. 初始化 `RAGAdapter` 时传入
3. 提取实体并验证类型

**预期结果**:
- 提取的实体类型符合自定义列表
- 不在列表中的类型不被提取

**示例代码**:
```python
custom_types = ["Drug", "Gene", "Protein", "Pathway"]

adapter = RAGAdapter(
    working_dir="./custom_storage",
    gid="custom_001",
    neo4j_graph=neo4j,
    llm_model_func=llm_func,
    embedding_func=embedding_func,
    entity_types=custom_types
)

assert adapter.entity_types == custom_types
```

---

## 技术约束

1. **Python 版本**: 需要 Python 3.10+
2. **依赖库**:
   - `rag-anything` >= 1.0.0
   - `lightrag-hku` >= 1.3.0
   - `neo4j` >= 5.0.0
3. **异步支持**: 所有主要方法必须是异步的（`async`/`await`）
4. **错误处理**: 必须处理 LLM 调用失败、Neo4j 连接失败等常见错误

---

## 非功能需求

1. **性能**:
   - 实体提取应在合理时间内完成（< 10秒/1000 tokens）
   - 查询响应时间应 < 5 秒（hybrid 模式）

2. **可测试性**:
   - 所有公共方法必须有单元测试
   - 测试覆盖率 > 80%

3. **文档**:
   - 所有公共方法必须有 docstring
   - 提供使用示例

---

## 参考资料

- [RAG-Anything 文档](https://github.com/hkuds/rag-anything)
- [LightRAG 文档](https://github.com/HKUDS/LightRAG)
- [Medical-Graph-RAG 论文](https://arxiv.org/abs/2408.04187)
