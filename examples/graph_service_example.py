#!/usr/bin/env python3
"""
图谱服务验证代码示例。

该脚本演示如何使用 GraphService 进行：
- 列出所有图谱
- 获取图谱详情
- 导出图谱（JSON、CSV、Mermaid 格式）
- 合并相似节点
- 删除实体和关系

运行方式：
    source venv/bin/activate
    python examples/graph_service_example.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.graph import GraphService


async def main():
    """主函数：演示图谱服务的各项功能。"""

    print("=" * 60)
    print("图谱服务验证示例")
    print("=" * 60)

    # 1. 初始化配置和适配器
    print("\n[步骤 1] 初始化适配器...")
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    print(f"  工作目录: {config.rag_working_dir}")
    print(f"  工作空间: {config.rag_workspace}")

    # 2. 创建图谱服务
    print("\n[步骤 2] 创建图谱服务...")
    service = GraphService(adapter)
    print("  图谱服务创建成功")

    # 3. 列出所有图谱
    print("\n[步骤 3] 列出所有图谱...")
    graphs = await service.list_graphs()
    print(f"  找到 {len(graphs)} 个图谱")

    for i, graph in enumerate(graphs, 1):
        print(f"    [{i}] {graph.graph_id}")
        print(f"        - 工作空间: {graph.workspace}")
        print(f"        - 实体数: {graph.entity_count}")
        print(f"        - 关系数: {graph.relationship_count}")
        print(f"        - 文档数: {graph.document_count}")
        if graph.created_at:
            print(f"        - 创建时间: {graph.created_at}")

    # 4. 获取图谱详情
    if graphs:
        print(f"\n[步骤 4] 获取图谱详情: {graphs[0].graph_id}...")
        info = await service.get_graph_info(graphs[0].graph_id)
        print(f"  图谱 ID: {info.graph_id}")
        print(f"  实体总数: {info.entity_count}")
        print(f"  关系总数: {info.relationship_count}")
        print(f"  文档总数: {info.document_count}")
        print(f"  存储信息: {info.storage_info}")

    # 5. 导出图谱为 JSON 格式
    if graphs:
        print(f"\n[步骤 5] 导出图谱为 JSON 格式: {graphs[0].graph_id}...")
        json_path = f"output/{graphs[0].graph_id}_export.json"
        try:
            await service.export_graph(
                graphs[0].graph_id,
                json_path,
                format="json",
                include_vectors=False
            )
            print(f"  JSON 导出成功: {json_path}")

            # 读取并显示部分内容
            with open(json_path, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
                print(f"  导出数据包含:")
                print(f"    - 元数据: {list(data.get('metadata', {}).keys())}")
                print(f"    - 统计: {list(data.get('statistics', {}).keys())}")
        except Exception as e:
            print(f"  JSON 导出失败: {e}")

    # 6. 导出图谱为 CSV 格式
    if graphs:
        print(f"\n[步骤 6] 导出图谱为 CSV 格式: {graphs[0].graph_id}...")
        csv_path = f"output/{graphs[0].graph_id}_export.csv"
        try:
            await service.export_graph(
                graphs[0].graph_id,
                csv_path,
                format="csv"
            )
            print(f"  CSV 导出成功: {csv_path}")
        except Exception as e:
            print(f"  CSV 导出失败: {e}")

    # 7. 导出图谱为 Mermaid 格式
    if graphs:
        print(f"\n[步骤 7] 导出图谱为 Mermaid 格式: {graphs[0].graph_id}...")
        mermaid_path = f"output/{graphs[0].graph_id}_graph.mmd"
        try:
            await service.export_graph(
                graphs[0].graph_id,
                mermaid_path,
                format="mermaid"
            )
            print(f"  Mermaid 导出成功: {mermaid_path}")
            print("  可以在支持 Mermaid 的 Markdown 查看器中打开")
        except Exception as e:
            print(f"  Mermaid 导出失败: {e}")

    # 8. 合并相似节点（示例）
    print("\n[步骤 8] 合并相似节点（示例）...")
    print("  注意: 实际使用时需要提供真实的实体名称")
    try:
        # 示例：合并相似的疾病实体
        # merged_count = await service.merge_graph_nodes(
        #     graph_id=graphs[0].graph_id,
        #     source_entities=["糖尿病", "糖尿病 mellitus", "DM"],
        #     target_entity="糖尿病",
        #     threshold=0.7
        # )
        # print(f"  合并了 {merged_count} 个节点")
        print("  跳过实际合并（需要真实实体数据）")
    except Exception as e:
        print(f"  节点合并失败: {e}")

    # 9. 删除实体（示例）
    print("\n[步骤 9] 删除实体（示例）...")
    print("  注意: 实际使用时需要提供真实的实体名称")
    try:
        # 示例：删除错误创建的实体
        # await service.delete_entity(
        #     graph_id=graphs[0].graph_id,
        #     entity_name="错误的实体"
        # )
        print("  跳过实际删除（需要真实实体数据）")
    except Exception as e:
        print(f"  实体删除失败: {e}")

    # 10. 删除关系（示例）
    print("\n[步骤 10] 删除关系（示例）...")
    print("  注意: 实际使用时需要提供真实的实体名称")
    try:
        # 示例：删除错误的关系
        # await service.delete_relationship(
        #     graph_id=graphs[0].graph_id,
        #     source_entity="实体A",
        #     target_entity="实体B"
        # )
        print("  跳过实际删除（需要真实实体数据）")
    except Exception as e:
        print(f"  关系删除失败: {e}")

    # 11. 关闭适配器
    print("\n[步骤 11] 关闭适配器...")
    await adapter.close()
    print("  适配器已关闭")

    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)


async def test_graph_filters():
    """测试图谱过滤功能。"""

    print("\n\n" + "=" * 60)
    print("测试图谱过滤功能")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = GraphService(adapter)

    # 测试 1: 按工作空间过滤
    print("\n[测试 1] 按工作空间过滤...")
    graphs = await service.list_graphs(workspace="medical")
    print(f"  找到 {len(graphs)} 个 medical 工作空间的图谱")

    # 测试 2: 按最小实体数过滤
    print("\n[测试 2] 按最小实体数过滤...")
    graphs = await service.list_graphs(min_entity_count=10)
    print(f"  找到 {len(graphs)} 个实体数 >= 10 的图谱")

    # 测试 3: 组合过滤
    print("\n[测试 3] 组合过滤...")
    graphs = await service.list_graphs(
        workspace="medical",
        min_entity_count=5
    )
    print(f"  找到 {len(graphs)} 个满足条件的图谱")

    await adapter.close()
    print("\n过滤测试完成！")


async def test_export_formats():
    """测试各种导出格式。"""

    print("\n\n" + "=" * 60)
    print("测试导出格式")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = GraphService(adapter)

    # 获取第一个图谱
    graphs = await service.list_graphs()
    if not graphs:
        print("没有可用的图谱用于测试")
        return

    graph_id = graphs[0].graph_id

    # 确保输出目录存在
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 测试各种格式
    formats = ["json", "csv", "mermaid"]
    for fmt in formats:
        print(f"\n[测试] 导出为 {fmt.upper()} 格式...")
        output_path = output_dir / f"{graph_id}_test.{fmt}"
        try:
            await service.export_graph(
                graph_id,
                str(output_path),
                format=fmt
            )
            print(f"  成功导出到: {output_path}")

            # 显示文件大小
            file_size = output_path.stat().st_size
            print(f"  文件大小: {file_size:,} 字节")

        except Exception as e:
            print(f"  导出失败: {e}")

    await adapter.close()
    print("\n导出格式测试完成！")


async def test_node_operations():
    """测试节点操作（需要实际数据）。"""

    print("\n\n" + "=" * 60)
    print("测试节点操作")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = GraphService(adapter)

    # 获取第一个图谱
    graphs = await service.list_graphs()
    if not graphs:
        print("没有可用的图谱用于测试")
        return

    graph_id = graphs[0].graph_id

    # 获取图谱信息
    info = await service.get_graph_info(graph_id)
    print(f"\n图谱信息: {graph_id}")
    print(f"  实体数: {info.entity_count}")
    print(f"  关系数: {info.relationship_count}")

    # 注意: 以下操作需要实际的实体数据
    print("\n注意: 以下操作需要提供真实的实体名称")
    print("请在实际使用时取消注释并提供正确的实体名称")

    # 示例 1: 合并节点
    # merged = await service.merge_graph_nodes(
    #     graph_id=graph_id,
    #     source_entities=["实体1", "实体2"],
    #     target_entity="合并后的实体",
    #     threshold=0.7
    # )
    # print(f"合并了 {merged} 个节点")

    # 示例 2: 删除实体
    # await service.delete_entity(graph_id, "要删除的实体")
    # print("实体删除成功")

    # 示例 3: 删除关系
    # await service.delete_relationship(
    #     graph_id,
    #     "源实体",
    #     "目标实体"
    # )
    # print("关系删除成功")

    await adapter.close()
    print("\n节点操作测试完成！")


if __name__ == "__main__":
    # 运行主测试
    asyncio.run(main())

    # 运行额外的测试
    # asyncio.run(test_graph_filters())
    # asyncio.run(test_export_formats())
    # asyncio.run(test_node_operations())
