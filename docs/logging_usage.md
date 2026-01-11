# 日志系统使用指南

## 概述

Medical Graph RAG 项目使用 `loguru` 作为日志库，提供了功能完善的日志系统，支持：

- 控制台输出（带颜色）
- 文件输出（支持轮转和压缩）
- 结构化日志（JSON 格式）
- 请求 ID 跟踪
- 异常捕获和堆栈跟踪
- 性能监控装饰器
- 日志上下文管理

## 快速开始

### 1. 基本使用

```python
from src.core.logging import setup_logging, logger

# 初始化日志系统
setup_logging(log_level="INFO", log_dir="./logs")

# 记录日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 2. 使用命名 Logger

```python
from src.core.logging import get_logger

# 获取指定名称的 logger
logger = get_logger("my_module")
logger.info("这是来自 my_module 的日志")

# 添加额外上下文
user_logger = get_logger("user_module", user_id="123", username="张三")
user_logger.info("用户登录成功")
```

### 3. 请求跟踪

```python
from src.core.logging import set_request_id, set_session_id, logger

# 设置请求 ID
request_id = set_request_id("req-20230111-001")
logger.info("处理用户请求")

# 设置会话 ID
session_id = set_session_id("sess-20230111-abc")
logger.info("用户会话操作")

# 自动生成 UUID
auto_request_id = set_request_id()
logger.info(f"自动生成的请求 ID: {auto_request_id}")
```

### 4. 日志上下文管理

```python
from src.core.logging import LogContext, logger

# 使用上下文管理器
with LogContext(request_id="ctx-001", session_id="sess-001"):
    logger.info("这条日志会包含上下文信息")
    logger.info("处理业务逻辑")

    # 嵌套上下文
    with LogContext(request_id="ctx-002"):
        logger.info("嵌套上下文的日志")

# 退出上下文后，ID 会恢复
logger.info("退出上下文后的日志")
```

### 5. 异常日志

```python
from src.core.logging import logger

# 方法 1: 使用 exception() 自动捕获异常
try:
    result = 1 / 0
except ZeroDivisionError:
    logger.exception("捕获到除零异常")

# 方法 2: 使用 opt() 方法手动指定异常
try:
    raise ValueError("业务逻辑错误")
except ValueError as e:
    logger.opt(exception=True).error(f"处理失败: {e}")
```

### 6. 性能监控

```python
from src.core.logging import log_execution_time, log_async_execution_time
import time
import asyncio

# 同步函数性能监控
@log_execution_time(level="INFO")
def process_data():
    time.sleep(0.5)
    return "处理完成"

result = process_data()
# 输出: 函数执行完成 | 耗时: 0.5023秒

# 异步函数性能监控
@log_async_execution_time(level="INFO")
async def async_process_data():
    await asyncio.sleep(0.3)
    return "异步处理完成"

async def main():
    result = await async_process_data()
    # 输出: 异步函数执行完成 | 耗时: 0.3015秒

asyncio.run(main())
```

### 7. 高级配置

```python
from src.core.logging import setup_logging, LoggingConfig

# 方法 1: 使用关键字参数
setup_logging(
    log_level="DEBUG",
    log_dir="./logs",
    log_file="my_app.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    json_format=False
)

# 方法 2: 使用配置对象
config = LoggingConfig(
    log_level="DEBUG",
    log_file="app.log",
    log_dir="./logs",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    json_format=True,
    enable_console=True,
    enable_file=True,
    console_level="INFO",
    file_level="DEBUG"
)
setup_logging(config)

# 方法 3: 从环境变量读取
# 设置环境变量:
# LOG_LEVEL=DEBUG
# LOG_DIR=./logs
# LOG_JSON=true
config = LoggingConfig.from_env()
setup_logging(config)
```

### 8. JSON 格式日志

```python
from src.core.logging import setup_logging, logger

# 启用 JSON 格式
setup_logging(
    log_level="INFO",
    log_dir="./logs",
    json_format=True
)

# 记录日志（会自动转换为 JSON 格式）
logger.info("用户登录", extra={"user_id": "123", "ip": "192.168.1.1"})
```

JSON 输出示例：
```json
{
  "timestamp": "2026-01-11T16:20:00.123456",
  "level": "INFO",
  "logger": "__main__",
  "function": "test_function",
  "line": 42,
  "request_id": "req-001",
  "session_id": "sess-001",
  "message": "用户登录",
  "user_id": "123",
  "ip": "192.168.1.1"
}
```

### 9. 拦截标准库日志

```python
from src.core.logging import intercept_standard_logging, logger

# 拦截标准库 logging 的输出
intercept_standard_logging()

# 现在标准库的日志也会通过 loguru 输出
import logging
std_logger = logging.getLogger("requests")
std_logger.info("这是通过标准库记录的日志")
```

## 配置选项

### LoggingConfig 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log_level` | str | "INFO" | 默认日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | str | "app.log" | 日志文件名 |
| `log_dir` | str | "./logs" | 日志目录路径 |
| `rotation` | str | "10 MB" | 日志轮转策略 (如 "10 MB", "1 day", "00:00") |
| `retention` | str | "30 days" | 日志保留时间 (如 "7 days", "1 week") |
| `compression` | str | "zip" | 压缩格式 ("zip", "gz", "tar") |
| `json_format` | bool | False | 是否使用 JSON 格式 |
| `enable_console` | bool | True | 是否启用控制台输出 |
| `enable_file` | bool | True | 是否启用文件输出 |
| `console_level` | str | "INFO" | 控制台日志级别 |
| `file_level` | str | "DEBUG" | 文件日志级别 |

### 环境变量配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_FILE` | 日志文件名 | app.log |
| `LOG_DIR` | 日志目录 | ./logs |
| `LOG_ROTATION` | 日志轮转 | 10 MB |
| `LOG_RETENTION` | 保留时间 | 30 days |
| `LOG_COMPRESSION` | 压缩格式 | zip |
| `LOG_JSON` | JSON 格式 | false |
| `LOG_CONSOLE` | 控制台输出 | true |
| `LOG_FILE_ENABLED` | 文件输出 | true |
| `LOG_CONSOLE_LEVEL` | 控制台级别 | INFO |
| `LOG_FILE_LEVEL` | 文件级别 | DEBUG |

## 日志格式

### 控制台格式（带颜色）

```
2026-01-11 16:20:00.123 | INFO     | module:function:42 | Req:req-001 | 这是一条日志
```

### 文件格式

```
2026-01-11 16:20:00.123 | INFO     | module:function:42 | Req:req-001 | Sess:sess-001 | 这是一条日志
```

### 错误日志

```
2026-01-11 16:20:00.123 | ERROR    | module:function:42 | Req:req-001 | Sess:sess-001 | 错误消息
Traceback (most recent call last):
  File "app.py", line 42, in function
    ...
```

## 最佳实践

### 1. 在应用启动时初始化

```python
# main.py
from src.core.logging import setup_logging

def main():
    # 在应用启动时初始化日志
    setup_logging(log_level="INFO", log_dir="./logs")

    # 启动应用
    app.run()

if __name__ == "__main__":
    main()
```

### 2. 在每个模块中使用命名 logger

```python
# services/user_service.py
from src.core.logging import get_logger

logger = get_logger("user_service")

class UserService:
    def create_user(self, username):
        logger.info(f"创建用户: {username}")
        # 业务逻辑
```

### 3. 在 API 请求中使用请求跟踪

```python
# api/handlers.py
from src.core.logging import set_request_id, get_logger

logger = get_logger("api_handler")

def handle_request(request):
    # 为每个请求设置唯一 ID
    request_id = set_request_id()
    logger.info(f"处理请求: {request.path}")

    try:
        # 处理请求
        return process_request(request)
    except Exception as e:
        logger.exception("请求处理失败")
        raise
```

### 4. 在长时间运行的任务中使用性能监控

```python
# services/data_processor.py
from src.core.logging import log_execution_time, get_logger

logger = get_logger("data_processor")

@log_execution_time(level="INFO")
def process_large_dataset(data):
    logger.info("开始处理大数据集")
    # 处理逻辑
    return result
```

### 5. 使用适当的日志级别

- **DEBUG**: 详细的调试信息，仅在开发时使用
- **INFO**: 一般信息，记录应用的正常运行流程
- **WARNING**: 警告信息，表示潜在问题但不影响运行
- **ERROR**: 错误信息，表示功能失败但应用仍可运行
- **CRITICAL**: 严重错误，表示应用可能无法继续运行

## 故障排查

### 问题 1: 日志文件未创建

**解决方案**: 确保日志目录有写入权限

```python
from pathlib import Path
log_dir = Path("./logs")
log_dir.mkdir(parents=True, exist_ok=True)
```

### 问题 2: 日志级别不生效

**解决方案**: 检查控制台和文件级别的设置

```python
setup_logging(
    log_level="DEBUG",      # 默认级别
    console_level="INFO",   # 控制台级别
    file_level="DEBUG"      # 文件级别
)
```

### 问题 3: JSON 格式日志乱码

**解决方案**: 确保 `ensure_ascii=False`

```python
# 日志系统已默认设置
# 如需自定义，确保 JSON 格式化函数包含:
json.dumps(data, ensure_ascii=False)
```

## 示例项目

完整的使用示例请参考 `test_logging_simple.py`。

## 相关文件

- 日志系统实现: `src/core/logging.py`
- 使用示例: `test_logging_simple.py`
- 完整测试: `test_logging.py`
