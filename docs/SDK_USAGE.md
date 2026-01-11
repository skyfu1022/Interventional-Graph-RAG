# SDK 异步上下文管理器使用指南

## 概述

MedGraphClient 现在完全支持 Python 异步上下文管理器协议（`async with`），自动处理资源的初始化和清理。这是使用 SDK 的推荐方式。

## 核心特性

### 1. 自动初始化和清理

使用 `async with` 语句，SDK 会自动：
- 初始化适配器和连接
- 配置存储后端
- 在退出时关闭连接并释放资源

### 2. 超时保护

初始化过程内置 30 秒超时保护，防止无限等待。

### 3. 异常安全

即使在上下文中发生异常，资源也会被正确清理，不会掩盖原始异常。

### 4. 支持嵌套使用

可以同时使用多个客户端实例，每个实例独立管理自己的资源。

## 基本用法

### 推荐方式：使用异步上下文管理器

```python
from src.sdk import MedGraphClient
import asyncio

async def main():
    # 使用 async with 自动管理资源
    async with MedGraphClient(workspace="medical") as client:
        # 摄入文档
        await client.ingest_document("medical_doc.txt")

        # 查询知识图谱
        result = await client.query("什么是糖尿病?")
        print(result.answer)
    # 退出时自动关闭连接

asyncio.run(main())
```

### 手动管理方式

如果不使用上下文管理器，可以手动管理生命周期：

```python
async def main():
    # 创建客户端
    client = MedGraphClient(workspace="medical")

    # 手动初始化
    await client.initialize()

    try:
        # 使用客户端
        result = await client.query("问题")
        print(result.answer)
    finally:
        # 手动关闭
        await client.close()

asyncio.run(main())
```

## 文档摄入

### 摄入文件

```python
async with MedGraphClient() as client:
    doc_info = await client.ingest_document("report.txt", doc_id="doc-001")
    print(f"文档 ID: {doc_info.doc_id}")
    print(f"状态: {doc_info.status}")
    print(f"实体数: {doc_info.entities_count}")
```

### 摄入文本

```python
async with MedGraphClient() as client:
    text = "糖尿病是一种慢性代谢性疾病..."
    doc_info = await client.ingest_text(text, doc_id="text-001")
```

### 批量摄入

```python
async with MedGraphClient() as client:
    texts = ["文档1", "文档2", "文档3"]
    doc_infos = await client.ingest_batch(texts)
    print(f"成功摄入 {len(doc_infos)} 个文档")
```

### 多模态摄入

```python
async with MedGraphClient() as client:
    contents = [
        {"content_type": "text", "content": "报告文本"},
        {"content_type": "image", "content": "base64..."}
    ]
    doc_info = await client.ingest_multimodal(contents)
```

## 知识图谱查询

### 基本查询

```python
async with MedGraphClient() as client:
    result = await client.query("什么是糖尿病?")
    print(result.answer)
```

### 查询模式

SDK 支持多种查询模式：

```python
# naive: 直接使用 LLM（不使用知识图谱）
result = await client.query("问题", mode="naive")

# local: 仅使用局部上下文（实体邻居）
result = await client.query("问题", mode="local")

# global: 仅使用全局上下文（社区摘要）
result = await client.query("问题", mode="global")

# hybrid: 结合局部和全局（推荐）
result = await client.query("问题", mode="hybrid")

# mix: 混合模式
result = await client.query("问题", mode="mix")
```

### 带参数的查询

```python
async with MedGraphClient() as client:
    result = await client.query(
        "糖尿病的症状",
        mode="hybrid",
        top_k=10,
        max_entity_tokens=2000
    )
```

### 流式查询

```python
async with MedGraphClient() as client:
    async for chunk in client.query_stream("详细说明糖尿病的病因"):
        print(chunk, end="", flush=True)
```

## 高级用法

### 嵌套上下文管理器

```python
async def use_multiple_clients():
    """同时使用多个客户端"""
    async with MedGraphClient(workspace="graph1") as client1:
        async with MedGraphClient(workspace="graph2") as client2:
            result1 = await client1.query("查询1")
            result2 = await client2.query("查询2")
```

### 便捷方法

```python
async with MedGraphClient() as client:
    # 摄入并查询（一步完成）
    result = await client.ingest_and_query(
        text="糖尿病是一种代谢性疾病...",
        query_text="什么是糖尿病?"
    )
```

### 图谱管理

```python
async with MedGraphClient() as client:
    # 获取统计信息
    stats = await client.get_stats()
    print(f"实体数: {stats.entity_count}")
    print(f"关系数: {stats.relationship_count}")

    # 导出数据
    await client.export_data(
        "knowledge_graph.csv",
        file_format="csv"
    )

    # 删除文档
    await client.delete_document("doc-123")
```

## 配置管理

### 从环境变量创建

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["NEO4J_URI"] = "neo4j://localhost:7687"

client = MedGraphClient.from_env()
```

### 从配置文件创建

```python
# config.yaml
# workspace: "medical"
# openai_api_key: "sk-..."
# neo4j_uri: "neo4j://localhost:7687"
# ...

client = MedGraphClient.from_config("config.yaml")
```

### 自定义配置

```python
async with MedGraphClient(
    workspace="medical",
    log_level="DEBUG",
    llm_model="gpt-4o-mini",
    embedding_model="text-embedding-3-large"
) as client:
    # 使用客户端
    pass
```

## 错误处理

### 基本错误处理

```python
from src.core.exceptions import (
    DocumentError,
    QueryError,
    ValidationError,
    ConfigError
)

async def main():
    try:
        async with MedGraphClient() as client:
            result = await client.query("问题")
    except ValidationError as e:
        print(f"参数验证失败: {e}")
    except QueryError as e:
        print(f"查询失败: {e}")
    except DocumentError as e:
        print(f"文档操作失败: {e}")
    except ConfigError as e:
        print(f"配置错误: {e}")

asyncio.run(main())
```

### 异常安全

```python
# 即使发生异常，资源也会被正确清理
try:
    async with MedGraphClient() as client:
        await client.ingest_document("doc.txt")
        raise ValueError("测试异常")
except ValueError:
    print("异常被捕获，连接已自动关闭")
```

## 最佳实践

### 1. 始终使用上下文管理器

```python
# ✓ 推荐：使用 async with
async with MedGraphClient() as client:
    await client.query("问题")

# ✗ 不推荐：手动管理（容易出错）
client = MedGraphClient()
await client.initialize()
# ... 如果这里抛出异常，close() 不会被调用
await client.close()
```

### 2. 合理使用工作空间

```python
# 为不同的数据集使用不同的工作空间
async with MedGraphClient(workspace="dataset_a") as client_a:
    # 处理数据集 A
    pass

async with MedGraphClient(workspace="dataset_b") as client_b:
    # 处理数据集 B
    pass
```

### 3. 批量操作优化

```python
# ✓ 推荐：批量摄入
texts = ["文档1", "文档2", "文档3"]
await client.ingest_batch(texts)

# ✗ 不推荐：逐个摄入
for text in texts:
    await client.ingest_text(text)  # 效率较低
```

### 4. 选择合适的查询模式

```python
# 简单问题：使用 naive（快速）
result = await client.query("简单问题", mode="naive")

# 复杂推理：使用 hybrid（准确）
result = await client.query("复杂问题", mode="hybrid")

# 实体关系：使用 local（关注局部）
result = await client.query("实体关系", mode="local")
```

## 性能提示

1. **初始化开销**：首次初始化需要时间（约 5-10 秒），建议复用客户端实例
2. **批量操作**：批量摄入比逐个摄入效率更高
3. **查询模式**：naive 模式最快但不使用知识图谱，hybrid 模式最准确但稍慢
4. **流式查询**：长答案使用流式查询可以改善用户体验

## 故障排查

### 初始化超时

```python
# 如果初始化超时，检查配置
async with MedGraphClient() as client:
    pass
# 超时错误：检查 Neo4j 和 Milvus 是否正常运行
```

### 连接失败

```python
# 检查环境变量和配置
import os
print(os.environ.get("NEO4J_URI"))
print(os.environ.get("MILVUS_URI"))
```

### 查询无结果

```python
# 确保已摄入相关文档
stats = await client.get_stats()
print(f"文档数: {stats.document_count}")
```

## 更多示例

查看 `examples/sdk_context_manager_demo.py` 获取更多完整示例。
