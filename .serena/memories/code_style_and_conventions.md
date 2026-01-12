# 代码风格与约定

## 核心原则
严格遵循 PEP 8 标准，所有代码必须符合以下规范。

## 类型提示
- **必须**使用 `mypy` 进行静态类型检查（严格模式）
- LangGraph 的 State 和 Node 定义时，类型提示是强制的
- 所有公共模块、类和函数必须包含类型提示

## 文档字符串
- 所有公共模块、类和函数必须包含 **Google 风格**的文档字符串
- 示例：
  ```python
  def retrieve_knowledge(query: str, top_k: int = 5) -> list[dict]:
      """检索相关知识。

      Args:
          query: 查询字符串
          top_k: 返回结果数量

      Returns:
          包含检索结果的字典列表
      """
      pass
  ```

## 环境管理
- **必须**使用 `venv` 管理环境
- 严禁使用系统 Python

## 代码格式化和 Linting
- 使用 `ruff` 进行代码格式化和 Linting
- 统一的代码风格

## 测试标准
- 采用测试优先（TDD）理念
- 代码覆盖率目标：**90% 以上**
- 使用 `pytest` 编写测试
- 严格区分单元测试（Mock）和集成测试（真实 DB/API）

## 性能要求
- Async-first 架构处理 I/O 操作（数据库、网络）
- API 响应时间目标：
  - 标准请求 <200ms
  - 复杂 RAG 检索 <500ms
- 数据库查询必须经过优化（索引、Explain 分析）

## 命名约定
- 类名：PascalCase (如 `GraphRAG`)
- 函数/变量：snake_case (如 `retrieve_knowledge`)
- 常量：UPPER_SNAKE_CASE (如 `MAX_RETRIES`)
- 私有成员：前缀下划线 (如 `_internal_method`)
