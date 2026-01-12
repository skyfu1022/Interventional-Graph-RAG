# 规范：查询系统

**所有者**: Medical-Graph-RAG 团队
**创建日期**: 2026-01-12
**状态**: 提案中

---

## 新增需求

### 需求：混合查询模式

**编号**: QUERY-001

**描述**:
系统必须支持 local、global 和 hybrid 三种查询模式,以满足不同场景的查询需求。

**验收标准**:
1. `local` 模式基于实体邻域和社区报告返回答案
2. `global` 模式基于整个图的全局结构返回答案
3. `hybrid` 模式结合 local 和 global 的优势
4. 每种模式都返回清晰、有上下文的答案

#### 场景：Local 查询 - 特定实体相关问题

**前提条件**:
- 图已构建完成
- 社区报告已生成

**步骤**:
1. 提出关于特定实体的问题
2. 使用 `local` 模式查询
3. 验证答案

**预期结果**:
- 返回基于该实体及其邻居的详细答案
- 答案包含实体的描述和关系信息
- 查询速度快（< 3秒）

**示例代码**:
```python
question = "患者的糖尿病是什么类型?"
result = await adapter.query(question, mode="local")

assert isinstance(result, str)
assert "糖尿病" in result.lower() or "diabetes" in result.lower()
```

#### 场景：Global 查询 - 综合性问题

**前提条件**:
- 图已构建完成
- 全局社区报告已生成

**步骤**:
1. 提出需要全局视角的问题
2. 使用 `global` 模式查询
3. 验证答案的全面性

**预期结果**:
- 返回基于整个图的全局分析答案
- 答案涵盖多个相关领域
- 答案有组织和结构化

**示例代码**:
```python
question = "整体来看,患者的主要健康问题有哪些?"
result = await adapter.query(question, mode="global")

assert len(result) > 100  # 全局答案应该更详细
```

#### 场景：Hybrid 查询 - 平衡型问题

**前提条件**:
- 图已构建完成

**步骤**:
1. 提出需要局部细节和全局视角的问题
2. 使用 `hybrid` 模式查询
3. 验证答案质量

**预期结果**:
- 返回结合局部和全局信息的答案
- 既有细节又有全局视角
- 答案质量最高（通常）

**示例代码**:
```python
question = "患者的糖尿病与其他疾病有什么关联?"
result = await adapter.query(question, mode="hybrid")

assert "糖尿病" in result.lower() or "diabetes" in result.lower()
# hybrid 模式应该提供更全面的答案
```

---

### 需求：基于摘要节点的检索

**编号**: QUERY-002

**描述**:
系统必须支持基于摘要节点的检索策略,先定位到相关的文档摘要,再深入到具体的实体图。

**验收标准**:
1. 每个文档/数据块有对应的摘要节点
2. `seq_ret()` 函数基于查询找到相关摘要节点
3. 返回摘要节点关联的 `gid` 列表
4. 支持多个 `gid` 的联合查询

#### 场景：通过摘要定位相关子图

**前提条件**:
- 多个文档已处理,每个有独立的 `gid` 和摘要节点
- 查询问题与某些文档相关

**步骤**:
1. 处理用户查询,生成查询摘要
2. 调用 `seq_ret(neo4j, query_summary)`
3. 获取相关的 `gid` 列表
4. 在这些 `gid` 对应的子图中进行详细查询

**预期结果**:
- 返回最相关的 1-3 个 `gid`
- 这些 `gid` 对应的文档与查询高度相关
- 后续查询聚焦在这些子图,提高效率和准确性

**示例代码**:
```python
from retrieve import seq_ret
from summerize import process_chunks

question = "患者在 2023 年 3 月的血糖水平如何?"
query_summary = process_chunks(question)

# 找到相关的子图
relevant_gids = seq_ret(neo4j, query_summary)

assert isinstance(relevant_gids, list)
assert len(relevant_gids) > 0

# 在相关子图中查询
for gid in relevant_gids:
    adapter = RAGAdapter(
        working_dir=f"./storage_{gid}",
        gid=gid,
        neo4j_graph=neo4j,
        llm_model_func=llm_func,
        embedding_func=embedding_func
    )
    result = await adapter.query(question, mode="hybrid")
    # 处理结果
```

---

### 需求：跨层级查询

**编号**: QUERY-003

**描述**:
系统必须支持跨三层架构的联合查询,能够从患者数据追溯到医学词典定义。

**验收标准**:
1. 查询可以从 Top-level（患者）开始
2. 自动跟踪 `LINKS_TO` 关系到 Mid-level 和 Bot-level
3. 返回的答案包含多层级的信息
4. 引用来源包含层级信息

#### 场景：从患者症状到标准医学定义

**前提条件**:
- 三层架构已建立并链接
- 患者图、医学书籍图、UMLS 词典图都已构建

**步骤**:
1. 提出关于患者症状的问题
2. 系统查询患者图找到症状实体
3. 跟踪 `LINKS_TO` 关系到 UMLS 词典
4. 返回包含标准医学定义的答案

**预期结果**:
- 答案包含患者的具体症状描述
- 答案包含 UMLS 的标准医学定义
- 答案包含来自医学书籍的相关知识
- 引用明确标注来源层级

**示例代码**:
```python
question = "患者的高血压是什么?"

# 使用患者图查询,但启用跨层级
result = await patient_adapter.query(question, mode="hybrid")

# 结果应该包含:
# 1. 患者的具体高血压情况（Top-level）
# 2. 医学书籍中关于高血压的知识（Mid-level）
# 3. UMLS 中高血压的标准定义（Bot-level）

assert "高血压" in result.lower() or "hypertension" in result.lower()
# 验证包含多层级信息（可以通过特定标记）
```

---

### 需求：查询结果引用

**编号**: QUERY-004

**描述**:
系统必须在查询结果中提供清晰的引用,标明信息来源于哪些实体、关系或文档。

**验收标准**:
1. 答案包含引用标记（如 [1], [2]）
2. 引用列表包含实体名称、类型、`gid`
3. 可选包含原始文本片段
4. 引用可追溯到具体的 Neo4j 节点

#### 场景：带引用的查询答案

**步骤**:
1. 执行查询
2. 验证答案包含引用
3. 验证引用的完整性和准确性

**预期结果**:
- 答案文本包含 [1], [2] 等引用标记
- 答案末尾有引用列表
- 引用可以追溯到 Neo4j 中的具体节点

**示例代码**:
```python
question = "胰岛素如何治疗糖尿病?"
result = await adapter.query(question, mode="hybrid")

# 验证引用格式
assert "[1]" in result or "[source:" in result

# 可以解析引用
# 引用格式示例:
# "胰岛素用于降低血糖 [1]。它通过促进细胞摄取葡萄糖发挥作用 [2]。
#
# 引用:
# [1] Entity: INSULIN (Medication, gid: patient_001)
# [2] Entity: GLUCOSE_UPTAKE (Procedure, gid: umls_dict)"
```

---

## 修改需求

### 需求：优化医学领域查询提示词

**编号**: QUERY-005

**修改内容**:
系统**必须**自定义 LightRAG 的查询提示词,使其更适合医学领域的问答。

**验收标准**:
1. 提示词强调医学术语的准确性
2. 提示词要求引用标准医学资源
3. 提示词鼓励提供循证医学支持
4. 提示词格式化输出以提高可读性

#### 场景：使用医学优化的提示词

**步骤**:
1. 配置医学领域的查询提示词
2. 执行医学问题查询
3. 对比默认提示词和优化提示词的结果

**预期结果**:
- 优化后的答案更专业和准确
- 使用标准医学术语
- 包含循证支持（如果有）

---

## 技术约束

1. **响应时间**:
   - Local 查询 < 3 秒
   - Global 查询 < 8 秒
   - Hybrid 查询 < 5 秒

2. **上下文窗口**: 需要考虑 LLM 的 token 限制,合理截断上下文

3. **并发**: 支持多个查询并发执行

---

## 非功能需求

1. **准确性**:
   - 查询结果应基于图中的实际数据
   - 不应产生幻觉（无中生有）

2. **可解释性**:
   - 所有答案都应有引用支持
   - 用户可以验证答案的来源

3. **用户体验**:
   - 答案清晰、结构化
   - 避免过于冗长或过于简短

---

## 参考资料

- [LightRAG Query Modes](https://github.com/HKUDS/LightRAG#query-modes)
- [Medical Question Answering Best Practices](https://arxiv.org/abs/2408.04187)
