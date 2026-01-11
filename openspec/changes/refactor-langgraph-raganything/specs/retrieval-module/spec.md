# 检索模块规范

## 新增需求

### 需求：LangGraph 查询工作流

系统**必须**使用 LangGraph 实现智能查询路由和检索增强生成。

#### 场景：完整的查询流程

**给定**：
- 一个用户查询
- 配置的查询工作流
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
   - 从图谱检索相关节点
   - 从向量库检索相关分块
   - 合并检索结果

4. **评估文档** (grade_documents)
   - 评估检索结果相关性
   - 低相关性 → 优化查询重试
   - 高相关性 → 继续生成

5. **生成答案** (generate_answer)
   - 使用 LLM 基于上下文生成答案
   - 添加引用和来源

**验证**：
```python
workflow = create_query_workflow()
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

**当**：工作流到达 `grade_documents` 节点

**那么**：
- 应识别相关性不足
- 应转换到 `refine_query` 节点
- 应优化原始查询
- 应重新执行检索
- 最多重试 3 次

---

### 需求：混合检索器

系统**必须**结合图检索和向量检索，提供多种检索模式。

#### 场景：6 种检索模式

系统**必须**支持以下 6 种检索模式：

1. **naive**：仅使用向量相似度搜索，不考虑图谱结构
2. **local**：聚焦于查询中提到的特定实体，检索与实体直接相关的节点
3. **global**：检索整个图谱的社区摘要，返回广泛的上下文
4. **hybrid**：结合局部和全局检索，提供全面的上下文
5. **mix**：混合多种检索策略，优化结果质量
6. **bypass**：直接生成答案，不执行检索

**验证**：
```python
from src.core.adapters import RAGAnythingAdapter

adapter = RAGAnythingAdapter(config)

# 测试所有 6 种模式
modes = ["naive", "local", "global", "hybrid", "mix", "bypass"]
for mode in modes:
    result = await adapter.query("测试查询", mode=mode)
    assert result.answer is not None
```

#### 场景：混合检索模式

**给定**：
- 一个查询
- 配置的混合检索器

**当**：使用 `mode="hybrid"` 执行检索

**那么**：
- 应同时执行局部检索 (local) 和全局检索 (global)
- 应合并两个检索结果
- 应使用重排序优化结果顺序

#### 场景：局部检索模式

**给定**：`mode="local"`

**当**：执行检索

**那么**：
- 应聚焦于查询中提到的特定实体
- 应检索与实体直接相关的节点
- 应返回高精度的上下文

#### 场景：全局检索模式

**给定**：`mode="global"`

**当**：执行检索

**那么**：
- 应检索整个图谱的社区摘要
- 应返回广泛的上下文
- 适合探索性问题

#### 场景：朴素检索模式

**给定**：`mode="naive"`

**当**：执行检索

**那么**：
- 应仅使用向量相似度搜索
- 不考虑图谱结构
- 返回最相似的分块

**验证**：
```python
retriever = HybridRetriever(rag_instance, neo4j_adapter)
results = retriever.retrieve(
    query="糖尿病症状",
    graph_id="graph-123",
    mode="hybrid",
    top_k=10,
)
assert len(results) == 10
assert all(r.score > 0 for r in results)
```

---

### 需求：结果排序和重排

系统**必须**智能排序检索结果。

#### 场景：基于相关性的排序

**给定**：
- 一组检索结果
- 原始相关性分数

**当**：调用 `rank_results()` 方法

**那么**：
- 结果应按相关性降序排列
- 多样性应被考虑（避免重复内容）
- 新鲜度应被考虑（如果有时间戳）

#### 场景：使用重排序模型

**给定**：
- 初始检索结果
- 配置的重排序模型

**当**：调用 `rerank()` 方法

**那么**：
- 应使用重排序模型重新评分
- 前 K 个结果应被重新排序
- 重排序应考虑查询-文档匹配度

**验证**：
```python
ranker = ResultRanker(reranker_model)
reranked = ranker.rerank(
    query="糖尿病治疗",
    results=initial_results,
    top_k=5,
)
assert len(reranked) == 5
assert reranked[0].score >= reranked[1].score
```

---

### 需求：多模态查询

系统**必须**支持包含多模态内容的查询。

#### 场景：带图像的查询

**给定**：
- 一个文本查询
- 一张医学图像（如 X 光片）

**当**：调用 `query_with_multimodal()` 方法

**那么**：
- 图像应被编码为 base64
- 视觉模型应分析图像内容
- 图像和文本应共同用于检索

**验证**：
```python
result = await retriever.aquery_with_multimodal(
    query="分析这张图像中的异常",
    multimodal_content=[{
        "type": "image",
        "img_path": "/path/to/xray.jpg",
    }],
    mode="hybrid",
)
```

#### 场景：带表格数据的查询

**给定**：
- 一个查询
- 结构化表格数据

**当**：执行查询

**那么**：
- 表格应被解析为结构化数据
- 表格内容应与知识库内容合并
- 查询应能引用表格中的具体值

---

### 需求：上下文组装

系统**必须**智能组装检索到的上下文。

#### 场景：图谱上下文组装

**给定**：
- 一个查询的 `graph_id`
- 检索到的相关节点

**当**：调用 `assemble_graph_context()` 方法

**那么**：
- 应包含节点及其关系
- 应包含关系的类型和方向
- 应按重要性排序（中心度、相关性）

**输出格式**：
```python
{
    "entities": [
        {"id": "e1", "name": "糖尿病", "type": "DISEASE"},
        {"id": "e2", "name": "胰岛素", "type": "MEDICINE"},
    ],
    "relationships": [
        {"source": "e2", "target": "e1", "type": "TREATS"},
    ],
}
```

#### 场景：向量上下文组装

**给定**：
- 检索到的文本分块

**当**：组装向量上下文

**那么**：
- 应包含分块文本
- 应包含元数据（来源、分块 ID）
- 应包含相关性分数

---

### 需求：答案生成

系统**必须**基于检索上下文生成高质量的答案。

#### 场景：带引用的答案生成

**给定**：
- 用户查询
- 检索到的上下文

**当**：调用 `generate_answer()` 方法

**那么**：
- 答案应基于提供的上下文
- 关键信息应有引用标记 [1], [2]
- 引用应映射到来源文档
- 答案应避免幻觉

**验证**：
```python
generator = AnswerGenerator(llm)
response = generator.generate(
    query="糖尿病的主要症状是什么？",
    context=retrieved_context,
)
assert "[1]" in response.answer or len(response.sources) == 0
```

#### 场景：流式答案生成

**给定**：
- 启用流式输出的配置

**当**：生成答案

**那么**：
- 答案应以流的形式生成
- 每个token应尽快返回
- 引用应在句子完成后添加
