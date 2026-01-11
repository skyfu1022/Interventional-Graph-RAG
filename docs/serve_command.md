# Serve 命令实现文档

## 概述

`medgraph serve` 命令用于启动 Medical Graph RAG API 开发服务器。该命令基于 FastAPI 和 Uvicorn，提供完整的 RESTful API 接口用于与知识图谱系统交互。

## 创建的文件

### 1. `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/app.py`

FastAPI 应用主入口文件，包含：
- 应用生命周期管理 (`lifespan`)
- CORS 中间件配置
- 路由注册（documents、graphs、query）
- 全局异常处理器
- 根路径和健康检查端点

### 2. `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/cli/commands/serve.py`

Serve 命令的独立实现模块，包含：
- `serve_app`: Typer 应用实例
- `serve()`: 主命令函数
- `_is_port_available()`: 端口可用性检查
- `_print_server_info()`: Rich 格式化的服务器信息显示

### 3. 路由模块更新

更新了以下路由文件，添加了基本的 `APIRouter` 实例：
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/routes/documents.py`
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/routes/graphs.py`
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/api/routes/query.py`

### 4. `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/cli/main.py`

更新了主 CLI 文件，集成了完整的 serve 命令实现。

## 功能特性

### 命令参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--host` | `-h` | str | 127.0.0.1 | 服务器监听的主机地址 |
| `--port` | `-p` | int | 8000 | 服务器端口号 (1-65535) |
| `--reload` | `-r` | bool | False | 启用自动重载 (开发模式) |
| `--log-level` | | str | info | 日志级别 |

### 核心功能

1. **端口检查**: 启动前自动检查端口是否可用
2. **Rich 输出**: 使用 Rich 库显示美观的服务器信息面板
3. **热重载**: 支持开发模式下的代码自动重载
4. **错误处理**: 完善的参数验证和错误提示
5. **优雅退出**: 支持 Ctrl+C 安全停止服务器

## 使用示例

### 基本用法

```bash
# 默认配置启动
medgraph serve

# 启用热重载（开发模式）
medgraph serve --reload

# 自定义端口
medgraph serve --port 8080

# 监听所有网络接口（局域网访问）
medgraph serve --host 0.0.0.0

# 组合使用
medgraph serve --host 0.0.0.0 --port 9000 --reload
```

### 使用 Python 模块运行

```bash
python -m src.cli.main serve --reload
```

## API 端点

启动服务器后，可以访问以下端点：

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 根路径，显示 API 信息 |
| `/health` | GET | 健康检查端点 |
| `/docs` | GET | Swagger UI 交互式 API 文档 |
| `/redoc` | GET | ReDoc API 文档 |
| `/api/v1/documents` | POST/GET | 文档管理 |
| `/api/v1/graphs` | GET | 图谱操作 |
| `/api/v1/query` | POST | 智能查询 |

## 技术实现

### 技术栈

- **FastAPI**: 现代化的 Web 框架
- **Uvicorn**: ASGI 服务器
- **Typer**: CLI 命令框架
- **Rich**: 终端美化输出

### 架构设计

```
src/
├── api/
│   ├── app.py                 # FastAPI 应用主入口
│   └── routes/
│       ├── documents.py       # 文档管理路由
│       ├── graphs.py          # 图谱操作路由
│       └── query.py           # 查询路由
├── cli/
│   ├── main.py                # CLI 主入口
│   ├── commands/
│   │   ├── __init__.py
│   │   └── serve.py           # Serve 命令实现
│   └── ui.py                  # Rich UI 工具
└── core/
    ├── config.py              # 配置管理
    └── logging.py             # 日志配置
```

### 代码特点

1. **遵循 PEP 8**: 严格的代码格式规范
2. **类型提示**: 完整的类型注解
3. **文档字符串**: Google 风格的 docstring
4. **错误处理**: 完善的异常处理机制
5. **日志记录**: 使用 Loguru 记录日志

## 测试

运行测试脚本验证功能：

```bash
python test_serve_command.py
```

测试覆盖：
- 模块导入
- FastAPI 应用创建
- 端口可用性检查
- 命令帮助信息
- Rich 输出格式

## 开发工作流

推荐的开发流程：

1. **启动服务器**（启用热重载）
   ```bash
   medgraph serve --reload
   ```

2. **访问 API 文档**
   ```
   http://localhost:8000/docs
   ```

3. **测试 API 端点**
   使用 Swagger UI 或 curl/Postman

4. **修改代码**
   保存后服务器会自动重新加载

5. **查看日志**
   终端会显示请求日志和错误信息

## 示例 curl 命令

```bash
# 健康检查
curl http://localhost:8000/health

# 获取 API 信息
curl http://localhost:8000/

# 查询知识图谱（示例）
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是糖尿病?"}'
```

## 注意事项

### 生产环境部署

在生产环境中使用时，建议：

1. 使用进程管理器（如 systemd、supervisor）
2. 配置反向代理（如 Nginx）
3. 使用多 workers 提高并发性能
4. 禁用热重载
5. 配置适当的日志级别
6. 使用 HTTPS 加密通信

### 端口冲突

如果遇到端口被占用的错误：

```bash
# 尝试其他端口
medgraph serve --port 8080

# 或检查占用进程
lsof -i :8000
```

### 局域网访问

如需让其他设备访问 API：

```bash
# 监听所有网络接口
medgraph serve --host 0.0.0.0

# 防火墙可能需要开放端口
```

## 相关文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Uvicorn 官方文档](https://www.uvicorn.org/)
- [Typer 官方文档](https://typer.tiangolo.com/)
- [Rich 官方文档](https://rich.readthed.io/)

## 版本信息

- **创建日期**: 2026-01-11
- **版本**: 1.0.0
- **作者**: Medical Graph RAG Team
- **许可**: MIT
