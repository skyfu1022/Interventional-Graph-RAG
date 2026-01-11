"""
Query 命令实现。

提供知识图谱查询功能的 CLI 命令，支持：
- 单次查询：medgraph query "问题"
- 交互式查询：medgraph query --interactive
- 多种查询模式：naive, local, global, hybrid, mix, bypass
- 美化的 Rich 输出格式
"""

import asyncio
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import box
from rich.syntax import Syntax

from src.sdk import MedGraphClient, QueryMode
from src.core.exceptions import QueryError, ValidationError, MedGraphError

# 创建 Typer 应用和 Rich 控制台
query_app = typer.Typer(
    name="query",
    help="查询医疗知识图谱",
    add_completion=False,
)

console = Console()


def format_query_result(result, show_sources: bool = True, show_context: bool = False) -> None:
    """使用 Rich 格式化输出查询结果。

    Args:
        result: QueryResult 对象
        show_sources: 是否显示来源
        show_context: 是否显示上下文
    """
    # 1. 显示答案（使用 Markdown 渲染）
    console.print()
    answer_panel = Panel(
        Markdown(result.answer),
        title="[bold green]答案[/bold green]",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    )
    console.print(answer_panel)

    # 2. 显示查询元数据
    metadata_table = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="blue",
        padding=(0, 1),
        show_edge=False,
    )
    metadata_table.add_column("属性", style="cyan")
    metadata_table.add_column("值", style="yellow")

    metadata_table.add_row("查询模式", f"[bold]{result.mode.value.upper()}[/bold]")
    metadata_table.add_row("图谱 ID", result.graph_id)
    metadata_table.add_row("检索数量", str(result.retrieval_count))
    metadata_table.add_row("延迟", f"{result.latency_ms} ms")

    console.print()
    console.print(Panel(
        metadata_table,
        title="[bold blue]查询信息[/bold blue]",
        border_style="blue",
    ))

    # 3. 显示来源（如果请求）
    if show_sources and result.sources:
        console.print()
        sources_table = Table(
            title="[bold magenta]来源文档[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta",
            padding=(0, 1),
            show_header=True,
            header_style="bold magenta",
        )
        sources_table.add_column("文档 ID", style="cyan", width=20)
        sources_table.add_column("内容块 ID", style="blue", width=15)
        sources_table.add_column("相关性", style="green", width=8)
        sources_table.add_column("内容", style="white", width=50)

        for source in result.sources[:5]:  # 最多显示 5 个来源
            # 截断过长内容
            content = source.content[:80] + "..." if len(source.content) > 80 else source.content
            relevance_score = f"{source.relevance:.2f}"
            sources_table.add_row(
                source.doc_id[:20],
                source.chunk_id[:15],
                relevance_score,
                content,
            )

        console.print(sources_table)

        if len(result.sources) > 5:
            console.print(f"[dim]... 还有 {len(result.sources) - 5} 个来源[/dim]")

    # 4. 显示上下文（如果请求）
    if show_context and result.context:
        console.print()
        context_panel = Panel(
            "\n".join(result.context[:3]),  # 最多显示 3 个上下文
            title="[bold yellow]上下文[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(context_panel)


def format_error(error: Exception, query_text: str = "") -> None:
    """格式化错误信息。

    Args:
        error: 异常对象
        query_text: 查询文本（可选）
    """
    error_message = str(error)

    # 根据错误类型选择不同的样式
    if isinstance(error, ValidationError):
        border_style = "yellow"
        title = "[bold yellow]验证错误[/bold yellow]"
    elif isinstance(error, QueryError):
        border_style = "red"
        title = "[bold red]查询错误[/bold red]"
    elif isinstance(error, MedGraphError):
        border_style = "red"
        title = "[bold red]SDK 错误[/bold red]"
    else:
        border_style = "red"
        title = "[bold red]未知错误[/bold red]"

    # 构建错误面板
    error_content = f"[red]{error_message}[/red]"
    if query_text:
        error_content += f"\n\n[dim]查询: {query_text}[/dim]"

    console.print()
    console.print(
        Panel(
            error_content,
            title=title,
            border_style=border_style,
            padding=(1, 2),
        )
    )


async def execute_query(
    query_text: str,
    mode: str,
    graph_id: str,
    workspace: str,
) -> None:
    """执行查询的异步函数。

    Args:
        query_text: 查询文本
        mode: 查询模式
        graph_id: 图谱 ID
        workspace: 工作空间名称
    """
    try:
        # 显示查询信息
        console.print()
        console.print(
            f"[cyan]正在查询: [/cyan][bold yellow]{query_text}[/bold yellow]"
        )
        console.print(f"[dim]模式: {mode} | 图谱: {graph_id}[/dim]")

        # 创建客户端并执行查询
        async with MedGraphClient(workspace=workspace) as client:
            result = await client.query(
                query_text=query_text,
                mode=mode,
                graph_id=graph_id,
            )

            # 格式化输出结果
            format_query_result(result, show_sources=True, show_context=False)

    except (ValidationError, QueryError, MedGraphError) as e:
        format_error(e, query_text)
        raise typer.Exit(code=1)
    except Exception as e:
        format_error(e, query_text)
        raise typer.Exit(code=1)


def run_interactive_mode(
    mode: str,
    graph_id: str,
    workspace: str,
) -> None:
    """运行交互式查询模式。

    Args:
        mode: 查询模式
        graph_id: 图谱 ID
        workspace: 工作空间名称
    """
    console.print()
    welcome_panel = Panel(
        "[bold cyan]交互式查询模式[/bold cyan]\n\n"
        "输入您的问题，系统将从医疗知识图谱中检索相关信息。\n"
        "输入 [bold red]quit[/bold red] 或 [bold red]exit[/bold red] 退出，"
        "输入 [bold yellow]help[/bold yellow] 查看帮助。",
        title="欢迎",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(welcome_panel)

    query_count = 0

    while True:
        try:
            # 获取用户输入
            console.print()
            query_text = Prompt.ask(
                "[bold green]查询[/bold green]",
                default="",
                show_default=False,
            )

            # 检查退出命令
            if not query_text or query_text.lower() in ["quit", "exit", "q"]:
                console.print()
                console.print("[yellow]退出交互模式。[/yellow]")
                break

            # 检查帮助命令
            if query_text.lower() == "help":
                console.print()
                help_table = Table(
                    title="可用命令",
                    box=box.ROUNDED,
                    border_style="blue",
                )
                help_table.add_column("命令", style="cyan")
                help_table.add_column("说明", style="white")
                help_table.add_row("quit / exit / q", "退出交互模式")
                help_table.add_row("help", "显示此帮助信息")
                help_table.add_row("<任何问题>", "执行查询")
                console.print(help_table)
                continue

            # 执行查询
            query_count += 1
            console.print(f"\n[dim]{'=' * 60}[/dim]")
            console.print(f"[dim]查询 #{query_count} | {datetime.now().strftime('%H:%M:%S')}[/dim]")
            console.print(f"[dim]{'=' * 60}[/dim]")

            asyncio.run(execute_query(query_text, mode, graph_id, workspace))

        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]检测到中断，退出交互模式。[/yellow]")
            break
        except Exception as e:
            console.print()
            console.print(f"[red]发生错误: {e}[/red]")
            continue


@query_app.command("query")
def query_command(
    query: Optional[str] = typer.Argument(
        None,
        help="查询问题。如果不提供，则进入交互模式。",
        show_default=False,
    ),
    mode: str = typer.Option(
        "hybrid",
        "--mode",
        "-m",
        help="查询模式",
        show_choices=True,
        case_sensitive=False,
    ),
    graph_id: str = typer.Option(
        "default",
        "--graph-id",
        "-g",
        help="图谱 ID",
    ),
    workspace: str = typer.Option(
        "medical",
        "--workspace",
        "-w",
        help="工作空间名称",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="交互式查询模式",
    ),
    show_context: bool = typer.Option(
        False,
        "--show-context",
        "-c",
        help="显示上下文信息",
    ),
) -> None:
    """查询医疗知识图谱。

    支持单次查询和交互式查询模式。

    示例:
        # 单次查询
        medgraph query "糖尿病患者的主要症状是什么？"

        # 使用特定模式查询
        medgraph query "什么是糖尿病?" --mode local

        # 交互式查询
        medgraph query --interactive

        # 查询特定图谱
        medgraph query "高血压的治疗方法" --graph-id cardiology
    """
    # 验证查询模式
    valid_modes = ["naive", "local", "global", "hybrid", "mix", "bypass"]
    if mode.lower() not in valid_modes:
        console.print()
        console.print(
            f"[red]无效的查询模式: {mode}[/red]"
        )
        console.print(f"[dim]有效模式: {', '.join(valid_modes)}[/dim]")
        raise typer.Exit(code=1)

    mode = mode.lower()

    # 显示标题
    console.print()
    title = "[bold cyan]Medical Graph RAG - 查询工具[/bold cyan]"
    console.print(title)
    console.print("[dim]" + "=" * 50 + "[/dim]")

    # 根据参数选择模式
    if interactive or not query:
        # 交互式模式
        run_interactive_mode(mode, graph_id, workspace)
    else:
        # 单次查询
        asyncio.run(execute_query(query, mode, graph_id, workspace))

    console.print()
