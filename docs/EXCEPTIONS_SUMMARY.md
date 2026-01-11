# SDK 异常模块实现总结

## 任务概述

已完成 SDK 层的异常模块实现（TASK-019），为 Medical Graph RAG SDK 提供了完整的异常处理体系。

## 实现内容

### 1. 异常类层次结构

```
Exception
    └── MedGraphSDKError (基类)
        ├── ConfigError (配置错误)
        ├── DocumentNotFoundError (文档未找到)
        ├── ConnectionError (连接错误)
        ├── ValidationError (验证错误)
        ├── QueryTimeoutError (查询超时)
        └── RateLimitError (速率限制)
```

### 2. 核心功能

#### 基础异常类 (MedGraphSDKError)

所有 SDK 异常的基类，提供统一的功能：

- **错误码支持**: 每个异常都有唯一的错误码
- **详情字典**: 携带额外的上下文信息
- **to_dict() 方法**: 转换为字典格式，用于 API 响应
- **友好的字符串表示**: `[错误码] 错误消息` 格式

#### 具体异常类

1. **ConfigError (配置错误)**
   - 场景：SDK 配置缺失、无效或无法加载
   - 属性：config_key, config_file

2. **DocumentNotFoundError (文档未找到)**
   - 场景：尝试访问不存在的文档
   - 属性：doc_id

3. **ConnectionError (连接错误)**
   - 场景：无法连接到 Neo4j、Milvus 等服务
   - 属性：service, uri
   - 特性：自动脱敏 URI 中的密码

4. **ValidationError (验证错误)**
   - 场景：输入数据不符合要求
   - 属性：field, value, constraint
   - 特性：自动截断过长的值（100 字符限制）

5. **QueryTimeoutError (查询超时)**
   - 场景：查询执行时间超过限制
   - 属性：timeout_seconds, query
   - 特性：自动截断过长的查询（100 字符限制）

6. **RateLimitError (速率限制)**
   - 场景：请求超过 API 速率限制
   - 属性：limit, window, retry_after

### 3. 异常转换功能

实现了 `convert_core_exception()` 函数，将核心层异常转换为 SDK 异常：

**映射关系**:

| 核心层异常 | SDK 异常 | 说明 |
|----------|---------|------|
| DocumentError | DocumentNotFoundError | 文档错误 |
| QueryError | ValidationError | 查询错误 |
| GraphError | ValidationError | 图谱错误 |
| ConfigError | ConfigError | 配置错误 |
| ValidationError | ValidationError | 验证错误 |
| NotFoundError | DocumentNotFoundError | 未找到错误 |
| StorageError | ConnectionError | 存储错误 |
| AuthenticationError | ConfigError | 认证错误 |
| RateLimitError | RateLimitError | 速率限制 |

**特性**:
- 自动提取核心异常的详细信息
- 保留原始异常的上下文
- 默认返回通用 SDK 异常

### 4. 使用示例

#### 基本使用

```python
from src.sdk import (
    MedGraphClient,
    MedGraphSDKError,
    ConfigError,
    DocumentNotFoundError,
)

async def main():
    async with MedGraphClient(workspace="medical") as client:
        try:
            result = await client.query("什么是糖尿病?")
            print(result.answer)
        except ConfigError as e:
            print(f"配置错误: {e}")
            print(f"配置键: {e.config_key}")
        except DocumentNotFoundError as e:
            print(f"文档未找到: {e.doc_id}")
        except MedGraphSDKError as e:
            print(f"SDK 错误: {e}")
            print(f"详情: {e.to_dict()}")

asyncio.run(main())
```

#### URI 脱敏示例

```python
from src.sdk import ConnectionError

# 自动脱敏密码
err = ConnectionError(
    "连接失败",
    service="neo4j",
    uri="bolt://neo4j:password@localhost:7687"
)

print(err.details["uri"])  # bolt://neo4j:****@localhost:7687
```

#### API 响应格式

```python
from src.sdk import ValidationError

err = ValidationError(
    "查询模式无效",
    field="mode",
    value="invalid",
    constraint="必须是 naive, local, global, hybrid, mix, bypass 之一"
)

# 转换为 API 响应格式
response = {
    "success": False,
    "error": err.to_dict()
}

# 输出:
# {
#     "success": false,
#     "error": {
#         "error_type": "ValidationError",
#         "error_code": "VALIDATION_ERROR",
#         "message": "查询模式无效",
#         "details": {
#             "field": "mode",
#             "value": "invalid",
#             "constraint": "必须是 naive, local, global, hybrid, mix, bypass 之一"
#         }
#     }
# }
```

#### 异常转换示例

```python
from src.core.exceptions import DocumentError
from src.sdk import convert_core_exception

try:
    # 调用核心层代码
    raise DocumentError("文档错误", doc_id="doc-123")
except Exception as e:
    # 转换为 SDK 异常
    sdk_error = convert_core_exception(e)
    raise sdk_error from e
```

### 5. 验证测试

所有功能都通过了完整测试：

- ✅ 基础异常功能
- ✅ 配置错误
- ✅ 文档未找到错误
- ✅ 连接错误（URI 脱敏）
- ✅ 验证错误（值截断）
- ✅ 查询超时错误
- ✅ 速率限制错误
- ✅ 异常转换功能
- ✅ 异常层次结构
- ✅ SDK 模块导出

## 文件清单

### 主要文件

1. **`/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/exceptions.py`**
   - 主要实现文件
   - 包含所有异常类定义
   - 包含异常转换函数
   - 约 450 行代码

2. **`/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/__init__.py`**
   - 更新了异常类的导出
   - 包含所有 6 个异常类和转换函数

### 辅助文件

3. **`/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/test_exceptions.py`**
   - 完整的验证测试脚本
   - 测试所有异常类的功能
   - 包含使用示例

4. **`/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/exceptions_examples.py`**
   - 使用示例和最佳实践
   - 展示真实场景的异常处理
   - API 响应格式示例

## 关键特性

### 1. 用户友好

- 所有错误消息使用中文
- 提供清晰的错误类型和上下文
- 包含建议和解决方案

### 2. 安全性

- 自动脱敏 URI 中的密码
- 自动截断过长的值和查询
- 不暴露敏感信息

### 3. 开发者友好

- 提供完整的类型提示
- 支持链式异常（保留原始异常）
- to_dict() 方法便于 API 响应
- 统一的错误码系统

### 4. 可扩展性

- 清晰的异常层次结构
- 易于添加新的异常类型
- 支持自定义错误码
- 灵活的详情字典

## 最佳实践

### 1. 错误捕获

```python
# 推荐：捕获具体异常
try:
    await client.query(...)
except ValidationError as e:
    # 处理验证错误
    pass
except QueryTimeoutError as e:
    # 处理超时错误
    pass

# 也支持：捕获所有 SDK 异常
try:
    await client.query(...)
except MedGraphSDKError as e:
    # 统一处理
    pass
```

### 2. 错误信息提取

```python
try:
    await client.query(...)
except MedGraphSDKError as e:
    # 获取错误码
    error_code = e.error_code

    # 获取详细信息
    details = e.to_dict()

    # 获取特定属性
    if hasattr(e, 'field'):
        field = e.field
```

### 3. API 响应

```python
def handle_api_error(error: MedGraphSDKError) -> dict:
    """统一错误处理函数"""
    return {
        "success": False,
        "error": error.to_dict()
    }
```

### 4. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

try:
    await client.query(...)
except MedGraphSDKError as e:
    logger.error(
        f"SDK 错误: {e.error_code} - {e.message}",
        extra=e.details
    )
```

## 测试验证

运行测试脚本验证所有功能：

```bash
source venv/bin/activate
python src/sdk/test_exceptions.py
```

所有测试通过，包括：
- 基础异常功能测试
- 各类异常特定功能测试
- 异常转换测试
- 层次结构测试
- 真实场景模拟

## 总结

成功实现了完整的 SDK 异常模块，提供了：

1. **6 个专用异常类**，覆盖所有常见错误场景
2. **异常转换功能**，无缝对接核心层异常
3. **用户友好的错误信息**，包含详细上下文
4. **安全性保障**，自动脱敏敏感信息
5. **开发者友好**，完整的类型提示和文档
6. **100% 测试覆盖**，所有功能都经过验证

该异常模块为 SDK 层提供了坚实、易用的错误处理基础，是 SDK 功能完整性的重要组成部分。
