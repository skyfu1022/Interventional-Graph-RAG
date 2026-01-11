# 查询服务使用指南

## 概述

`QueryService` 是 Medical Graph RAG 项目的核心查询服务，封装了 LangGraph 查询工作流，提供智能图谱查询能力。

## 核心功能

### 1. 支持 6 种检索模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `naive` | 简单检索，直接返回答案 | 简单事实性查询 |
| `local` | 局部社区检索，基于局部实体关系 | 需要了解实体间直接关系的查询 |
| `global` | 全局社区检索，基于全局图谱结构 | 需要理解整体图谱结构的查询 |
| `hybrid` | 混合检索，结合局部和全局信息 | 通用查询，平衡精度和召回 |
| `mix` | 混合模式，灵活组合多种检索策略 | 复杂查询，需要多角度分析 |
| `bypass` | 绕过图谱，直接检索向量数据库 | 快速检索，不依赖图谱结构 |

### 2. 异步查询执行

所有查询方法都是异步的，支持高并发场景。

### 3. 流式查询

支持流式输出，适用于需要实时展示的场景。

### 4. 性能监控

自动记录查询延迟、检索次数等性能指标。

## 快速开始

### 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装 langgraph 和相关依赖
pip install langgraph langgraph-checkpoint-sqlite
```

### 基本使用

```python
import asyncio
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.query import QueryService

async def main():
    # 1. 初始化配置和适配器
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()

    # 2. 创建查询服务
    service = QueryService(adapter)

    # 3. 执行查询
    result = await service.query(
        "什么是糖尿病?",
        mode="hybrid",
        graph_id="medical"
    )

    # 4. 查看结果
    print(f"答案: {result.answer}")
    print(f"耗时: {result.latency_ms}ms")
    print(f"检索次数: {result.retrieval_count}")
    print(f"来源: {result.sources}")

    # 5. 关闭适配器
    await adapter.close()

asyncio.run(main())
```

## 详细用法

### 1. 基本查询

```python
result = await service.query(
    query_text="什么是糖尿病?",
    mode="hybrid",        # 查询模式
    graph_id="medical",   # 图谱 ID
    top_k=5              # 额外参数
)

# 访问结果
print(result.answer)           # 答案
print(result.mode)             # 查询模式
print(result.query_complexity) # 查询复杂度
print(result.context)          # 检索上下文
print(result.sources)          # 答案来源
print(result.latency_ms)       # 延迟（毫秒）
```

### 2. 流式查询

```python
async for chunk in service.query_stream(
    "糖尿病的症状有哪些?",
    mode="hybrid"
):
    print(chunk, end="", flush=True)
print()  # 换行
```

### 3. 带上下文的查询

适用于多轮对话场景：

```python
from src.services.query import QueryContext

# 创建查询上下文
context = QueryContext(
    conversation_history=[
        {"role": "user", "content": "什么是糖尿病?"},
        {"role": "assistant", "content": "糖尿病是..."}
    ],
    domain_context="医学领域",
    previous_queries=["什么是糖尿病?"]
)

# 执行带上下文的查询
result = await service.query_with_context(
    "它有哪些并发症?",
    mode="hybrid",
    context=context
)
```

### 4. 批量查询

并发执行多个查询：

```python
queries = [
    "什么是糖尿病?",
    "什么是高血压?",
    "什么是心脏病?"
]

results = await service.batch_query(
    queries,
    mode="hybrid",
    graph_id="medical"
)

# 处理结果
for result in results:
    print(f"{result.query}: {result.answer[:50]}...")
```

### 5. 不同查询模式

```python
# 简单检索
result = await service.query("什么是糖尿病?", mode="naive")

# 局部检索
result = await service.query(
    "糖尿病和高血压的关系?",
    mode="local"
)

# 全局检索
result = await service.query(
    "分析心血管疾病的整体影响",
    mode="global"
)

# 混合检索（推荐）
result = await service.query(
    "糖尿病的并发症有哪些?",
    mode="hybrid"
)
```

## 结果格式化

### 转换为字典

```python
result_dict = result.to_dict()
print(result_dict)
# {
#     "query": "什么是糖尿病?",
#     "answer": "...",
#     "mode": "hybrid",
#     "graph_id": "medical",
#     "sources": [...],
#     "context": [...],
#     "retrieval_count": 3,
#     "latency_ms": 150,
#     "query_complexity": "medium",
#     "metadata": {...}
# }
```

### 转换为 JSON

```python
json_str = result.to_json()
print(json_str)
```

## 错误处理

```python
from src.core.exceptions import QueryError, ValidationError

try:
    result = await service.query(
        "什么是糖尿病?",
        mode="hybrid"
    )
except ValidationError as e:
    print(f"参数验证失败: {e}")
    print(f"字段: {e.field}")
    print(f"值: {e.value}")
except QueryError as e:
    print(f"查询执行失败: {e}")
    print(f"查询文本: {e.query_text}")
    print(f"详情: {e.details}")
```

## 辅助功能

### 查看支持的查询模式

```python
modes = service.get_supported_modes()
print(modes)  # ['naive', 'local', 'global', 'hybrid', 'mix', 'bypass']
```

### 获取模式描述

```python
desc = service.get_mode_description("hybrid")
print(desc)
# "混合检索，结合局部和全局信息"
```

### 验证查询模式

```python
from src.services.query import validate_query_mode

if validate_query_mode("hybrid"):
    print("有效的查询模式")
```

### 获取所有模式描述

```python
from src.services.query import get_mode_descriptions

descriptions = get_mode_descriptions()
for mode, desc in descriptions.items():
    print(f"{mode}: {desc}")
```

## 性能优化

### 1. 选择合适的查询模式

- **简单查询**: 使用 `naive` 模式，最快
- **实体关系查询**: 使用 `local` 模式
- **全局分析**: 使用 `global` 模式
- **通用场景**: 使用 `hybrid` 模式（推荐）

### 2. 批量查询

对于多个独立查询，使用 `batch_query` 方法并发执行：

```python
# 不推荐（顺序执行）
for query in queries:
    result = await service.query(query)

# 推荐（并发执行）
results = await service.batch_query(queries)
```

### 3. 监控性能

查看查询性能指标：

```python
result = await service.query(...)

print(f"延迟: {result.latency_ms}ms")
print(f"检索次数: {result.retrieval_count}")
print(f"查询复杂度: {result.query_complexity}")
```

## LangGraph 集成

`QueryService` 基于 LangGraph 工作流实现，使用以下最佳实践：

### 异步工作流调用

```python
# 使用 ainvoke 执行工作流
result = await self._workflow.ainvoke(workflow_input)
```

### 流式输出

```python
# 使用 astream 进行流式输出
async for chunk in self._workflow.astream(
    workflow_input,
    stream_mode="updates"
):
    # 处理每个节点的输出
    ...
```

### 错误处理

```python
try:
    result = await self._workflow.ainvoke(workflow_input)
except Exception as e:
    raise QueryError(f"查询执行失败: {e}") from e
```

## 完整示例

### 示例 1：医疗问答系统

```python
import asyncio
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.query import QueryService

async def medical_qa():
    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = QueryService(adapter)

    # 问题列表
    questions = [
        "什么是糖尿病?",
        "糖尿病的主要症状有哪些?",
        "如何预防糖尿病?",
        "糖尿病和高血压有什么关系?"
    ]

    # 回答问题
    for question in questions:
        print(f"\n问题: {question}")
        result = await service.query(
            question,
            mode="hybrid",
            graph_id="medical"
        )
        print(f"答案: {result.answer}")
        print(f"耗时: {result.latency_ms}ms")

    # 关闭
    await adapter.close()

asyncio.run(medical_qa())
```

### 示例 2：多轮对话

```python
async def multi_turn_conversation():
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = QueryService(adapter)

    # 对话历史
    context = QueryContext()

    # 多轮对话
    while True:
        user_input = input("\n用户: ")

        if user_input.lower() in ["退出", "exit", "quit"]:
            break

        # 添加到历史
        context.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # 查询
        result = await service.query_with_context(
            user_input,
            mode="hybrid",
            context=context
        )

        print(f"\n助手: {result.answer}")

        # 添加到历史
        context.conversation_history.append({
            "role": "assistant",
            "content": result.answer
        })

        # 添加到历史查询
        context.previous_queries.append(user_input)

    await adapter.close()

asyncio.run(multi_turn_conversation())
```

## 故障排查

### 问题 1：导入错误

```
ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'
```

**解决方案**：
```bash
pip install langgraph-checkpoint-sqlite
```

### 问题 2：工作流未初始化

```
QueryError: 查询工作流未初始化，无法执行查询
```

**原因**：`create_query_workflow` 导入失败。

**解决方案**：确保所有依赖已正确安装。

### 问题 3：查询结果为空

**可能原因**：
1. 图谱中没有相关数据
2. 查询模式不合适
3. 查询文本过于模糊

**解决方案**：
1. 检查图谱数据是否已摄入
2. 尝试不同的查询模式
3. 优化查询文本，使其更具体

## 参考资源

- [LangGraph 官方文档](https://github.com/langchain-ai/langgraph)
- [LightRAG 文档](https://github.com/HKUDS/LightRAG)
- 项目文档：`/docs`
- 示例代码：`/examples`

## 版本信息

- 实现版本：1.0.0
- LangGraph 版本：0.2+
- Python 版本：3.10+
