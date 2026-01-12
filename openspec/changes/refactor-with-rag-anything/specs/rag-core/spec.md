# 规范：核心 RAG 功能

## 功能 ID
`rag-core`

## 修改需求

### 需求：RAG Anything 集成

系统应使用 RAG-Anything 作为核心 RAG 引擎，替代原有的 `nano_graphrag` 模块。

#### 场景：初始化 RAG 引擎

**给定** 用户已配置好 API 密钥和存储参数
**当** 调用 `MedicalRAG.__init__(config)`
**那么** 应成功初始化 RAGAnything 实例
**并且** 应连接到 Neo4j 和 Milvus 存储

```python
# 示例
config = MedicalRAGConfig(
    api_key="sk-xxx",
    working_dir="./data",
    neo4j_url="bolt://localhost:7687",
    milvus_url="http://localhost:19530"
)
rag = MedicalRAG(config)
```

#### 场景：处理文本文档

**给定** 已初始化的 RAG 实例
**当** 调用 `await rag.ainsert(["这是一段医学文本..."])`
**那么** 应提取实体和关系
**并且** 应存入知识图谱
**并且** 应更新向量索引

#### 场景：处理多模态文档

**给定** 已初始化的 RAG 实例，且启用了多模态处理
**当** 调用 `await rag.ainsert(["medical_report.pdf"])`
**那么** 应解析文本内容
**并且** 应提取图像描述
**并且** 应提取表格内容
**并且** 应提取公式信息
**并且** 所有内容应关联到同一文档

#### 场景：执行本地查询

**给定** 图谱中已存在医学知识
**当** 调用 `await rag.aquery("什么是远端栓塞保护装置?", mode="local")`
**那么** 应返回基于相关实体的答案
**并且** 应包含引用的来源信息

#### 场景：执行全局查询

**给定** 图谱中已存在医学知识
**当** 调用 `await rag.aquery("总结介入治疗的主要方法", mode="global")`
**那么** 应返回基于社区报告的综合答案
**并且** 答案应涵盖多个相关概念

---

### 需求：接口兼容性

新的 RAG 实现应保持与 `nano_graphrag` 的接口兼容。

#### 场景：异步插入接口

**给定** 使用原 `nano_graphrag` 接口的代码
**当** 将导入替换为 `MedicalRAG`
**并且** 调用 `await rag.ainsert(documents)`
**那么** 应正常工作无需修改调用代码

#### 场景：异步查询接口

**给定** 使用原 `nano_graphrag` 查询接口的代码
**当** 将导入替换为 `MedicalRAG`
**并且** 调用 `await rag.aquery(query, mode="hybrid")`
**那么** 应返回与原实现格式兼容的结果

#### 场景：同步接口

**给定** 需要同步调用的场景
**当** 调用 `rag.insert(documents)` 或 `rag.query(query)`
**那么** 应正确处理异步调用
**并且** 返回同步结果

---

### 需求：多模态内容处理

系统应支持处理和索引多模态医学文档内容。

#### 场景：图像内容索引

**给定** 包含医学影像的 PDF 文档
**当** 文档被处理
**那么** 图像应通过 Vision LLM 生成描述
**并且** 图像描述应作为实体存入图谱
**并且** 图像应与关联文本建立关系

#### 场景：表格内容索引

**给定** 包含医学数据表格的文档
**当** 文档被处理
**那么** 表格内容应被解析为结构化数据
**并且** 表格关键信息应提取为实体
**并且** 表格应与上下文建立关联

#### 场景：公式内容索引

**给定** 包含医学公式的文档
**当** 文档被处理
**那么** 公式应转换为可理解的形式
**并且** 公式变量和含义应被提取
**并且** 公式应与相关概念建立关联

---

## 接口定义

```python
class MedicalRAG:
    """基于 RAG Anything 的医学 RAG 接口"""

    def __init__(self, config: MedicalRAGConfig):
        """初始化 RAG 实例"""

    async def ainsert(self, documents: list[str]) -> None:
        """异步插入文档"""

    async def aquery(
        self,
        query: str,
        mode: Literal["local", "global", "hybrid"] = "hybrid"
    ) -> dict:
        """异步查询"""

    def insert(self, documents: list[str]) -> None:
        """同步插入文档"""

    def query(
        self,
        query: str,
        mode: Literal["local", "global", "hybrid"] = "hybrid"
    ) -> dict:
        """同步查询"""
```

---

## 数据格式

### 查询结果格式

```python
{
    "answer": str,           # 生成的答案
    "context": list[str],    # 使用的上下文片段
    "entities": list[str],   # 相关实体
    "sources": list[dict]    # 来源信息
}
```
