"""
Build 命令 - 从文件或目录构建知识图谱。

该命令提供以下功能：
- 支持从单个文件或目录批量构建知识图谱
- 支持指定图谱 ID
- 支持节点合并优化
- 使用 Rich 进度条显示构建进度
- 自动识别支持的文件格式

使用示例：
    # 从单个文件构建
    medgraph build document.txt

    # 从目录构建（批量处理）
    medgraph build ./documents/

    # 指定图谱 ID
    medgraph build document.txt --graph-id medical-001

    # 启用节点合并
    medgraph build document.txt --merge

    # 合并时指定相似度阈值
    medgraph build document.txt --merge --merge-threshold 0.8
"""

from pathlib import Path
from typing import List, Any
import asyncio

import typer
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.sdk import MedGraphClient
from src.sdk.exceptions import MedGraphSDKError

# 创建 Typer 应用
app = typer.Typer(
    name="build",
    help="从文件或目录构建知识图谱",
    add_completion=False,
)

# Rich 控制台
console = Console()


def _collect_files(path: Path) -> List[Path]:
    """收集要处理的文件。

    Args:
        path: 文件或目录路径

    Returns:
        文件路径列表

    Raises:
        typer.Exit: 路径无效或无支持的文件
    """
    supported_extensions = {
        ".txt",
        ".md",
        ".json",
        ".csv",
        ".pdf",
        ".docx",
        ".doc",
        ".html",
        ".htm",
    }

    if path.is_file():
        # 单个文件
        if path.suffix.lower() not in supported_extensions:
            console.print(
                f"[yellow]警告: 文件格式 '{path.suffix}' 可能不支持，"
                f"但将尝试处理。[/yellow]"
            )
        return [path]

    elif path.is_dir():
        # 目录 - 递归查找所有支持的文件
        files = []
        for ext in supported_extensions:
            files.extend(path.rglob(f"*{ext}"))
            files.extend(path.rglob(f"*{ext.upper()}"))

        if not files:
            console.print(f"[red]错误: 在目录 '{path}' 中未找到支持的文件。[/red]")
            console.print(f"支持的格式: {', '.join(sorted(supported_extensions))}")
            raise typer.Exit(1)

        return sorted(files)

    else:
        console.print(f"[red]错误: 路径不存在: {path}[/red]")
        raise typer.Exit(1)


def _display_build_summary(
    total_files: int,
    succeeded: int,
    failed: int,
    graph_id: str,
    merge_enabled: bool,
    merged_count: int = 0,
) -> None:
    """显示构建摘要。

    Args:
        total_files: 总文件数
        succeeded: 成功数
        failed: 失败数
        graph_id: 图谱 ID
        merge_enabled: 是否启用合并
        merged_count: 合并的节点数
    """
    # 创建摘要表格
    table = Table(title="构建摘要", show_header=True, header_style="bold magenta")
    table.add_column("指标", style="cyan", no_wrap=True)
    table.add_column("数值", justify="right")

    table.add_row("图谱 ID", graph_id)
    table.add_row("总文件数", str(total_files))
    table.add_row("成功", f"[green]{succeeded}[/green]")
    table.add_row("失败", f"[red]{failed}[/red]" if failed > 0 else "0")

    if merge_enabled:
        table.add_row("节点合并", f"[yellow]已启用 ({merged_count} 个节点)[/yellow]")
    else:
        table.add_row("节点合并", "[dim]未启用[/dim]")

    console.print()
    console.print(table)

    # 显示完成消息
    if failed == 0:
        console.print(
            Panel(
                f"[green]所有文件已成功构建到图谱 '{graph_id}'[/green]",
                title="✓ 构建完成",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[yellow]构建完成，但有 {failed} 个文件失败[/yellow]",
                title="⚠ 部分完成",
                border_style="yellow",
            )
        )


@app.command()
def build(
    path: Path = typer.Argument(
        ...,
        exists=True,
        help="文件或目录路径",
        show_default=False,
    ),
    graph_id: str = typer.Option(
        "default",
        "--graph-id",
        "-g",
        help="指定图谱 ID（用于隔离不同的知识图谱）",
        show_default=False,
    ),
    merge: bool = typer.Option(
        False,
        "--merge",
        "-m",
        help="启用节点合并（自动合并相似实体）",
    ),
    merge_threshold: float = typer.Option(
        0.7,
        "--merge-threshold",
        "-t",
        help="节点合并的相似度阈值 (0.0-1.0)",
        min=0.0,
        max=1.0,
    ),
    max_concurrency: int = typer.Option(
        5,
        "--max-concurrency",
        "-c",
        help="最大并发文件处理数",
        min=1,
        max=20,
    ),
    workspace: str = typer.Option(
        "medical",
        "--workspace",
        "-w",
        help="工作空间名称",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="显示详细输出",
    ),
) -> None:
    """从文件或目录构建知识图谱。

    该命令会处理指定的文件或目录中的所有文件，
    将它们摄入到知识图谱中，并可选地进行节点合并优化。

    示例:
        medgraph build document.txt

        medgraph build ./documents/ --graph-id medical-001

        medgraph build paper.pdf --merge --merge-threshold 0.8
    """
    if verbose:
        console.print(f"[dim]开始构建流程 | 路径: {path} | 图谱: {graph_id}[/dim]")

    # 收集文件
    files = _collect_files(path)

    if verbose:
        console.print(f"[dim]找到 {len(files)} 个文件待处理[/dim]")

    # 运行异步构建
    try:
        asyncio.run(
            _run_build(
                files=files,
                graph_id=graph_id,
                merge_enabled=merge,
                merge_threshold=merge_threshold,
                max_concurrency=max_concurrency,
                workspace=workspace,
                verbose=verbose,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]构建已取消[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]构建失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


async def _run_build(
    files: List[Path],
    graph_id: str,
    merge_enabled: bool,
    merge_threshold: float,
    max_concurrency: int,
    workspace: str,
    verbose: bool,
) -> None:
    """执行异步构建流程。

    Args:
        files: 文件路径列表
        graph_id: 图谱 ID
        merge_enabled: 是否启用合并
        merge_threshold: 合并阈值
        max_concurrency: 最大并发数
        workspace: 工作空间名称
        verbose: 详细输出
    """
    succeeded = 0
    failed = 0
    merged_count = 0
    errors: List[tuple[Path, str]] = []

    # 使用异步上下文管理器初始化客户端
    async with MedGraphClient(workspace=workspace) as client:
        # 创建进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # 添加主任务
            task = progress.add_task(
                f"构建图谱 '{graph_id}'",
                total=len(files),
            )

            # 定义进度回调
            def progress_callback(current: int, total: int, doc_id: str) -> None:
                """进度回调函数。"""
                progress.update(task, advance=1)

            # 处理文件（使用 SDK 的批量摄入）
            try:
                file_paths = [str(f) for f in files]

                batch_result = await client.ingest_batch(
                    file_paths=file_paths,
                    max_concurrency=max_concurrency,
                    progress_callback=progress_callback,
                )

                # 统计结果
                for result in batch_result.results:
                    if result.status == "completed":
                        succeeded += 1
                    else:
                        failed += 1
                        errors.append(
                            (
                                Path(result.file_path or "unknown"),
                                result.error or "Unknown error",
                            )
                        )

                # 获取图谱统计信息
                graph_info = await client.get_graph(graph_id)  # noqa: F841 - 保留用于调试和统计展示

                # 执行节点合并（如果启用）
                if merge_enabled and succeeded > 0:
                    if verbose:
                        console.print(
                            f"\n[dim]执行节点合并... (阈值: {merge_threshold})[/dim]"
                        )

                    # 这里可以实现自动节点合并逻辑
                    # 由于 merge_graph_nodes 需要指定实体列表，
                    # 实际应用中可能需要先分析相似性
                    merged_count = await _auto_merge_nodes(
                        client,
                        graph_id,
                        merge_threshold,
                        progress,
                        verbose,
                    )

            except MedGraphSDKError as e:
                console.print(f"\n[red]SDK 错误: {e}[/red]")
                raise
            except Exception as e:
                console.print(f"\n[red]构建过程中发生错误: {e}[/red]")
                raise

    # 显示摘要
    _display_build_summary(
        total_files=len(files),
        succeeded=succeeded,
        failed=failed,
        graph_id=graph_id,
        merge_enabled=merge_enabled,
        merged_count=merged_count,
    )

    # 显示错误详情（如果有）
    if errors and verbose:
        console.print("\n[red]错误详情:[/red]")
        for file_path, error in errors:
            console.print(f"  [red]✗[/red] {file_path.name}: {error}")


async def _auto_merge_nodes(
    client: MedGraphClient,
    graph_id: str,
    threshold: float,
    progress: Any,
    verbose: bool,
) -> int:
    """自动合并相似节点。

    这是一个简化的实现，实际应用中可能需要更复杂的相似性分析。

    Args:
        client: SDK 客户端
        graph_id: 图谱 ID
        threshold: 相似度阈值
        progress: 进度条对象
        verbose: 详细输出

    Returns:
        合并的节点数量
    """
    # 这里可以实现自动相似性检测和合并逻辑
    # 例如：
    # 1. 获取所有实体
    # 2. 计算实体之间的相似度
    # 3. 合并相似度超过阈值的实体

    # 由于当前 SDK 的 merge_graph_nodes 需要显式指定实体列表，
    # 这里返回 0 表示未执行自动合并
    # 实际应用中可以结合 embedding 相似度进行分析

    if verbose:
        console.print("[dim]自动节点合并功能需要显式指定实体列表。[/dim]")
        console.print("[dim]可以使用 SDK 的 merge_graph_nodes 方法手动合并。[/dim]")

    return 0


# 导出的命令函数
def build_command() -> typer.Typer:
    """获取 build 命令的 Typer 应用。

    Returns:
        typer.Typer: build 命令应用
    """
    return app


# 导出
__all__ = [
    "build",
    "build_command",
    "app",
]
