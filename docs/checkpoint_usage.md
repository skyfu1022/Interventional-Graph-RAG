# LangGraph 检查点功能使用指南

## 概述

检查点（Checkpoint）功能允许 LangGraph 工作流保存和恢复状态，实现以下能力：

- **状态持久化**：工作流执行后状态自动保存
- **会话恢复**：从上次停止的地方继续执行
- **时间旅行调试**：查看和恢复历史状态
- **多租户支持**：通过 thread_id 隔离不同会话

## 快速开始

### 1. 内存检查点（开发环境）

```python
from src.agents.workflows import create_query_workflow
from src.agents.checkpoints import create_memory_checkpointer

# 创建内存检查点
memory = create_memory_checkpointer()

# 创建带检查点的工作流
workflow = create_query_workflow(
    rag_adapter=adapter,
    llm=llm,
    checkpointer=memory
)

# 执行工作流（需要提供 config）
config = {"configurable": {"thread_id": "conversation-123"}}
result = workflow.invoke({
    "query": "什么是高血压？",
    "graph_id": "medical_graph"
}, config)

# 获取当前状态
from src.agents.checkpoints import get_checkpoint_state
state = get_checkpoint_state(workflow, "conversation-123")
print(f"当前状态: {state.values}")
```

### 2. SQLite 检查点（生产环境）

```python
from src.agents.workflows import create_query_workflow
from src.agents.checkpoints import create_sqlite_checkpointer

# 创建 SQLite 检查点（持久化存储）
checkpointer = create_sqlite_checkpointer("./checkpoints.db")

# 创建带检查点的工作流
workflow = create_query_workflow(
    rag_adapter=adapter,
    llm=llm,
    checkpointer=checkpointer
)

# 执行工作流
config = {"configurable": {"thread_id": "production-123"}}
result = workflow.invoke({
    "query": "什么是高血压？",
    "graph_id": "medical_graph"
}, config)

# 程序重启后，状态依然可以恢复
restored_state = workflow.get_state(config)
print(f"恢复的状态: {restored_state.values}")
```

## 高级功能

### 1. 查看检查点历史

```python
from src.agents.checkpoints import list_checkpoints

# 列出所有检查点
checkpoints = list_checkpoints(workflow, "conversation-123")

for i, cp in enumerate(checkpoints):
    print(f"检查点 {i + 1}:")
    print(f"  ID: {cp['checkpoint_id']}")
    print(f"  步骤: {cp['step']}")
    print(f"  值: {cp['values']}")
```

### 2. 时间旅行调试

```python
# 获取所有检查点
checkpoints = list_checkpoints(workflow, "conversation-123")

# 回退到之前的检查点（例如第 3 个检查点）
if len(checkpoints) >= 3:
    target_checkpoint_id = checkpoints[2]['checkpoint_id']

    # 使用该检查点继续执行
    time_travel_config = {
        "configurable": {
            "thread_id": "conversation-123",
            "checkpoint_id": target_checkpoint_id
        }
    }

    # 从该检查点继续
    result = workflow.invoke({
        "query": "新问题"
    }, time_travel_config)
```

### 3. 线程统计

```python
from src.agents.checkpoints import get_thread_stats

# 获取线程统计信息
stats = get_thread_stats(workflow, "conversation-123")

print(f"总检查点数: {stats['total_checkpoints']}")
print(f"当前步骤: {stats['current_step']}")
print(f"是否完成: {stats['is_completed']}")
print(f"最后检查点 ID: {stats['last_checkpoint_id']}")
```

### 4. 构建工作流检查点

```python
from src.agents.workflows import create_build_workflow
from src.agents.checkpoints import create_sqlite_checkpointer

# 创建带检查点的构建工作流
checkpointer = create_sqlite_checkpointer("./build_checkpoints.db")
workflow = create_build_workflow(
    rag_adapter=adapter,
    merge_enabled=True,
    checkpointer=checkpointer
)

# 执行构建任务
config = {"configurable": {"thread_id": "build-001"}}
result = workflow.invoke({
    "file_path": "/path/to/document.pdf",
    "graph_id": "graph_001"
}, config)

# 如果构建过程中断，可以从检查点恢复
state = workflow.get_state(config)
if state.values.get("status") != "completed":
    # 继续执行
    result = workflow.invoke(None, config)
```

## 最佳实践

### 1. 选择合适的检查点存储

| 存储类型 | 适用场景 | 优点 | 缺点 |
|---------|---------|------|------|
| **MemorySaver** | 开发、测试、演示 | 速度快，无需配置 | 程序重启后数据丢失 |
| **SqliteSaver** | 生产环境、单机部署 | 持久化存储，轻量级 | 不支持分布式 |
| **PostgresSaver** | 生产环境、分布式 | 高可用，支持并发 | 需要额外部署 |

### 2. 线程 ID 命名规范

```python
# 推荐：使用有意义的线程 ID
thread_id = f"user-{user_id}-session-{session_id}"
thread_id = f"build-{graph_id}-{timestamp}"
thread_id = f"query-{graph_id}-{conversation_id}"

# 不推荐：使用随机或无意义的 ID
thread_id = "abc123"  # 难以管理
```

### 3. 资源管理

```python
# SQLite 检查点使用完毕后关闭连接
checkpointer = create_sqlite_checkpointer("./checkpoints.db")
workflow = create_build_workflow(adapter, checkpointer=checkpointer)

try:
    result = workflow.invoke(initial_state, config)
finally:
    # 关闭数据库连接
    checkpointer.conn.close()
```

### 4. 错误处理

```python
from src.agents.checkpoints import get_checkpoint_state

# 安全地获取检查点状态
state = get_checkpoint_state(workflow, "conversation-123")
if state is None:
    print("没有找到检查点，可能是第一次执行")
else:
    print(f"找到检查点: {state.values}")
```

## API 参考

### create_memory_checkpointer()

创建内存检查点存储。

```python
from src.agents.checkpoints import create_memory_checkpointer

memory = create_memory_checkpointer()
```

### create_sqlite_checkpointer(db_path: str)

创建 SQLite 检查点存储。

```python
from src.agents.checkpoints import create_sqlite_checkpointer

checkpointer = create_sqlite_checkpointer("./checkpoints.db")
```

**参数:**
- `db_path`: SQLite 数据库文件路径

### get_checkpoint_state(workflow, thread_id, checkpoint_id=None)

获取指定线程的检查点状态。

```python
from src.agents.checkpoints import get_checkpoint_state

# 获取最新状态
state = get_checkpoint_state(workflow, "conversation-123")

# 获取特定检查点
state = get_checkpoint_state(
    workflow,
    "conversation-123",
    checkpoint_id="checkpoint-abc-123"
)
```

### list_checkpoints(workflow, thread_id, limit=None)

列出指定线程的所有检查点。

```python
from src.agents.checkpoints import list_checkpoints

# 列出所有检查点
checkpoints = list_checkpoints(workflow, "conversation-123")

# 只获取最近 10 个
recent = list_checkpoints(workflow, "conversation-123", limit=10)
```

### get_thread_stats(workflow, thread_id)

获取指定线程的统计信息。

```python
from src.agents.checkpoints import get_thread_stats

stats = get_thread_stats(workflow, "conversation-123")
```

## 完整示例

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.workflows import create_query_workflow
from src.agents.checkpoints import (
    create_sqlite_checkpointer,
    get_checkpoint_state,
    list_checkpoints,
    get_thread_stats,
)

# 创建工作流
checkpointer = create_sqlite_checkpointer("./checkpoints.db")
workflow = create_query_workflow(
    rag_adapter=None,  # 替换为实际的 adapter
    llm=None,          # 替换为实际的 llm
    checkpointer=checkpointer
)

# 第一次执行
config = {"configurable": {"thread_id": "example-001"}}
result1 = workflow.invoke({
    "query": "什么是糖尿病？",
    "graph_id": "medical_graph"
}, config)

# 查看状态
state = get_checkpoint_state(workflow, "example-001")
print(f"状态: {state.values}")

# 查看历史
checkpoints = list_checkpoints(workflow, "example-001")
print(f"共 {len(checkpoints)} 个检查点")

# 获取统计
stats = get_thread_stats(workflow, "example-001")
print(f"统计: {stats}")
```

## 故障排除

### 问题 1: 检查点未保存

**症状**: 执行工作流后无法获取检查点状态

**解决方案**:
- 确保在 `invoke` 时传递了 `config` 参数
- 确保 `config` 包含 `{"configurable": {"thread_id": "..."}}`

### 问题 2: SQLite 数据库锁定

**症状**: 出现 "database is locked" 错误

**解决方案**:
```python
# 使用 check_same_thread=False
import sqlite3
conn = sqlite3.connect(db_path, check_same_thread=False)
checkpointer = SqliteSaver(conn)
```

### 问题 3: 内存检查点数据丢失

**症状**: 程序重启后检查点数据丢失

**解决方案**:
- MemorySaver 仅用于开发和测试
- 生产环境使用 SqliteSaver 或 PostgresSaver

## 参考资料

- [LangGraph 官方文档 - 持久化](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph 检查点存储选项](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint)
- 项目验证脚本: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/test_checkpoints.py`
