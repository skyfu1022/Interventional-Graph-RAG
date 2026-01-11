"""
导出命令模块。

提供图谱数据导出功能，支持多种格式。

使用示例：
    $ medgraph export --graph-id graph-001 --output graph.json
    $ medgraph export --graph-id graph-001 --output data.csv --format csv
    $ medgraph export --graph-id graph-001 --output graph.mmd --format mermaid
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

from src.sdk import MedGraphClient
from src.core.exceptions import GraphError, NotFoundError, ValidationError

# ========== 控制台和配置 ==========

console = Console()
export_app = typer.Typer(
    name="export",
    help="导出知识图谱数据",
    add_completion=False,
)


# ========== 辅助函数 ==========


def _validate_output_path(output_path: str) -> Path:
    """验证输出路径。

    Args:
        output_path: 输出文件路径

    Returns:
        Path: 验证后的路径对象

    Raises:
        typer.Exit: 路径无效
    """
    path = Path(output_path)

    # 检查父目录是否可写
    if path.parent.exists() and not path.parent.is_dir():
        console.print(
            f"[red]✗[/red] 父路径不是目录: {path.parent}",
            style="red"
        )
        raise typer.Exit(1)

    return path


def _display_export_summary(
    graph_id: str,
    output_path: Path,
    format: str,
    entity_count: int = 0,
    relationship_count: int = 0,
) -> None:
    """显示导出摘要。

    Args:
        graph_id: 图谱 ID
        output_path: 输出路径
        format: 导出格式
        entity_count: 实体数量
        relationship_count: 关系数量
    """
    # 创建摘要表格
    table = Table(title="导出摘要", show_header=False, padding=(0, 2))
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")

    table.add_row("图谱 ID", graph_id)
    table.add_row("输出文件", str(output_path))
    table.add_row("导出格式", format.upper())
    table.add_row("实体数量", str(entity_count))
    table.add_row("关系数量", str(relationship_count))

    console.print()
    console.print(table)

    # 显示成功消息
    console.print(
        Panel(
            f"[green]✓[/green] 图谱导出成功！\n\n"
            f"文件已保存到: [cyan]{output_path}[/cyan]",
            title="导出完成",
            border_style="green",
        )
    )


def _format_error_message(error: Exception) -> str:
    """格式化错误消息。

    Args:
        error: 异常对象

    Returns:
        str: 格式化的错误消息
    """
    if isinstance(error, NotFoundError):
        return f"图谱不存在: {error.resource_id}"
    elif isinstance(error, ValidationError):
        return f"参数验证失败: {error.message}"
    elif isinstance(error, GraphError):
        return f"导出失败: {error.message}"
    else:
        return f"未知错误: {str(error)}"


# ========== 核心导出函数 ==========


async def _export_graph(
    graph_id: str,
    output_path: Path,
    format: str,
    workspace: str,
) -> None:
    """执行图谱导出。

    Args:
        graph_id: 图谱 ID
        output_path: 输出路径
        format: 导出格式
        workspace: 工作空间名称

    Raises:
        NotFoundError: 图谱不存在
        ValidationError: 参数无效
        GraphError: 导出失败
    """
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 使用 Rich 进度条
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        # 初始化任务
        init_task = progress.add_task(
            "[cyan]初始化客户端...", total=1
        )

        # 使用 SDK 客户端
        async with MedGraphClient(workspace=workspace) as client:
            progress.update(init_task, completed=1)

            # 获取图谱信息
            info_task = progress.add_task(
                "[cyan]获取图谱信息...", total=1
            )

            try:
                graph_info = await client.get_graph(graph_id)
                progress.update(info_task, completed=1)
            except Exception as e:
                progress.update(info_task, completed=1)
                raise

            # 导出任务
            export_task = progress.add_task(
                f"[cyan]导出图谱数据 ({format.upper()})...", total=1
            )

            try:
                await client.export_graph(
                    graph_id=graph_id,
                    output_path=str(output_path),
                    format=format,
                )
                progress.update(export_task, completed=1)
            except Exception as e:
                progress.update(export_task, completed=1)
                raise

            # 返回统计信息
            return graph_info


# ========== Typer 命令 ==========


@export_app.command()
def export(
    graph_id: str = typer.Option(
        ...,
        "--graph-id", "-g",
        help="图谱 ID",
        rich_help_panel="必需参数",
    ),
    output: str = typer.Option(
        ...,
        "--output", "-o",
        help="输出文件路径",
        rich_help_panel="必需参数",
    ),
    format: str = typer.Option(
        "json",
        "--format", "-f",
        help="导出格式 (json, csv, mermaid)",
        rich_help_panel="可选参数",
    ),
    workspace: str = typer.Option(
        "medical",
        "--workspace", "-w",
        help="工作空间名称",
        rich_help_panel="可选参数",
    ),
) -> None:
    """导出知识图谱数据。

    支持多种导出格式：
    - json: 完整的图谱数据（JSON 格式）
    - csv: 表格格式，便于分析
    - mermaid: 可视化图表格式

    示例:
        $ medgraph export --graph-id graph-001 --output graph.json
        $ medgraph export -g graph-001 -o data.csv -f csv
        $ medgraph export -g graph-001 -o graph.mmd -f mermaid
    """
    # 验证格式
    valid_formats = ["json", "csv", "mermaid"]
    if format not in valid_formats:
        console.print(
            f"[red]✗[/red] 无效的导出格式: {format}\n"
            f"支持的格式: {', '.join(valid_formats)}",
            style="red"
        )
        raise typer.Exit(1)

    # 验证输出路径
    try:
        output_path = _validate_output_path(output)
    except typer.Exit:
        raise

    # 显示开始信息
    console.print(
        f"\n[bold cyan]开始导出图谱[/bold cyan]\n"
        f"  图谱 ID: [yellow]{graph_id}[/yellow]\n"
        f"  输出文件: [yellow]{output_path}[/yellow]\n"
        f"  导出格式: [yellow]{format.upper()}[/yellow]\n"
    )

    try:
        # 执行导出
        graph_info = asyncio.run(_export_graph(
            graph_id=graph_id,
            output_path=output_path,
            format=format,
            workspace=workspace,
        ))

        # 显示摘要
        _display_export_summary(
            graph_id=graph_id,
            output_path=output_path,
            format=format,
            entity_count=graph_info.entity_count,
            relationship_count=graph_info.relationship_count,
        )

    except (NotFoundError, ValidationError, GraphError) as e:
        # 显示错误
        error_msg = _format_error_message(e)
        console.print(
            Panel(
                f"[red]✗[/red] {error_msg}",
                title="导出失败",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    except Exception as e:
        # 未知错误
        console.print(
            Panel(
                f"[red]✗[/red] 未知错误: {str(e)}",
                title="导出失败",
                border_style="red",
            )
        )
        raise typer.Exit(1)


# ========== 导出的公共接口 ==========

__all__ = [
    "export_app",
    "export",
]
