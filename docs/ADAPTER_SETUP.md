# RAG-Anything 适配器设置说明

## 概述

`src/core/adapters.py` 模块提供了 LightRAG 1.4.9+ 的核心适配器，支持：
- Neo4j 图存储
- Milvus 向量存储
- 异步文档摄入和查询
- 多模态内容处理

## 安装要求

### 1. Python 环境
- Python 3.10 或更高版本

### 2. LightRAG 包（重要）

本项目使用 `lightrag-hku` 包，而非普通的 `lightrag` 包。

**安装步骤：**

```bash
# 卸载可能存在的旧版 lightrag
pip uninstall lightrag -y

# 安装正确的 lightrag-hku 包
pip install 'lightrag-hku>=1.4.9'
```

**验证安装：**

```bash
python -c "from lightrag import LightRAG, QueryParam; print('安装成功')"
```

### 3. 数据库服务

#### Neo4j 图数据库

```bash
# Docker 方式运行
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15-community
```

#### Milvus 向量数据库

```bash
# 使用 Docker Compose
wget https://github.com/milvus-io/milvus/releases/download/v2.4.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

### 4. 环境变量配置

在项目根目录创建 `.env` 文件：

```env
# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1

# LLM 配置
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large

# Neo4j 配置
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Milvus 配置
MILVUS_URI=http://localhost:19530
# MILVUS_TOKEN=your-token-if-using-cloud

# RAG 工作目录
RAG_WORKING_DIR=./data/rag_storage
RAG_WORKSPACE=medical
```

## 使用示例

### 基础用法

```python
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
import asyncio

async def main():
    # 加载配置
    config = Settings()

    # 创建适配器
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()

    # 摄入文本
    result = await adapter.ingest_text(
        "糖尿病是一种慢性代谢性疾病...",
        doc_id="doc-001"
    )
    print(f"摄入结果: {result.to_dict()}")

    # 查询知识图谱
    result = await adapter.query(
        "什么是糖尿病？",
        mode="hybrid"
    )
    print(f"答案: {result.answer}")

    # 关闭适配器
    await adapter.close()

asyncio.run(main())
```

### 使用上下文管理器

```python
async def main():
    config = Settings()

    # 自动管理资源
    async with RAGAnythingAdapter(config) as adapter:
        # 批量摄入
        texts = ["文本1", "文本2", "文本3"]
        results = await adapter.ingest_batch(
            texts,
            doc_ids=["doc-1", "doc-2", "doc-3"]
        )

        # 查询
        result = await adapter.query("查询问题", mode="hybrid")
        print(result.answer)

asyncio.run(main())
```

### 流式查询

```python
async def main():
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()

    # 流式输出答案
    async for chunk in adapter.query_stream("问题", mode="hybrid"):
        print(chunk, end="", flush=True)
    print()

    await adapter.close()
asyncio.run(main())
```

## 查询模式

适配器支持 6 种查询模式：

| 模式 | 描述 |
|------|------|
| `naive` | 简单向量搜索，适合快速问答 |
| `local` | 基于实体的局部检索，关注细节 |
| `global` | 全局社区摘要，关注宏观关系 |
| `hybrid` | 结合 local 和 global，推荐默认模式 |
| `mix` | 知识图谱 + 向量检索混合 |
| `bypass` | 直接调用 LLM，不使用 RAG |

## 故障排除

### 导入错误

如果看到 `ImportError: cannot import name 'LightRAG'`：

```bash
# 检查已安装的包
pip list | grep lightrag

# 如果显示 lightrag 而不是 lightrag-hku
pip uninstall lightrag -y
pip install 'lightrag-hku>=1.4.9'
```

### Neo4j 连接失败

```bash
# 检查 Neo4j 是否运行
docker ps | grep neo4j

# 查看 Neo4j 日志
docker logs neo4j

# 测试连接
bolt://localhost:7687
```

### Milvus 连接失败

```bash
# 检查 Milvus 是否运行
docker ps | grep milvus

# 查看 Milvus 日志
docker logs milvus-standalone

# 测试连接
curl http://localhost:19530/healthz
```

## 验证脚本

运行验证测试：

```bash
python tests/test_adapter.py
```

这将测试：
- 适配器初始化
- 文本摄入
- 查询功能
- 流式输出
- 所有查询模式
- 错误处理

## API 参考

### RAGAnythingAdapter

**方法：**

| 方法 | 描述 |
|------|------|
| `initialize()` | 初始化存储和管道状态 |
| `ingest_text(text, doc_id)` | 摄入文本 |
| `ingest_document(file_path, doc_id)` | 摄入文件 |
| `ingest_batch(texts, doc_ids)` | 批量摄入 |
| `ingest_multimodal(content_list)` | 摄入多模态内容 |
| `query(question, mode, **kwargs)` | 查询知识图谱 |
| `query_stream(question, mode)` | 流式查询 |
| `get_stats()` | 获取图谱统计 |
| `export_data(path, format)` | 导出图谱数据 |
| `close()` | 关闭适配器 |

### 结果类

| 类 | 描述 |
|------|------|
| `IngestResult` | 文档摄入结果 |
| `QueryResult` | 查询结果 |
| `GraphStats` | 图谱统计信息 |

## 更多信息

- LightRAG GitHub: https://github.com/hkuds/lightrag
- LightRAG 文档: https://context7.com/hkuds/lightrag
- Neo4j 文档: https://neo4j.com/docs/
- Milvus 文档: https://milvus.io/docs/
