"""
摄入服务快速示例代码。

这是一个可以直接运行的示例，展示 IngestionService 的基本用法。

运行方式：
    source venv/bin/activate
    python examples/ingestion_service_example.py
"""

import asyncio
from pathlib import Path
from src.core.config import Settings
from src.core.adapters import RAGAnythingAdapter
from src.services.ingestion import IngestionService


async def example_basic_usage():
    """基础用法示例"""
    print("=" * 60)
    print("示例 1: 基础用法")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = IngestionService(adapter)

    # 摄入文本
    result = await service.ingest_text(
        "糖尿病是一种代谢性疾病，主要特征是慢性高血糖。",
        doc_id="example-001"
    )

    print(f"✓ 文本摄入成功")
    print(f"  文档 ID: {result.doc_id}")
    print(f"  状态: {result.status}")

    await adapter.close()


async def example_batch_ingestion():
    """批量摄入示例"""
    print("\n" + "=" * 60)
    print("示例 2: 批量摄入")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = IngestionService(adapter)

    # 创建临时测试文件
    test_dir = Path("/tmp/ingestion_example")
    test_dir.mkdir(exist_ok=True)

    test_files = []
    for i, content in enumerate([
        "心脏病是循环系统疾病。",
        "肺炎是呼吸系统感染。",
        "胃炎是消化系统疾病。"
    ], 1):
        test_file = test_dir / f"doc{i}.txt"
        test_file.write_text(content, encoding="utf-8")
        test_files.append(str(test_file))

    # 定义进度回调
    def on_progress(current: int, total: int, doc_id: str):
        print(f"  进度: {current}/{total} ({current/total*100:.0f}%) - {doc_id}")

    # 批量摄入
    batch_result = await service.ingest_batch(
        file_paths=test_files,
        max_concurrency=2,
        progress_callback=on_progress
    )

    print(f"\n✓ 批量摄入完成")
    print(f"  {batch_result}")

    # 清理测试文件
    for file_path in test_files:
        Path(file_path).unlink()
    test_dir.rmdir()

    await adapter.close()


async def example_status_management():
    """状态管理示例"""
    print("\n" + "=" * 60)
    print("示例 3: 状态管理")
    print("=" * 60)

    # 初始化
    config = Settings()
    adapter = RAGAnythingAdapter(config)
    await adapter.initialize()
    service = IngestionService(adapter)

    # 摄入多个文档
    for i in range(3):
        await service.ingest_text(
            f"测试文档 {i+1} 的内容",
            doc_id=f"status-example-{i+1}"
        )

    # 列出所有文档
    all_docs = await service.list_documents()
    print(f"✓ 总文档数: {len(all_docs)}")

    # 按状态过滤
    completed_docs = await service.list_documents(status_filter="completed")
    print(f"✓ 已完成文档: {len(completed_docs)}")

    # 获取统计信息
    stats = service.get_stats()
    print(f"✓ 统计信息:")
    print(f"    总数: {stats['total_cached']}")
    print(f"    成功率: {stats['success_rate']:.1f}%")
    print(f"    按状态: {stats['by_status']}")

    # 清理缓存
    cleared = await service.clear_cache()
    print(f"✓ 清理缓存: {cleared} 个状态")

    await adapter.close()


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("摄入服务示例代码")
    print("=" * 60)

    try:
        await example_basic_usage()
        await example_batch_ingestion()
        await example_status_management()

        print("\n" + "=" * 60)
        print("✓ 所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
