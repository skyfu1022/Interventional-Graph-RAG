"""
SDK 异常使用示例。

展示如何在 Medical Graph RAG SDK 中使用异常类。
"""

import asyncio
from src.sdk import (
    MedGraphClient,
    MedGraphSDKError,
    ConfigError,
    DocumentNotFoundError,
    ConnectionError,
    ValidationError,
    QueryTimeoutError,
    RateLimitError,
)


async def example_config_error():
    """示例：配置错误处理。"""
    print("=" * 60)
    print("示例 1: 配置错误")
    print("=" * 60)

    try:
        # 尝试使用无效配置创建客户端
        client = MedGraphClient(
            workspace="medical",
            neo4j_uri="bolt://invalid:7687",
            neo4j_user="neo4j",
            neo4j_password="",  # 空密码
        )
        await client.initialize()
    except ConfigError as e:
        print(f"捕获配置错误: {e}")
        print(f"配置键: {e.config_key}")
        print(f"详情: {e.to_dict()}")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_document_not_found():
    """示例：文档未找到错误处理。"""
    print("=" * 60)
    print("示例 2: 文档未找到")
    print("=" * 60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 尝试获取不存在的文档
            doc_info = await client.get_document("non-existent-doc-id")
            print(f"文档: {doc_info}")
    except DocumentNotFoundError as e:
        print(f"捕获文档未找到错误: {e}")
        print(f"文档 ID: {e.doc_id}")
        print("建议: 请检查文档 ID 是否正确")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_validation_error():
    """示例：验证错误处理。"""
    print("=" * 60)
    print("示例 3: 验证错误")
    print("=" * 60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 使用无效的查询模式
            result = await client.query(
                "测试查询",
                mode="invalid_mode",  # 无效的模式
            )
            print(f"结果: {result}")
    except ValidationError as e:
        print(f"捕获验证错误: {e}")
        print(f"字段: {e.field}")
        print(f"值: {e.value}")
        print(f"约束: {e.constraint}")
        print("建议: 请使用有效的查询模式")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_connection_error():
    """示例：连接错误处理。"""
    print("=" * 60)
    print("示例 4: 连接错误")
    print("=" * 60)

    try:
        # 尝试连接到不可用的服务
        client = MedGraphClient(
            workspace="medical",
            neo4j_uri="bolt://unavailable:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        await client.initialize()
    except ConnectionError as e:
        print(f"捕获连接错误: {e}")
        print(f"服务: {e.service}")
        print(f"脱敏 URI: {e.details.get('uri', 'N/A')}")
        print("建议: 请检查服务是否运行")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_query_timeout():
    """示例：查询超时处理。"""
    print("=" * 60)
    print("示例 5: 查询超时")
    print("=" * 60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 执行可能超时的查询
            result = await client.query(
                "非常复杂的查询...",
                timeout=0.001,  # 极短超时
            )
            print(f"结果: {result}")
    except QueryTimeoutError as e:
        print(f"捕获查询超时错误: {e}")
        print(f"超时时间: {e.timeout_seconds} 秒")
        print(f"查询: {e.query}")
        print("建议: 请简化查询或增加超时时间")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_rate_limit():
    """示例：速率限制处理。"""
    print("=" * 60)
    print("示例 6: 速率限制")
    print("=" * 60)

    try:
        async with MedGraphClient(workspace="medical") as client:
            # 模拟频繁请求
            for i in range(1000):
                result = await client.query(f"查询 {i}")  # noqa: F841 - 示例代码，保留用于演示
                print(f"查询 {i}: 完成")
    except RateLimitError as e:
        print(f"捕获速率限制错误: {e}")
        print(f"限制: {e.limit} 次")
        print(f"时间窗口: {e.window} 秒")
        print(f"重试等待: {e.retry_after} 秒")
        print(f"建议: 请降低请求频率或等待 {e.retry_after} 秒后重试")
    except MedGraphSDKError as e:
        print(f"捕获通用 SDK 错误: {e}")
    print()


async def example_comprehensive_error_handling():
    """示例：综合错误处理。"""
    print("=" * 60)
    print("示例 7: 综合错误处理")
    print("=" * 60)

    async def safe_query(client: MedGraphClient, query_text: str) -> dict:
        """安全的查询函数，包含完整的错误处理。"""
        try:
            result = await client.query(query_text)
            return {
                "success": True,
                "answer": result.answer,
                "mode": result.mode,
            }
        except ValidationError as e:
            return {
                "success": False,
                "error_type": "validation",
                "message": str(e),
                "field": e.field,
                "suggestion": f"请检查字段 {e.field} 的值",
            }
        except QueryTimeoutError as e:
            return {
                "success": False,
                "error_type": "timeout",
                "message": str(e),
                "timeout": e.timeout_seconds,
                "suggestion": "请简化查询或增加超时时间",
            }
        except RateLimitError as e:
            return {
                "success": False,
                "error_type": "rate_limit",
                "message": str(e),
                "retry_after": e.retry_after,
                "suggestion": f"请等待 {e.retry_after} 秒后重试",
            }
        except MedGraphSDKError as e:
            return {
                "success": False,
                "error_type": "unknown",
                "message": str(e),
                "error_code": e.error_code,
                "suggestion": "请查看日志了解详情",
            }

    # 使用安全查询函数
    async with MedGraphClient(workspace="medical") as client:
        result = await safe_query(client, "什么是糖尿病?")
        print(f"查询结果: {result}")
    print()


async def example_api_response_format():
    """示例：API 响应格式。"""
    print("=" * 60)
    print("示例 8: API 响应格式")
    print("=" * 60)

    # 模拟 API 错误响应
    def handle_api_error(error: MedGraphSDKError) -> dict:
        """将 SDK 异常转换为 API 响应格式。"""
        return {"success": False, "error": error.to_dict()}

    # 测试各种异常的 API 响应格式
    errors = [
        ConfigError("API Key 未配置", config_key="openai_api_key"),
        DocumentNotFoundError("文档不存在", doc_id="doc-123"),
        ValidationError("查询模式无效", field="mode", value="invalid"),
        QueryTimeoutError("查询超时", timeout_seconds=30.0),
        RateLimitError("超出速率限制", limit=100, window=60, retry_after=30),
    ]

    for err in errors:
        response = handle_api_error(err)
        print(f"{err.__class__.__name__}:")
        print(f"  {response}")
        print()


async def main():
    """运行所有示例。"""
    print("\n" + "=" * 60)
    print("SDK 异常使用示例")
    print("=" * 60 + "\n")

    # 注意：这些示例需要实际的服务才能运行
    # 这里仅展示代码结构

    print("示例代码已准备好，但需要实际的服务才能运行。")
    print("\n以下是异常使用模式的说明：\n")

    print("1. 配置错误 (ConfigError):")
    print("   - 当 SDK 配置缺失或无效时抛出")
    print("   - 包含 config_key 和 config_file 信息")
    print()

    print("2. 文档未找到 (DocumentNotFoundError):")
    print("   - 当尝试访问不存在的文档时抛出")
    print("   - 包含 doc_id 信息")
    print()

    print("3. 验证错误 (ValidationError):")
    print("   - 当输入数据不符合要求时抛出")
    print("   - 包含 field、value 和 constraint 信息")
    print()

    print("4. 连接错误 (ConnectionError):")
    print("   - 当无法连接到服务时抛出")
    print("   - 自动脱敏 URI 中的密码")
    print()

    print("5. 查询超时 (QueryTimeoutError):")
    print("   - 当查询执行时间超过限制时抛出")
    print("   - 包含 timeout_seconds 和 query 信息")
    print()

    print("6. 速率限制 (RateLimitError):")
    print("   - 当请求超过 API 速率限制时抛出")
    print("   - 包含 limit、window 和 retry_after 信息")
    print()

    print("7. 统一错误处理:")
    print("   - 所有异常都继承自 MedGraphSDKError")
    print("   - 可以使用基类捕获所有 SDK 异常")
    print("   - 每个异常都提供 to_dict() 方法用于 API 响应")
    print()


if __name__ == "__main__":
    asyncio.run(main())
