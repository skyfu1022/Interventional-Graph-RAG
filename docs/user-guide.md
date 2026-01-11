# Medical Graph RAG 用户指南

Medical Graph RAG 是一个基于 LangGraph 和 RAG-Anything 的医学知识图谱构建和查询工具。本指南将帮助您快速上手使用 CLI 和 REST API。

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [CLI 使用指南](#cli-使用指南)
- [API 使用指南](#api-使用指南)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 安装

### 环境要求

- Python 3.10+
- Neo4j 数据库（图存储）
- Milvus 数据库（向量存储）
- OpenAI API 密钥

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/your-org/Medical-Graph-RAG.git
cd Medical-Graph-RAG
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境**

复制环境变量示例文件并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写您的 API 密钥和数据库配置。

## 快速开始

### 使用 CLI

```bash
# 查看帮助信息
python -m src.cli.main --help

# 启动 API 服务器
python -m src.cli.main serve

# 查询知识图谱
python -m src.cli.main query "什么是糖尿病?"

# 摄入文档
python -m src.cli.main ingest document.txt

# 查看系统信息
python -m src.cli.main info
```

### 使用 API

```bash
# 启动 API 服务器
python -m src.cli.main serve

# 访问 API 文档
open http://localhost:8000/docs
```

## CLI 使用指南

Medical Graph RAG 提供了一个功能完整的命令行界面（CLI），名为 `medgraph`。

### 全局选项

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--workspace` | `-w` | `medical` | 工作空间名称 |
| `--config` | `-c` | `None` | 配置文件路径（JSON 或 YAML） |
| `--log-level` | `-l` | `INFO` | 日志级别（DEBUG, INFO, WARNING, ERROR） |
| `--verbose` | `-V` | `false` | 启用详细输出模式 |
| `--version` | `-v` | - | 显示版本信息 |

### 命令列表

#### 1. build - 构建知识图谱

初始化或重建知识图谱。

```bash
medgraph build [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--chunk-size` | - | `512` | 文本块大小（字符数） |
| `--overlap` | - | `50` | 文本块重叠大小 |
| `--force` | `-f` | `false` | 强制重新构建，覆盖现有图谱 |

**示例：**

```bash
# 使用默认参数构建
medgraph build

# 自定义文本块大小并强制重建
medgraph build --chunk-size 1024 --overlap 100 --force

# 指定工作空间
medgraph build --workspace my-medical-graph
```

#### 2. query - 查询知识图谱

使用自然语言问题查询医学知识图谱。

```bash
medgraph query QUESTION [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode` | `-m` | `hybrid` | 查询模式 |
| `--graph-id` | `-g` | `default` | 图谱 ID |
| `--format` | `-f` | `text` | 输出格式（text, json） |
| `--stream` | `-s` | `false` | 启用流式输出 |

**查询模式：**

- `naive`: 朴素模式，直接检索
- `local`: 本地模式，基于实体邻域检索
- `global`: 全局模式，基于全局社区摘要检索
- `hybrid`: 混合模式，结合本地和全局检索（推荐）
- `mix`: 混合模式，动态调整检索策略
- `bypass`: 旁路模式，直接使用 LLM

**示例：**

```bash
# 基本查询
medgraph query "什么是糖尿病?"

# 使用特定查询模式
medgraph query "糖尿病的症状有哪些?" --mode local

# 输出 JSON 格式
medgraph query "高血压的治疗方法" --format json

# 流式输出
medgraph query "详细说明心脏病的病因" --stream

# 查询特定图谱
medgraph query "什么是肺炎?" --graph-id respiratory
```

#### 3. ingest - 摄入文档

将文档摄入到知识图谱中。

```bash
medgraph ingest FILE_PATH [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--doc-id` | `-d` | `None` | 文档 ID（不指定则自动生成） |
| `--batch` | `-b` | `false` | 批量模式（file_path 指向目录） |
| `--max-concurrency` | - | `5` | 批量处理时的最大并发数 |

**支持的文件格式：**

- `.txt` - 纯文本文件
- `.md` - Markdown 文件
- `.json` - JSON 文件
- `.csv` - CSV 文件
- `.pdf` - PDF 文件

**示例：**

```bash
# 摄入单个文档
medgraph ingest medical_textbook.txt

# 指定文档 ID
medgraph ingest research_paper.pdf --doc-id paper-001

# 批量摄入目录中的所有文档
medgraph ingest ./documents/ --batch

# 批量摄入时限制并发数
medgraph ingest ./documents/ --batch --max-concurrency 3
```

#### 4. serve - 启动 API 服务器

启动 FastAPI 开发服务器。

```bash
medgraph serve [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--host` | `-h` | `127.0.0.1` | 服务器监听的主机地址 |
| `--port` | `-p` | `8000` | 服务器端口号 |
| `--reload` | `-r` | `false` | 启用自动重载（开发模式） |
| `--log-level` | - | `info` | 日志级别 |

**示例：**

```bash
# 默认启动
medgraph serve

# 启用热重载（开发模式）
medgraph serve --reload

# 自定义端口
medgraph serve --port 8080

# 监听所有网络接口（允许局域网访问）
medgraph serve --host 0.0.0.0

# 组合使用
medgraph serve --host 0.0.0.0 --port 9000 --reload
```

#### 5. export - 导出图谱数据

将知识图谱数据导出为指定格式的文件。

```bash
medgraph export [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--output` | `-o` | `export.json` | 输出文件路径 |
| `--format` | `-f` | `json` | 导出格式（json, csv, mermaid） |
| `--graph-id` | `-g` | `default` | 要导出的图谱 ID |

**导出格式：**

- `json`: JSON 格式的图谱数据
- `csv`: CSV 格式的图谱数据（节点和边）
- `mermaid`: Mermaid 图表定义（可用于可视化）

**示例：**

```bash
# 导出为 JSON（默认）
medgraph export

# 导出为 Mermaid 图表
medgraph export --format mermaid --output graph.mmd

# 导出为 CSV
medgraph export --format csv --output data.csv

# 导出特定图谱
medgraph export --graph-id my-graph --format json --output my-graph.json
```

#### 6. info - 显示系统信息

列出所有图谱或显示特定图谱的详细信息。

```bash
medgraph info [OPTIONS]
```

**选项：**

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--graph-id` | `-g` | `None` | 显示特定图谱的详细信息 |

**示例：**

```bash
# 列出所有图谱
medgraph info

# 显示特定图谱的详细信息
medgraph info --graph-id medical

# 查看性能统计
medgraph info
```

## API 使用指南

Medical Graph RAG 提供了 RESTful API，支持通过 HTTP 请求访问所有功能。

### 启动 API 服务器

```bash
python -m src.cli.main serve --host 0.0.0.0 --port 8000
```

### API 文档

启动服务器后，访问以下地址查看交互式 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 认证方式

如果配置了 `API_KEYS` 环境变量，API 将启用认证。需要在请求头中提供 API Key：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/query
```

### API 端点

#### 健康检查

**根路径**

```bash
curl http://localhost:8000/
```

**响应：**

```json
{
  "name": "Medical Graph RAG API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc",
  "health": "/health"
}
```

**健康检查**

```bash
curl http://localhost:8000/health
```

**响应：**

```json
{
  "status": "healthy",
  "service": "medical-graph-rag-api",
  "version": "1.0.0"
}
```

#### 查询 API

**1. 执行查询**

```bash
POST /api/v1/query
Content-Type: application/json
```

**请求体：**

```json
{
  "query": "什么是糖尿病?",
  "mode": "hybrid",
  "graph_id": "medical"
}
```

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是糖尿病?",
    "mode": "hybrid",
    "graph_id": "medical"
  }'
```

**响应：**

```json
{
  "query": "什么是糖尿病?",
  "answer": "糖尿病是一种慢性代谢疾病...",
  "mode": "hybrid",
  "graph_id": "medical",
  "sources": [
    {
      "content": "糖尿病（diabetes mellitus）是...",
      "relevance": 0.95
    }
  ],
  "context": "...",
  "graph_context": "...",
  "retrieval_count": 5,
  "latency_ms": 234
}
```

**2. 流式查询（SSE）**

```bash
POST /api/v1/query/stream
Content-Type: application/json
```

**请求体：**

```json
{
  "query": "详细说明糖尿病的病因",
  "mode": "hybrid",
  "graph_id": "medical"
}
```

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "详细说明糖尿病的病因",
    "mode": "hybrid"
  }'
```

**响应（Server-Sent Events）：**

```
data: {"chunk": "糖尿病"}

data: {"chunk": "是一种"}

data: {"chunk": "慢性疾病"}

...

data: {"done": true}
```

**3. 智能查询（多轮对话）**

```bash
POST /api/v1/query/intelligent
Content-Type: application/json
```

**请求体：**

```json
{
  "query": "它有哪些症状?",
  "mode": "hybrid",
  "graph_id": "medical",
  "conversation_history": [
    {"role": "user", "content": "什么是糖尿病?"},
    {"role": "assistant", "content": "糖尿病是..."}
  ]
}
```

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/query/intelligent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "它有哪些症状?",
    "mode": "hybrid",
    "conversation_history": [
      {"role": "user", "content": "什么是糖尿病?"},
      {"role": "assistant", "content": "糖尿病是..."}
    ]
  }'
```

#### 文档管理 API

**1. 上传文档**

```bash
POST /api/v1/documents
Content-Type: multipart/form-data
```

**curl 示例：**

```bash
# 上传文本文件
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@medical.txt" \
  -F "doc_id=doc-001"

# 上传 PDF 文件
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@research.pdf"
```

**响应：**

```json
{
  "doc_id": "doc-001",
  "status": "completed",
  "file_name": "medical.txt",
  "message": "文档上传成功",
  "entity_count": 42,
  "relationship_count": 35
}
```

**2. 获取文档详情**

```bash
GET /api/v1/documents/{doc_id}
```

**curl 示例：**

```bash
curl -X GET "http://localhost:8000/api/v1/documents/doc-001"
```

**响应：**

```json
{
  "doc_id": "doc-001",
  "file_name": "medical.txt",
  "file_path": "/path/to/file",
  "status": "completed",
  "entity_count": 42,
  "relationship_count": 35,
  "created_at": "2026-01-11T12:00:00Z",
  "updated_at": "2026-01-11T12:00:00Z"
}
```

**3. 删除文档**

```bash
DELETE /api/v1/documents/{doc_id}
```

**curl 示例：**

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/doc-001"
```

**响应：**

```json
{
  "doc_id": "doc-001",
  "success": true,
  "message": "文档删除成功"
}
```

#### 图谱管理 API

**1. 列出所有图谱**

```bash
GET /api/v1/graphs?min_entity_count=0
```

**curl 示例：**

```bash
curl -X GET "http://localhost:8000/api/v1/graphs"
```

**响应：**

```json
{
  "total": 2,
  "graphs": [
    {
      "graph_id": "medical",
      "workspace": "medical",
      "entity_count": 1234,
      "relationship_count": 2345,
      "document_count": 10,
      "created_at": "2026-01-11T12:00:00Z",
      "updated_at": "2026-01-11T12:00:00Z"
    }
  ]
}
```

**2. 获取图谱详情**

```bash
GET /api/v1/graphs/{graph_id}
```

**curl 示例：**

```bash
curl -X GET "http://localhost:8000/api/v1/graphs/medical"
```

**响应：**

```json
{
  "graph_info": {
    "graph_id": "medical",
    "workspace": "medical",
    "entity_count": 1234,
    "relationship_count": 2345,
    "document_count": 10,
    "created_at": "2026-01-11T12:00:00Z",
    "updated_at": "2026-01-11T12:00:00Z"
  },
  "config": null
}
```

**3. 删除图谱**

```bash
DELETE /api/v1/graphs/{graph_id}
Content-Type: application/json
```

**请求体：**

```json
{
  "confirm": true
}
```

**curl 示例：**

```bash
curl -X DELETE "http://localhost:8000/api/v1/graphs/medical" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

**响应：**

```json
{
  "graph_id": "medical",
  "deleted": true,
  "message": "图谱 medical 已成功删除"
}
```

**4. 合并图谱节点**

```bash
POST /api/v1/graphs/{graph_id}/merge
Content-Type: application/json
```

**请求体：**

```json
{
  "source_entities": ["实体1", "实体2"],
  "target_entity": "合并后的实体",
  "threshold": 0.8,
  "merge_strategy": "union"
}
```

**curl 示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/graphs/medical/merge" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entities": ["糖尿病", "糖尿病 mellitus"],
    "target_entity": "糖尿病",
    "threshold": 0.8,
    "merge_strategy": "union"
  }'
```

**响应：**

```json
{
  "graph_id": "medical",
  "merged_count": 1,
  "source_entities": ["糖尿病", "糖尿病 mellitus"],
  "target_entity": "糖尿病",
  "message": "成功合并 1 个节点"
}
```

**5. 导出图谱可视化**

```bash
GET /api/v1/graphs/{graph_id}/visualize?format=mermaid
```

**支持的格式：** `mermaid`, `json`, `csv`

**curl 示例：**

```bash
# 导出为 Mermaid 图表
curl -X GET "http://localhost:8000/api/v1/graphs/medical/visualize?format=mermaid" \
  -o graph.mmd

# 导出为 JSON
curl -X GET "http://localhost:8000/api/v1/graphs/medical/visualize?format=json" \
  -o graph.json

# 导出为 CSV
curl -X GET "http://localhost:8000/api/v1/graphs/medical/visualize?format=csv" \
  -o graph.csv
```

#### 多模态查询 API

**多模态查询（支持图像和表格）**

```bash
POST /api/v1/query/multimodal
Content-Type: multipart/form-data
```

**支持的文件类型：**
- 图像: `.jpg`, `.jpeg`, `.png`, `.gif`
- 表格: `.csv`, `.xlsx`, `.xls`
- 最大文件大小: 10MB

**curl 示例（图像查询）：**

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -F "query=这张X光片显示什么?" \
  -F "image=@xray.jpg" \
  -F "mode=hybrid"
```

**curl 示例（表格查询）：**

```bash
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -F "query=分析这个血常规检查结果" \
  -F "table_data=@blood_test.csv" \
  -F "mode=hybrid"
```

**响应：**

```json
{
  "query": "这张X光片显示什么?",
  "answer": "根据X光片显示...",
  "mode": "hybrid",
  "graph_id": "medical",
  "sources": [...],
  "retrieval_count": 3,
  "latency_ms": 456
}
```

### 速率限制

API 实现了基于 IP 的速率限制：

- 默认配置：每个 IP 地址在 60 秒内最多 100 个请求
- 超过限制时返回 `429 Too Many Requests` 错误

可通过环境变量配置：

```bash
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS=100
export RATE_LIMIT_WINDOW=60
```

### 错误响应

API 错误响应遵循以下格式：

```json
{
  "error": "ErrorType",
  "message": "错误描述",
  "detail": {}
}
```

常见 HTTP 状态码：

- `200` - 成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `422` - 数据验证失败
- `429` - 请求过于频繁（速率限制）
- `500` - 服务器内部错误

## 配置说明

Medical Graph RAG 支持多种配置方式，按优先级从高到低为：

1. 环境变量
2. `.env` 文件
3. 配置文件（JSON 或 YAML）
4. 代码默认值

### 环境变量配置

创建 `.env` 文件（可从 `.env.example` 复制）：

```bash
cp .env.example .env
```

**必需配置：**

| 环境变量 | 说明 | 示例值 |
|----------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-proj-...` |
| `NEO4J_URI` | Neo4j 连接 URI | `neo4j://localhost:7687` |
| `MILVUS_URI` | Milvus 连接 URI | `http://localhost:19530` |

**可选配置：**

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OPENAI_API_BASE` | OpenAI API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 语言模型名称 | `gpt-4o-mini` |
| `EMBEDDING_MODEL` | 嵌入模型名称 | `text-embedding-3-large` |
| `NEO4J_USERNAME` | Neo4j 用户名 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码 | `password` |
| `MILVUS_TOKEN` | Milvus 认证令牌 | - |
| `MILVUS_API_KEY` | Milvus API 密钥 | - |
| `RAG_WORKING_DIR` | RAG 工作目录 | `./data/rag_storage` |
| `RAG_WORKSPACE` | RAG 工作空间名称 | `medical` |
| `MEDICAL_ENTITY_TYPES` | 医学实体类型列表 | `["DISEASE","MEDICINE",...]` |

**API 认证配置：**

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `API_KEYS` | API 密钥列表（逗号分隔） | - |
| `RATE_LIMIT_ENABLED` | 是否启用速率限制 | `true` |
| `RATE_LIMIT_REQUESTS` | 时间窗口内的最大请求数 | `100` |
| `RATE_LIMIT_WINDOW` | 时间窗口长度（秒） | `60` |

### 配置文件（YAML）

创建 `config.yaml` 文件：

```yaml
# 工作空间配置
workspace: "medical"

# OpenAI 配置
openai_api_key: "sk-your-api-key-here"
openai_api_base: null  # 可选
llm_model: "gpt-4o-mini"
embedding_model: "text-embedding-3-large"

# Neo4j 配置
neo4j_uri: "neo4j://localhost:7687"
neo4j_username: "neo4j"
neo4j_password: "password"

# Milvus 配置
milvus_uri: "http://localhost:19530"
milvus_token: null  # 可选
milvus_api_key: null  # 可选

# RAG-Anything 配置
rag_working_dir: "./data/rag_storage"
rag_workspace: "medical"

# 医学领域实体类型
medical_entity_types:
  - "DISEASE"
  - "MEDICINE"
  - "SYMPTOM"
  - "ANATOMICAL_STRUCTURE"
  - "BODY_FUNCTION"
  - "LABORATORY_DATA"
  - "PROCEDURE"
```

### 配置文件（JSON）

创建 `config.json` 文件：

```json
{
  "workspace": "medical",
  "openai_api_key": "sk-your-api-key-here",
  "openai_api_base": null,
  "llm_model": "gpt-4o-mini",
  "embedding_model": "text-embedding-3-large",
  "neo4j_uri": "neo4j://localhost:7687",
  "neo4j_username": "neo4j",
  "neo4j_password": "password",
  "milvus_uri": "http://localhost:19530",
  "milvus_token": null,
  "milvus_api_key": null,
  "rag_working_dir": "./data/rag_storage",
  "rag_workspace": "medical",
  "medical_entity_types": [
    "DISEASE",
    "MEDICINE",
    "SYMPTOM",
    "ANATOMICAL_STRUCTURE",
    "BODY_FUNCTION",
    "LABORATORY_DATA",
    "PROCEDURE"
  ]
}
```

### 使用配置文件

**在 CLI 中使用：**

```bash
# 使用配置文件
medgraph --config config.yaml query "什么是糖尿病?"

# 使用环境变量
medgraph query "什么是糖尿病?"
```

**在代码中使用：**

```python
from src.sdk import MedGraphClient

# 从配置文件加载
client = MedGraphClient.from_config("config.yaml")

# 从环境变量加载
client = MedGraphClient.from_env()

# 使用默认配置
client = MedGraphClient()
```

### 医学实体类型

系统预定义了以下医学实体类型：

| 实体类型 | 说明 |
|----------|------|
| `DISEASE` | 疾病/问题 |
| `MEDICINE` | 药物 |
| `SYMPTOM` | 症状 |
| `ANATOMICAL_STRUCTURE` | 解剖结构 |
| `BODY_FUNCTION` | 身体功能 |
| `LABORATORY_DATA` | 实验室数据 |
| `PROCEDURE` | 医疗程序 |

可以通过配置文件自定义实体类型列表。

## 常见问题

### 1. 如何获取 OpenAI API 密钥？

访问 [OpenAI API 密钥页面](https://platform.openai.com/api-keys) 创建 API 密钥。

### 2. 如何安装和配置 Neo4j？

**使用 Docker：**

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

访问 http://localhost:7474 打开 Neo4j Browser。

### 3. 如何安装和配置 Milvus？

**使用 Docker：**

```bash
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -v /path/to/milvus:/var/lib/milvus \
  milvusdb/milvus:latest
```

### 4. CLI 命令找不到？

确保已激活虚拟环境并安装了依赖：

```bash
source venv/bin/activate
pip install -r requirements.txt

# 使用 Python 模块方式运行
python -m src.cli.main --help
```

### 5. API 认证失败？

检查 `API_KEYS` 环境变量是否正确配置：

```bash
# 在 .env 文件中设置
API_KEYS=sk-key-1,sk-key-2,sk-key-3

# 或在命令行中设置
export API_KEYS=sk-your-api-key

# 在请求中添加认证头
curl -H "X-API-Key: sk-your-api-key" http://localhost:8000/api/v1/query
```

### 6. 如何提高查询性能？

- 使用更小的 LLM 模型（如 `gpt-4o-mini`）
- 调整 `--chunk-size` 参数（默认 512）
- 选择合适的查询模式（`hybrid` 通常效果最好）
- 确保数据库连接正常

### 7. 流式查询没有响应？

流式查询使用 Server-Sent Events (SSE)，确保客户端支持 SSE。使用 curl 测试时：

```bash
curl -N -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试查询", "mode": "hybrid"}'
```

### 8. 文档摄入失败？

检查以下几点：

- 文件格式是否支持（.txt, .md, .json, .csv, .pdf）
- 文件大小是否合理（建议 < 10MB）
- OpenAI API 密钥是否有效
- 网络连接是否正常

### 9. 如何查看详细日志？

使用 `--verbose` 或 `--log-level DEBUG`：

```bash
medgraph --verbose query "测试"

# 或
medgraph --log-level DEBUG query "测试"
```

### 10. 如何备份知识图谱？

使用导出功能：

```bash
# CLI 方式
medgraph export --format json --output backup.json

# API 方式
curl -X GET "http://localhost:8000/api/v1/graphs/medical/visualize?format=json" \
  -o backup.json
```

### 11. 如何使用多模态查询？

多模态查询支持图像和表格文件上传：

```bash
# 图像查询
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -F "query=描述这张图像" \
  -F "image=@xray.jpg"

# 表格查询
curl -X POST "http://localhost:8000/api/v1/query/multimodal" \
  -F "query=分析数据" \
  -F "table_data=@data.csv"
```

### 12. 速率限制如何调整？

修改 `.env` 文件中的速率限制配置：

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=200  # 增加请求数
RATE_LIMIT_WINDOW=60     # 时间窗口（秒）
```

## 技术支持

如有问题或建议，请：

1. 查看 [GitHub Issues](https://github.com/your-org/Medical-Graph-RAG/issues)
2. 提交新的 Issue 描述问题
3. 参与讨论和贡献代码

## 许可证

MIT License
