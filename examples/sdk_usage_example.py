#!/usr/bin/env python3
"""
Medical Graph RAG SDK 使用示例。

展示如何使用 SDK 进行常见操作：
- 创建客户端
- 摄入文档
- 查询知识图谱
- 获取性能统计
"""

import asyncio
from pathlib import Path

from src.sdk import (
    MedGraphClient,
    QueryMode,
    get_version,
    get_info,
)


async def main():
    """主函数：演示 SDK 使用。"""

    # ========== 1. 查看 SDK 信息 ==========
    print("=" * 60)
    print("Medical Graph RAG SDK 使用示例")
    print("=" * 60)

    print(f"\nSDK 版本: {get_version()}")
    print("\nSDK 信息:")
    info = get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # ========== 2. 创建客户端 ==========
    print("\n" + "=" * 60)
    print("创建客户端")
    print("=" * 60)

    # 使用异步上下文管理器（推荐）
    async with MedGraphClient(
        workspace="medical",
        log_level="INFO",
        enable_metrics=True
    ) as client:

        print(f"✅ 客户端创建成功 | 工作空间: {client.workspace}")

        # ========== 3. 摄入文本 ==========
        print("\n" + "=" * 60)
        print("摄入文本")
        print("=" * 60)

        medical_text = """
        糖尿病是一种慢性代谢性疾病，主要特征是高血糖。
        糖尿病分为 1 型和 2 型，2 型糖尿病最为常见。
        糖尿病的并发症包括心血管疾病、肾病、视网膜病变等。
        治疗方法包括药物治疗、饮食控制和运动疗法。
        """

        doc_info = await client.ingest_text(
            text=medical_text,
            doc_id="example-diabetes-doc"
        )

        print(f"✅ 文本摄入成功 | ID: {doc_info.doc_id}")
        print(f"   状态: {doc_info.status}")
        print(f"   文本块数: {doc_info.chunks_count}")
        print(f"   实体数: {doc_info.entities_count}")

        # ========== 4. 查询知识图谱 ==========
        print("\n" + "=" * 60)
        print("查询知识图谱")
        print("=" * 60)

        # 4.1 混合模式查询（推荐）
        print("\n【混合模式查询】")
        result = await client.query(
            query_text="什么是糖尿病？",
            mode="hybrid"
        )

        print(f"问题: {result.query}")
        print(f"答案: {result.answer}")
        print(f"模式: {result.mode.value}")
        print(f"延迟: {result.latency_ms}ms")
        print(f"检索次数: {result.retrieval_count}")

        # 4.2 局部模式查询（关注实体关系）
        print("\n【局部模式查询】")
        result = await client.query(
            query_text="糖尿病有哪些并发症？",
            mode="local"
        )

        print(f"问题: {result.query}")
        print(f"答案: {result.answer}")

        # 4.3 全局模式查询（关注图谱结构）
        print("\n【全局模式查询】")
        result = await client.query(
            query_text="糖尿病的治疗方法有哪些？",
            mode="global"
        )

        print(f"问题: {result.query}")
        print(f"答案: {result.answer}")

        # ========== 5. 获取图谱信息 ==========
        print("\n" + "=" * 60)
        print("获取图谱信息")
        print("=" * 60)

        graphs = await client.list_graphs()
        print(f"图谱数量: {len(graphs)}")

        for graph in graphs:
            print(f"\n图谱 {graph.graph_id}:")
            print(f"  工作空间: {graph.workspace}")
            print(f"  实体数: {graph.entity_count}")
            print(f"  关系数: {graph.relationship_count}")
            print(f"  文档数: {graph.document_count}")

        # ========== 6. 获取性能统计 ==========
        print("\n" + "=" * 60)
        print("性能统计")
        print("=" * 60)

        stats = client.get_stats()
        print(f"总查询次数: {stats['total_queries']}")
        print(f"总文档数: {stats['total_documents']}")
        print(f"平均延迟: {stats['avg_latency_ms']}ms")
        print(f"P50 延迟: {stats['p50_latency_ms']}ms")
        print(f"P95 延迟: {stats['p95_latency_ms']}ms")
        print(f"P99 延迟: {stats['p99_latency_ms']}ms")
        print(f"错误率: {stats['error_rate']:.2%}")
        print(f"查询分布: {stats['queries_by_mode']}")

        # ========== 7. 获取性能摘要 ==========
        print("\n" + "=" * 60)
        print("性能摘要")
        print("=" * 60)

        summary = client.get_performance_summary()
        print(summary)

    # 客户端自动关闭
    print("\n" + "=" * 60)
    print("客户端已自动关闭")
    print("=" * 60)


async def example_query_modes():
    """演示不同的查询模式。"""

    print("\n" + "=" * 60)
    print("查询模式示例")
    print("=" * 60)

    print("\n可用的查询模式:")
    for mode in QueryMode:
        print(f"  - {mode.name}: {mode.value}")

    print("\n查询模式说明:")
    print("  - NAIVE: 简单检索，直接返回相关内容")
    print("  - LOCAL: 局部社区检索，关注实体局部关系")
    print("  - GLOBAL: 全局社区检索，关注图谱全局结构")
    print("  - HYBRID: 混合检索，结合局部和全局优势（推荐）")
    print("  - MIX: 混合模式，动态调整检索策略")
    print("  - BYPASS: 绕过图谱，直接检索原始文档")


async def example_error_handling():
    """演示错误处理。"""

    print("\n" + "=" * 60)
    print("错误处理示例")
    print("=" * 60)

    from src.sdk import (
        ConfigError,
        DocumentNotFoundError,
        ValidationError,
    )

    try:
        # 示例：配置错误
        raise ConfigError(
            "API Key 未配置",
            config_key="openai_api_key"
        )
    except ConfigError as e:
        print(f"捕获配置错误: {e}")
        print(f"错误详情: {e.to_dict()}")

    try:
        # 示例：文档未找到
        raise DocumentNotFoundError(
            "文档不存在",
            doc_id="doc-123"
        )
    except DocumentNotFoundError as e:
        print(f"捕获文档未找到错误: {e}")

    try:
        # 示例：验证错误
        raise ValidationError(
            "查询模式无效",
            field="mode",
            value="invalid",
            constraint="必须是 naive, local, global, hybrid, mix, bypass 之一"
        )
    except ValidationError as e:
        print(f"捕获验证错误: {e}")


async def example_streaming_query():
    """演示流式查询。"""

    print("\n" + "=" * 60)
    print("流式查询示例")
    print("=" * 60)

    async with MedGraphClient(workspace="medical") as client:
        # 先摄入一些文本
        await client.ingest_text(
            "Python 是一种高级编程语言，由 Guido van Rossum 创建。",
            doc_id="python-doc"
        )

        # 流式查询
        print("\n流式查询结果:")
        async for chunk in client.query_stream(
            query_text="Python 是什么？",
            mode="hybrid"
        ):
            print(chunk, end="", flush=True)

        print()  # 换行


async def example_from_config():
    """演示从配置文件创建客户端。"""

    print("\n" + "=" * 60)
    print("从配置文件创建客户端")
    print("=" * 60)

    # 创建示例配置文件
    import json

    config = {
        "rag_workspace": "medical",
        "log_level": "INFO",
        "enable_metrics": True,
    }

    config_path = Path("example_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"配置文件已创建: {config_path}")

    # 从配置文件创建客户端
    client = MedGraphClient.from_config(
        config_path=str(config_path),
        enable_metrics=True
    )

    print(f"✅ 客户端创建成功 | 工作空间: {client.workspace}")

    # 清理
    config_path.unlink()
    print(f"配置文件已删除")


if __name__ == "__main__":
    # 运行主示例
    asyncio.run(main())

    # 运行其他示例
    asyncio.run(example_query_modes())
    asyncio.run(example_error_handling())
    asyncio.run(example_from_config())
