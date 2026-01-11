#!/usr/bin/env python3
"""
UI 模块演示脚本

展示各种 UI 组件的使用方法。
"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cli.ui import (
    console_instance,
    create_result_table,
    print_code,
    print_error,
    print_info,
    print_success,
    print_warning,
    show_progress,
    show_status,
)


def demo_messages():
    """演示各种消息类型。"""
    print("\n" + "=" * 80)
    print("UI 消息类型演示")
    print("=" * 80 + "\n")

    # 成功消息
    print_success("文档处理成功完成!", "操作成功")

    # 错误消息
    print_error(
        "无法连接到 Neo4j 数据库",
        "连接失败",
        "请检查数据库服务是否运行以及配置是否正确",
    )

    # 警告消息
    print_warning("配置文件未找到,使用默认配置", "配置警告")

    # 信息消息
    print_info("正在初始化向量数据库...", "系统信息")


def demo_tables():
    """演示表格功能。"""
    print("\n" + "=" * 80)
    print("表格演示")
    print("=" * 80 + "\n")

    # 实体列表表格
    table = create_result_table(
        ["ID", "实体名称", "类型", "置信度"],
        title="医学知识图谱 - 实体列表",
    )
    table.add_row("1", "心脏", "器官", "0.98")
    table.add_row("2", "高血压", "疾病", "0.95")
    table.add_row("3", "阿司匹林", "药物", "0.92")
    table.add_row("4", "血液循环", "生理过程", "0.89")

    console_instance.print_table(table)

    # 关系列表表格
    relation_table = create_result_table(
        ["源实体", "关系", "目标实体", "权重"],
        title="实体关系",
    )
    relation_table.add_row("高血压", "导致", "心脏病", "0.87")
    relation_table.add_row("阿司匹林", "治疗", "心脏病", "0.91")
    relation_table.add_row("心脏", "参与", "血液循环", "0.99")

    console_instance.print_table(relation_table)


def demo_code():
    """演示代码高亮。"""
    print("\n" + "=" * 80)
    print("代码高亮演示")
    print("=" * 80 + "\n")

    python_code = '''
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

class GraphState(TypedDict):
    """图状态定义"""
    query: str
    context: list[str]
    answer: str
    steps: Annotated[list[str], add]

def retrieve_node(state: GraphState) -> GraphState:
    """检索节点"""
    # 实现检索逻辑
    return {"context": ["相关文档片段"]}

def generate_node(state: GraphState) -> GraphState:
    """生成节点"""
    # 实现生成逻辑
    return {"answer": "生成的答案"}

# 构建图
workflow = StateGraph(GraphState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
'''

    print_code(python_code, "python", "LangGraph 工作流示例")


def demo_progress():
    """演示进度条。"""
    print("\n" + "=" * 80)
    print("进度条演示")
    print("=" * 80 + "\n")

    with show_progress("处理医学文档", total=100) as (progress, task):
        for i in range(100):
            time.sleep(0.02)
            progress.update(task, advance=1)

    print_success("所有文档处理完成!")


def demo_status():
    """演示状态指示器。"""
    print("\n" + "=" * 80)
    print("状态指示器演示")
    print("=" * 80 + "\n")

    with show_status("连接到向量数据库..."):
        time.sleep(2)

    print_success("数据库连接成功!")


def demo_dict_and_list():
    """演示字典和列表打印。"""
    print("\n" + "=" * 80)
    print("字典和列表演示")
    print("=" * 80 + "\n")

    # 字典数据
    entity_data = {
        "名称": "冠状动脉粥样硬化性心脏病",
        "别名": "冠心病",
        "类型": "心血管疾病",
        "ICD-10编码": "I25",
        "发病率": "约 2.2%",
        "主要症状": "胸痛、气短、乏力",
    }

    console_instance.print_dict(entity_data, "实体详情")

    print("\n")

    # 列表数据
    treatments = [
        "药物治疗: 抗血小板药物、他汀类药物",
        "介入治疗: 经皮冠状动脉介入治疗(PCI)",
        "手术治疗: 冠状动脉旁路移植术(CABG)",
        "生活方式干预: 戒烟、健康饮食、适量运动",
    ]

    console_instance.print_list(treatments, "治疗方案")


def demo_separator():
    """演示分隔线。"""
    print("\n" + "=" * 80)
    print("分隔线演示")
    print("=" * 80 + "\n")

    print_info("这是第一部分内容")
    console_instance.print_separator("─", 80)
    print_info("这是第二部分内容")
    console_instance.print_separator("=", 80)
    print_info("这是第三部分内容")


def main():
    """运行所有演示。"""
    console_instance.clear_screen()

    # 标题
    console_instance.console.print(
        "\n[bold cyan]Medical Graph RAG - UI 模块演示[/bold cyan]\n"
    )
    console_instance.print_separator("═", 80)

    try:
        demo_messages()
        demo_tables()
        demo_code()
        demo_progress()
        demo_status()
        demo_dict_and_list()
        demo_separator()

        # 结束
        console_instance.print_separator("═", 80)
        print_success("所有演示完成!", "完成")

    except KeyboardInterrupt:
        print_warning("\n演示被用户中断")
    except Exception as e:
        print_error(f"演示过程中发生错误: {e}", "错误")


if __name__ == "__main__":
    main()
