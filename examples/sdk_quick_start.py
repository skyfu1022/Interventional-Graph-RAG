"""
SDK 快速开始示例。

该文件展示了 MedGraphClient 的核心用法。
"""

import asyncio
from src.sdk import MedGraphClient


async def quick_start_example():
    """SDK 快速开始示例。"""
    print("=" * 70)
    print("Medical Graph RAG SDK - 快速开始示例")
    print("=" * 70)

    # 示例 1: 基本使用（异步上下文管理器）
    print("\n📖 示例 1: 基本使用（推荐方式）")
    print("-" * 70)

    print("""
from src.sdk import MedGraphClient
import asyncio

async def main():
    async with MedGraphClient(workspace="medical") as client:
        # 摄入文档
        await client.ingest_document("medical_doc.txt")

        # 查询知识图谱
        result = await client.query("什么是糖尿病?")
        print(result.answer)

asyncio.run(main())
    """)

    # 示例 2: 摄入文本
    print("\n📖 示例 2: 摄入文本")
    print("-" * 70)

    print("""
async with MedGraphClient() as client:
    text = "糖尿病是一种慢性代谢性疾病，主要特征是高血糖。"
    doc_info = await client.ingest_text(text, doc_id="doc-001")

    print(f"文档 ID: {doc_info.doc_id}")
    print(f"状态: {doc_info.status}")
    print(f"实体数: {doc_info.entities_count}")
    """)

    # 示例 3: 批量摄入
    print("\n📖 示例 3: 批量摄入")
    print("-" * 70)

    print("""
async with MedGraphClient() as client:
    texts = [
        "糖尿病是一种慢性代谢性疾病。",
        "高血压是心血管疾病的主要危险因素。",
        "心脏病是全球主要的死亡原因之一。"
    ]

    doc_infos = await client.ingest_batch(texts)
    print(f"成功摄入 {len(doc_infos)} 个文档")
    """)

    # 示例 4: 查询模式
    print("\n📖 示例 4: 不同的查询模式")
    print("-" * 70)

    print("""
async with MedGraphClient() as client:
    # naive: 直接使用 LLM（快速，但不使用知识图谱）
    result = await client.query("简单问题", mode="naive")

    # local: 仅使用局部上下文（关注实体关系）
    result = await client.query("实体关系", mode="local")

    # global: 仅使用全局上下文（社区摘要）
    result = await client.query("宏观问题", mode="global")

    # hybrid: 结合局部和全局（推荐，最准确）
    result = await client.query("复杂问题", mode="hybrid")
    """)

    # 示例 5: 流式查询
    print("\n📖 示例 5: 流式查询")
    print("-" * 70)

    print("""
async with MedGraphClient() as client:
    async for chunk in client.query_stream("详细说明糖尿病的病因"):
        print(chunk, end="", flush=True)
    """)

    # 示例 6: 便捷方法
    print("\n📖 示例 6: 便捷方法（摄入后立即查询）")
    print("-" * 70)

    print("""
async with MedGraphClient() as client:
    result = await client.ingest_and_query(
        text="阿司匹林是一种非甾体抗炎药...",
        query_text="阿司匹林有哪些作用?"
    )
    print(result.answer)
    """)

    # 示例 7: 手动生命周期管理
    print("\n📖 示例 7: 手动生命周期管理")
    print("-" * 70)

    print("""
client = MedGraphClient(workspace="medical")
await client.initialize()

try:
    result = await client.query("问题")
    print(result.answer)
finally:
    await client.close()
    """)

    # 示例 8: 嵌套使用
    print("\n📖 示例 8: 同时使用多个客户端")
    print("-" * 70)

    print("""
async with MedGraphClient(workspace="dataset_a") as client_a:
    async with MedGraphClient(workspace="dataset_b") as client_b:
        result_a = await client_a.query("数据集 A 的问题")
        result_b = await client_b.query("数据集 B 的问题")
    """)

    # 示例 9: 错误处理
    print("\n📖 示例 9: 错误处理")
    print("-" * 70)

    print("""
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
    """)

    # 示例 10: 配置管理
    print("\n📖 示例 10: 配置管理")
    print("-" * 70)

    print("""
# 从环境变量创建
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["NEO4J_URI"] = "neo4j://localhost:7687"

client = MedGraphClient.from_env()

# 从配置文件创建
client = MedGraphClient.from_config("config.yaml")

# 自定义配置
async with MedGraphClient(
    workspace="medical",
    log_level="DEBUG",
    llm_model="gpt-4o-mini"
) as client:
    # 使用客户端
    pass
    """)

    # 关键特性总结
    print("\n" + "=" * 70)
    print("📋 SDK 关键特性")
    print("=" * 70)

    features = [
        "✅ 异步上下文管理器（自动资源管理）",
        "✅ 超时保护（30 秒初始化超时）",
        "✅ 异常安全（即使发生异常也会清理资源）",
        "✅ 支持嵌套使用（多个客户端实例）",
        "✅ 多种查询模式（naive, local, global, hybrid）",
        "✅ 流式查询支持",
        "✅ 批量操作（提高效率）",
        "✅ 多模态文档处理",
        "✅ 图谱管理和统计",
        "✅ 灵活的配置管理",
    ]

    for feature in features:
        print(f"  {feature}")

    # 最佳实践
    print("\n" + "=" * 70)
    print("💡 最佳实践")
    print("=" * 70)

    practices = [
        "1. 始终使用 async with 语句（自动资源管理）",
        "2. 为不同数据集使用不同的工作空间",
        "3. 批量操作比逐个操作更高效",
        "4. 根据问题类型选择合适的查询模式",
        "5. 长答案使用流式查询改善用户体验",
        "6. 妥善处理各种异常类型",
        "7. 使用环境变量或配置文件管理敏感信息",
    ]

    for practice in practices:
        print(f"  {practice}")

    print("\n" + "=" * 70)
    print("📚 更多信息")
    print("=" * 70)
    print("""
- 完整文档: docs/SDK_USAGE.md
- 验证示例: examples/sdk_context_manager_demo.py
- 基本测试: test_sdk_basic.py
- 实现总结: docs/TASK-022_SUMMARY.md
    """)

    print("=" * 70)
    print("✨ 开始使用 Medical Graph RAG SDK!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(quick_start_example())
