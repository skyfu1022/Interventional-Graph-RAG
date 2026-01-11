# 核心模块规范

## 新增需求

### 需求：配置管理系统

系统**必须**提供统一的配置管理机制，支持环境变量和配置文件，使用 Pydantic Settings 进行类型安全的配置。

#### 场景：从环境变量加载配置

**给定**：系统已设置必要的环境变量
- `OPENAI_API_KEY`
- `NEO4J_URL`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

**当**：应用程序启动并初始化配置

**那么**：
- 配置应从环境变量自动加载
- 缺失的必需配置应抛出清晰的验证错误
- 可选配置应使用默认值

**验证**：
```python
settings = Settings()
assert settings.openai_api_key == "sk-..."
assert settings.neo4j_url == "bolt://localhost:7687"
```

#### 场景：从 .env 文件加载配置

**给定**：存在 `.env` 文件包含配置

**当**：应用程序启动

**那么**：
- 配置应从 `.env` 文件加载
- 环境变量应覆盖 `.env` 文件中的值

---

### 需求：LangGraph 状态定义

系统**必须**定义类型安全的状态类，用于 LangGraph 工作流的状态管理。

#### 场景：图谱构建状态

**给定**：正在执行图谱构建工作流

**当**：工作流在不同节点间流转

**那么**：状态应包含以下字段：
- `document_path: str` - 文档路径
- `content_chunks: List[str]` - 内容分块
- `entities: List[Entity]` - 提取的实体
- `relationships: List[Relationship]` - 提取的关系
- `graph_id: Optional[str]` - 图谱 ID
- `error: Optional[str]` - 错误信息

**验证**：
```python
state = GraphState(
    document_path="/path/to/doc.pdf",
    content_chunks=["chunk1", "chunk2"],
    entities=[],
    relationships=[],
)
```

#### 场景：查询状态继承 MessagesState

**给定**：使用 LangChain 的消息功能

**当**：定义查询状态

**那么**：
- `QueryState` 应继承 `MessagesState`
- 应包含查询特定字段：`query`, `retrieved_context`, `answer`, `sources`

---

### 需求：异常处理

系统**必须**定义清晰的异常层次结构，便于错误处理和调试。

#### 场景：文档处理异常

**给定**：文档处理过程中发生错误

**当**：捕获到文档相关错误

**那么**：
- 应抛出 `DocumentError` 异常
- 异常应包含描述性消息和原始异常

**验证**：
```python
try:
    process_document("invalid.pdf")
except DocumentError as e:
    assert "Failed to process" in str(e)
```

#### 场景：图数据库操作异常

**给定**：Neo4j 连接失败

**当**：执行图操作

**那么**：应抛出 `GraphError` 异常

---

### 需求：日志系统

系统**必须**提供统一的日志配置，支持不同级别和输出目标。

#### 场景：配置控制台和文件日志

**给定**：应用程序启动

**当**：配置日志系统

**那么**：
- 控制台应输出 INFO 及以上级别日志
- 文件应记录 DEBUG 及以上级别日志
- 日志应包含时间戳、级别、模块名和消息

#### 场景：模块化日志

**给定**：不同模块需要不同日志级别

**当**：配置模块日志

**那么**：
- 可以为每个模块单独设置日志级别
- 敏感信息（API 密钥）应被自动过滤
