#!/usr/bin/env python3
"""
Medical Graph RAG 日志系统使用示例

展示如何在项目中使用日志系统
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logging import (
    setup_logging,
    get_logger,
    LoggingConfig,
    set_request_id,
    set_session_id,
    LogContext,
    log_execution_time,
    logger,
)


# 示例 1: 基本日志记录
def example_basic_logging():
    """演示基本的日志记录功能"""
    print("\n=== 示例 1: 基本日志记录 ===")

    logger.debug("这是调试信息 - 通常只在开发时使用")
    logger.info("这是普通信息 - 记录应用的正常运行")
    logger.warning("这是警告信息 - 表示潜在问题")
    logger.error("这是错误信息 - 功能失败但应用仍可运行")
    logger.critical("这是严重错误 - 应用可能无法继续运行")


# 示例 2: 使用命名 Logger
def example_named_logger():
    """演示使用命名 logger 进行模块化日志记录"""
    print("\n=== 示例 2: 使用命名 Logger ===")

    # 为不同模块创建专门的 logger
    user_service_logger = get_logger("user_service")
    user_service_logger.info("用户服务启动")

    graph_service_logger = get_logger("graph_service")
    graph_service_logger.info("图谱服务启动")

    # 带额外上下文的 logger
    auth_logger = get_logger("auth_service", user_id="12345", ip="192.168.1.100")
    auth_logger.info("用户登录成功")


# 示例 3: 请求跟踪
def example_request_tracking():
    """演示请求跟踪功能"""
    print("\n=== 示例 3: 请求跟踪 ===")

    # 模拟处理 API 请求
    request_id = set_request_id("api-req-20230111-001")
    logger.info("收到 API 请求")

    # 处理业务逻辑
    logger.info("处理业务逻辑")
    logger.info("业务逻辑处理完成")

    # 请求结束
    logger.info(f"请求 {request_id} 处理完成")


# 示例 4: 异常处理
def example_exception_logging():
    """演示异常日志记录"""
    print("\n=== 示例 4: 异常处理 ===")

    # 模拟数据处理异常
    try:
        data = {"key": "value"}
        result = data["non_existent_key"]
    except KeyError as e:
        logger.error(f"数据键不存在: {e}")
        logger.exception("详细异常信息:")


# 示例 5: 性能监控
def example_performance_monitoring():
    """演示性能监控装饰器"""
    print("\n=== 示例 5: 性能监控 ===")

    @log_execution_time(level="INFO")
    def process_user_data(user_id: str):
        """处理用户数据（模拟耗时操作）"""
        logger.info(f"开始处理用户 {user_id} 的数据")
        time.sleep(0.2)  # 模拟处理时间
        logger.info(f"用户 {user_id} 的数据处理完成")
        return {"user_id": user_id, "status": "processed"}

    # 执行带性能监控的函数
    result = process_user_data("user-123")
    logger.info(f"处理结果: {result}")


# 示例 6: 日志上下文管理
def example_log_context():
    """演示日志上下文管理器的使用"""
    print("\n=== 示例 6: 日志上下文管理 ===")

    # 主流程
    logger.info("开始主流程")

    # 子流程 1
    with LogContext(request_id="sub-flow-1", session_id="session-abc"):
        logger.info("执行子流程 1")
        logger.info("子流程 1 的业务逻辑")

        # 嵌套子流程
        with LogContext(request_id="nested-flow"):
            logger.info("执行嵌套流程")

    # 子流程 2（恢复主流程的上下文）
    with LogContext(request_id="sub-flow-2"):
        logger.info("执行子流程 2")

    logger.info("返回主流程")


# 示例 7: 自定义配置
def example_custom_config():
    """演示自定义日志配置"""
    print("\n=== 示例 7: 自定义配置 ===")

    # 创建自定义配置
    config = LoggingConfig(
        log_level="DEBUG",
        log_file="example.log",
        log_dir="./example_logs",
        rotation="5 MB",
        retention="7 days",
        compression="zip",
        json_format=False,
        console_level="INFO",
        file_level="DEBUG"
    )

    # 应用配置
    setup_logging(config)
    logger.info("使用自定义配置记录日志")


# 示例 8: 环境变量配置
def example_env_config():
    """演示从环境变量读取配置"""
    print("\n=== 示例 8: 环境变量配置 ===")

    # 从环境变量创建配置
    # 可以通过设置以下环境变量来配置:
    # LOG_LEVEL, LOG_DIR, LOG_FILE, LOG_ROTATION, etc.
    config = LoggingConfig.from_env()

    # 应用配置
    setup_logging(config)
    logger.info("使用环境变量配置记录日志")


# 示例 9: 实际业务场景
@log_execution_time(level="INFO")
def example_business_scenario():
    """演示实际业务场景中的日志使用"""
    print("\n=== 示例 9: 实际业务场景 ===")

    # 创建业务 logger
    business_logger = get_logger("medical_graph_rag", operation="graph_query")

    # 设置请求上下文
    set_request_id("query-req-001")
    set_session_id("user-session-123")

    # 记录请求开始
    business_logger.info("开始处理图谱查询")

    # 模拟查询过程
    try:
        business_logger.debug("连接到 Neo4j 数据库")
        business_logger.debug("构建查询语句")

        # 模拟查询执行
        time.sleep(0.1)

        business_logger.info("查询执行成功")
        business_logger.info("返回查询结果", extra={"result_count": 42})

    except Exception as e:
        business_logger.error(f"查询执行失败: {e}")
        business_logger.exception("详细错误信息:")

    # 记录请求结束
    business_logger.info("图谱查询处理完成")


def main():
    """运行所有示例"""
    print("=" * 70)
    print("Medical Graph RAG 日志系统使用示例")
    print("=" * 70)

    # 初始化日志系统
    setup_logging(
        log_level="INFO",
        log_dir="./example_logs",
        log_file="examples.log"
    )

    logger.info("日志系统初始化完成")

    # 运行各个示例
    example_basic_logging()
    example_named_logger()
    example_request_tracking()
    example_exception_logging()
    example_performance_monitoring()
    example_log_context()
    example_custom_config()
    example_env_config()
    example_business_scenario()

    # 显示日志文件信息
    print("\n" + "=" * 70)
    print("日志文件已创建")
    print("=" * 70)

    log_dir = Path("./example_logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"  ✓ {log_file.name} ({size} bytes)")
            print(f"    路径: {log_file.absolute()}")

    print("\n" + "=" * 70)
    print("所有示例运行完成！")
    print("=" * 70)
    print("\n提示: 查看 ./example_logs 目录中的日志文件")


if __name__ == "__main__":
    main()
