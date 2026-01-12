"""
介入性治疗 CLI 命令模块。

该模块提供介入性治疗相关的命令行界面（CLI）命令，
用于与 Medical Graph RAG 系统的介入性治疗智能体进行交互。

主要命令:
- medgraph interventional plan: 术前规划
- medgraph interventional devices: 器械推荐
- medgraph interventional guidelines: 临床指南查询
- medgraph interventional simulate: 手术模拟
- medgraph interventional risk: 风险评估
- medgraph interventional postop: 术后护理规划

使用示例:
    # 术前规划
    medgraph interventional plan --procedure-type PCI --age 65 --diagnosis 冠心病

    # 查询临床指南
    medgraph interventional guidelines --procedure-type PCI

    # 手术模拟
    medgraph interventional simulate --procedure-type PCI --age 65

    # 风险评估
    medgraph interventional risk --procedure-type PCI --age 75

基于 Typer 框架构建。
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

# 导入 SDK
from src.sdk.interventional import (
    InterventionalClient,
    InterventionalPlan,
    PreopRiskAssessment,
    DeviceRecommendation,
    GuidelineInfo,
    PostopCarePlan,
)
from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError as SDKConfigError,
)

# ========== 全局配置 ==========

console = Console()

# 创建 Typer 应用
app = typer.Typer(
    name="interventional",
    help="介入性治疗规划 - 术前评估、器械推荐、风险评估和手术模拟",
    add_completion=True,
    rich_markup_mode="rich",
)


# ========== 辅助函数 ==========


async def create_client() -> InterventionalClient:
    """创建介入性治疗客户端。

    Returns:
        InterventionalClient: 客户端实例

    Raises:
        typer.Exit: 创建客户端失败时退出
    """
    try:
        client = InterventionalClient()
        await client.__aenter__()
        return client

    except SDKConfigError as e:
        console.print(f"[red]配置错误: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]创建客户端失败: {e}[/red]")
        raise typer.Exit(code=1)


def display_interventional_plan(plan: InterventionalPlan) -> None:
    """显示术前规划结果。

    Args:
        plan: 术前规划结果
    """
    # 显示基本信息
    console.print(
        Panel(
            f"[bold cyan]手术类型:[/] {plan.procedure_type}\n"
            f"[bold cyan]置信度:[/] {plan.confidence_score:.2f}\n"
            f"[bold cyan]推理步骤:[/] {len(plan.reasoning_steps)}",
            title="术前规划结果",
            border_style="cyan",
        )
    )

    # 显示首选方案
    if plan.primary_plan:
        console.print("\n[bold green]首选方案[/bold green]")
        console.print(json.dumps(plan.primary_plan, ensure_ascii=False, indent=2))

    # 显示备选方案
    if plan.alternative_plan:
        console.print("\n[bold yellow]备选方案[/bold yellow]")
        console.print(json.dumps(plan.alternative_plan, ensure_ascii=False, indent=2))

    # 显示器械推荐
    if plan.device_recommendations:
        console.print("\n[bold]器械推荐[/bold]")
        for i, device in enumerate(plan.device_recommendations[:5], 1):
            if isinstance(device, dict):
                name = device.get("device_name", "未知")
                device_type = device.get("device_type", "未知")
                rationale = device.get("rationale", "")
                console.print(f"  {i}. [cyan]{name}[/cyan] ({device_type})")
                if rationale:
                    console.print(f"     [dim]{rationale}[/dim]")

    # 显示风险评估
    if plan.risk_assessment:
        console.print("\n[bold red]风险评估[/bold red]")
        for i, risk in enumerate(plan.risk_assessment[:5], 1):
            if isinstance(risk, dict):
                factor = risk.get("factor", "未知")
                impact = risk.get("impact", "未知")
                console.print(f"  {i}. {factor} ([yellow]{impact}[/yellow])")

    # 显示推荐方案（Markdown 格式）
    if plan.recommendations:
        console.print("\n[bold]完整推荐方案[/bold]")
        markdown = Markdown(plan.recommendations)
        console.print(markdown)


def display_device_recommendations(devices: List[DeviceRecommendation]) -> None:
    """显示器械推荐结果。

    Args:
        devices: 器械推荐列表
    """
    table = Table(title="器械推荐")
    table.add_column("序号", style="cyan")
    table.add_column("器械名称", style="green")
    table.add_column("类型", style="yellow")
    table.add_column("选择理由", style="dim")

    for i, device in enumerate(devices, 1):
        table.add_row(
            str(i),
            device.device_name,
            device.device_type,
            device.rationale[:50] + "..."
            if len(device.rationale) > 50
            else device.rationale,
        )

    console.print(table)


def display_guidelines(guidelines: List[GuidelineInfo]) -> None:
    """显示临床指南结果。

    Args:
        guidelines: 临床指南列表
    """
    table = Table(title="临床指南")
    table.add_column("序号", style="cyan")
    table.add_column("来源", style="green")
    table.add_column("年份", style="yellow")
    table.add_column("标题", style="dim")
    table.add_column("证据等级", style="red")

    for i, guideline in enumerate(guidelines, 1):
        table.add_row(
            str(i),
            guideline.source,
            str(guideline.year),
            guideline.title[:40] + "..."
            if len(guideline.title) > 40
            else guideline.title,
            guideline.evidence_level,
        )

    console.print(table)


def display_risk_assessment(risks: PreopRiskAssessment) -> None:
    """显示风险评估结果。

    Args:
        risks: 风险评估结果
    """
    # 显示风险等级
    risk_color = {
        "low": "green",
        "medium": "yellow",
        "high": "orange",
        "critical": "red",
    }.get(risks.overall_risk_level, "dim")

    console.print(
        Panel(
            f"[bold {risk_color}]整体风险等级:[/] {risks.overall_risk_level.upper()}\n"
            f"[bold cyan]评估置信度:[/] {risks.confidence:.2f}\n"
            f"[bold cyan]风险因素数:[/] {len(risks.primary_risk_factors)}",
            title="术前风险评估",
            border_style=risk_color,
        )
    )

    # 显示主要风险因素
    if risks.primary_risk_factors:
        console.print("\n[bold red]主要风险因素[/bold red]")
        for i, risk in enumerate(risks.primary_risk_factors[:10], 1):
            if isinstance(risk, dict):
                factor = risk.get("factor", "未知")
                impact = risk.get("impact", "未知")
                console.print(f"  {i}. {factor} ([yellow]{impact}[/yellow])")

    # 显示风险缓解策略
    if risks.risk_mitigation_strategies:
        console.print("\n[bold green]风险缓解策略[/bold green]")
        for i, strategy in enumerate(risks.risk_mitigation_strategies[:5], 1):
            console.print(f"  {i}. {strategy}")

    # 显示禁忌症
    if risks.contraindications:
        console.print("\n[bold red]禁忌症[/bold red]")
        if risks.contraindications.get("absolute"):
            console.print("  [bold]绝对禁忌:[/bold]")
            for c in risks.contraindications["absolute"]:
                console.print(f"    [red]- {c}[/red]")
        if risks.contraindications.get("relative"):
            console.print("  [bold]相对禁忌:[/bold]")
            for c in risks.contraindications["relative"]:
                console.print(f"    [yellow]- {c}[/yellow]")


def display_postop_care(care_plan: PostopCarePlan) -> None:
    """显示术后护理计划。

    Args:
        care_plan: 术后护理计划
    """
    # 显示监测计划
    if care_plan.monitoring_plan:
        console.print("\n[bold cyan]监测计划[/bold cyan]")
        for i, item in enumerate(care_plan.monitoring_plan, 1):
            console.print(f"  {i}. {item}")

    # 显示用药计划
    if care_plan.medication_plan:
        console.print("\n[bold green]用药计划[/bold green]")
        for i, med in enumerate(care_plan.medication_plan, 1):
            if isinstance(med, dict):
                name = med.get("medication", "未知")
                dosage = med.get("dosage", "")
                duration = med.get("duration", "")
                console.print(f"  {i}. [cyan]{name}[/cyan] - {dosage} ({duration})")

    # 显示活动限制
    if care_plan.activity_restrictions:
        console.print("\n[bold yellow]活动限制[/bold yellow]")
        for i, restriction in enumerate(care_plan.activity_restrictions, 1):
            console.print(f"  {i}. {restriction}")

    # 显示随访安排
    if care_plan.follow_up_schedule:
        console.print("\n[bold]随访安排[/bold]")
        for i, followup in enumerate(care_plan.follow_up_schedule, 1):
            if isinstance(followup, dict):
                time = followup.get("time", "")
                purpose = followup.get("purpose", "")
                console.print(f"  {i}. [cyan]{time}[/cyan]: {purpose}")

    # 显示警示信号
    if care_plan.warning_signs:
        console.print("\n[bold red]警示信号[/bold red]")
        console.print("  如出现以下情况请立即就医：")
        for sign in care_plan.warning_signs:
            console.print(f"    [red]- {sign}[/red]")


# ========== 命令实现 ==========


@app.command("plan")
def plan_intervention(
    procedure_type: str = typer.Option(
        ...,
        "--procedure-type",
        "-p",
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    age: int = typer.Option(
        ...,
        "--age",
        "-a",
        help="患者年龄",
    ),
    gender: str = typer.Option(
        "male",
        "--gender",
        "-g",
        help="患者性别（male, female, other）",
    ),
    diagnosis: List[str] = typer.Option(
        [],
        "--diagnosis",
        "-d",
        help="诊断列表（可多次使用）",
    ),
    comorbidities: List[str] = typer.Option(
        [],
        "--comorbidity",
        "-c",
        help="合并症列表（可多次使用）",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="输出格式（text, json）",
    ),
    include_alternatives: bool = typer.Option(
        True,
        "--include-alternatives/--no-alternatives",
        help="是否包含备选方案",
    ),
):
    """术前规划。

    执行完整的术前评估工作流，生成个性化手术方案建议。
    """

    async def _plan() -> None:
        try:
            client = await create_client()

            # 构建患者数据
            patient_data = {
                "age": age,
                "gender": gender,
                "diagnosis": diagnosis,
                "comorbidities": comorbidities,
            }

            console.print(
                f"[bold cyan]术前规划[/bold cyan] | "
                f"手术: {procedure_type} | "
                f"患者: {age}岁 {gender}"
            )

            # 执行术前规划
            plan = await client.plan_intervention(
                patient_data=patient_data,
                procedure_type=procedure_type,
            )

            if output == "json":
                # JSON 输出
                console.print_json(plan.to_dict())
            else:
                # 文本输出
                display_interventional_plan(plan)

        except MedGraphSDKError as e:
            console.print(f"[red]规划失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]规划异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_plan())


@app.command("devices")
def get_devices(
    procedure_type: str = typer.Option(
        ...,
        "--procedure-type",
        "-p",
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    age: int = typer.Option(
        65,
        "--age",
        "-a",
        help="患者年龄",
    ),
    gender: str = typer.Option(
        "male",
        "--gender",
        "-g",
        help="患者性别",
    ),
    anatomy: Optional[str] = typer.Option(
        None,
        "--anatomy",
        help="解剖特点描述",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="输出格式（text, json）",
    ),
):
    """器械推荐。

    根据患者特征和手术类型推荐合适的介入器械。
    """

    async def _devices() -> None:
        try:
            client = await create_client()

            # 构建患者数据
            patient_data = {
                "age": age,
                "gender": gender,
                "diagnosis": [],
                "comorbidities": [],
            }

            if anatomy:
                patient_data["imaging_findings"] = [anatomy]

            console.print(
                f"[bold cyan]器械推荐[/bold cyan] | "
                f"手术: {procedure_type} | "
                f"患者: {age}岁"
            )

            # 获取器械推荐
            devices = await client.get_device_recommendations(
                patient_data=patient_data,
                procedure_type=procedure_type,
            )

            if output == "json":
                # JSON 输出
                console.print_json([d.to_dict() for d in devices])
            else:
                # 文本输出
                display_device_recommendations(devices)

        except MedGraphSDKError as e:
            console.print(f"[red]器械推荐失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]器械推荐异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_devices())


@app.command("guidelines")
def get_guidelines(
    procedure_type: str = typer.Argument(
        ...,
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="返回数量限制",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="输出格式（text, json）",
    ),
):
    """临床指南查询。

    检索特定手术类型相关的临床指南和循证医学证据。
    """

    async def _guidelines() -> None:
        try:
            client = await create_client()

            console.print(
                f"[bold cyan]临床指南查询[/bold cyan] | 手术: {procedure_type}"
            )

            # 获取临床指南
            guidelines = await client.get_guidelines(
                procedure_type=procedure_type,
                limit=limit,
            )

            if not guidelines:
                console.print("[yellow]未找到相关指南[/yellow]")
                return

            if output == "json":
                # JSON 输出
                console.print_json([g.to_dict() for g in guidelines])
            else:
                # 文本输出
                display_guidelines(guidelines)

        except MedGraphSDKError as e:
            console.print(f"[red]指南查询失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]指南查询异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_guidelines())


@app.command("simulate")
def simulate_procedure(
    procedure_type: str = typer.Option(
        ...,
        "--procedure-type",
        "-p",
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    age: int = typer.Option(
        65,
        "--age",
        "-a",
        help="患者年龄",
    ),
    gender: str = typer.Option(
        "male",
        "--gender",
        "-g",
        help="患者性别",
    ),
    diagnosis: List[str] = typer.Option(
        [],
        "--diagnosis",
        "-d",
        help="诊断列表",
    ),
    detail_level: str = typer.Option(
        "standard",
        "--detail",
        "-D",
        help="详细程度（basic, standard, detailed）",
    ),
):
    """手术模拟。

    以流式方式生成手术模拟过程，包括术前准备、手术步骤和注意事项。
    """

    async def _simulate() -> None:
        try:
            client = await create_client()

            # 构建患者数据
            patient_data = {
                "age": age,
                "gender": gender,
                "diagnosis": diagnosis,
                "comorbidities": [],
            }

            console.print(
                f"[bold cyan]手术模拟[/bold cyan] | "
                f"手术: {procedure_type} | "
                f"患者: {age}岁\n"
            )

            # 流式模拟
            async for chunk in client.simulate_procedure(
                patient_data=patient_data,
                procedure_type=procedure_type,
                detail_level=detail_level,
            ):
                console.print(chunk, end="")

            console.print()  # 换行
            console.print("\n[bold green]✓[/bold green] 模拟完成")

        except MedGraphSDKError as e:
            console.print(f"\n[red]模拟失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"\n[red]模拟异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_simulate())


@app.command("risk")
def assess_risks(
    procedure_type: str = typer.Option(
        ...,
        "--procedure-type",
        "-p",
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    age: int = typer.Option(
        ...,
        "--age",
        "-a",
        help="患者年龄",
    ),
    gender: str = typer.Option(
        "male",
        "--gender",
        "-g",
        help="患者性别",
    ),
    comorbidities: List[str] = typer.Option(
        [],
        "--comorbidity",
        "-c",
        help="合并症列表（可多次使用）",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="输出格式（text, json）",
    ),
):
    """术前风险评估。

    评估患者进行特定手术的风险等级和主要风险因素。
    """

    async def _risk() -> None:
        try:
            client = await create_client()

            # 构建患者数据
            patient_data = {
                "age": age,
                "gender": gender,
                "diagnosis": [],
                "comorbidities": comorbidities,
            }

            console.print(
                f"[bold cyan]术前风险评估[/bold cyan] | "
                f"手术: {procedure_type} | "
                f"患者: {age}岁"
            )

            # 执行风险评估
            risks = await client.assess_preop_risks(
                patient_data=patient_data,
                procedure_type=procedure_type,
            )

            if output == "json":
                # JSON 输出
                console.print_json(risks.to_dict())
            else:
                # 文本输出
                display_risk_assessment(risks)

        except MedGraphSDKError as e:
            console.print(f"[red]风险评估失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]风险评估异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_risk())


@app.command("postop")
def plan_postop_care(
    procedure_type: str = typer.Option(
        ...,
        "--procedure-type",
        "-p",
        help="手术类型（PCI, CAS, TAVI 等）",
    ),
    age: int = typer.Option(
        ...,
        "--age",
        "-a",
        help="患者年龄",
    ),
    gender: str = typer.Option(
        "male",
        "--gender",
        "-g",
        help="患者性别",
    ),
    comorbidities: List[str] = typer.Option(
        [],
        "--comorbidity",
        "-c",
        help="合并症列表（可多次使用）",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        "-o",
        help="输出格式（text, json）",
    ),
):
    """术后护理规划。

    生成个性化术后护理计划。
    """

    async def _postop() -> None:
        try:
            client = await create_client()

            # 构建患者数据
            patient_data = {
                "age": age,
                "gender": gender,
                "diagnosis": [],
                "comorbidities": comorbidities,
            }

            console.print(
                f"[bold cyan]术后护理规划[/bold cyan] | "
                f"手术: {procedure_type} | "
                f"患者: {age}岁"
            )

            # 生成护理计划
            care_plan = await client.plan_postop_care(
                patient_data=patient_data,
                procedure_type=procedure_type,
            )

            if output == "json":
                # JSON 输出
                console.print_json(care_plan.to_dict())
            else:
                # 文本输出
                console.print(
                    Panel(
                        "[bold green]术后护理计划[/bold green]",
                        border_style="green",
                    )
                )
                display_postop_care(care_plan)

        except MedGraphSDKError as e:
            console.print(f"[red]护理规划失败: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]护理规划异常: {e}[/red]")
            raise typer.Exit(code=1)
        finally:
            if "client" in locals():
                await client.__aexit__(None, None, None)

    asyncio.run(_postop())


__all__ = ["app"]
