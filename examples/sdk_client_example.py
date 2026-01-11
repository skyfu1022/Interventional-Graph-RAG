"""
Medical Graph RAG SDK 客户端验证代码。

该文件提供完整的 SDK 客户端使用示例，包括：
- 基本查询功能
- 文档摄入
- 批量操作
- 性能监控
- 配置管理
- 异常处理

运行方式:
    python examples/sdk_client_example.py

前提条件:
    1. 确保 Neo4j 和 Milvus 服务正在运行
    2. 设置 OPENAI_API_KEY 环境变量
    3. 安装依赖: pip install -r requirements.txt
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sdk import MedGraphClient
from src.sdk.types import QueryMode, QueryResult
from src.sdk.exceptions import MedGraphSDKError, ConfigError


# ========== 示例 1: 基本查询功能 ==========

async def example_basic_query():
    """示例 1: 基本查询功能。

    演示如何使用 SDK 客户端执行简单的知识图谱查询。
    """
    print("\n" + "="*60)
    print("示例 1: 基本查询功能")
    print("="*60)

    try:
        # 使用异步上下文管理器（推荐方式）
        async with MedGraphClient(workspace="medical") as client:
            # 执行混合模式查询
            result = await client.query(
                "什么是糖尿病?",
                mode="hybrid"
            )

            print(f"\n查询问题: {result.query}")
            print(f"查询模式: {result.mode.value}")
            print(f"答案长度: {len(result.answer)} 字符")
            print(f"\n答案摘要:")
            print(result.answer[:200] + "..." if len(result.answer) > 200 else result.answer)

            # 获取性能统计
            stats = client.get_stats()
            print(f"\n性能统计:")
            print(f"  查询次数: {stats['total_queries']}")
            print(f"  平均延迟: {stats.get('avg_latency_ms', 0)}ms")

    except ConfigError as e:
        print(f"配置错误: {e.message}")
        print(f"详情: {e.details}")
    except MedGraphSDKError as e:
        print(f"SDK 错误: {e.message}")


# ========== 示例 2: 文档摄入 ==========

async def example_document_ingestion():
    """示例 2: 文档摄入。

    演示如何摄入单个文档并查询。
    """
    print("\n" + "="*60)
    print("示例 2: 文档摄入")
    print("="*60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 摄入测试文档
            test_text = """
            糖尿病是一种慢性代谢性疾病，主要特征是高血糖。
            糖尿病主要分为 1 型和 2 型两种类型。
            1 型糖尿病通常在青少年时期发病，需要胰岛素治疗。
            2 型糖尿病多见于成年人，与生活方式和遗传因素相关。
            糖尿病的常见症状包括多饮、多尿、多食和体重下降。
            """

            doc_info = await client.ingest_text(
                text=test_text,
                doc_id="diabetes_intro"
            )

            print(f"\n文档摄入成功:")
            print(f"  文档 ID: {doc_info.doc_id}")
            print(f"  状态: {doc_info.status}")
            print(f"  文本块数: {doc_info.chunks_count}")
            print(f"  实体数: {doc_info.entities_count}")

            # 稍作等待，确保索引完成
            await asyncio.sleep(1)

            # 查询刚摄入的文档
            result = await client.query("糖尿病有哪些症状?")
            print(f"\n查询结果:")
            print(f"  {result.answer[:150]}...")

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 3: 批量操作 ==========

async def example_batch_operations():
    """示例 3: 批量操作。

    演示如何批量摄入文档并使用进度回调。
    """
    print("\n" + "="*60)
    print("示例 3: 批量操作")
    print("="*60)

    # 准备测试文档
    test_docs = [
        ("高血压是一种常见的慢性疾病，表现为血压持续升高。", "hypertension_01"),
        ("高血压可能导致心脏病、中风等严重并发症。", "hypertension_02"),
        ("高血压的治疗包括药物治疗和生活方式调整。", "hypertension_03"),
    ]

    def progress_callback(current: int, total: int, doc_id: str):
        """进度回调函数。"""
        print(f"  进度: {current}/{total} - 当前文档: {doc_id}")

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 批量摄入文本
            print("\n批量摄入文档:")
            for i, (text, doc_id) in enumerate(test_docs):
                await client.ingest_text(text, doc_id)
                progress_callback(i + 1, len(test_docs), doc_id)

            await asyncio.sleep(1)

            # 批量查询
            queries = [
                "什么是高血压?",
                "高血压有哪些并发症?",
                "如何治疗高血压?"
            ]

            print("\n批量查询:")
            for query in queries:
                result = await client.query(query)
                print(f"\n  Q: {query}")
                print(f"  A: {result.answer[:100]}...")

            # 显示性能统计
            stats = client.get_stats()
            print(f"\n批量操作统计:")
            print(f"  总查询次数: {stats['total_queries']}")
            print(f"  总文档数: {stats['total_documents']}")
            print(f"  平均延迟: {stats.get('avg_latency_ms', 0)}ms")

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 4: 流式查询 ==========

async def example_streaming_query():
    """示例 4: 流式查询。

    演示如何使用流式查询实时获取答案。
    """
    print("\n" + "="*60)
    print("示例 4: 流式查询")
    print("="*60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            query = "请详细介绍糖尿病的病因和发病机制"
            print(f"\n查询问题: {query}")
            print("\n流式答案:")
            print("-" * 40)

            # 流式查询
            async for chunk in client.query_stream(query, mode="hybrid"):
                print(chunk, end="", flush=True)

            print("\n" + "-" * 40)
            print("\n流式查询完成")

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 5: 配置管理 ==========

async def example_config_management():
    """示例 5: 配置管理。

    演示如何从环境变量和配置文件创建客户端。
    """
    print("\n" + "="*60)
    print("示例 5: 配置管理")
    print("="*60)

    try:
        # 方式 1: 从环境变量创建
        print("\n方式 1: 从环境变量创建客户端")
        client = MedGraphClient.from_env(
            workspace="medical",
            enable_metrics=True
        )

        async with client:
            result = await client.query("测试查询")
            print(f"查询成功: {result.answer[:50]}...")

        # 方式 2: 从配置文件创建（如果存在）
        # 首先创建一个示例配置文件
        config_path = project_root / "examples" / "config_example.json"

        # 检查配置文件是否存在
        if not config_path.exists():
            print(f"\n方式 2: 配置文件不存在，跳过此示例")
            print(f"  可以创建 {config_path} 来测试此功能")
        else:
            print(f"\n方式 2: 从配置文件创建客户端")
            client = MedGraphClient.from_config(
                config_path=str(config_path),
                workspace="medical"
            )

            async with client:
                result = await client.query("测试查询")
                print(f"查询成功: {result.answer[:50]}...")

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 6: 性能监控 ==========

async def example_performance_monitoring():
    """示例 6: 性能监控。

    演示如何使用性能监控功能。
    """
    print("\n" + "="*60)
    print("示例 6: 性能监控")
    print("="*60)

    try:
        # 启用性能监控
        async with MedGraphClient(
            workspace="medical",
            enable_metrics=True
        ) as client:
            # 执行多次查询
            queries = [
                "什么是糖尿病?",
                "什么是高血压?",
                "糖尿病和高血压有什么关系?"
            ]

            print("\n执行多次查询...")
            for query in queries:
                result = await client.query(query)
                print(f"  ✓ {query[:30]}... ({result.latency_ms}ms)")

            # 获取详细统计
            stats = client.get_stats()
            print("\n性能统计详情:")
            print(f"  总查询次数: {stats['total_queries']}")
            print(f"  平均延迟: {stats.get('avg_latency_ms', 0)}ms")
            print(f"  P50 延迟: {stats.get('p50_latency_ms', 0)}ms")
            print(f"  P95 延迟: {stats.get('p95_latency_ms', 0)}ms")
            print(f"  P99 延迟: {stats.get('p99_latency_ms', 0)}ms")
            print(f"  查询分布: {stats.get('queries_by_mode', {})}")
            print(f"  错误次数: {stats.get('errors', 0)}")
            print(f"  错误率: {stats.get('error_rate', 0):.2%}")

            # 获取性能摘要
            summary = client.get_performance_summary()
            print("\n性能摘要:")
            print(summary)

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 7: 图谱管理 ==========

async def example_graph_management():
    """示例 7: 图谱管理。

    演示如何列出、获取和导出图谱。
    """
    print("\n" + "="*60)
    print("示例 7: 图谱管理")
    print("="*60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 列出所有图谱
            print("\n列出所有图谱:")
            graphs = await client.list_graphs()

            if graphs:
                for graph in graphs:
                    print(f"  - {graph.graph_id}")
                    print(f"    实体数: {graph.entity_count}")
                    print(f"    关系数: {graph.relationship_count}")
                    print(f"    文档数: {graph.document_count}")
            else:
                print("  (暂无图谱)")

            # 获取当前图谱详情
            print("\n获取当前图谱详情:")
            try:
                graph_info = await client.get_graph("medical")
                print(f"  图谱 ID: {graph_info.graph_id}")
                print(f"  工作空间: {graph_info.workspace}")
                print(f"  实体数: {graph_info.entity_count}")
                print(f"  关系数: {graph_info.relationship_count}")
            except Exception as e:
                print(f"  获取图谱详情失败: {e}")

            # 导出图谱（可选）
            export_path = project_root / "data" / "medical_graph_export.json"
            export_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"\n导出图谱到: {export_path}")
            await client.export_graph(
                graph_id="medical",
                output_path=str(export_path),
                format="json"
            )
            print("  导出成功")

    except Exception as e:
        print(f"错误: {e}")


# ========== 示例 8: 异常处理 ==========

async def example_error_handling():
    """示例 8: 异常处理。

    演示如何处理各种 SDK 异常。
    """
    print("\n" + "="*60)
    print("示例 8: 异常处理")
    print("="*60)

    # 测试 1: 配置错误
    print("\n测试 1: 配置错误")
    try:
        # 尝试从不存在的配置文件创建客户端
        client = MedGraphClient.from_config("/nonexistent/config.json")
    except ConfigError as e:
        print(f"  捕获到配置错误: {e.message}")
        print(f"  配置文件: {e.config_file}")

    # 测试 2: 查询验证错误
    print("\n测试 2: 查询验证错误")
    try:
        async with MedGraphClient(workspace="medical") as client:
            # 尝试使用空查询
            await client.query("")
    except Exception as e:
        print(f"  捕获到验证错误: {e}")

    # 测试 3: 图谱不存在错误
    print("\n测试 3: 图谱不存在错误")
    try:
        async with MedGraphClient(workspace="medical") as client:
            # 尝试获取不存在的图谱
            await client.get_graph("nonexistent_graph")
    except Exception as e:
        print(f"  捕获到错误: {type(e).__name__}: {e}")

    print("\n所有异常处理测试完成")


# ========== 主函数 ==========

async def main():
    """主函数，运行所有示例。"""
    print("\n" + "="*60)
    print("Medical Graph RAG SDK 客户端验证代码")
    print("="*60)
    print("\n该脚本将演示 SDK 客户端的各种功能。")
    print("请确保：")
    print("  1. Neo4j 和 Milvus 服务正在运行")
    print("  2. 已设置 OPENAI_API_KEY 环境变量")
    print("  3. 已安装所有依赖: pip install -r requirements.txt")

    # 确认是否继续
    try:
        response = input("\n是否继续运行示例？(y/n): ").strip().lower()
        if response != 'y':
            print("已取消运行。")
            return
    except (EOFError, KeyboardInterrupt):
        print("\n已取消运行。")
        return

    # 运行示例
    examples = [
        ("基本查询功能", example_basic_query),
        ("文档摄入", example_document_ingestion),
        ("批量操作", example_batch_operations),
        ("流式查询", example_streaming_query),
        ("配置管理", example_config_management),
        ("性能监控", example_performance_monitoring),
        ("图谱管理", example_graph_management),
        ("异常处理", example_error_handling),
    ]

    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    try:
        choice = input("\n选择要运行的示例 (1-8, 或 'all' 运行所有): ").strip().lower()

        if choice == 'all':
            # 运行所有示例
            for name, example_func in examples:
                try:
                    await example_func()
                except Exception as e:
                    print(f"\n示例 '{name}' 执行失败: {e}")
                    print("继续执行下一个示例...")
        else:
            # 运行选定的示例
            example_num = int(choice)
            if 1 <= example_num <= len(examples):
                name, example_func = examples[example_num - 1]
                print(f"\n运行示例: {name}")
                await example_func()
            else:
                print(f"无效的选择: {choice}")

    except ValueError:
        print("无效的输入")
    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print(f"\n执行失败: {e}")

    print("\n" + "="*60)
    print("验证代码执行完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
