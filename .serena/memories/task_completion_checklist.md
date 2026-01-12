# 任务完成检查清单

## 代码完成后必须执行的操作

### 1. 类型检查
```bash
mypy camel/ nano_graphrag/ --strict
```
- 必须通过 mypy 严格模式检查
- 无类型错误

### 2. 代码格式化
```bash
ruff format camel/ nano_graphrag/ tests/
```

### 3. Linting 检查
```bash
ruff check camel/ nano_graphrag/ tests/
```
- 无 Linting 错误

### 4. 运行测试
```bash
# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=camel --cov=nano_graphrag --cov-report=html
```
- 所有测试必须通过
- 代码覆盖率必须达到 90% 以上

### 5. 提交前检查
- 确保 Conventional Commits 格式
- 提交类型：
  - `feat`: 新功能
  - `fix`: Bug 修复
  - `docs`: 文档更新
  - `style`: 代码格式
  - `refactor`: 代码重构
  - `test`: 测试相关
  - `chore`: 构建/工具相关

## 性能检查
- 标准 API 请求 <200ms
- 复杂 RAG 检索 <500ms

## 安全检查
- 无命令注入漏洞
- 无 XSS 漏洞
- 无 SQL/NoSQL 注入漏洞
- 输入验证在系统边界处进行
