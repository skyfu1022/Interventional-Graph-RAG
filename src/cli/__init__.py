"""
Medical Graph RAG CLI 模块。

提供命令行界面（CLI）用于与 Medical Graph RAG 系统交互。

主要命令:
- build: 构建知识图谱
- query: 查询知识图谱
- ingest: 摄入文档
- serve: 启动 API 服务器
- export: 导出图谱数据
- info: 显示系统或图谱信息

使用示例:
    >>> from src.cli import main
    >>> main.app()  # 运行 CLI 应用

或在命令行中:
    $ python -m src.cli.main --help
    $ python -m src.cli.main query "什么是糖尿病?"
"""

from src.cli.main import app

__all__ = ["app"]
