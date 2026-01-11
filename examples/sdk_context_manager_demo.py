"""
SDK 异步上下文管理器验证示例。

该文件演示如何使用 MedGraphClient 的异步上下文管理器功能。
"""

import asyncio
from src.sdk import MedGraphClient, DocumentInfo


async def test_basic_context_manager():
    """测试基本异步上下文管理器功能。"""
    print("=" * 60)
    print("测试 1: 基本异步上下文管理器")
    print("=" * 60)

    # 使用 async with 自动初始化和清理
    async with MedGraphClient(workspace="test_basic") as client:
        print("✓ 客户端已自动初始化")

        # 摄入测试文本
        text = "糖尿病是一种慢性代谢性疾病，主要特征是高血糖。"
        doc_info = await client.ingest_text(text, doc_id="test-doc-001")
        print(f"✓ 文档摄入成功 | ID: {doc_info.doc_id} | 状态: {doc_info.status}")

        # 执行查询
        result = await client.query("什么是糖尿病?", mode="hybrid")
        print(f"✓ 查询成功 | 答案长度: {len(result.answer)} 字符")
        print(f"  答案预览: {result.answer[:100]}...")

    # 退出上下文后自动关闭连接
    print("✓ 客户端已自动关闭")
    print()


async def test_exception_handling():
    """测试异常处理和资源清理。"""
    print("=" * 60)
    print("测试 2: 异常处理和资源清理")
    print("=" * 60)

    try:
        async with MedGraphClient(workspace="test_exception") as client:
            print("✓ 客户端已初始化")

            # 执行正常操作
            text = "高血压是心血管疾病的主要危险因素。"
            await client.ingest_text(text, doc_id="test-doc-002")
            print("✓ 文档摄入成功")

            # 抛出测试异常
            print("✓ 抛出测试异常...")
            raise ValueError("测试异常：验证资源清理")

    except ValueError as e:
        # 异常被正确传播
        print(f"✓ 异常被正确处理: {e}")
        print("✓ 连接已自动关闭（即使发生异常）")

    print()


async def test_nested_context_managers():
    """测试嵌套上下文管理器（多个客户端）。"""
    print("=" * 60)
    print("测试 3: 嵌套上下文管理器（多个客户端）")
    print("=" * 60)

    # 同时使用多个客户端
    async with MedGraphClient(workspace="test_nested_1") as client1:
        print("✓ 客户端 1 已初始化")

        async with MedGraphClient(workspace="test_nested_2") as client2:
            print("✓ 客户端 2 已初始化")

            # 两个客户端都可以正常工作
            text1 = "心脏病是全球主要的死亡原因之一。"
            text2 = "中风是脑血管疾病的一种急性发作。"

            await client1.ingest_text(text1, doc_id="test-doc-003")
            await client2.ingest_text(text2, doc_id="test-doc-004")

            print("✓ 两个客户端同时工作正常")

            result1 = await client1.query("什么是心脏病?")
            result2 = await client2.query("什么是中风?")

            print(f"✓ 客户端 1 查询成功 | 答案长度: {len(result1.answer)}")
            print(f"✓ 客户端 2 查询成功 | 答案长度: {len(result2.answer)}")

        print("✓ 客户端 2 已关闭")
    print("✓ 客户端 1 已关闭")
    print()


async def test_manual_lifecycle():
    """测试手动生命周期管理（不使用上下文管理器）。"""
    print("=" * 60)
    print("测试 4: 手动生命周期管理")
    print("=" * 60)

    # 手动创建和初始化客户端
    client = MedGraphClient(workspace="test_manual")
    print("✓ 客户端已创建")

    # 手动初始化
    await client.initialize()
    print("✓ 客户端已手动初始化")

    # 执行操作
    text = "哮喘是一种慢性呼吸道疾病。"
    await client.ingest_text(text, doc_id="test-doc-005")
    print("✓ 文档摄入成功")

    # 手动关闭
    await client.close()
    print("✓ 客户端已手动关闭")
    print()


async def test_multiple_sequential_uses():
    """测试多次连续使用同一工作空间。"""
    print("=" * 60)
    print("测试 5: 多次连续使用同一工作空间")
    print("=" * 60)

    # 第一次使用
    async with MedGraphClient(workspace="test_sequential") as client:
        text1 = "肺炎是肺部感染性疾病。"
        await client.ingest_text(text1, doc_id="test-doc-006")
        print("✓ 第一次使用完成")

    # 第二次使用（同一工作空间）
    async with MedGraphClient(workspace="test_sequential") as client:
        text2 = "支气管炎是支气管炎症。"
        await client.ingest_text(text2, doc_id="test-doc-007")
        print("✓ 第二次使用完成")

    # 查询两个文档
    async with MedGraphClient(workspace="test_sequential") as client:
        result = await client.query("肺炎和支气管炎有什么区别?")
        print(f"✓ 跨会话查询成功 | 答案长度: {len(result.answer)}")

    print()


async def test_stream_query():
    """测试流式查询功能。"""
    print("=" * 60)
    print("测试 6: 流式查询")
    print("=" * 60)

    async with MedGraphClient(workspace="test_stream") as client:
        # 摄入文档
        text = """
        糖尿病是一种代谢性疾病，其特征是慢性高血糖。
        主要类型包括1型糖尿病、2型糖尿病和妊娠期糖尿病。
        常见症状包括多饮、多尿、多食和体重下降。
        并发症可能涉及心血管、肾脏、视网膜和神经系统。
        """
        await client.ingest_text(text, doc_id="test-doc-008")
        print("✓ 文档摄入成功")

        # 流式查询
        print("✓ 开始流式查询...")
        answer_chunks = []
        async for chunk in client.query_stream(
            "详细说明糖尿病的类型和症状",
            mode="hybrid"
        ):
            answer_chunks.append(chunk)
            print(chunk, end="", flush=True)

        full_answer = "".join(answer_chunks)
        print(f"\n✓ 流式查询完成 | 总长度: {len(full_answer)} 字符")

    print()


async def test_batch_operations():
    """测试批量操作。"""
    print("=" * 60)
    print("测试 7: 批量操作")
    print("=" * 60)

    async with MedGraphClient(workspace="test_batch") as client:
        # 批量摄入文本
        texts = [
            "流感是由流感病毒引起的急性呼吸道传染病。",
            "肺结核是由结核分枝杆菌引起的慢性传染病。",
            "慢性阻塞性肺疾病（COPD）是一种常见的慢性呼吸系统疾病。",
        ]

        doc_infos = await client.ingest_batch(texts)
        print(f"✓ 批量摄入成功 | 文档数: {len(doc_infos)}")

        # 批量查询（使用列表推导式）
        queries = [
            "什么是流感?",
            "什么是肺结核?",
            "什么是 COPD?",
        ]

        results = []
        for query in queries:
            result = await client.query(query, mode="hybrid")
            results.append(result)

        print(f"✓ 批量查询完成 | 查询数: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"  查询 {i}: {len(result.answer)} 字符")

    print()


async def test_convenience_methods():
    """测试便捷方法。"""
    print("=" * 60)
    print("测试 8: 便捷方法")
    print("=" * 60)

    async with MedGraphClient(workspace="test_convenience") as client:
        # 使用 ingest_and_query 便捷方法
        text = """
        阿司匹林是一种非甾体抗炎药，具有镇痛、退热和抗炎作用。
        常用于缓解疼痛、降低发热和预防心血管疾病。
        """
        result = await client.ingest_and_query(
            text,
            "阿司匹林有哪些作用?"
        )

        print(f"✓ 便捷方法执行成功 | 答案长度: {len(result.answer)}")
        print(f"  答案预览: {result.answer[:100]}...")

    print()


async def main():
    """运行所有测试。"""
    print("\n" + "=" * 60)
    print("SDK 异步上下文管理器验证测试")
    print("=" * 60 + "\n")

    try:
        # 运行所有测试
        await test_basic_context_manager()
        await test_exception_handling()
        await test_nested_context_managers()
        await test_manual_lifecycle()
        await test_multiple_sequential_uses()
        await test_stream_query()
        await test_batch_operations()
        await test_convenience_methods()

        print("=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
