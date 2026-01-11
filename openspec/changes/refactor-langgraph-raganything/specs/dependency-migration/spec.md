# 依赖迁移规范

## 移除需求

### 需求：移除 CAMEL 依赖

系统需要完全移除 CAMEL 框架依赖。

#### 场景：从 requirements.txt 移除 CAMEL

**给定**：当前的 `requirements.txt` 包含 CAMEL

**当**：更新依赖

**然后**：
- 应移除所有 `camel` 相关包
- 应移除 `camel` 目录（如果存在）
- 应验证无残留导入

**移除的包**：
```
camel-ai[all]  # 或其他 camel 变体
```

**验证**：
```bash
# 不应有任何 camel 相关导入
grep -r "from camel" src/  # 应无结果
grep -r "import camel" src/  # 应无结果
```

#### 场景：替换 CAMEL KnowledgeGraphAgent

**给定**：当前使用 `camel.agents.KnowledgeGraphAgent`

**当**：迁移到新架构

**然后**：
- 应使用 LangGraph 工作流替代
- 应使用 RAG-Anything 进行图谱构建
- 应使用自定义 Neo4j 适配器

**旧代码**：
```python
from camel.agents import KnowledgeGraphAgent
kg_agent = KnowledgeGraphAgent()
```

**新代码**：
```python
from src.graph.builder import create_build_workflow
workflow = create_build_workflow()
```

#### 场景：替换 CAMEL Neo4jGraph

**给定**：当前使用 `camel.storages.Neo4jGraph`

**当**：迁移到新架构

**然后**：
- 应使用自定义 `Neo4jAdapter`
- 应保持相同的连接配置

**旧代码**：
```python
from camel.storages import Neo4jGraph
n4j = Neo4jGraph(url=url, username=username, password=password)
```

**新代码**：
```python
from src.graph.neo4j_adapter import Neo4jAdapter
adapter = Neo4jAdapter(url=url, username=username, password=password)
```

#### 场景：替换 CAMEL UnstructuredIO

**给定**：当前使用 `camel.loaders.UnstructuredIO`

**当**：迁移到新架构

**然后**：
- 应使用 RAG-Anything 的解析功能
- 或使用 LangChain 的文档加载器

**旧代码**：
```python
from camel.loaders import UnstructuredIO
uio = UnstructuredIO()
element = uio.create_element_from_text(text)
```

**新代码**：
```python
from src.ingestion.parsers import RAGAnythingIngestor
ingestor = RAGAnythingIngestor(config)
await ingestor.ingest_content_list(content_list, filename)
```

---

### 需求：移除 Nano GraphRAG 依赖

系统需要完全移除 Nano GraphRAG 依赖。

#### 场景：从 requirements.txt 移除 Nano GraphRAG

**给定**：当前项目包含 `nano_graphrag` 目录和依赖

**当**：更新依赖

**然后**：
- 应移除 `nano_graphrag` 目录
- 应移除相关依赖
- 应验证无残留导入

**移除的目录**：
```
nano_graphrag/  # 整个目录
```

**验证**：
```bash
# 不应有任何 nano_graphrag 相关导入
grep -r "from nano_graphrag" src/  # 应无结果
grep -r "import nano_graphrag" src/  # 应无结果
```

#### 场景：替换 Nano GraphRAG

**给定**：当前使用 `nano_graphrag.GraphRAG`

**当**：迁移到新架构

**然后**：
- 应使用 `lightrag-hku` (RAG-Anything 核心)
- 应保持相同的检索模式

**旧代码**：
```python
from nano_graphrag import GraphRAG, QueryParam
graph = GraphRAG(working_dir="./storage")
result = graph.query("query", param=QueryParam(mode="local"))
```

**新代码**：
```python
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embed

rag = LightRAG(
    working_dir="./storage",
    llm_model_func=openai_complete_if_cache,
    embedding_func=openai_embed,
)
result = await rag.aquery("query", param=QueryParam(mode="local"))
```

---

## 新增需求

### 需求：添加 RAG-Anything 依赖

系统**必须**添加 RAG-Anything (lightrag-hku) 作为核心依赖。

#### 场景：安装 RAG-Anything

**给定**：更新后的 `requirements.txt`

**当**：运行 `pip install -r requirements.txt`

**然后**：
- 应安装 `lightrag-hku>=0.1.0`
- 应安装相关依赖（如 `lightrag`）

**新增包**：
```
# RAG-Anything (基于 LightRAG)
# Context7 Library ID: /hkuds/lightrag
# Benchmark Score: 81.6/100
# ⚠️ 关键 API 变更：必须调用 initialize_storages() 和 initialize_pipeline_status()
lightrag-hku>=1.4.9
lightrag>=1.4.9
```

#### 场景：验证 RAG-Anything 安装

**给定**：已安装 RAG-Anything

**当**：运行验证脚本

**验证**：
```python
from raganything import RAGAnything, RAGAnythingConfig
# 或
from lightrag import LightRAG

# 应能成功导入
```

---

### 需求：LightRAG 1.4.9+ 初始化

系统**必须**遵循 LightRAG 1.4.9+ 的初始化要求。

#### 场景：LightRAG 初始化步骤

**给定**：使用 LightRAG 1.4.9+

**当**：创建 LightRAG 实例

**然后**：必须在首次使用前执行初始化

**旧版本 (< 1.4.9) 代码**：
```python
from lightrag import LightRAG
rag = LightRAG(working_dir="./rag_storage", ...)
await rag.ainsert("文档")
```

**新版本 (>= 1.4.9) 代码**：
```python
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status

rag = LightRAG(
    working_dir="./rag_storage",
    graph_storage="Neo4JStorage",
    vector_storage="MilvusVectorDBStorage",
    ...
)
# ⚠️ 必须先执行初始化
await rag.initialize_storages()
await initialize_pipeline_status()
await rag.ainsert("文档")
```

**验证**：
```python
# 测试初始化是否正确执行
async def test_lightrag_initialization():
    from lightrag import LightRAG
    from lightrag.kg.shared_storage import initialize_pipeline_status

    rag = LightRAG(working_dir="./test_storage")
    await rag.initialize_storages()
    await initialize_pipeline_status()

    # 现在可以正常使用
    await rag.ainsert("测试文档")
```

---

### 需求：添加 LangGraph 依赖

系统**必须**添加 LangGraph 和相关 LangChain 包。

#### 场景：安装 LangGraph

**给定**：更新后的 `requirements.txt`

**当**：运行 `pip install -r requirements.txt`

**然后**：应安装以下包

**新增包**：
```
# LangGraph 和 LangChain 生态
# Context7 Library ID: /langchain-ai/langgraph
# Benchmark Score: 88.5/100
# 版本：1.0.3
langgraph>=1.0.3
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0
langchain-anthropic>=0.3.0
```

#### 场景：验证 LangGraph 安装

**给定**：已安装 LangGraph

**当**：运行验证脚本

**验证**：
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# 应能成功导入和创建工作流
```

---

### 需求：添加 FastAPI 依赖

系统**必须**添加 FastAPI 作为 Web 框架。

#### 场景：安装 FastAPI

**给定**：更新后的 `requirements.txt`

**当**：运行 `pip install -r requirements.txt`

**然后**：应安装以下包

**新增包**：
```
# Web 框架
fastapi[standard]>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9  # 文件上传支持
```

#### 场景：验证 FastAPI 安装

**给定**：已安装 FastAPI

**验证**：
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 应能成功导入和创建应用
```

---

### 需求：添加 CLI 工具依赖

系统**必须**添加 Typer 和 Rich 用于 CLI。

#### 场景：安装 CLI 工具

**给定**：更新后的 `requirements.txt`

**当**：运行 `pip install -r requirements.txt`

**然后**：应安装以下包

**新增包**：
```
# CLI 工具
typer>=0.12.0
rich>=13.0.0
```

#### 场景：验证 CLI 工具安装

**验证**：
```python
import typer
from rich.console import Console
from rich.progress import Progress

# 应能成功导入
```

---

### 需求：保留的依赖

系统**必须**保留图数据库、LLM 相关、向量化和数据处理等依赖。

#### 保留的包

**图数据库**：
```
neo4j>=5.0.0
```

**LLM 相关**：
```
openai>=1.0.0
tiktoken>=0.7.0
```

**向量化和嵌入**：
```
sentence-transformers>=2.7.0
```

**数据处理**：
```
numpy>=1.24.0
pandas>=2.0.0
openpyxl>=3.1.0
```

**测试**：
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=5.0.0
```

---

## 迁移验证

### 需求：依赖验证测试

系统**必须**测试所有依赖的兼容性。

#### 场景：运行依赖验证

**给定**：更新后的所有依赖

**当**：运行验证脚本

**然后**：
```bash
# 1. 验证安装
pip install -r requirements.txt

# 2. 验证导入
python -c "
from raganything import RAGAnything
from langgraph.graph import StateGraph
from fastapi import FastAPI
from typer import Typer
print('All imports successful')
"

# 3. 运行测试
pytest tests/test_dependencies.py
```

#### 场景：冲突检测

**给定**：更新的依赖

**当**：检查包冲突

**然后**：
```bash
pip check
# 应报告无冲突
```

---

## 版本兼容性

### 需求：Python 版本

**要求**：Python >= 3.10

### 需求：平台兼容性

- **macOS**：完全支持
- **Linux**：完全支持
- **Windows**：支持（可能需要额外配置）
