# RESTful API 接口规范

## 新增需求

### 需求：FastAPI 应用

系统**必须**提供基于 FastAPI 的 RESTful API。

#### 场景：应用启动

**给定**：API 应用启动

**当**：访问根路径 `/`

**那么**：应返回欢迎信息

```json
{
  "name": "Medical Graph RAG API",
  "version": "2.0.0",
  "status": "running"
}
```

#### 场景：健康检查

**给定**：负载均衡器需要检查服务状态

**当**：访问 `/health`

**然后**：应返回服务健康状态

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "neo4j": "connected",
    "lightrag": "ready"
  }
}
```

---

### 需求：文档管理 API

系统**必须**提供文档上传、查询和删除的 API 端点。

#### 场景：上传文档

**给定**：
- 一个 PDF 文档

**当**：发送 `POST /api/v1/documents` 请求

**请求**：
```http
POST /api/v1/documents
Content-Type: multipart/form-data

file: paper.pdf
```

**响应** (201 Created):
```json
{
  "doc_id": "doc-abc123",
  "status": "processing",
  "filename": "paper.pdf",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### 场景：获取文档详情

**给定**：
- 一个已上传的文档 ID

**当**：发送 `GET /api/v1/documents/{doc_id}` 请求

**响应** (200 OK):
```json
{
  "doc_id": "doc-abc123",
  "filename": "paper.pdf",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "stats": {
    "text_length": 15234,
    "image_count": 3,
    "table_count": 2,
    "equation_count": 5
  }
}
```

#### 场景：删除文档

**给定**：
- 一个文档 ID

**当**：发送 `DELETE /api/v1/documents/{doc_id}` 请求

**响应** (200 OK):
```json
{
  "doc_id": "doc-abc123",
  "deleted": true
}
```

---

### 需求：查询 API

系统**必须**提供执行查询和检索的 API 端点。

#### 场景：执行查询

**给定**：
- 一个查询问题

**当**：发送 `POST /api/v1/query` 请求

**请求**：
```json
{
  "query": "糖尿病患者的主要症状是什么？",
  "graph_id": "graph-123",
  "mode": "hybrid",
  "top_k": 10
}
```

**响应** (200 OK):
```json
{
  "answer": "糖尿病的主要症状包括多饮、多尿、多食和体重减轻...",
  "sources": [
    {
      "doc_id": "doc-1",
      "chunk_id": "chunk-5",
      "content": "糖尿病患者常出现多饮、多尿...",
      "relevance": 0.95
    },
    {
      "doc_id": "doc-2",
      "chunk_id": "chunk-12",
      "content": "典型的糖尿病症状包括...",
      "relevance": 0.87
    }
  ],
  "graph_context": {
    "entities": [
      {"id": "e1", "name": "糖尿病", "type": "DISEASE"},
      {"id": "e2", "name": "血糖", "type": "LABORATORY_DATA"}
    ],
    "relationships": [
      {"source": "e1", "target": "e2", "type": "CAUSES"}
    ]
  },
  "query_time_ms": 1234
}
```

#### 场景：流式查询

**给定**：
- 启用流式输出的请求

**当**：发送 `POST /api/v1/query` 并设置 `stream=true`

**请求**：
```json
{
  "query": "解释糖尿病的病因",
  "graph_id": "graph-123",
  "stream": true
}
```

**响应** (text/event-stream):
```
data: {"token": "糖尿病"}

data: {"token": "的"}

data: {"token": "病因"}

...

data: {"done": true, "sources": [...]}
```

#### 场景：多模态查询

**给定**：
- 包含图像的查询

**当**：发送带图像的查询请求

**请求**：
```http
POST /api/v1/query
Content-Type: multipart/form-data

query: "分析这张医学图像"
image: xray.jpg
graph_id: graph-123
```

**响应**：应包含对图像的分析

---

### 需求：图谱管理 API

系统**必须**提供图谱列表、详情、删除和节点合并的 API 端点。

#### 场景：列出所有图谱

**给定**：系统中有多个图谱

**当**：发送 `GET /api/v1/graphs` 请求

**响应** (200 OK):
```json
{
  "graphs": [
    {
      "graph_id": "graph-123",
      "created_at": "2024-01-15T10:00:00Z",
      "entity_count": 127,
      "relationship_count": 342,
      "document_count": 5
    },
    {
      "graph_id": "graph-456",
      "created_at": "2024-01-14T15:30:00Z",
      "entity_count": 89,
      "relationship_count": 156,
      "document_count": 2
    }
  ],
  "total": 2
}
```

#### 场景：获取图谱详情

**给定**：
- 一个图谱 ID

**当**：发送 `GET /api/v1/graphs/{graph_id}` 请求

**响应** (200 OK):
```json
{
  "graph_id": "graph-123",
  "created_at": "2024-01-15T10:00:00Z",
  "stats": {
    "entity_count": 127,
    "relationship_count": 342,
    "document_count": 5
  },
  "entity_types": {
    "DISEASE": 15,
    "MEDICINE": 23,
    "SYMPTOM": 34,
    "ANATOMICAL_STRUCTURE": 28
  },
  "relationship_types": {
    "TREATS": 45,
    "CAUSES": 67,
    "SYMPTOM_OF": 89
  }
}
```

#### 场景：删除图谱

**给定**：
- 一个图谱 ID

**当**：发送 `DELETE /api/v1/graphs/{graph_id}` 请求

**响应** (200 OK):
```json
{
  "graph_id": "graph-123",
  "deleted": true
}
```

#### 场景：合并图谱节点

**给定**：
- 一个图谱 ID

**当**：发送 `POST /api/v1/graphs/{graph_id}/merge` 请求

**请求**：
```json
{
  "threshold": 0.7,
  "entity_types": ["DISEASE", "MEDICINE"]
}
```

**响应** (200 OK):
```json
{
  "graph_id": "graph-123",
  "merged_count": 23,
  "final_entity_count": 104
}
```

#### 场景：图谱可视化

**给定**：
- 一个图谱 ID

**当**：发送 `GET /api/v1/graphs/{graph_id}/visualize?format=mermaid` 请求

**响应** (200 OK):
```json
{
  "format": "mermaid",
  "content": "graph TD\n    D1[糖尿病] -->|TREATS| M1[胰岛素]\n    ..."
}
```

---

#### 场景：导出图谱

**给定**：
- 一个图谱 ID
- 导出格式（json, csv, mermaid）

**当**：发送 `GET /api/v1/graphs/{graph_id}/export?format=json` 请求

**响应** (200 OK):
```json
{
  "graph_id": "graph-123",
  "format": "json",
  "download_url": "/downloads/graph-123-export.json",
  "expires_at": "2024-01-15T11:00:00Z"
}
```

---

#### 场景：三层图谱关联

**给定**：
- 三个图谱 ID（顶层、中层、底层）

**当**：发送 `POST /api/v1/graphs/trinity/link` 请求

**请求**：
```json
{
  "top_graph_id": "patient-data",
  "middle_graph_id": "medical-literature",
  "bottom_graph_id": "medical-dictionary",
  "similarity_threshold": 0.75
}
```

**响应** (200 OK):
```json
{
  "link_count": 47,
  "top_graph_id": "patient-data",
  "middle_graph_id": "medical-literature",
  "bottom_graph_id": "medical-dictionary",
  "created_at": "2024-01-15T10:45:00Z"
}
```

---

### 需求：错误处理

系统**必须**提供统一的错误响应格式。

#### 场景：文档不存在

**给定**：
- 一个不存在的文档 ID

**当**：访问 `GET /api/v1/documents/nonexistent`

**响应** (404 Not Found):
```json
{
  "error": "Document not found",
  "doc_id": "nonexistent",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 场景：验证错误

**给定**：
- 无效的请求参数

**当**：发送 `POST /api/v1/query` 缺少必填字段

**响应** (422 Unprocessable Entity):
```json
{
  "error": "Validation error",
  "details": [
    {
      "field": "query",
      "message": "This field is required"
    },
    {
      "field": "graph_id",
      "message": "This field is required"
    }
  ]
}
```

#### 场景：服务器错误

**给定**：
- 内部处理错误

**响应** (500 Internal Server Error):
```json
{
  "error": "Internal server error",
  "message": "Failed to process request",
  "request_id": "req-abc123"
}
```

---

### 需求：API 文档

系统**必须**提供 OpenAPI (Swagger) 和 ReDoc 格式的 API 文档。

#### 场景：OpenAPI 文档

**给定**：应用启动

**当**：访问 `/docs`

**然后**：
- 应显示 Swagger UI
- 应包含所有端点的文档
- 应包含请求/响应示例
- 应支持 "Try it out" 功能

#### 场景：ReDoc 文档

**给定**：应用启动

**当**：访问 `/redoc`

**然后**：应显示 ReDoc 格式的 API 文档

---

### 需求：认证和授权

系统**必须**支持 API Key 认证和速率限制（未来扩展）。

#### 场景：API Key 认证

**给定**：启用 API Key 认证

**当**：发送请求

**请求**：
```http
GET /api/v1/graphs
Authorization: Bearer YOUR_API_KEY
```

**未认证响应** (401 Unauthorized):
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing API key"
}
```

#### 场景：速率限制

**给定**：配置了速率限制

**当**：超过限制

**响应** (429 Too Many Requests):
```json
{
  "error": "Rate limit exceeded",
  "limit": 100,
  "window": "1h",
  "retry_after": 3600
}
```
