# CLI UI 工具模块使用指南

## 概述

`src/cli/ui.py` 模块提供了统一的终端用户界面组件,基于 Rich 库实现美观的输出格式。

## 文件位置

- **UI 模块**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/cli/ui.py`
- **演示脚本**: `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/examples/ui_demo.py`

## 快速开始

### 基本使用

```python
from src.cli.ui import (
    print_success,
    print_error,
    print_warning,
    print_info,
    create_result_table,
    console_instance,
)

# 打印各种消息
print_success("操作成功完成!")
print_error("发生错误", "错误标题", "错误详情")
print_warning("这是一条警告")
print_info("系统正在处理...")

# 创建和显示表格
table = create_result_table(["ID", "名称", "类型"], "数据列表")
table.add_row("1", "实体1", "类型A")
table.add_row("2", "实体2", "类型B")
console_instance.print_table(table)
```

### 进度条

```python
from src.cli.ui import show_progress

# 使用进度条
with show_progress("处理文档", total=100) as (progress, task):
    for i in range(100):
        # 执行操作
        progress.update(task, advance=1)
```

### 状态指示器

```python
from src.cli.ui import show_status

# 使用状态指示器(用于不确定时长的操作)
with show_status("连接数据库..."):
    # 执行连接操作
    connect_to_database()
```

### 代码高亮

```python
from src.cli.ui import print_code

code = '''
def hello():
    print("Hello, World!")
'''

print_code(code, "python", "代码示例")
```

## 主要功能

### 1. 消息类型

- `print_success(message, title)` - 绿色成功消息
- `print_error(message, title, subtitle)` - 红色错误消息
- `print_warning(message, title)` - 黄色警告消息
- `print_info(message, title)` - 蓝色信息消息

### 2. 表格功能

- `create_result_table(columns, title)` - 创建结果表格
- `console_instance.print_table(table)` - 打印表格
- `console_instance.print_dict(data, title)` - 以表格形式打印字典
- `console_instance.print_list(items, title, numbered)` - 打印列表

### 3. 进度显示

- `show_progress(description, total)` - 显示进度条
- `show_status(message, spinner)` - 显示状态指示器

### 4. 代码高亮

- `print_code(code, language, title, line_numbers)` - 打印语法高亮的代码

### 5. 其他工具

- `console_instance.clear_screen()` - 清空屏幕
- `console_instance.print_separator(char, length)` - 打印分隔线
- `console_instance.print_json(data)` - 打印 JSON 格式数据

## UIConsole 类

如果需要更多控制,可以直接使用 `UIConsole` 类:

```python
from src.cli.ui import UIConsole

ui = UIConsole()

# 使用所有功能
ui.print_success("成功!")
ui.print_error("失败!", "错误", "详情")
ui.print_warning("警告")
ui.print_info("信息")

table = ui.create_result_table(["列1", "列2"])
table.add_row("值1", "值2")
ui.print_table(table)
```

## 运行演示

查看完整的功能演示:

```bash
python examples/ui_demo.py
```

## 设计原则

1. **统一风格**: 所有 CLI 命令使用相同的 UI 风格
2. **语义化颜色**: 成功(绿)、错误(红)、警告(黄)、信息(蓝)
3. **上下文管理**: 进度条和状态指示器使用上下文管理器
4. **类型安全**: 完整的类型提示,支持 mypy 静态检查
5. **文档完善**: 所有函数都有 Google 风格的文档字符串

## 技术细节

- **基础库**: Rich 13.0+
- **Python 版本**: 3.10+
- **类型检查**: mypy (严格模式)
- **代码风格**: PEP 8, 使用 ruff 格式化

## 集成到现有 CLI

在 CLI 命令中使用 UI 模块:

```python
import typer
from src.cli.ui import print_success, print_error, show_progress

app = typer.Typer()

@app.command()
def process_documents():
    """处理文档"""
    try:
        with show_progress("处理文档", total=100) as (progress, task):
            # 处理逻辑
            for i in range(100):
                process_item(i)
                progress.update(task, advance=1)
        print_success("所有文档处理完成!")
    except Exception as e:
        print_error(f"处理失败: {e}")
        raise typer.Exit(1)
```

## 注意事项

1. 确保在虚拟环境中运行
2. Rich 已在 `requirements.txt` 中声明依赖
3. 所有输出都使用 UTF-8 编码
4. 颜色和样式在终端中效果最佳
