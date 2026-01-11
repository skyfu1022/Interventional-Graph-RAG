"""
图谱导出功能使用示例。

演示如何使用 SDK 客户端导出知识图谱为不同格式。
"""

import asyncio
from pathlib import Path

from src.sdk import MedGraphClient


async def export_graph_example():
    """导出图谱示例。"""
    
    print("=" * 60)
    print("图谱导出功能使用示例")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("./output/graph_exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用 SDK 客户端
    async with MedGraphClient(workspace="medical") as client:
        
        # 获取图谱列表
        print("\n1. 获取图谱列表")
        graphs = await client.list_graphs()
        print(f"找到 {len(graphs)} 个图谱:")
        for graph in graphs:
            print(f"  - {graph.graph_id}: {graph.entity_count} 实体, {graph.relationship_count} 关系")
        
        if not graphs:
            print("\n没有找到图谱。请先摄入一些文档。")
            return
        
        # 使用第一个图谱
        graph_id = graphs[0].graph_id
        print(f"\n使用图谱: {graph_id}")
        
        # 导出为 JSON
        print("\n2. 导出为 JSON 格式")
        json_file = output_dir / f"{graph_id}.json"
        await client.export_graph(graph_id, str(json_file), "json")
        print(f"✓ JSON 文件已保存: {json_file}")
        
        # 导出为 CSV
        print("\n3. 导出为 CSV 格式")
        csv_file = output_dir / f"{graph_id}.csv"
        await client.export_graph(graph_id, str(csv_file), "csv")
        print(f"✓ CSV 文件已保存: {csv_file}")
        
        # 导出为 Mermaid
        print("\n4. 导出为 Mermaid 格式")
        mermaid_file = output_dir / f"{graph_id}.mmd"
        await client.export_graph(graph_id, str(mermaid_file), "mermaid")
        print(f"✓ Mermaid 文件已保存: {mermaid_file}")
        
        print("\n" + "=" * 60)
        print("导出完成！")
        print(f"输出目录: {output_dir.absolute()}")
        print("=" * 60)
        
        # 显示 Mermaid 图表预览
        print("\nMermaid 图表预览:")
        print("-" * 60)
        with open(mermaid_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 显示前 20 行
            for line in lines[:20]:
                print(line.rstrip())
        print("-" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(export_graph_example())
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
