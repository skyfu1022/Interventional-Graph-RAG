"""
SDK 类型定义使用示例。

该脚本展示了如何使用 SDK 中的各种类型定义。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.sdk.types import (
    QueryMode,
    QueryResult,
    DocumentInfo,
    GraphInfo,
    GraphConfig,
    SourceInfo,
    GraphContext,
)


def example_1_basic_types():
    """示例 1: 基本类型使用。"""
    print("=" * 60)
    print("示例 1: 基本类型使用")
    print("=" * 60)

    # 创建查询模式枚举
    mode = QueryMode.HYBRID
    print(f"查询模式: {mode.value}")

    # 创建来源信息
    source = SourceInfo(
        doc_id="doc_123",
        chunk_id="chunk_456",
        content="糖尿病是一种代谢疾病...",
        relevance=0.92,
    )
    print(f"来源信息: {source.doc_id}, 相关性: {source.relevance}")

    # 创建图谱上下文
    context = GraphContext(
        entities=["糖尿病", "胰岛素", "血糖"],
        relationships=["糖尿病-需要-胰岛素治疗"],
        communities=["内分泌疾病"],
    )
    print(f"图谱上下文: {len(context.entities)} 个实体")

    print()


def example_2_query_result():
    """示例 2: 创建查询结果。"""
    print("=" * 60)
    print("示例 2: 创建查询结果")
    print("=" * 60)

    # 创建完整的查询结果
    result = QueryResult(
        query="糖尿病的主要症状是什么?",
        answer="糖尿病的主要症状包括: 1) 多饮(过度口渴) 2) 多尿(频繁排尿) "
        "3) 多食(过度饥饿) 4) 体重下降 5) 疲劳乏力...",
        mode=QueryMode.HYBRID,
        graph_id="medical_graph_v1",
        latency_ms=245,
        retrieval_count=8,
        sources=[
            SourceInfo(
                doc_id="diabetes_guide.pdf",
                chunk_id="page_5_para_2",
                content="糖尿病的临床表现...",
                relevance=0.95,
            ),
            SourceInfo(
                doc_id="medical_textbook_ch12.pdf",
                chunk_id="section_3_1",
                content="症状学分析...",
                relevance=0.88,
            ),
        ],
        context=["糖尿病是代谢紊乱疾病", "影响血糖调节"],
        graph_context=GraphContext(
            entities=["糖尿病", "症状", "血糖", "胰岛素"],
            relationships=["糖尿病-具有-症状", "胰岛素-调节-血糖"],
            communities=["内分泌系统疾病"],
        ),
    )

    print(f"查询: {result.query}")
    print(f"模式: {result.mode.value}")
    print(f"延迟: {result.latency_ms}ms")
    print(f"来源数量: {len(result.sources)}")
    print(f"实体数量: {len(result.graph_context.entities)}")

    # 序列化
    json_str = result.to_json()
    print(f"\nJSON 输出（前 200 字符）:\n{json_str[:200]}...")

    print()


def example_3_document_info():
    """示例 3: 文档信息管理。"""
    print("=" * 60)
    print("示例 3: 文档信息管理")
    print("=" * 60)

    # 创建文档信息
    doc = DocumentInfo(
        doc_id="doc_20240111_001",
        file_name="糖尿病诊疗指南.pdf",
        file_path="/data/medical/guidelines/糖尿病诊疗指南.pdf",
        status="completed",
        entity_count=156,
        relationship_count=243,
        created_at="2026-01-11T10:30:00Z",
        updated_at="2026-01-11T11:45:00Z",
    )

    print(f"文档 ID: {doc.doc_id}")
    print(f"文件名: {doc.file_name}")
    print(f"状态: {doc.status}")
    print(f"提取统计: {doc.entity_count} 个实体, {doc.relationship_count} 个关系")

    # 状态转换示例
    processing_doc = doc.model_copy(update={"status": "processing"})
    print(f"\n状态更新: {doc.status} -> {processing_doc.status}")

    print()


def example_4_graph_info():
    """示例 4: 图谱信息统计。"""
    print("=" * 60)
    print("示例 4: 图谱信息统计")
    print("=" * 60)

    # 创建图谱信息
    graph = GraphInfo(
        graph_id="medical_diabetes_v2",
        workspace="diabetes_research",
        entity_count=5420,
        relationship_count=12800,
        document_count=145,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-11T12:00:00Z",
    )

    print(f"图谱 ID: {graph.graph_id}")
    print(f"工作空间: {graph.workspace}")
    print(f"统计信息:")
    print(f"  - 实体: {graph.entity_count:,}")
    print(f"  - 关系: {graph.relationship_count:,}")
    print(f"  - 文档: {graph.document_count:,}")
    print(f"  - 平均关系/实体: {graph.relationship_count / graph.entity_count:.2f}")

    print()


def example_5_graph_config():
    """示例 5: 图谱配置管理。"""
    print("=" * 60)
    print("示例 5: 图谱配置管理")
    print("=" * 60)

    # 使用默认配置
    default_config = GraphConfig()
    print("默认配置:")
    print(f"  - 工作空间: {default_config.workspace}")
    print(f"  - 块大小: {default_config.chunk_size}")
    print(f"  - 重叠: {default_config.overlap}")
    print(f"  - 实体类型: {', '.join(default_config.entity_types[:3])}...")

    # 自定义配置
    custom_config = GraphConfig(
        workspace="cardiology",
        chunk_size=1024,
        overlap=100,
        entity_types=["DISEASE", "MEDICINE", "PROCEDURE", "SYMPTOM"],
    )
    print("\n自定义配置:")
    print(f"  - 工作空间: {custom_config.workspace}")
    print(f"  - 块大小: {custom_config.chunk_size}")
    print(f"  - 重叠: {custom_config.overlap}")
    print(f"  - 实体类型: {', '.join(custom_config.entity_types)}")

    # 小写输入自动转大写
    lowercase_config = GraphConfig(entity_types=["disease", "medicine"])
    print(f"\n小写自动转大写: {lowercase_config.entity_types}")

    print()


def example_6_serialization():
    """示例 6: 序列化和反序列化。"""
    print("=" * 60)
    print("示例 6: 序列化和反序列化")
    print("=" * 60)

    # 创建对象
    result = QueryResult(
        query="高血压的治疗方法",
        answer="高血压的治疗包括生活方式调整和药物治疗...",
        mode=QueryMode.LOCAL,
        graph_id="cardio_v1",
    )

    # 序列化为字典
    data_dict = result.to_dict()
    print(f"序列化为字典: {len(data_dict)} 个字段")

    # 序列化为 JSON
    json_str = result.to_json()
    print(f"序列化为 JSON: {len(json_str)} 字符")

    # 从字典反序列化
    restored = QueryResult.from_dict(data_dict)
    print(f"从字典恢复: {restored.query}")

    # 验证数据一致性
    print(f"数据一致性: {restored == result}")

    print()


def example_7_validation():
    """示例 7: 数据验证。"""
    print("=" * 60)
    print("示例 7: 数据验证")
    print("=" * 60)

    from pydantic import ValidationError

    # 有效数据
    valid_source = SourceInfo(
        doc_id="doc_001",
        chunk_id="chunk_001",
        content="有效内容",
        relevance=0.85,  # 在 [0, 1] 范围内
    )
    print(f"✓ 有效的 SourceInfo 创建成功")

    # 无效数据 - 相关性超出范围
    print("\n测试无效数据:")
    try:
        invalid_source = SourceInfo(
            doc_id="doc_001",
            chunk_id="chunk_001",
            content="内容",
            relevance=1.5,  # 超出 [0, 1] 范围
        )
        print("✗ 应该抛出 ValidationError")
    except ValidationError as e:
        print(f"✓ 相关性验证: 正确拒绝超出范围的值")

    # 无效数据 - 空的实体类型列表
    try:
        invalid_config = GraphConfig(entity_types=[])
        print("✗ 应该抛出 ValidationError")
    except ValidationError as e:
        print(f"✓ 实体类型验证: 正确拒绝空列表")

    print()


def example_8_nested_operations():
    """示例 8: 嵌套对象操作。"""
    print("=" * 60)
    print("示例 8: 嵌套对象操作")
    print("=" * 60)

    # 创建包含嵌套对象的查询结果
    result = QueryResult(
        query="心脏病和糖尿病的关系",
        answer="心脏病和糖尿病之间存在密切的相互关系...",
        mode=QueryMode.GLOBAL,
        graph_id="medical_v1",
        sources=[
            SourceInfo(
                doc_id="cardio_diabetes_relation.pdf",
                chunk_id="section_2",
                content="研究表明糖尿病患者患心脏病的风险显著增加...",
                relevance=0.94,
            ),
            SourceInfo(
                doc_id="metabolic_syndrome.pdf",
                chunk_id="chapter_5",
                content="代谢综合征包含多种心血管危险因素...",
                relevance=0.89,
            ),
        ],
        graph_context=GraphContext(
            entities=["心脏病", "糖尿病", "代谢综合征", "胰岛素抵抗"],
            relationships=[
                "糖尿病-增加-心脏病风险",
                "胰岛素抵抗-导致-动脉粥样硬化",
            ],
            communities=["代谢性疾病", "心血管疾病"],
        ),
    )

    # 访问嵌套对象
    print(f"查询结果包含:")
    print(f"  - {len(result.sources)} 个来源")
    print(f"  - {len(result.graph_context.entities)} 个实体")
    print(f"  - {len(result.graph_context.relationships)} 个关系")

    # 遍历来源
    print(f"\n来源列表:")
    for i, source in enumerate(result.sources, 1):
        print(f"  {i}. {source.doc_id} (相关性: {source.relevance:.2f})")

    # 遍历实体
    print(f"\n实体列表:")
    for entity in result.graph_context.entities:
        print(f"  - {entity}")

    print()


def main():
    """运行所有示例。"""
    print("\n" + "=" * 60)
    print("SDK 类型定义使用示例")
    print("=" * 60 + "\n")

    example_1_basic_types()
    example_2_query_result()
    example_3_document_info()
    example_4_graph_info()
    example_5_graph_config()
    example_6_serialization()
    example_7_validation()
    example_8_nested_operations()

    print("=" * 60)
    print("✓ 所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
