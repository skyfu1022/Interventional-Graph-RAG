"""
Medical Graph RAG - CLI UI 工具模块

本模块提供统一的终端用户界面组件,使用 Rich 库实现美观的输出格式。
遵循 PEP 8 标准,包含完整的类型提示和 Google 风格文档字符串。

作者: Medical Graph RAG Team
创建时间: 2026-01-11
版本: 1.0.0
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table


class UIConsole:
    """
    统一的 UI 控制台类,提供所有终端输出功能。

    这个类封装了 Rich 库的各种组件,提供一致的 UI 风格。

    Attributes:
        console: Rich Console 实例,用于所有终端输出
    """

    def __init__(self) -> None:
        """初始化 UI 控制台。"""
        self.console = Console()

    def print_success(self, message: str, title: str = "成功") -> None:
        """
        打印成功消息。

        使用绿色边框的 Panel 显示成功消息,提供视觉反馈。

        Args:
            message: 要显示的成功消息内容
            title: Panel 的标题,默认为"成功"

        Example:
            >>> ui = UIConsole()
            >>> ui.print_success("操作成功完成!")
        """
        panel = Panel(
            f"[bold green]✓[/] {message}",
            title=f"[bold green]{title}[/]",
            border_style="green",
            padding=(0, 2),
        )
        self.console.print(panel)

    def print_error(
        self, message: str, title: str = "错误", subtitle: Optional[str] = None
    ) -> None:
        """
        打印错误消息。

        使用红色边框的 Panel 显示错误消息,突出显示问题。

        Args:
            message: 错误消息内容
            title: Panel 的标题,默认为"错误"
            subtitle: 可选的副标题,用于提供额外信息或建议

        Example:
            >>> ui = UIConsole()
            >>> ui.print_error("无法连接到数据库", "连接失败", "请检查网络设置")
        """
        panel = Panel(
            f"[bold red]✗[/] {message}",
            title=f"[bold red]{title}[/]",
            subtitle=subtitle,
            border_style="red",
            padding=(0, 2),
        )
        self.console.print(panel)

    def print_warning(self, message: str, title: str = "警告") -> None:
        """
        打印警告消息。

        使用黄色边框的 Panel 显示警告消息,提醒用户注意。

        Args:
            message: 警告消息内容
            title: Panel 的标题,默认为"警告"

        Example:
            >>> ui = UIConsole()
            >>> ui.print_warning("配置文件使用默认值")
        """
        panel = Panel(
            f"[bold yellow]⚠[/] {message}",
            title=f"[bold yellow]{title}[/]",
            border_style="yellow",
            padding=(0, 2),
        )
        self.console.print(panel)

    def print_info(self, message: str, title: str = "信息") -> None:
        """
        打印一般信息消息。

        使用蓝色边框的 Panel 显示信息,用于一般性通知。

        Args:
            message: 信息消息内容
            title: Panel 的标题,默认为"信息"

        Example:
            >>> ui = UIConsole()
            >>> ui.print_info("正在处理文档...")
        """
        panel = Panel(
            f"[bold blue]ℹ[/] {message}",
            title=f"[bold blue]{title}[/]",
            border_style="blue",
            padding=(0, 2),
        )
        self.console.print(panel)

    def create_result_table(
        self,
        columns: List[str],
        title: Optional[str] = None,
        show_header: bool = True,
        header_style: str = "bold magenta",
    ) -> Table:
        """
        创建用于展示查询结果的表格。

        创建一个 Rich Table 对象,预配置列和样式。

        Args:
            columns: 列名列表
            title: 可选的表格标题
            show_header: 是否显示表头,默认为 True
            header_style: 表头样式,默认为 "bold magenta"

        Returns:
            配置好的 Rich Table 对象

        Example:
            >>> ui = UIConsole()
            >>> table = ui.create_result_table(["ID", "名称", "类型"], "实体列表")
            >>> table.add_row("1", "心脏", "器官")
            >>> ui.console.print(table)
        """
        table = Table(title=title, show_header=show_header, header_style=header_style)
        for column in columns:
            # 根据列类型自动设置样式和对齐
            if column.lower() in ["id", "数量", "分数"]:
                table.add_column(column, style="cyan", no_wrap=True, justify="right")
            else:
                table.add_column(column, style="white")
        return table

    def print_table(self, table: Table) -> None:
        """
        打印表格到控制台。

        Args:
            table: Rich Table 对象

        Example:
            >>> ui = UIConsole()
            >>> table = ui.create_result_table(["列1", "列2"])
            >>> table.add_row("值1", "值2")
            >>> ui.print_table(table)
        """
        self.console.print(table)

    def create_progress(self) -> Progress:
        """
        创建进度条对象。

        创建并返回一个配置好的 Progress 对象,用于长时间运行的操作。

        Returns:
            配置好的 Progress 对象

        Example:
            >>> ui = UIConsole()
            >>> progress = ui.create_progress()
            >>> with progress:
            ...     task = progress.add_task("处理中...", total=100)
            ...     for i in range(100):
            ...         progress.update(task, advance=1)
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
        )

    @contextmanager
    def show_progress(
        self,
        description: str = "处理中...",
        total: Optional[int] = None,
    ) -> Generator[tuple[Progress, TaskID], None, None]:
        """
        显示进度条的上下文管理器。

        用于长时间运行的操作,显示实时进度。

        Args:
            description: 进度条描述文本
            total: 总任务数,如果为 None 则为不确定进度

        Yields:
            元组 (Progress, TaskID),可用于更新进度

        Example:
            >>> ui = UIConsole()
            >>> with ui.show_progress("处理文档", total=100) as (progress, task):
            ...     for i in range(100):
            ...         progress.update(task, advance=1)
        """
        progress = self.create_progress()
        with progress:
            task = progress.add_task(description, total=total)
            yield progress, task

    @contextmanager
    def show_status(
        self,
        message: str,
        spinner: str = "dots",
    ) -> Generator[Status, None, None]:
        """
        显示状态指示器的上下文管理器。

        用于不确定时长的操作,显示动画 spinner。

        Args:
            message: 状态消息
            spinner: spinner 样式名称

        Yields:
            Status 对象

        Example:
            >>> ui = UIConsole()
            >>> with ui.show_status("连接数据库..."):
            ...     connect_to_database()
        """
        with self.console.status(
            f"[bold green]{message}[/]",
            spinner=spinner,
        ) as status:
            yield status

    def print_code(
        self,
        code: str,
        language: str = "python",
        title: Optional[str] = None,
        line_numbers: bool = True,
    ) -> None:
        """
        打印语法高亮的代码。

        使用 Rich Syntax 组件显示带语法高亮的代码。

        Args:
            code: 代码内容
            language: 编程语言,默认为 "python"
            title: 可选的代码标题
            line_numbers: 是否显示行号,默认为 True

        Example:
            >>> ui = UIConsole()
            >>> ui.print_code("print('Hello, World!')", "python")
        """
        syntax = Syntax(
            code,
            language,
            line_numbers=line_numbers,
            theme="monokai",
        )
        if title:
            panel = Panel(syntax, title=title, border_style="bright_blue")
            self.console.print(panel)
        else:
            self.console.print(syntax)

    def print_dict(self, data: dict[str, Any], title: Optional[str] = None) -> None:
        """
        以表格形式打印字典数据。

        Args:
            data: 要显示的字典
            title: 可选的表格标题

        Example:
            >>> ui = UIConsole()
            >>> ui.print_dict({"name": "张三", "age": "30"}, "用户信息")
        """
        table = self.create_result_table(["键", "值"], title=title)
        for key, value in data.items():
            table.add_row(str(key), str(value))
        self.console.print(table)

    def print_list(
        self,
        items: List[Any],
        title: Optional[str] = None,
        numbered: bool = True,
    ) -> None:
        """
        打印列表数据。

        Args:
            items: 要显示的列表
            title: 可选的标题
            numbered: 是否添加序号,默认为 True

        Example:
            >>> ui = UIConsole()
            >>> ui.print_list(["项目1", "项目2", "项目3"], "任务列表")
        """
        if title:
            self.console.print(f"\n[bold cyan]{title}[/]\n")
        for i, item in enumerate(items, 1):
            prefix = f"{i}. " if numbered else "• "
            self.console.print(f"[white]{prefix}[/]{item}")

    def clear_screen(self) -> None:
        """清空控制台屏幕。"""
        self.console.clear()

    def print_separator(self, char: str = "─", length: int = 80) -> None:
        """
        打印分隔线。

        Args:
            char: 分隔线字符
            length: 分隔线长度
        """
        self.console.print(char * length)

    def print_json(self, data: Any) -> None:
        """
        打印 JSON 格式的数据。

        Args:
            data: 要打印的数据(可被 JSON 序列化)
        """
        self.console.print_json(data=data)


# 全局单例实例
console_instance = UIConsole()


# 便捷函数,直接使用全局实例
def print_success(message: str, title: str = "成功") -> None:
    """
    打印成功消息的便捷函数。

    Args:
        message: 成功消息
        title: 标题
    """
    console_instance.print_success(message, title)


def print_error(
    message: str, title: str = "错误", subtitle: Optional[str] = None
) -> None:
    """
    打印错误消息的便捷函数。

    Args:
        message: 错误消息
        title: 标题
        subtitle: 副标题
    """
    console_instance.print_error(message, title, subtitle)


def print_warning(message: str, title: str = "警告") -> None:
    """
    打印警告消息的便捷函数。

    Args:
        message: 警告消息
        title: 标题
    """
    console_instance.print_warning(message, title)


def print_info(message: str, title: str = "信息") -> None:
    """
    打印信息消息的便捷函数。

    Args:
        message: 信息消息
        title: 标题
    """
    console_instance.print_info(message, title)


def create_result_table(
    columns: List[str],
    title: Optional[str] = None,
    show_header: bool = True,
    header_style: str = "bold magenta",
) -> Table:
    """
    创建结果表格的便捷函数。

    Args:
        columns: 列名列表
        title: 表格标题
        show_header: 是否显示表头
        header_style: 表头样式

    Returns:
        Rich Table 对象
    """
    return console_instance.create_result_table(
        columns, title, show_header, header_style
    )


@contextmanager
def show_progress(
    description: str = "处理中...",
    total: Optional[int] = None,
) -> Generator[tuple[Progress, TaskID], None, None]:
    """
    显示进度条的便捷函数。

    Args:
        description: 描述文本
        total: 总任务数

    Yields:
        元组 (Progress, TaskID)
    """
    with console_instance.show_progress(description, total) as result:
        yield result


@contextmanager
def show_status(message: str, spinner: str = "dots") -> Generator[Status, None, None]:
    """
    显示状态指示器的便捷函数。

    Args:
        message: 状态消息
        spinner: spinner 样式

    Yields:
        Status 对象
    """
    with console_instance.show_status(message, spinner) as status:
        yield status


def print_code(
    code: str,
    language: str = "python",
    title: Optional[str] = None,
    line_numbers: bool = True,
) -> None:
    """
    打印代码的便捷函数。

    Args:
        code: 代码内容
        language: 编程语言
        title: 标题
        line_numbers: 是否显示行号
    """
    console_instance.print_code(code, language, title, line_numbers)


def get_console() -> Console:
    """
    获取全局 Console 实例。

    Returns:
        Rich Console 对象
    """
    return console_instance.console


__all__ = [
    # 主要类
    "UIConsole",
    # 全局实例
    "console_instance",
    # 便捷函数
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "create_result_table",
    "show_progress",
    "show_status",
    "print_code",
    "get_console",
]
