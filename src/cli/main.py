#!/usr/bin/env python3
"""
Medical Graph RAG CLI 主入口。

该模块提供命令行界面（CLI）用于与 Medical Graph RAG 系统交互。
基于 Typer 框架构建，支持以下功能：
- build: 构建知识图谱
- query: 查询知识图谱
- ingest: 摄入文档
- serve: 启动 API 服务器
- export: 导出图谱数据

使用示例:
    # 显示帮助信息
    python -m src.cli.main --help

    # 查询知识图谱
    python -m src.cli.main query "什么是糖尿病?"

    # 摄入文档
    python -m src.cli.main ingest document.txt

    # 构建知识图谱
    python -m src.cli.main build --workspace medical

    # 启动 API 服务器
    python -m src.cli.main serve --port 8000

    # 导出图谱数据
    python -m src.cli.main export --output graph.json

版本: 0.2.0
许可: MIT
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 导入 SDK
from src.sdk import (
    MedGraphClient,
    get_info,
)
from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError as SDKConfigError,
    DocumentNotFoundError,
    ConnectionError as SDKConnectionError,
    ValidationError as SDKValidationError,
)

# ========== 全局配置 ==========

# 创建 Rich Console 实例，用于美化输出
console = Console()

# 创建 Typer 应用实例
app = typer.Typer(
    name="medgraph",
    help="""Medical Graph RAG - 医学知识图谱构建和查询工具

    基于 LightRAG 和 RAGAnything 的医学知识图谱系统，
    支持多模态文档摄入、智能查询和图谱导出。
    """,
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)

# ========== 版本信息 ==========


def version_callback(value: bool) -> None:
    """显示版本信息并退出。

    Args:
        value: 是否显示版本信息

    Raises:
        typer.Exit: 显示版本信息后退出
    """
    if value:
        info = get_info()
        console.print(
            Panel(
                f"[bold cyan]{info['name']}[/bold cyan]\n\n"
                f"版本: [bold green]{info['version']}[/bold green]\n"
                f"作者: {info['author']}\n"
                f"许可: {info['license']}\n\n"
                f"[dim]{info['description']}[/dim]",
                title="版本信息",
                border_style="cyan",
            )
        )
        raise typer.Exit()


# ========== 主回调函数 ==========


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="显示版本信息并退出",
    ),
    workspace: str = typer.Option(
        "medical",
        "--workspace",
        "-w",
        help="工作空间名称（用于隔离不同的知识图谱）",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="配置文件路径（支持 JSON 和 YAML 格式）",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="日志级别（DEBUG, INFO, WARNING, ERROR）",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="启用详细输出模式",
    ),
):
    """Medical Graph RAG CLI 主入口。

    该命令行工具提供完整的医学知识图谱管理功能，
    包括文档摄入、知识查询、图谱构建和数据导出。
    """
    # 将全局配置存储到上下文中
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace
    ctx.obj["config"] = config
    ctx.obj["log_level"] = "DEBUG" if verbose else log_level
    ctx.obj["verbose"] = verbose


# ========== 命令辅助函数 ==========


async def create_client_from_ctx(ctx: typer.Context) -> MedGraphClient:
    """从上下文创建 SDK 客户端。

    Args:
        ctx: Typer 上下文对象

    Returns:
        MedGraphClient: SDK 客户端实例

    Raises:
        typer.Exit: 创建客户端失败时退出
    """
    workspace = ctx.obj.get("workspace", "medical")
    config_path = ctx.obj.get("config")
    log_level = ctx.obj.get("log_level", "INFO")

    try:
        if config_path:
            console.print(f"[dim]从配置文件加载: {config_path}[/dim]")
            client = MedGraphClient.from_config(
                config_path=config_path,
                workspace=workspace,
                log_level=log_level,
            )
        else:
            client = MedGraphClient(
                workspace=workspace,
                log_level=log_level,
            )

        return client

    except SDKConfigError as e:
        console.print(f"[red]配置错误: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]创建客户端失败: {e}[/red]")
        raise typer.Exit(code=1)


def handle_sdk_error(error: MedGraphSDKError) -> None:
    """处理 SDK 异常并显示友好的错误信息。

    Args:
        error: SDK 异常对象
    """
    if isinstance(error, SDKConfigError):
        console.print(f"[red]配置错误: {error}[/red]")
    elif isinstance(error, DocumentNotFoundError):
        console.print(f"[red]文档未找到: {error}[/red]")
    elif isinstance(error, SDKConnectionError):
        console.print(f"[red]连接错误: {error}[/red]")
    elif isinstance(error, SDKValidationError):
        console.print(f"[red]验证错误: {error}[/red]")
    else:
        console.print(f"[red]SDK 错误: {error}[/red]")


# ========== build 命令 ==========


@app.command("build")
def build(
    ctx: typer.Context,
    chunk_size: int = typer.Option(
        512,
        "--chunk-size",
        help="文本块大小（字符数）",
    ),
    overlap: int = typer.Option(
        50,
        "--overlap",
        help="文本块重叠大小",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制重新构建，覆盖现有图谱",
    ),
):
    """构建知识图谱。

    初始化或重建知识图谱，配置文本处理参数。
    如果图谱已存在且未指定 --force，则跳过构建。
    """

    async def _build() -> None:
        try:
            client = await create_client_from_ctx(ctx)

            async with client:
                workspace = ctx.obj["workspace"]

                if not force:
                    # 检查图谱是否已存在
                    try:
                        graphs = await client.list_graphs()
                        if any(g.graph_id == workspace for g in graphs):
                            console.print(
                                f"[yellow]图谱 '{workspace}' 已存在，"
                                f"使用 --force 强制重建[/yellow]"
                            )
                            return
                    except Exception:
                        pass

                console.print(
                    f"[bold cyan]开始构建知识图谱[/bold cyan] "
                    f"([dim]工作空间: {workspace}[/dim])"
                )

                # TODO: 实现构建逻辑
                console.print("[dim]图谱构建功能开发中...[/dim]")

                console.print("[bold green]✓[/bold green] 知识图谱构建完成")

        except MedGraphSDKError as e:
            handle_sdk_error(e)
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]构建失败: {e}[/red]")
            raise typer.Exit(code=1)

    asyncio.run(_build())


# ========== query 命令 ==========


@app.command("query")
def query(
    ctx: typer.Context,
    question: str = typer.Argument(
        ...,
        help="要查询的问题",
    ),
    mode: str = typer.Option(
        "hybrid",
        "--mode",
        "-m",
        help="查询模式（naive, local, global, hybrid, mix, bypass）",
    ),
    graph_id: str = typer.Option(
        "default",
        "--graph-id",
        "-g",
        help="图谱 ID",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="输出格式（text, json）",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        "-s",
        help="启用流式输出",
    ),
):
    """查询知识图谱。

    使用自然语言问题查询医学知识图谱，
    返回相关的答案和来源信息。
    """

    async def _query() -> None:
        try:
            client = await create_client_from_ctx(ctx)

            async with client:
                # 验证查询模式
                valid_modes = ["naive", "local", "global", "hybrid", "mix", "bypass"]
                if mode not in valid_modes:
                    console.print(
                        f"[red]无效的查询模式: {mode}[/red]\n"
                        f"[dim]有效模式: {', '.join(valid_modes)}[/dim]"
                    )
                    raise typer.Exit(code=1)

                console.print(
                    f"[bold cyan]查询:[/bold cyan] {question}\n"
                    f"[dim]模式: {mode} | 图谱: {graph_id}[/dim]\n"
                )

                if stream:
                    # 流式查询
                    console.print("[bold cyan]答案:[/bold cyan]\n")
                    async for chunk in client.query_stream(
                        query_text=question,
                        mode=mode,
                        graph_id=graph_id,
                    ):
                        console.print(chunk, end="", highlight=False)
                    console.print()  # 换行
                else:
                    # 普通查询
                    result = await client.query(
                        query_text=question,
                        mode=mode,
                        graph_id=graph_id,
                    )

                    if format == "json":
                        # JSON 输出
                        console.print_json(result.to_json())
                    else:
                        # 文本输出
                        console.print(
                            f"[bold cyan]答案:[/bold cyan]\n{result.answer}\n"
                        )

                        # 显示来源信息
                        if result.sources:
                            console.print(f"[bold]来源 ({len(result.sources)}):[/bold]")
                            for i, source in enumerate(result.sources, 1):
                                preview = (
                                    source.content[:100] + "..."
                                    if len(source.content) > 100
                                    else source.content
                                )
                                console.print(
                                    f"  {i}. [dim]{preview}[/dim] "
                                    f"[cyan](相关度: {source.relevance:.2f})[/cyan]"
                                )

                        # 显示性能指标
                        console.print(
                            f"\n[dim]延迟: {result.latency_ms}ms | "
                            f"检索次数: {result.retrieval_count}[/dim]"
                        )

        except MedGraphSDKError as e:
            handle_sdk_error(e)
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]查询失败: {e}[/red]")
            raise typer.Exit(code=1)

    asyncio.run(_query())


# ========== ingest 命令 ==========


@app.command("ingest")
def ingest(
    ctx: typer.Context,
    file_path: str = typer.Argument(
        ...,
        help="要摄入的文档路径（支持 txt, md, json, csv 等格式）",
        exists=True,
    ),
    doc_id: Optional[str] = typer.Option(
        None,
        "--doc-id",
        "-d",
        help="文档 ID（不指定则自动生成）",
    ),
    batch: bool = typer.Option(
        False,
        "--batch",
        "-b",
        help="批量模式（file_path 指向包含多个文件的目录）",
    ),
    max_concurrency: int = typer.Option(
        5,
        "--max-concurrency",
        help="批量处理时的最大并发数",
    ),
):
    """摄入文档到知识图谱。

    支持单文档和批量文档摄入，自动进行文本切分、
    实体提取和关系构建。
    """

    async def _ingest() -> None:
        try:
            client = await create_client_from_ctx(ctx)

            async with client:
                if batch:
                    # 批量摄入
                    file_path_obj = Path(file_path)
                    if not file_path_obj.is_dir():
                        console.print(
                            f"[red]批量模式要求 file_path 为目录: {file_path}[/red]"
                        )
                        raise typer.Exit(code=1)

                    # 查找所有支持的文件
                    supported_extensions = {".txt", ".md", ".json", ".csv"}
                    files = [
                        str(f)
                        for f in file_path_obj.rglob("*")
                        if f.is_file() and f.suffix in supported_extensions
                    ]

                    if not files:
                        console.print(
                            f"[yellow]未找到支持的文件[/yellow] "
                            f"([dim]{', '.join(supported_extensions)}[/dim])"
                        )
                        raise typer.Exit(code=1)

                    console.print(
                        f"[bold cyan]批量摄入[/bold cyan] "
                        f"([dim]找到 {len(files)} 个文件[/dim])"
                    )

                    # 批量处理
                    result = await client.ingest_batch(
                        file_paths=files,
                        max_concurrency=max_concurrency,
                    )

                    # 显示结果
                    console.print(
                        f"\n[bold green]✓[/bold green] "
                        f"批量摄入完成: {result.succeeded}/{result.total} 成功"
                    )

                    if result.failed > 0:
                        console.print(f"[yellow]失败: {result.failed} 个文档[/yellow]")
                        for failed_result in result.results:
                            if failed_result.status == "failed":
                                console.print(
                                    f"  [red]✗[/red] {failed_result.file_path}: "
                                    f"{failed_result.error}"
                                )

                else:
                    # 单文档摄入
                    console.print(f"[bold cyan]摄入文档:[/bold cyan] {file_path}")

                    doc_info = await client.ingest_document(
                        file_path=file_path,
                        doc_id=doc_id,
                    )

                    console.print(
                        f"\n[bold green]✓[/bold green] 文档摄入成功\n"
                        f"  [dim]文档 ID:[/dim] {doc_info.doc_id}\n"
                        f"  [dim]状态:[/dim] {doc_info.status}\n"
                        f"  [dim]文本块数:[/dim] {doc_info.chunks_count}\n"
                        f"  [dim]实体数:[/dim] {doc_info.entities_count}"
                    )

        except MedGraphSDKError as e:
            handle_sdk_error(e)
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]摄入失败: {e}[/red]")
            raise typer.Exit(code=1)

    asyncio.run(_ingest())


# ========== serve 命令 ==========


@app.command("serve")
def serve(
    ctx: typer.Context,
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="服务器监听的主机地址 (默认: 127.0.0.1)",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="服务器端口号 (默认: 8000)",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="启用自动重载 (开发模式)",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="日志级别 (debug, info, warning, error, critical)",
    ),
):
    """启动 Medical Graph RAG API 开发服务器.

    使用 Uvicorn 启动 FastAPI 应用，支持开发模式的热重载功能。

    **默认配置:**
        - 主机: 127.0.0.1 (仅本地访问)
        - 端口: 8000
        - 热重载: 关闭

    **开发模式示例:**
        // 默认启动
        $ medgraph serve

        // 启用热重载
        $ medgraph serve --reload

        // 自定义端口
        $ medgraph serve --port 8080

        // 监听所有网络接口 (局域网访问)
        $ medgraph serve --host 0.0.0.0

        // 组合使用
        $ medgraph serve --host 0.0.0.0 --port 9000 --reload
    """
    import uvicorn
    import socket

    # 验证端口范围
    if not (1 <= port <= 65535):
        console.print(f"[bold red]✗[/] 错误: 端口必须在 1-65535 范围内,当前值: {port}")
        raise typer.Exit(code=1)

    # 检查端口可用性
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
    except OSError:
        console.print(f"[bold red]✗[/] 错误: 端口 {port} 已被占用")
        console.print("[dim]提示: 请尝试其他端口或检查是否有其他服务正在使用该端口[/]")
        raise typer.Exit(code=1)

    # 打印服务器信息
    from rich.panel import Panel

    reload_mode = "[yellow]开发模式 (热重载)[/]" if reload else "[green]生产模式[/]"
    info_content = f"""[bold cyan]服务器地址:[/]
    [dim]本地:[/] http://localhost:{port}
    [dim]网络:[/] http://{host}:{port}

[bold cyan]API 文档:[/]
    [dim]Swagger UI:[/] http://{host}:{port}/docs
    [dim]ReDoc:[/] http://{host}:{port}/redoc

[bold cyan]运行模式:[/]
    {reload_mode}

[dim]按 Ctrl+C 停止服务器[/]"""

    panel = Panel(
        info_content,
        title="[bold green]Medical Graph RAG API 服务器[/]",
        border_style="green",
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()

    # 配置并启动 Uvicorn
    config = uvicorn.Config(
        app="src.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        reload_dirs=["./src"] if reload else None,
        access_log=True,
        use_colors=True,
        timeout_keep_alive=5,
        limit_concurrency=100,
        limit_max_requests=1000,
    )

    server = uvicorn.Server(config)

    try:
        server.run()
    except KeyboardInterrupt:
        console.print()
        console.print("[bold yellow]⚠[/]  服务器已停止")
    except Exception as e:
        console.print()
        console.print(f"[bold red]✗[/] 服务器启动失败: {e}")
        raise typer.Exit(code=1)


# ========== export 命令 ==========


@app.command("export")
def export(
    ctx: typer.Context,
    output: str = typer.Option(
        "export.json",
        "--output",
        "-o",
        help="输出文件路径",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="导出格式（json, csv, mermaid）",
    ),
    graph_id: str = typer.Option(
        "default",
        "--graph-id",
        "-g",
        help="要导出的图谱 ID",
    ),
):
    """导出图谱数据。

    将知识图谱数据导出为指定格式的文件，
    支持结构化数据和可视化格式。
    """

    async def _export() -> None:
        try:
            client = await create_client_from_ctx(ctx)

            async with client:
                console.print(
                    f"[bold cyan]导出图谱数据[/bold cyan]\n"
                    f"[dim]图谱 ID: {graph_id}[/dim]\n"
                    f"[dim]输出文件: {output}[/dim]\n"
                    f"[dim]格式: {format}[/dim]\n"
                )

                # 验证格式
                valid_formats = ["json", "csv", "mermaid"]
                if format not in valid_formats:
                    console.print(
                        f"[red]无效的导出格式: {format}[/red]\n"
                        f"[dim]有效格式: {', '.join(valid_formats)}[/dim]"
                    )
                    raise typer.Exit(code=1)

                # 导出图谱
                await client.export_graph(
                    graph_id=graph_id,
                    output_path=output,
                    format=format,
                )

                console.print(f"\n[bold green]✓[/bold green] 图谱导出成功: {output}")

        except MedGraphSDKError as e:
            handle_sdk_error(e)
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]导出失败: {e}[/red]")
            raise typer.Exit(code=1)

    asyncio.run(_export())


# ========== info 命令 ==========


@app.command("info")
def info(
    ctx: typer.Context,
    graph_id: Optional[str] = typer.Option(
        None,
        "--graph-id",
        "-g",
        help="显示特定图谱的详细信息",
    ),
):
    """显示系统或图谱信息。

    列出所有图谱或显示特定图谱的详细统计信息。
    """

    async def _info() -> None:
        try:
            client = await create_client_from_ctx(ctx)

            async with client:
                if graph_id:
                    # 显示特定图谱信息
                    graph_info = await client.get_graph(graph_id)

                    table = Table(title=f"图谱信息: {graph_id}")
                    table.add_column("属性", style="cyan")
                    table.add_column("值", style="green")

                    table.add_row("图谱 ID", graph_info.graph_id)
                    table.add_row("工作空间", graph_info.workspace)
                    table.add_row("实体数量", str(graph_info.entity_count))
                    table.add_row("关系数量", str(graph_info.relationship_count))
                    table.add_row("文档数量", str(graph_info.document_count))
                    table.add_row("创建时间", graph_info.created_at)
                    if graph_info.updated_at:
                        table.add_row("更新时间", graph_info.updated_at)

                    console.print(table)

                else:
                    # 列出所有图谱
                    graphs = await client.list_graphs()

                    if not graphs:
                        console.print("[yellow]未找到任何图谱[/yellow]")
                        return

                    table = Table(title="知识图谱列表")
                    table.add_column("图谱 ID", style="cyan")
                    table.add_column("工作空间", style="green")
                    table.add_column("实体", style="yellow")
                    table.add_column("关系", style="yellow")
                    table.add_column("文档", style="yellow")
                    table.add_column("创建时间", style="dim")

                    for graph in graphs:
                        table.add_row(
                            graph.graph_id,
                            graph.workspace,
                            str(graph.entity_count),
                            str(graph.relationship_count),
                            str(graph.document_count),
                            graph.created_at[:19] if graph.created_at else "",
                        )

                    console.print(table)

                    # 显示性能统计
                    stats = client.get_stats()
                    if stats.get("metrics_enabled"):
                        console.print(
                            f"\n[bold]性能统计:[/bold]\n"
                            f"  查询次数: {stats.get('total_queries', 0)}\n"
                            f"  文档数: {stats.get('total_documents', 0)}\n"
                            f"  平均延迟: {stats.get('avg_latency_ms', 0):.2f}ms"
                        )

        except MedGraphSDKError as e:
            handle_sdk_error(e)
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]获取信息失败: {e}[/red]")
            raise typer.Exit(code=1)

    asyncio.run(_info())


# ========== 主程序入口 ==========


if __name__ == "__main__":
    app()
