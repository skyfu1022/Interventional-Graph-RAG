# 任务列表：重构 Medical Graph RAG (混合架构版)

## 概述
采用**混合架构**：保留 LangGraph 用于智能体编排（为介入手术智能体扩展做准备），同时复用 RAG-Anything 的核心能力（Milvus/Neo4j 存储、实体关系提取）。

## 完成进度

| 阶段 | 状态 | 完成时间 |
|------|------|----------|
| 阶段 1：基础设施和依赖迁移 | ✅ 完成 | 2026-01-11 |
| 阶段 2：LangGraph 智能体层 | ✅ 完成 | 2026-01-11 |
| 阶段 3：核心适配器 | ✅ 完成 | 2026-01-11 |
| 阶段 4：底层服务层 | ✅ 完成 | 2026-01-11 |
| 阶段 4.5：SDK 层 | ✅ 完成 | 2026-01-11 |
| 阶段 5：CLI 接口 | ✅ 完成 | 2026-01-11 |
| 阶段 6：RESTful API | ✅ 完成 | 2026-01-11 |
| 阶段 7：测试 | ✅ 完成 | 2026-01-11 |
| 阶段 8：文档和部署 | ✅ 完成 | 2026-01-11 |
| 阶段 9：检索模块增强 | ✅ 完成 | 2026-01-11 |
| 阶段 10：图构建模块增强 | ✅ 完成 | 2026-01-11 |

**总进度**: 57/57 任务完成 (100%)

---

## 阶段 1：基础设施和依赖迁移

### 1.1 依赖管理
- [x] **TASK-001**: 更新 `requirements.txt` ✅
  - 移除 `camel` 和 `nano-graphrag`
  - 添加 `lightrag-hku>=0.1.0`
  - 添加 `langgraph>=0.2.0` 和 `langchain>=0.3.0`
  - 添加 `pymilvus>=2.4.0`
  - 添加 `fastapi[standard]>=0.115.0`
  - 添加 `typer>=0.12.0` 和 `rich>=13.0.0`
  - **验证**: `pip install -r requirements.txt` 无错误

- [x] **TASK-002**: 创建新的目录结构 ✅
  - `src/agents/` - LangGraph 智能体层
  - `src/core/` - 配置和适配器
  - `src/services/` - 底层业务服务
  - `src/sdk/` - Python SDK 层 ⭐ 新增
  - `src/api/` - FastAPI 应用（基于 SDK）
  - `src/cli/` - CLI 命令（基于 SDK）
  - **验证**: 所有目录存在且包含 `__init__.py`

---

## 阶段 2：LangGraph 智能体层

### 2.1 工作流状态定义
- [x] **TASK-003**: 实现状态类 (`src/agents/states.py`) ✅
  - `QueryState` - 查询工作流状态
  - `BuildState` - 图谱构建工作流状态
  - **依赖**: TASK-002

- [x] **TASK-004**: 实现查询工作流 (`src/agents/workflows/query.py`) ✅
  - `create_query_workflow()` - 创建工作流图
  - 节点：analyze_query, retrieve, grade_documents, generate_answer, refine_query
  - 条件边：相关性检查、重试逻辑
  - **依赖**: TASK-003

- [x] **TASK-005**: 实现工作流节点 (`src/agents/nodes.py`) ✅
  - `analyze_query_node()` - 查询分析节点
  - `retrieve_node()` - 检索节点（调用 RAG-Anything）
  - `grade_documents_node()` - 文档评估节点
  - `generate_answer_node()` - 答案生成节点
  - `refine_query_node()` - 查询优化节点
  - **依赖**: TASK-004

- [x] **TASK-006**: 实现图谱构建工作流 (`src/agents/workflows/build.py`) ✅
  - `create_build_workflow()` - 创建构建工作流
  - 节点：ingest, extract_entities, build_graph, merge_nodes（可选）, create_summary
  - 条件边：根据 `--merge` 参数决定是否执行 merge_nodes
  - **依赖**: TASK-003

- [x] **TASK-007**: 实现介入手术智能体扩展点 ✅
  - 定义 `InterventionalState` 状态类
  - 实现介入手术工作流节点
  - 节点：analyze_patient, select_devices, assess_risks, generate_plan
  - 为未来介入手术智能体提供基础
  - **依赖**: TASK-003
  - **验证**:
    ```python
    from src.agents.workflows.interventional import create_interventional_agent
    workflow = create_interventional_agent(rag_adapter)
    result = await workflow.ainvoke({
        "patient_data": {...},
        "procedure_type": "PCI",
    })
    assert result["recommendations"] is not None
    ```

- [x] **TASK-008**: 实现工作流检查点功能 ✅
  - 配置 LangGraph 检查点存储（MemorySaver 或自定义）
  - 支持保存工作流状态
  - 支持从检查点恢复工作流
  - 支持检查点过期和清理
  - **依赖**: TASK-004, TASK-006
  - **验证**:
    ```python
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    workflow = create_build_workflow(checkpointer=memory)
    config = {"configurable": {"thread_id": "build-123"}}
    result = await workflow.ainvoke(initial_state, config)
    restored = await workflow.ainvoke(None, config)
    assert restored["status"] == result["status"]
    ```

- [x] **TASK-009**: 实现工作流可视化功能 ✅
  - 实现 `get_graph()` 方法
  - 生成 Mermaid 格式的工作流图
  - 显示所有节点和边
  - 标注条件分支
  - **依赖**: TASK-004, TASK-006
  - **验证**:
    ```python
    workflow = create_query_workflow(rag_adapter)
    graph = workflow.get_graph()
    mermaid_code = graph.print_mermaid()
    assert "analyze_query" in mermaid_code
    assert "retrieve" in mermaid_code
    ```

---

## 阶段 3：核心适配器

### 3.1 配置管理
- [x] **TASK-010**: 实现配置管理 (`src/core/config.py`) ✅
  - Pydantic Settings 类
  - LLM 配置（OpenAI）
  - Neo4j 配置（图存储）
  - Milvus 配置（向量存储）
  - 医学领域实体类型配置
  - **依赖**: TASK-001

- [x] **TASK-011**: 实现 RAG-Anything 适配器 (`src/core/adapters.py`) ✅
  - `RAGAnythingAdapter` 核心适配器类
  - `ingest_document()` - 调用 LightRAG.ainsert()
  - `query()` - 调用 LightRAG.aquery()
  - 配置 MilvusVectorDBStorage 和 Neo4JStorage
  - **依赖**: TASK-010

- [x] **TASK-012**: 实现异常处理 (`src/core/exceptions.py`) ✅
  - `MedGraphError` 基础异常
  - `DocumentError`, `QueryError`, `GraphError`

- [x] **TASK-013**: 配置日志系统 (`src/core/logging.py`) ✅
  - 使用 `loguru`
  - 支持控制台和文件输出

---

## 阶段 4：底层服务层

### 4.1 业务服务
- [x] **TASK-014**: 实现摄入服务 (`src/services/ingestion.py`) ✅
  - 封装适配器的 `ingest_document()`
  - 支持批量摄入
  - 进度跟踪
  - **依赖**: TASK-011

- [x] **TASK-015**: 实现查询服务 (`src/services/query.py`) ✅
  - 封装 LangGraph 查询工作流
  - 支持 6 种检索模式
  - 结果格式化
  - **依赖**: TASK-005, TASK-011

- [x] **TASK-016**: 实现图谱服务 (`src/services/graph.py`) ✅
  - 图谱列表（遍历工作空间）
  - 图谱删除
  - 图谱导出
  - **依赖**: TASK-011

---

## 阶段 4.5：SDK 层 ⭐ 新增

### 4.5.1 SDK 核心
- [x] **TASK-017**: 实现 SDK 类型定义 (`src/sdk/types.py`) ✅
  - `QueryMode` 枚举（6种模式）
  - `DocumentInfo` 文档信息
  - `QueryResult` 查询结果
  - `GraphInfo` 图谱信息
  - `GraphConfig` 图谱配置
  - **依赖**: TASK-001

- [x] **TASK-018**: 实现 SDK 客户端 (`src/sdk/client.py`) ✅
  - `MedGraphClient` 主客户端类
  - 初始化方法（workspace, neo4j, milvus 配置）
  - 文档管理方法（ingest_document, ingest_documents, get_document, delete_document）
  - 查询方法（query, query_stream）
  - 图谱管理方法（list_graphs, get_graph, delete_graph, merge_graph_nodes, export_graph）
  - 三层图谱关联（link_trinity_graphs）
  - **依赖**: TASK-014, TASK-015, TASK-017

- [x] **TASK-019**: 实现 SDK 异常 (`src/sdk/exceptions.py`) ✅
  - `MedGraphError` 基础异常
  - `DocumentError`, `QueryError`, `GraphError`, `ConfigError`, `AuthenticationError`
  - **依赖**: TASK-017

- [x] **TASK-020**: 实现 SDK 导出 (`src/sdk/__init__.py`) ✅
  - 导出 `MedGraphClient`, `QueryMode`, 类型定义
  - **依赖**: TASK-018


- [x] **TASK-021**: 实现 SDK 配置管理功能 ✅
  - 支持从环境变量加载配置
  - 支持从配置文件加载配置（YAML/JSON）
  - 实现 `MedGraphClient.from_config()` 类方法
  - 实现 `MedGraphClient.from_env()` 类方法
  - **依赖**: TASK-010, TASK-013
  - **验证**:
    ```python
    # 从环境变量
    client = MedGraphClient.from_env()
    # 从配置文件
    client = MedGraphClient.from_config("config.yaml")
    ```

- [x] **TASK-022**: 实现 SDK 上下文管理器 ✅
  - 为 MedGraphClient 实现 `__aenter__()` 和 `__aexit__()` 方法
  - 支持异步上下文管理器协议
  - 自动关闭连接和释放资源
  - **依赖**: TASK-013
  - **验证**:
    ```python
    async with MedGraphClient(...) as client:
        result = await client.query("测试")
    # 退出后自动关闭连接
    ```

- [x] **TASK-023**: 实现 SDK 日志和监控功能 ✅
  - 在 SDK 中集成日志记录
  - 收集性能指标（延迟、Token 使用量）
  - 实现 `get_stats()` 方法
  - 支持日志级别配置
  - **依赖**: TASK-015, TASK-013
  - **验证**:
    ```python
    client = MedGraphClient(..., log_level="DEBUG")
    result = await client.query("测试")
    assert result.latency_ms > 0
    stats = client.get_stats()
    assert stats["total_queries"] > 0
    ```

---

## 阶段 5：CLI 接口（基于 SDK）

### 5.1 命令实现
- [x] **TASK-024**: 实现 CLI 主入口 (`src/cli/main.py`) ✅
  - 使用 Typer
  - 命令：`build`, `query`, `ingest`, `serve`, `export`
  - 基于SDK实现 ⭐
  - **依赖**: TASK-018, TASK-019

- [x] **TASK-025**: 实现 `build` 命令 ✅
  - 调用 LangGraph 构建工作流
  - Rich 进度显示
  - **依赖**: TASK-006, TASK-024

- [x] **TASK-026**: 实现 `query` 命令 ✅
  - 支持交互式和单次查询
  - 美化输出
  - **依赖**: TASK-024

- [x] **TASK-027**: 实现 `serve` 命令 ✅
  - 启动 FastAPI 服务器
  - 支持热重载
  - **依赖**: TASK-024

- [x] **TASK-028**: 实现 `export` 命令 ✅
  - 导出图谱数据
  - 支持 JSON/CSV 格式

- [x] **TASK-029**: 实现 `ingest` 命令 ✅
  - 支持单个文件摄入
  - 支持批量文件摄入
  - 调用 SDK 的 ingest_document() 方法
  - Rich 进度显示
  - **依赖**: TASK-024, TASK-025
  - **验证**:
    ```bash
    medgraph ingest paper.pdf
    medgraph ingest file1.pdf file2.pdf file3.pdf
    ```

- [x] **TASK-030**: 增强终端 UI 体验 ✅
  - 使用 Rich 进度条显示长时间操作
  - 使用 Rich 表格展示查询结果
  - 使用 Rich 面板展示错误信息
  - 美化输出格式
  - **依赖**: TASK-024
  - **验证**:
    ```python
    from rich.progress import track
    for file in track(files):
        ingest_document(file)
    # 显示进度条
    ```

---

## 阶段 6：RESTful API（基于 SDK）

### 6.1 API 实现
- [x] **TASK-031**: 创建 FastAPI 应用 (`src/api/app.py`) ✅
  - CORS 中间件
  - 路由注册
  - 健康检查
  - 基于SDK实现 ⭐
  - **依赖**: TASK-018, TASK-019
  - **实现细节**:
    - 使用 FastAPI 框架创建应用
    - 配置 CORS 中间件支持跨域请求
    - 注册文档、查询、图谱路由
    - 实现健康检查端点 /health
    - 全局异常处理器
    - 使用 src.api.deps 进行依赖注入
    - 生命周期管理（启动/关闭）

- [x] **TASK-032**: 实现文档路由 (`src/api/routes/documents.py`) ✅
  - `POST /api/v1/documents` - 上传文档
  - `GET /api/v1/documents/{doc_id}` - 获取详情
  - `DELETE /api/v1/documents/{doc_id}` - 删除文档
  - 基于SDK实现 ⭐
  - **依赖**: TASK-018
  - **实现细节**:
    - 使用 FastAPI 的 UploadFile 处理文件上传
    - 使用依赖注入模式获取 MedGraphClient 实例
    - 完整的异常处理和日志记录
    - 支持多种文件格式（txt, md, json, csv, pdf）
    - 自动清理临时文件

- [x] **TASK-033**: 实现查询路由 (`src/api/routes/query.py`) ✅
  - `POST /api/v1/query` - 执行查询
  - `POST /api/v1/query/stream` - 流式查询（SSE）
  - `POST /api/v1/query/intelligent` - 智能查询（使用 LangGraph 工作流）
  - 基于SDK实现 ⭐
  - **依赖**: TASK-018
  - **实现细节**:
    - 使用 FastAPI 的 APIRouter
    - 使用依赖注入模式获取 MedGraphClient 实例
    - 复用 src.api.schemas 中的模型
    - 流式响应使用 Server-Sent Events (SSE) 格式
    - 完整的异常处理和日志记录
    - 使用 src.core.logging 记录日志
    - 遵循 PEP 8 标准

- [x] **TASK-034**: 实现图谱路由 (`src/api/routes/graphs.py`) ✅
  - `GET /api/v1/graphs` - 列出图谱
  - `DELETE /api/v1/graphs/{id}` - 删除图谱
  - `POST /api/v1/graphs/{id}/merge` - 合并节点
  - `GET /api/v1/graphs/{id}/visualize` - 导出可视化
  - 基于SDK实现 ⭐
  - **依赖**: TASK-018
  - **实现细节**:
    - 使用 FastAPI 的 APIRouter
    - 使用依赖注入模式获取 MedGraphClient 实例
    - 复用 src.api.schemas 中的模型
    - 可视化导出使用 FileResponse
    - 完整的异常处理和日志记录
    - 支持多种导出格式（mermaid, json, csv）
    - 自动清理临时文件

- [x] **TASK-035**: 实现 API 模型 (`src/api/schemas/`) ✅
  - 请求/响应 Pydantic 模型
  - 复用 SDK 类型定义 ⭐
  - **依赖**: TASK-017
  - **实现细节**:
    - 使用 Pydantic v2 和 ConfigDict
    - 复用 SDK 的类型定义（从 src.sdk.types 导入）
    - 包含完整的类型提示和 Google 风格文档字符串
    - 遵循 PEP 8 标准
    - 支持所有必需的模型：
      - 文档请求/响应模型（DocumentUploadRequest, DocumentUploadResponse, DocumentDetailResponse）
      - 查询请求/响应模型（QueryRequest, QueryResponse, StreamQueryRequest）
      - 图谱请求/响应模型（GraphListResponse, GraphDetailResponse, GraphMergeRequest, GraphExportRequest）
      - 多模态查询模型（MultimodalQueryRequest）
      - 通用响应模型（HealthResponse, ErrorResponse）

- [x] **TASK-036**: 实现 API 文档和认证功能 ✅
  - 集成 OpenAPI/Swagger UI（FastAPI 自带）
  - 集成 ReDoc 文档
  - 实现 API Key 认证（可选）
  - 实现速率限制（可选）
  - **依赖**: TASK-031
  - **实现细节**:
    - 创建 `src/api/security.py` 实现 API Key 认证
    - 创建 `src/api/middleware.py` 实现速率限制中间件
    - 增强 `src/api/app.py` 添加自定义 OpenAPI 架构
    - 支持从环境变量加载 API Keys 和速率限制配置
    - 集成认证方案到 OpenAPI 文档
    - 添加详细的 API 描述和标签
  - **验证**:
    ```python
    # 访问 /docs 应显示 Swagger UI（带有认证按钮）
    # 访问 /redoc 应显示 ReDoc
    # 使用无效 API Key 应返回 401/403
    # 速率限制超过限制应返回 429
    ```

- [x] **TASK-037**: 实现多模态查询 API 端点 ✅
  - POST /api/v1/query/multimodal
  - 支持文件上传（图像、表格）
  - 集成多模态查询服务
  - **依赖**: TASK-033, TASK-035
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/routes/multimodal.py` - 多模态查询路由
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/deps.py` - 依赖注入模块
  - **验证**:
    ```python
    response = await client.post("/api/v1/query/multimodal", files={
        "query": "这张图显示什么？",
        "image": ("xray.jpg", open("xray.jpg", "rb"))
    })
    assert response.status_code == 200
    ```

---

## 阶段 7：测试

### 7.1 单元测试
- [x] **TASK-038**: 测试 SDK 客户端 ⭐ 新增 ✅
  - 测试 `MedGraphClient` 所有方法
  - Mock 服务层和适配器
  - 测试异常处理
  - **依赖**: TASK-018
  - **测试文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_sdk_client.py`
  - **测试统计**: 50 个测试通过，1 个跳过
  - **测试覆盖**:
    - 初始化方法：__init__, initialize, from_config, from_env
    - 异步上下文管理器：__aenter__, __aexit__
    - 文档管理：ingest_document, ingest_text, ingest_batch, ingest_multimodal, delete_document
    - 查询方法：query, query_stream
    - 图谱管理：list_graphs, get_graph, delete_graph, export_graph
    - 性能监控：get_stats, reset_stats, get_performance_summary
    - 便捷方法：ingest_and_query
    - 配置加载：YAML、JSON 配置文件

- [x] **TASK-039**: 测试 LangGraph 工作流 ✅
  - 测试查询工作流（analyze_query → retrieve → grade_documents → generate_answer → refine_query）
  - 测试构建工作流（ingest → extract_entities → build_graph → merge_nodes → create_summary）
  - 测试介入手术工作流（analyze_patient → select_devices → assess_risks → generate_plan）
  - Mock 适配器和 LLM 调用
  - 测试工作流的状态转换和条件边
  - 测试工作流检查点功能
  - 测试工作流可视化功能
  - 54 个测试用例，98% 代码覆盖率
  - **依赖**: TASK-006, TASK-007
  - **测试文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_workflows.py`
  - **验证**: `pytest tests/unit/test_workflows.py -v`

- [x] **TASK-040**: 测试适配器 ✅
  - 测试 `RAGAnythingAdapter` 所有方法
  - Mock LightRAG 调用
  - 测试 6 种查询模式（naive, local, global, hybrid, mix, bypass）
  - 测试异步上下文管理器
  - 53 个测试用例，79% 代码覆盖率
  - **依赖**: TASK-011
  - **测试文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_adapters.py`
  - **验证**: `pytest tests/unit/test_adapters.py -v`

- [x] **TASK-041**: 测试服务层 ✅
  - 测试各服务功能
  - **依赖**: TASK-016
  - **完成时间**: 2026-01-11
  - **测试文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_ingestion_service.py` - IngestionService 单元测试
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_query_service.py` - QueryService 单元测试
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_graph_service.py` - GraphService 单元测试
  - **测试覆盖**:
    - IngestionService: 31 个测试用例，91% 代码覆盖率
      - 测试单文档摄入、批量摄入、纯文本摄入
      - 测试进度跟踪和状态管理
      - 测试错误处理和部分失败容错
    - QueryService: 35 个测试用例，87% 代码覆盖率
      - 测试基础查询、指定模式查询、流式查询
      - 测试批量查询和带上下文查询
      - 测试查询模式验证和辅助函数
    - GraphService: 31 个测试用例，84% 代码覆盖率
      - 测试图谱列表、详情查询、删除图谱
      - 测试节点合并和导出功能（JSON、CSV、Mermaid）
      - 测试实体和关系删除
  - **总计**: 97 个测试用例全部通过
  - **平均覆盖率**: 87%
  - **验证**: `pytest tests/unit/test_*_service.py -v --cov=src.services`

### 7.2 集成测试
- [x] **TASK-042**: CLI 集成测试 ✅
  - 测试完整流程
  - **依赖**: TASK-028
  - **完成时间**: 2026-01-11
  - **测试文件**: `tests/integration/test_cli.py`
  - **测试覆盖**:
    - 42 个测试用例全部通过
    - 覆盖所有 CLI 命令（build, query, ingest, serve, export, info）
    - 使用 Mock 进行单元测试和集成测试
    - CLI 代码覆盖率: 74% (main.py)

- [x] **TASK-043**: API 集成测试 ✅
  - 测试所有端点
  - **依赖**: TASK-034
  - **完成时间**: 2026-01-11
  - **测试文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/integration/test_api.py` - 主测试文件
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/conftest.py` - 全局测试配置
  - **测试覆盖**:
    - 41 个测试用例，覆盖所有 FastAPI 端点
    - **文档路由**: 上传、详情、删除（7个测试）
    - **查询路由**: 查询、流式、智能（7个测试）
    - **图谱路由**: 列表、详情、删除、合并、导出（11个测试）
    - **多模态路由**: 图像、表格查询（6个测试）
    - **健康检查**: 根路径、健康检查（4个测试）
    - **集成流程**: 完整工作流程测试（3个测试）
    - **错误处理**: 400/404/422/500 错误（3个测试）
  - **测试特点**:
    - 使用 FastAPI TestClient 和 Mock SDK
    - 遵循 PEP 8 标准，完整类型提示
    - Google 风格文档字符串
    - 测试环境变量自动配置
  - **详细报告**: 见 `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/TASK-043-SUMMARY.md`

---

## 阶段 8：文档和部署

### 8.1 文档
- [x] **TASK-044**: 编写 SDK 使用文档 ⭐ 新增 ✅
  - SDK 快速开始
  - API 参考
  - 示例代码
  - **完成时间**: 2026-01-11
  - **实现文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/docs/sdk.md`
  - **文档内容**:
    - 概述（核心特性、技术栈）
    - 快速开始（安装、配置、初始化、基本使用）
    - API 参考（完整的客户端方法文档）
      - 客户端类（MedGraphClient）
      - 文档摄入方法（ingest_document, ingest_text, ingest_batch, ingest_multimodal, delete_document）
      - 查询方法（query, query_stream）
      - 图谱管理方法（list_graphs, get_graph, delete_graph, export_graph, merge_graph_nodes, find_similar_entities, auto_merge_similar_entities）
      - 性能监控方法（get_stats, reset_stats, get_performance_summary）
      - 配置管理方法（from_env, from_config）
      - 便捷方法（ingest_and_query）
    - 类型定义（QueryMode, SourceInfo, GraphContext, QueryResult, DocumentInfo, GraphInfo, GraphConfig）
    - 异常处理（MedGraphSDKError, ConfigError, DocumentNotFoundError, ConnectionError, ValidationError, QueryTimeoutError, RateLimitError）
    - 完整示例（6 个实用示例）
      - 完整的文档摄入和查询流程
      - 图谱节点合并
      - 多模态查询
      - 流式查询
      - 批量摄入和进度跟踪
      - 图谱导出和可视化
    - 最佳实践（7 个最佳实践）
    - 常见问题（FAQ）
  - **文档特点**:
    - 中文文档，结构清晰
    - 完整的 API 参考表格
    - 可直接运行的代码示例
    - 详细的参数说明和返回值
    - 异常处理指导
    - 最佳实践建议

- [x] **TASK-045**: 编写用户文档 ✅
  - CLI 使用指南
  - API 使用指南
  - 配置说明
  - **完成时间**: 2026-01-11
  - **实现文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/docs/user-guide.md`
  - **文档内容**:
    - 安装指南（环境要求、安装步骤）
    - 快速开始（CLI 和 API 基本使用）
    - CLI 使用指南（所有命令详细说明）
      - build - 构建知识图谱
      - query - 查询知识图谱（6种模式）
      - ingest - 摄入文档（单文件和批量）
      - serve - 启动API服务器
      - export - 导出图谱数据
      - info - 显示系统信息
    - API 使用指南（所有端点详细说明和curl示例）
      - 健康检查端点
      - 查询API（普通查询、流式查询、智能查询）
      - 文档管理API（上传、详情、删除）
      - 图谱管理API（列表、详情、删除、合并、导出）
      - 多模态查询API（图像、表格）
    - 配置说明（环境变量、配置文件）
      - 必需配置（OPENAI_API_KEY, NEO4J_URI, MILVUS_URI）
      - 可选配置（LLM模型、数据库连接、API认证）
      - 配置文件示例（YAML和JSON格式）
    - 常见问题（12个FAQ）

- [x] **TASK-046**: 编写开发者文档 ✅
  - 架构说明
  - 智能体扩展指南（介入手术智能体）
  - 适配器扩展指南
  - **完成时间**: 2026-01-11
  - **实现文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/docs/developer-guide.md`
  - **内容覆盖**:
    - 系统架构图 (使用 Mermaid)
    - 核心模块说明 (智能体层、适配器层、服务层)
    - 智能体扩展指南 (以介入手术智能体为例)
    - 适配器扩展指南 (3 个扩展示例)
    - 服务层扩展指南
    - 最佳实践 (7 个方面)
    - 附录 (相关文档链接、常见问题)

### 8.2 部署
- [x] **TASK-047**: 更新 Docker 配置 ✅
  - Dockerfile
  - docker-compose.yml (包含 Milvus)
  - .dockerignore
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/Dockerfile` - 多阶段构建配置
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/docker-compose.yml` - 完整服务编排
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/.dockerignore` - 构建忽略文件
  - **功能特性**:
    - **Dockerfile**:
      - 多阶段构建，优化镜像大小
      - 基于 Python 3.10 官方镜像
      - 包含所有运行时依赖（图像处理、OCR、文档处理）
      - 非 root 用户运行（安全最佳实践）
      - 健康检查配置
      - 暴露 8000 端口（FastAPI）
    - **docker-compose.yml**:
      - Neo4j 图数据库（端口 7687, 7474）
      - Milvus 向量数据库（含 etcd 和 MinIO 依赖）
      - Medical Graph RAG 主应用
      - 可选的 Nginx 反向代理
      - 完整的数据卷持久化
      - 健康检查和服务依赖
      - 环境变量配置
    - **.dockerignore**:
      - 排除虚拟环境、缓存、测试文件
      - 排除配置文件和敏感信息
      - 排除文档和示例
      - 优化构建上下文大小
  - **使用方法**:
    ```bash
    # 1. 配置环境变量
    cp .env.example .env
    # 编辑 .env 文件，填写必要的配置

    # 2. 构建并启动所有服务
    docker-compose up -d

    # 3. 查看服务状态
    docker-compose ps

    # 4. 查看日志
    docker-compose logs -f app

    # 5. 停止服务
    docker-compose down

    # 6. 启用 Nginx（可选）
    docker-compose --profile nginx up -d
    ```

---

## 阶段 9：检索模块增强功能

### 9.1 高级检索功能
- [x] **TASK-048**: 实现结果排序和重排功能 ✅
  - 实现 ResultRanker 类
  - 支持基于相关性的排序
  - 支持使用重排序模型（可选）
  - **依赖**: TASK-017
  - **完成时间**: 2026-01-11
  - **实现文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/ranking.py`
  - **测试文件**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_ranking.py`
  - **测试统计**: 37 个测试用例全部通过
  - **功能覆盖**:
    - 基于相关性分数的排序（SCORE 方法）
    - 支持自定义重排序模型（RERANK 方法）
    - 多样性排序（DIVERSITY 方法，使用 MMR 算法）
    - 三种去重方法：CONTENT（基于内容相似度）、FINGERPRINT（基于指纹哈希）、NONE（不去重）
    - 可配置的排序参数（top_n、diversity_lambda、dedup_threshold）
    - 异步重排序支持（arerank 方法）
  - **验证**:
    ```python
    ranker = ResultRanker()
    reranked = ranker.rerank(results, query="糖尿病")
    assert len(reranked) == 5
    assert reranked[0].score >= reranked[1].score
    ```

- [x] **TASK-049**: 实现多模态查询支持 ✅
  - 支持带图像的查询
  - 支持带表格数据的查询
  - 集成图像分析模型
  - 解析表格内容
  - **依赖**: TASK-017
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/multimodal.py` - 多模态查询服务
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_multimodal_service.py` - 单元测试
  - **验证**:
    ```python
    from src.services.multimodal import MultimodalQueryService
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o", max_tokens=1024)
    service = MultimodalQueryService(llm)

    # 图像查询
    result = await service.query_with_image(
        query="分析这张X光片显示的异常",
        image_path="xray.jpg"
    )
    assert "分析" in result.answer or len(result.answer) > 0

    # 表格查询
    table_data = [["患者", "年龄", "诊断"], ["张三", "45", "高血压"]]
    result = await service.query_with_table(
        query="从表格中提取所有诊断结果",
        table_data=table_data
    )
    assert "诊断" in result.answer or len(result.answer) > 0
    ```
  - **测试覆盖**: 27 个测试用例全部通过，覆盖所有主要功能
    - 图像查询：成功查询、参数验证、文件不存在、格式不支持、不同细节级别
    - 多图像查询：成功查询、空列表验证
    - 表格查询：成功查询、带表头、不同格式、无效数据、不支持格式
    - 辅助方法：查询验证、表格格式化、图像编码、路径验证、表格数据验证
    - 结果类：字典转换、无 Token 信息处理

- [x] **TASK-050**: 实现上下文组装逻辑 ✅
  - 实现 assemble_graph_context() 方法
  - 实现 assemble_vector_context() 方法
  - 智能组合检索结果
  - 去重和排序上下文
  - **依赖**: TASK-017
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/query.py` - 添加上下文组装方法
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_context_assembly.py` - 单元测试
  - **测试覆盖**: 17 个测试用例全部通过
    - 图上下文组装测试：4 个测试
    - 向量上下文组装测试：4 个测试
    - 上下文组合测试：5 个测试
    - 辅助方法测试：4 个测试
  - **验证**:
    ```python
    context = query_service.assemble_graph_context(
        graph_id="graph-123",
        nodes=retrieved_nodes
    )
    assert len(context.entities) > 0
    ```

---

## 阶段 10：图构建模块增强功能

### 10.1 高级图构建功能
- [x] **TASK-051**: 实现图谱节点合并功能 ✅
  - 基于语义相似度合并重复节点
  - 支持阈值配置
  - 返回合并的节点数量
  - **依赖**: TASK-018
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/graph.py` - 增强方法
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/client.py` - SDK 接口
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_graph_merge.py` - 单元测试
  - **测试覆盖**: 28 个测试用例全部通过
    - merge_graph_nodes: 9 个测试（基本合并、空列表验证、目标在源列表、参数验证、多种合并策略）
    - find_similar_entities: 4 个测试（查找成功、阈值过滤、Top-K 限制、空结果）
    - auto_merge_similar_entities: 3 个测试（自动合并成功、试运行模式、类型过滤）
    - SDK 接口测试: 6 个测试（merge_graph_nodes、find_similar_entities、auto_merge_similar_entities）
    - 集成测试: 2 个测试（完整工作流、错误恢复）
    - 边界情况: 4 个测试（空图谱、未初始化、无效阈值、无效实体类型）
  - **功能特性**:
    - 基于 LightRAG amerge_entities API 的节点合并
    - 支持语义相似度阈值（0-1）控制合并严格程度
    - 支持多种合并策略（description: concatenate/keep_first/keep_latest, entity_type: keep_first/majority, source_id: join_unique/join_all）
    - 自动查找相似实体的 find_similar_entities 方法
    - 自动合并相似实体的 auto_merge_similar_entities 方法（支持试运行模式）
    - 完整的 SDK 接口和单元测试
  - **验证**:
    ```python
    merged_count = await client.merge_graph_nodes(
        graph_id="graph-123",
        source_entities=["糖尿病", "糖尿病 mellitus", "DM"],
        target_entity="糖尿病",
        threshold=0.7
    )
    assert merged_count >= 0
    ```

- [x] **TASK-052**: 实现图谱可视化功能 ✅
  - 导出为 Mermaid 格式
  - 导出为 JSON 格式
  - 导出为 CSV 格式（节点和边）
  - **依赖**: TASK-018
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/graph.py` - 完善导出方法
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_graph_export.py` - 单元测试
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/verify_graph_export.py` - 验证脚本
  - **测试覆盖**: 14 个测试用例全部通过
    - JSON 导出: 3 个测试（成功导出、包含向量、无向量）
    - CSV 导出: 3 个测试（成功导出、包含向量、无向量）
    - Mermaid 导出: 3 个测试（成功导出、实体限制、样式正确）
    - CSV 解析: 2 个测试（成功解析、空文件）
    - 参数验证: 2 个测试（无效格式、文件不存在）
    - 辅助方法: 1 个测试（节点 ID 清理）
  - **功能特性**:
    - JSON 格式导出：完整图谱数据（元数据、统计、实体、关系）
    - CSV 格式导出：表格格式，便于 Excel 分析
    - Mermaid 格式导出：可视化图表（graph TD、按类型分组、不同形状、样式定义）
    - _parse_csv_for_entities_relations 辅助方法：解析 LightRAG 导出的 CSV
    - _sanitize_node_id 辅助方法：清理实体名称生成有效的 Mermaid 节点 ID
    - _escape_mermaid_label 辅助方法：转义 Mermaid 标签中的特殊字符
  - **验证**:
    ```python
    await client.export_graph("medical", "output.json", "json")
    assert Path("output.json").exists()

    await client.export_graph("medical", "output.csv", "csv")
    assert Path("output.csv").exists()

    await client.export_graph("medical", "output.mmd", "mermaid")
    assert Path("output.mmd").exists()
    content = Path("output.mmd").read_text()
    assert "graph TD" in content
    ```

- [x] **TASK-053**: 增强 Neo4j 适配器功能 ✅
  - 实现 create_graph() 方法（批量创建节点和关系）
  - 实现 query_cypher() 方法（执行 Cypher 查询）
  - 实现 vector_similarity_search() 方法（向量相似度搜索）
  - **依赖**: TASK-011
  - **完成时间**: 2026-01-11
  - **实现文件**:
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/core/adapters.py` - 添加三个新方法
    - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_adapters_enhanced.py` - 单元测试
  - **测试覆盖**: 28 个测试用例全部通过
    - create_graph: 7 个测试（成功创建、仅实体、仅关系、空输入、批量处理、带属性、未初始化）
    - query_cypher: 8 个测试（成功查询、参数化、空查询、危险关键字、自动限制、已有限制、结果格式、限制强制）
    - vector_similarity_search: 9 个测试（成功搜索、带过滤、空向量、无效top_k、复杂过滤、top_k限制、降级模式、分数计算、未初始化）
    - 集成测试: 2 个测试（完整工作流、错误恢复）
    - 性能测试: 2 个测试（大批量创建、查询结果限制）
  - **功能特性**:
    - 批量创建节点和关系，支持自定义批大小（默认 100）
    - 支持参数化 Cypher 查询，防止注入攻击
    - 自动添加 LIMIT 子句，防止内存溢出
    - 危险关键字拦截（DROP, DELETE, DETACH, REMOVE）
    - 向量相似度搜索，支持 Milvus 标量过滤
    - 支持复杂过滤条件（$gt, $lt, $gte, $lte, $ne, $in）
    - 降级模式：向量存储不支持搜索时使用 LightRAG 查询接口
    - 完整的错误处理和日志记录
  - **验证**:
    ```python
    # 测试创建图谱
    entities = [
        {"entity_name": "糖尿病", "entity_type": "DISEASE"},
        {"entity_name": "胰岛素", "entity_type": "MEDICINE"},
    ]
    relationships = [
        {"source": "胰岛素", "target": "糖尿病", "relation": "治疗"},
    ]
    created = await adapter.create_graph(entities, relationships)
    assert created["entity_count"] == 2
    assert created["relationship_count"] == 1

    # 测试 Cypher 查询
    results = await adapter.query_cypher(
        "MATCH (n:DISEASE) RETURN n LIMIT 10",
        graph_id="graph-123"
    )
    assert len(results) <= 10

    # 测试向量搜索
    results = await adapter.vector_similarity_search(
        query_vector=[0.1, 0.2, ...],
        top_k=5
    )
    assert len(results) == 5
    ```

---

## 依赖关系图

```
TASK-001 ──────────────────────────────────┐
TASK-002 ──────────────────────────────────┤
                                         │
TASK-003 ──┬──> TASK-004 ──┬──> TASK-005 ──┼──> TASK-014 ──┬──> TASK-017 (SDK types)
           │              │               │              │
           ├──> TASK-006 ──┼──> TASK-007 ─┤              ├──> TASK-018 (SDK client)
           │              │               │              │
           └──> TASK-008 ─┴──> TASK-009 ──┘              ├──> TASK-019 (SDK exceptions)
                                                          │
TASK-010 ──> TASK-011 ──┬──> TASK-012 ──┬───────────────┬──> TASK-020 (SDK export)
           │             │             │               │
           └─────────────┘             │               ├──> TASK-021 (SDK config) ─┐
                                         │               │                      │
TASK-016 ──────────────────────────────────┤               ├──> TASK-022 (context) ─┤
TASK-017 (SDK types) ──────────────────────┤               │                      │
                                         │               └──> TASK-023 (logging) ─┘
                                         │
                                         │
                                         ├──> TASK-024 (CLI) ──┬──> TASK-029 (ingest)
                                         │                    │
                                         │                    └──> TASK-030 (UI enhance)
                                         │
                                         ├──> TASK-031 (API app) ──┬──> TASK-036 (docs/auth)
                                         │                        │
                                         ├──> TASK-032 ──┐        │
                                         │             │        │
                                         ├──> TASK-033 ──┼──> TASK-037 (multimodal)
                                         │             │        │
                                         ├──> TASK-034 ──┼──> TASK-035
                                         │             │
TASK-038 (SDK tests) ──────────────────────┼──> TASK-036 ─┘
TASK-039 ──┬──> TASK-041 ──┬──> TASK-042   │
TASK-040 ──┘              │              │
                          │              │
                       TASK-043 ─────────┘
                          │
TASK-044 ──┬──> TASK-046 ─┤
TASK-045 ──┘              │
                          │
                       TASK-047 ────────────────────────────┘
                          │
TASK-048 ──┬──> TASK-049 ─┼──> TASK-050 ──────────────────┘
TASK-053 ──┘              │
                          │
TASK-051 ──┬──> TASK-052 ─┘
```

---

## 里程碑

| 里程碑 | 任务 | 描述 |
|--------|------|------|
| M1 | TASK-001 到 TASK-002 | 基础设施完成 ✅ |
| M2 | TASK-003 到 TASK-009 | LangGraph 智能体层完成（含介入手术扩展点、检查点和可视化）✅ |
| M3 | TASK-010 到 TASK-013 | 核心适配器完成 ✅ |
| M4 | TASK-014 到 TASK-016 | 底层服务层完成 ✅ |
| M5 | TASK-017 到 TASK-020 | SDK 层完成 ✅ |
| M6 | TASK-024 到 TASK-030 | CLI 接口完成（基于 SDK） |
| M7 | TASK-031 到 TASK-037 | REST API 完成（基于 SDK） |
| M8 | TASK-038 到 TASK-043 | 测试完成 |
| M9 | TASK-044 到 TASK-047 | 文档和部署完成 |
| M10 | TASK-048 到 TASK-053 | 检索和图构建增强功能完成 ⭐ 新增 |

---

## 与原任务列表的差异

### 保留的组件（LangGraph 相关）
- **LangGraph 工作流**：保留用于智能体编排和介入手术智能体扩展
- **查询路由工作流**：analyze_query → retrieve → grade → generate
- **图谱构建工作流**：ingest → extract → build → summary
- **状态管理**：TypedDict 状态定义

### 复用的 RAG-Anything 功能
- **存储层**：MilvusVectorDBStorage（向量存储）、Neo4JStorage（图存储）
- **实体关系提取**：LightRAG 内置
- **6 种检索模式**：naive, local, global, hybrid, mix, bypass

### 移除的自定义实现
- ~~自定义向量存储~~（使用 MilvusVectorDBStorage）
- ~~自定义图存储~~（使用 Neo4JStorage）
- ~~自定义实体提取器~~（使用 LightRAG 内置）
- ~~自定义关系提取器~~（使用 LightRAG 内置）

### 预计工作量
- 任务总数：53 个 (原 51 个)
- 新增 LangGraph 相关任务：7 个（TASK-003 到 TASK-006, TASK-007 到 TASK-009）
- 核心适配器任务：4 个（TASK-010 到 TASK-013）
- SDK 层任务：7 个（TASK-017 到 TASK-020, TASK-021 到 TASK-023）
- 服务层任务：3 个（TASK-014 到 TASK-016）
- CLI 接口任务：7 个（TASK-024 到 TASK-030）
- REST API 任务：7 个（TASK-031 到 TASK-037）
- 检索模块增强任务：3 个（TASK-048 到 TASK-050）⭐ 新增
- 图构建模块增强任务：3 个（TASK-051 到 TASK-053）⭐ 新增
- 测试任务：6 个（TASK-038 到 TASK-043）
- 文档和部署任务：4 个（TASK-044 到 TASK-047）
- 异常和日志任务：4 个（TASK-012, TASK-013, TASK-023）
