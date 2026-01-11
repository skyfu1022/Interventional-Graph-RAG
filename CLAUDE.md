# Medical-Graph-RAG 项目章程

## 核心原则

### I. Python 代码质量与标准
严格遵守 PEP 8 标准。必须使用 `mypy` 进行静态类型检查（严格模式），特别是在定义 LangGraph 的 State 和 Node 时，类型提示是必须的。所有公共模块、类和函数必须包含 Google 风格的文档字符串。使用 `venv` 管理环境，严禁使用系统 Python。代码格式化和 Linting 统一使用 `ruff`。

### II. 测试标准与可靠性
采用测试优先（TDD）理念。代码覆盖率目标必须达到 90% 以上。严格区分单元测试（Mock）和集成测试（真实 DB/API）。所有测试必须使用 `pytest` 编写。CI 流水线必须通过所有测试且无 Lint 错误才能合并。

### III. 用户体验与 API 一致性
后端 API 和 CLI 输出必须保持结构一致。错误信息必须语义化并提供可操作的建议。任何面向用户的界面（如有）需遵循响应式设计原则，确保加载状态和错误反馈清晰可见。

### IV. 性能与效率要求
采用 Async-first 架构处理 I/O 操作（数据库、网络）。API 响应时间目标：标准请求 <200ms，复杂 RAG 检索 <500ms。数据库查询必须经过优化（索引、Explain 分析）。

## 技术栈与约束


**核心语言**: Python 3.10+
**数据库**: 
- 图数据库: Neo4j
- 向量数据库: Milvus (替代 PostgreSQL/pgvector)
**AI/框架**: 
- Orchestration: LangGraph (必须用于构建 Agent 工作流)
- RAG Pipeline: RAGAnything (用于多模态文档处理与检索)
- LLM: OpenAI 或兼容接口
**环境管理**: 必须使用 `venv`，依赖项锁定在 `requirements.txt` 或 `pyproject.toml`。
**操作系统**: macOS (开发环境), Linux (部署环境)

## 开发工作流程

采用 Feature Branch 工作流。
1. 基于 `main` 创建功能分支 `feat/xxx` 或修复分支 `fix/xxx`。
2. 提交代码前必须运行本地测试和 Lint 检查。
3. 提交信息遵循 Conventional Commits 规范（feat, fix, docs, style, refactor, test, chore）。
4. Pull Request 必须经过至少一名团队成员审查并通过自动化 CI 检查。

## 治理

本项目章程优先于所有其他非正式实践。任何对核心原则的修改需经过团队 RFC 讨论并获得批准。违反章程原则的代码（如缺少测试、类型错误、性能不达标）将在 Code Review 或 CI 阶段被拒绝。

**版本**: 1.1.0 | **批准日期**: 2026-01-11 | **最后修正**: 2026-01-11
