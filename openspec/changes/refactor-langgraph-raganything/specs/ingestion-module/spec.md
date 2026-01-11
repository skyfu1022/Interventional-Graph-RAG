# 数据摄入模块规范

## 新增需求

### 需求：RAG-Anything 多模态文档摄入

系统**必须**集成 RAG-Anything，支持多模态文档的摄入和处理。

#### 场景：摄入包含图像和表格的 PDF 文档

**给定**：
- 一个 PDF 文档包含文本、图像和表格
- RAGAnythingIngestor 已正确配置

**当**：调用 `ingest_document()` 方法

**那么**：
- 文档应被完整解析
- 文本、图像、表格应被分别提取
- 内容应被索引到知识库
- 应返回包含 `doc_id` 的 `IngestResult`

**验证**：
```python
ingestor = RAGAnythingIngestor(config)
result = await ingestor.ingest_document("paper.pdf")
assert result.status == "completed"
assert result.doc_id is not None
```

#### 场景：直接摄入预解析的内容列表

**给定**：
- 一个包含多模态内容的列表
- 内容包括：文本、图像路径、表格数据、公式

**当**：调用 `ingest_content_list()` 方法

**那么**：
- 所有内容应被正确索引
- 图像路径必须是绝对路径
- 表格应保留结构信息

**验证**：
```python
content_list = [
    {"type": "text", "text": "Introduction...", "page_idx": 0},
    {"type": "image", "img_path": "/abs/path/fig1.jpg", "page_idx": 1},
    {"type": "table", "table_body": "| A | B |", "page_idx": 2},
]
result = await ingestor.ingest_content_list(content_list, "doc.pdf")
```

---

### 需求：文档加载器

系统**必须**支持多种文档格式的加载。

#### 场景：加载不同格式的文档

**给定**：不同格式的文档文件

**当**：使用 `DocumentLoader` 加载

**那么**：
- PDF 文档应返回文本内容
- TXT 文档应返回原始文本
- Markdown 文档应保留格式
- DOCX 文档应提取文本内容

**支持格式**：
- `.pdf`
- `.txt`
- `.md`
- `.docx`

**验证**：
```python
loader = DocumentLoader()
content = loader.load("document.pdf")
assert isinstance(content, str)
assert len(content) > 0
```

#### 场景：批量加载文档

**给定**：一个包含多个文档的目录

**当**：调用 `load_directory()` 方法

**那么**：
- 应递归加载所有支持的文档
- 应返回每个文档的路径和内容
- 应跳过不支持的格式

---

### 需求：语义感知文本分块

系统**必须**实现基于语义的文本分块，继承现有的 AgenticChunker 逻辑。

#### 场景：基于语义命题的分块

**给定**：
- 一段医学文档
- 配置了语义分块器

**当**：调用 `chunk_text()` 方法

**那么**：
- 文本应被分解为语义命题
- 相关命题应被聚合为分块
- 每个分块应保持语义完整性

**验证**：
```python
chunker = SemanticChunker()
chunks = chunker.chunk_text(medical_text)
assert all(len(c) > 0 for c in chunks)
assert all(len(c) < 2000 for c in chunks)  # 合理的分块大小
```

#### 场景：基于 Token 的分块

**给定**：需要精确控制 Token 数量

**当**：使用 `TokenChunker` 并指定 `max_tokens=500`

**然后**：每个分块应不超过指定 Token 数

---

### 需求：医学实体提取

系统**必须**从医学文档中提取结构化的医学实体。

#### 场景：提取医学实体

**给定**：
- 一段医学报告
- 配置的医学实体提取器

**当**：调用 `extract_entities()` 方法

**然后**：应提取以下类型的实体：
- `ANATOMICAL_STRUCTURE` - 解剖结构
- `BODY_FUNCTION` - 身体功能
- `LABORATORY_DATA` - 实验室数据
- `MEDICINE` - 药物
- `PROBLEM` - 医学问题/疾病
- `PROCEDURE` - 医疗程序

**验证**：
```python
extractor = MedicalEntityExtractor()
entities = extractor.extract("Patient has diabetes and high blood pressure")
assert any(e.type == "PROBLEM" for e in entities)
assert any(e.name == "diabetes" for e in entities)
```

#### 场景：保留实体上下文

**给定**：提取的医学实体

**当**：实体被存储

**然后**：
- 每个实体应包含其在原文中的位置
- 实体应关联到源文档
- 实体应包含置信度分数
