"""
Ingest 命令 - 文档摄入到知识图谱。

支持单个文件和批量文件摄入，使用 Rich 进度条和表格显示结果。
"""

import asyncio
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.table import Table

from src.sdk import MedGraphClient
from src.sdk.exceptions import MedGraphSDKError

# 创建 Typer 应用和 Console 实例
ingest_app = typer.Typer(help="文档摄入命令")
console = Console()


def _validate_file_paths(file_paths: List[Path]) -> List[Path]:
    """验证文件路径是否存在且可读。

    Args:
        file_paths: 文件路径列表

    Returns:
        List[Path]: 有效的文件路径列表

    Raises:
        typer.BadParameter: 如果文件不存在或不可读
    """
    valid_paths = []
    for file_path in file_paths:
        if not file_path.exists():
            raise typer.BadParameter(f"文件不存在: {file_path}")
        if not file_path.is_file():
            raise typer.BadParameter(f"路径不是文件: {file_path}")
        if not file_path.is_file() or not file_path.stat().st_size > 0:
            # 允许空文件，但给出警告
            console.print(f"[yellow]⚠ 警告: 文件可能为空: {file_path}[/yellow]")
        valid_paths.append(file_path)
    return valid_paths


def _display_ingest_results(results: List, total_files: int, graph_id: str) -> None:
    """显示摄入结果表格。

    Args:
        results: 摄入结果列表
        total_files: 总文件数
        graph_id: 图谱 ID
    """
    console.print()
    console.print(f"[bold green]✓ 摄入完成[/bold green] | 图谱: {graph_id}")
    console.print()

    # 创建结果表格
    table = Table(title="文档摄入结果", show_header=True, header_style="bold magenta")
    table.add_column("文件名", style="cyan", no_wrap=False)
    table.add_column("状态", style="green")
    table.add_column("文档 ID", style="blue")
    table.add_column("文本块", justify="right", style="yellow")
    table.add_column("实体数", justify="right", style="yellow")

    # 统计信息
    success_count = 0
    failed_count = 0
    total_chunks = 0
    total_entities = 0

    for result in results:
        file_path = result.get("file_path", "未知")
        status = result.get("status", "unknown")
        doc_id = result.get("doc_id", "N/A")
        chunks = result.get("chunks_count", 0)
        entities = result.get("entities_count", 0)

        # 状态样式
        status_style = {
            "completed": "[green]✓ 成功[/green]",
            "failed": "[red]✗ 失败[/red]",
            "processing": "[yellow]⏳ 处理中[/yellow]",
            "pending": "[blue]⏸ 等待[/blue]",
        }.get(status, f"[grey]{status}[/grey]")

        table.add_row(
            Path(file_path).name if file_path != "未知" else "未知",
            status_style,
            doc_id[:12] + "..." if len(doc_id) > 12 else doc_id,
            str(chunks),
            str(entities),
        )

        # 统计
        if status == "completed":
            success_count += 1
            total_chunks += chunks
            total_entities += entities
        else:
            failed_count += 1

    console.print(table)

    # 显示统计信息
    console.print()
    console.print("[bold]统计信息:[/bold]")
    console.print(f"  总文件数: {total_files}")
    console.print(f"  [green]成功: {success_count}[/green]")
    if failed_count > 0:
        console.print(f"  [red]失败: {failed_count}[/red]")
    console.print(f"  总文本块: {total_chunks}")
    console.print(f"  总实体数: {total_entities}")
    console.print()


async def _ingest_files(
    file_paths: List[Path],
    graph_id: str,
    workspace: str,
    max_concurrency: int,
) -> List[dict]:
    """异步摄入文件。

    Args:
        file_paths: 文件路径列表
        graph_id: 图谱 ID
        workspace: 工作空间名称
        max_concurrency: 最大并发数

    Returns:
        List[dict]: 摄入结果列表
    """
    results = []

    try:
        async with MedGraphClient(workspace=workspace) as client:
            # 使用进度条显示摄入进度
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                # 创建总任务
                total_task = progress.add_task(
                    f"[cyan]摄入文档到图谱 '{graph_id}'...",
                    total=len(file_paths),
                )

                # 定义进度回调
                def progress_callback(current: int, total: int, doc_id: str) -> None:
                    """进度回调函数。"""
                    progress.update(total_task, advance=1)
                    console.print(f"  [dim]处理中: {doc_id} ({current}/{total})[/dim]")

                # 执行批量摄入
                batch_result = await client.ingest_batch(
                    file_paths=[str(fp) for fp in file_paths],
                    max_concurrency=max_concurrency,
                    progress_callback=progress_callback,
                )

                # 转换结果为字典列表
                for idx, result in enumerate(batch_result.results):
                    results.append(
                        {
                            "file_path": str(file_paths[idx]),
                            "status": result.status,
                            "doc_id": result.doc_id or "N/A",
                            "chunks_count": result.chunks_count,
                            "entities_count": result.entities_count,
                            "error": result.error,
                        }
                    )

    except MedGraphSDKError as e:
        console.print(f"[red]✗ SDK 错误: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗ 未知错误: {e}[/red]")
        raise typer.Exit(code=1)

    return results


@ingest_app.command("ingest")
def ingest_command(
    files: List[Path] = typer.Argument(
        ...,
        help="要摄入的文件路径（支持多个文件）",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    graph_id: str = typer.Option(
        "default",
        "--graph-id",
        "-g",
        help="目标图谱 ID",
    ),
    workspace: str = typer.Option(
        "medical",
        "--workspace",
        "-w",
        help="工作空间名称",
    ),
    max_concurrency: int = typer.Option(
        5,
        "--max-concurrency",
        "-c",
        help="最大并发摄入数",
    ),
) -> None:
    """摄入文档到知识图谱。

    支持单个文件和批量文件摄入，自动进行文本切分、实体提取和关系构建。

    示例:
        # 摄入单个文件
        medgraph ingest document.pdf

        # 摄入多个文件
        medgraph ingest file1.pdf file2.pdf file3.pdf

        # 指定目标图谱
        medgraph ingest document.pdf --graph-id my-graph

        # 指定工作空间和并发数
        medgraph ingest *.pdf --workspace research --max-concurrency 10
    """
    # 显示开始信息
    console.print()
    console.print("[bold cyan]Medical Graph RAG - 文档摄入[/bold cyan]")
    console.print()

    # 验证文件路径
    try:
        valid_files = _validate_file_paths(files)
    except typer.BadParameter as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)

    file_count = len(valid_files)
    console.print(f"准备摄入 [bold]{file_count}[/bold] 个文件")
    console.print(f"目标图谱: [cyan]{graph_id}[/cyan]")
    console.print(f"工作空间: [cyan]{workspace}[/cyan]")
    console.print()

    # 异步执行摄入
    try:
        results = asyncio.run(
            _ingest_files(
                file_paths=valid_files,
                graph_id=graph_id,
                workspace=workspace,
                max_concurrency=max_concurrency,
            )
        )

        # 显示结果
        _display_ingest_results(results, file_count, graph_id)

        # 检查是否有失败
        failed_count = sum(1 for r in results if r["status"] != "completed")
        if failed_count > 0:
            console.print(f"[yellow]⚠ 警告: {failed_count} 个文件摄入失败[/yellow]")
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]✓ 所有文件摄入成功！[/bold green]")

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]⚠ 操作已取消[/yellow]")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print()
        console.print(f"[red]✗ 摄入失败: {e}[/red]")
        raise typer.Exit(code=1)


# 导出命令函数
__all__ = ["ingest_command", "ingest_app"]
