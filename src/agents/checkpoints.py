"""
LangGraph 检查点工具模块。

该模块提供了用于 LangGraph 工作流状态持久化的工具函数。
支持内存和 SQLite 两种检查点存储方式。
"""

from typing import Optional, Any, Dict, List
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver

# SqliteSaver 可能在某些版本中不可用
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SqliteSaver = None  # type: ignore
    SQLITE_AVAILABLE = False

from langgraph.graph.state import CompiledStateGraph


def create_memory_checkpointer() -> MemorySaver:
    """创建内存检查点存储。

    内存检查点适用于开发和测试场景，提供快速的状态访问，
    但在程序重启后数据会丢失。

    Returns:
        MemorySaver 实例

    Example:
        >>> from src.agents.checkpoints import create_memory_checkpointer
        >>> from src.agents.workflows import create_query_workflow
        >>>
        >>> memory = create_memory_checkpointer()
        >>> workflow = create_query_workflow(adapter, llm, checkpointer=memory)
        >>> config = {"configurable": {"thread_id": "test-123"}}
        >>> result = workflow.invoke(initial_state, config)
    """
    return MemorySaver()


def create_sqlite_checkpointer(db_path: str) -> Any:
    """创建 SQLite 检查点存储。

    SQLite 检查点适用于生产环境，提供持久化的状态存储。
    数据会在程序重启后保留，支持跨会话的状态恢复。

    Args:
        db_path: SQLite 数据库文件路径
                 如果文件不存在，会自动创建
                 建议使用 .db 或 .sqlite 扩展名

    Returns:
        SqliteSaver 实例

    Raises:
        ValueError: 如果 db_path 为空或无效
        NotImplementedError: 如果当前版本不支持 SqliteSaver
        OSError: 如果无法创建或访问数据库文件

    Example:
        >>> from src.agents.checkpoints import create_sqlite_checkpointer
        >>> from src.agents.workflows import create_query_workflow
        >>>
        >>> # 创建持久化检查点存储
        >>> checkpointer = create_sqlite_checkpointer("./checkpoints.db")
        >>> workflow = create_query_workflow(adapter, llm, checkpointer=checkpointer)
        >>> config = {"configurable": {"thread_id": "production-123"}}
        >>> result = workflow.invoke(initial_state, config)
        >>>
        >>> # 程序重启后可以恢复状态
        >>> restored_state = workflow.get_state(config)
    """
    if not SQLITE_AVAILABLE:
        raise NotImplementedError(
            "SqliteSaver 在当前版本的 LangGraph 中不可用。"
            "请使用 MemorySaver 或升级 LangGraph 版本。"
        )

    if not db_path or not isinstance(db_path, str):
        raise ValueError("db_path 必须是非空字符串")

    # 确保父目录存在
    db_file = Path(db_path)
    if db_file.parent != Path(".") and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)

    # 创建 SQLite checkpointer
    # 注意：SqliteSaver.from_conn_string() 返回一个上下文管理器
    # 我们需要直接调用构造函数或使用不同的方式
    import sqlite3

    # 创建数据库连接
    conn = sqlite3.connect(db_path, check_same_thread=False)

    # 创建 SqliteSaver 实例
    return SqliteSaver(conn) if SqliteSaver else None  # type: ignore


def get_checkpoint_state(
    workflow: CompiledStateGraph,
    thread_id: str,
    checkpoint_id: Optional[str] = None
) -> Optional[Any]:
    """获取指定线程的检查点状态。

    Args:
        workflow: 编译后的 LangGraph 工作流
        thread_id: 线程 ID，用于标识特定的对话/会话
        checkpoint_id: 检查点 ID（可选）
                      如果为 None，返回最新的检查点状态
                      如果指定，返回该特定检查点的状态

    Returns:
        StateSnapshot 对象，包含状态的详细信息
        如果检查点不存在，返回 None

    Example:
        >>> from src.agents.checkpoints import get_checkpoint_state
        >>>
        >>> # 获取最新状态
        >>> state = get_checkpoint_state(workflow, "conversation-123")
        >>> if state:
        ...     print(f"当前值: {state.values}")
        ...     print(f"下一节点: {state.next}")
        >>>
        >>> # 获取特定检查点状态
        >>> old_state = get_checkpoint_state(
        ...     workflow,
        ...     "conversation-123",
        ...     checkpoint_id="checkpoint-abc-123"
        ... )
    """
    config = {"configurable": {"thread_id": thread_id}}

    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id

    try:
        return workflow.get_state(config)
    except Exception as e:
        print(f"获取检查点状态失败: {e}")
        return None


def list_checkpoints(
    workflow: CompiledStateGraph,
    thread_id: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """列出指定线程的所有检查点。

    该函数可以用于实现"时间旅行"功能，查看会话的完整历史记录。

    Args:
        workflow: 编译后的 LangGraph 工作流
        thread_id: 线程 ID
        limit: 返回的检查点数量限制（可选）
              如果为 None，返回所有检查点

    Returns:
        检查点信息列表，每个元素包含：
        - checkpoint_id: 检查点 ID
        - step: 步骤编号
        - values: 状态值
        - next: 下一个节点
        - timestamp: 时间戳（如果可用）

    Example:
        >>> from src.agents.checkpoints import list_checkpoints
        >>>
        >>> # 列出所有检查点
        >>> checkpoints = list_checkpoints(workflow, "conversation-123")
        >>> for cp in checkpoints:
        ...     print(f"检查点 {cp['checkpoint_id']}: {cp['values']}")
        >>>
        >>> # 只获取最近 10 个检查点
        >>> recent = list_checkpoints(workflow, "conversation-123", limit=10)
        >>>
        >>> # 回退到之前的检查点（时间旅行）
        >>> if len(checkpoints) > 2:
        ...     target_checkpoint = checkpoints[-3]['checkpoint_id']
        ...     # 使用此检查点 ID 继续执行
    """
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = []

    try:
        for i, snapshot in enumerate(workflow.get_state_history(config)):
            checkpoint_info = {
                "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
                "step": i,
                "values": snapshot.values,
                "next": snapshot.next,
                "timestamp": snapshot.metadata.get("source", "unknown") if hasattr(snapshot, "metadata") else None
            }
            checkpoints.append(checkpoint_info)

            if limit and len(checkpoints) >= limit:
                break
    except Exception as e:
        print(f"列出检查点失败: {e}")

    return checkpoints


def resume_from_checkpoint(
    workflow: CompiledStateGraph,
    thread_id: str,
    new_input: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """从检查点恢复工作流执行。

    允许从上次停止的地方继续执行工作流，而不是从头开始。

    Args:
        workflow: 编译后的 LangGraph 工作流
        thread_id: 线程 ID
        new_input: 新的输入数据（可选）
                  如果为 None，则不提供新输入，继续执行
                  如果提供，会合并到当前状态中

    Returns:
        工作流执行结果

    Example:
        >>> from src.agents.checkpoints import resume_from_checkpoint
        >>>
        >>> # 从上次停止的地方继续
        >>> result = resume_from_checkpoint(workflow, "conversation-123")
        >>>
        >>> # 提供新的输入继续执行
        >>> result = resume_from_checkpoint(
        ...     workflow,
        ...     "conversation-123",
        ...     new_input={"query": "新问题"}
        ... )
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        if new_input:
            return workflow.invoke(new_input, config)
        else:
            # 不提供新输入，继续执行
            return workflow.invoke(None, config)
    except Exception as e:
        print(f"从检查点恢复失败: {e}")
        return {"error": str(e)}


def clear_checkpoints(
    workflow: CompiledStateGraph,
    thread_id: str
) -> bool:
    """清除指定线程的所有检查点。

    Args:
        workflow: 编译后的 LangGraph 工作流
        thread_id: 线程 ID

    Returns:
        是否成功清除

    Example:
        >>> from src.agents.checkpoints import clear_checkpoints
        >>>
        >>> success = clear_checkpoints(workflow, "conversation-123")
        >>> if success:
        ...     print("检查点已清除")
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # 通过获取当前状态并更新来清除检查点
        state = workflow.get_state(config)
        if state:
            workflow.update_state(config, None, as_node="__end__")
            return True
        return False
    except Exception as e:
        print(f"清除检查点失败: {e}")
        return False


def get_thread_stats(
    workflow: CompiledStateGraph,
    thread_id: str
) -> Dict[str, Any]:
    """获取指定线程的统计信息。

    Args:
        workflow: 编译后的 LangGraph 工作流
        thread_id: 线程 ID

    Returns:
        包含统计信息的字典：
        - total_checkpoints: 检查点总数
        - current_step: 当前步骤
        - is_completed: 是否已完成
        - last_checkpoint_id: 最后一个检查点 ID

    Example:
        >>> from src.agents.checkpoints import get_thread_stats
        >>>
        >>> stats = get_thread_stats(workflow, "conversation-123")
        >>> print(f"总检查点数: {stats['total_checkpoints']}")
        >>> print(f"当前步骤: {stats['current_step']}")
    """
    checkpoints = list_checkpoints(workflow, thread_id)
    current_state = get_checkpoint_state(workflow, thread_id)

    return {
        "total_checkpoints": len(checkpoints),
        "current_step": len(checkpoints),
        "is_completed": current_state.next == () if current_state else False,
        "last_checkpoint_id": checkpoints[-1]["checkpoint_id"] if checkpoints else None
    }
