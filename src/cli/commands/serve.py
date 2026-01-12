"""
Medical Graph RAG - Serve 命令模块

本模块提供 `medgraph serve` 命令的实现,用于启动 FastAPI 开发服务器。
使用 Uvicorn 作为 ASGI 服务器,支持热重载和自定义配置。

遵循 PEP 8 标准,包含完整的类型提示和 Google 风格文档字符串。

命令格式:
    medgraph serve                    # 默认: localhost:8000
    medgraph serve --port 8080        # 自定义端口
    medgraph serve --reload           # 开发模式热重载
    medgraph serve --host 0.0.0.0     # 监听所有网络接口

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

import socket

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

# 创建 serve 命令的 Typer 应用
serve_app = typer.Typer(
    help="启动 Medical Graph RAG API 开发服务器",
    add_completion=False,
)

console = Console()


def _is_port_available(host: str, port: int) -> bool:
    """
    检查指定端口是否可用。

    尝试绑定到指定端口,如果失败则说明端口已被占用。

    Args:
        host: 主机地址
        port: 端口号

    Returns:
        bool: 如果端口可用返回 True,否则返回 False

    Example:
        >>> _is_port_available("localhost", 8000)
        True
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def _print_server_info(
    host: str,
    port: int,
    reload: bool,
    docs_url: str,
) -> None:
    """
    打印服务器启动信息。

    使用 Rich Panel 显示美观的服务器信息,包括访问地址、
    API 文档链接和运行模式。

    Args:
        host: 服务器主机地址
        port: 服务器端口
        reload: 是否启用热重载
        docs_url: API 文档 URL
    """
    # 构建信息面板
    info_content = f"""[bold cyan]服务器地址:[/]
    [dim]本地:[/] http://localhost:{port}
    [dim]网络:[/] http://{host}:{port}

[bold cyan]API 文档:[/]
    [dim]Swagger UI:[/] {docs_url}
    [dim]ReDoc:[/] {docs_url.replace("/docs", "/redoc")}

[bold cyan]运行模式:[/]
    {("[yellow]开发模式 (热重载)[/]" if reload else "[green]生产模式[/]")}

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


@serve_app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="服务器监听的主机地址 (默认: 127.0.0.1)",
        show_default=False,
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="服务器端口号 (默认: 8000)",
        show_default=False,
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="启用自动重载 (开发模式)",
        show_default=False,
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="日志级别 (debug, info, warning, error, critical)",
        show_default=False,
    ),
) -> None:
    """
    启动 Medical Graph RAG API 开发服务器。

    使用 Uvicorn 启动 FastAPI 应用,支持开发模式的热重载功能。

    **默认配置:**
        - 主机: 127.0.0.1 (仅本地访问)
        - 端口: 8000
        - 热重载: 关闭

    **开发模式示例:**
        [dim]// 默认启动[/]
        $ medgraph serve

        [dim]// 启用热重载[/]
        $ medgraph serve --reload

        [dim]// 自定义端口[/]
        $ medgraph serve --port 8080

        [dim]// 监听所有网络接口 (局域网访问)[/]
        $ medgraph serve --host 0.0.0.0

        [dim]// 组合使用[/]
        $ medgraph serve --host 0.0.0.0 --port 9000 --reload

    **生产环境提示:**
        生产环境建议使用:
        - 更多的 workers (--workers)
        - 进程管理器 (如 systemd, supervisor)
        - 反向代理 (如 Nginx)
        - 禁用热重载

    Args:
        host: 服务器监听的主机地址
        port: 服务器端口号 (1-65535)
        reload: 是否启用自动重载
        log_level: 日志级别

    Raises:
        typer.Exit: 如果端口被占用或配置无效
    """
    # 验证端口范围
    if not (1 <= port <= 65535):
        console.print(
            f"[bold red]✗[/] 错误: 端口必须在 1-65535 范围内,当前值: {port}",
            style="red",
        )
        raise typer.Exit(code=1)

    # 检查端口是否可用
    if not _is_port_available(host, port):
        console.print(
            f"[bold red]✗[/] 错误: 端口 {port} 已被占用",
            style="red",
        )
        console.print(
            "[dim]提示: 请尝试其他端口或检查是否有其他服务正在使用该端口[/]",
        )
        raise typer.Exit(code=1)

    # 打印服务器信息
    _print_server_info(
        host=host,
        port=port,
        reload=reload,
        docs_url=f"http://{host}:{port}/docs",
    )

    # 配置 Uvicorn
    config = uvicorn.Config(
        app="src.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        # 如果启用重载,限制重载目录
        reload_dirs=["./src"] if reload else None,
        # 开发友好的配置
        access_log=True,
        use_colors=True,
        # 超时配置
        timeout_keep_alive=5,
        # 限制并发 (开发环境)
        limit_concurrency=100,
        limit_max_requests=1000,
    )

    # 启动服务器
    server = uvicorn.Server(config)

    try:
        # 使用同步方式运行 (避免事件循环冲突)
        server.run()
    except KeyboardInterrupt:
        console.print()
        console.print(
            "[bold yellow]⚠[/]  服务器已停止",
            style="yellow",
        )
    except Exception as e:
        console.print()
        console.print(
            f"[bold red]✗[/] 服务器启动失败: {e}",
            style="red",
        )
        raise typer.Exit(code=1)


# 导出命令函数,供主 CLI 使用
__all__ = ["serve_app", "serve"]
