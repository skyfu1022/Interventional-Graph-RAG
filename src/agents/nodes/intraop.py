"""介入手术术中执行节点模块。

该模块实现了介入手术术中执行的所有节点函数，包括：
- execute_procedure_node(): 执行术式
- monitor_complications_node(): 监测并发症
- handle_events_node(): 处理术中事件

每个节点都是独立的、可测试的函数，接收 ExtendedInterventionalState
并返回更新后的状态字典。
"""

from typing import Any, Dict, List, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from src.agents.states import ExtendedInterventionalState
from src.agents.models import (
    ReasoningStepModel,
    RiskFactorModel,
    Severity,
    Phase,
)
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.agents.nodes.intraop")


# ==================== 术中执行输出模型 ====================


class ProcedureExecutionOutput(BaseModel):
    """术中执行输出模型。

    用于 LLM 结构化输出的术中执行结果。

    Attributes:
        execution_status: 执行状态（进行中/已完成/暂停/中止）
        completed_steps: 已完成的步骤列表
        current_step: 当前执行步骤
        next_step: 下一步骤
        devices_used: 已使用的器械列表
        unexpected_events: 意外事件列表
        confidence: 执行置信度
        reasoning: 执行推理说明
    """

    execution_status: Literal["in_progress", "completed", "paused", "aborted"] = Field(
        ..., description="执行状态"
    )
    completed_steps: List[str] = Field(
        default_factory=list, description="已完成的步骤列表"
    )
    current_step: str = Field(..., description="当前执行步骤")
    next_step: Optional[str] = Field(None, description="下一步骤")
    devices_used: List[Dict[str, Any]] = Field(
        default_factory=list, description="已使用的器械列表"
    )
    unexpected_events: List[str] = Field(
        default_factory=list, description="意外事件列表"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="执行置信度")
    reasoning: str = Field(..., description="执行推理说明")


class ComplicationMonitoringOutput(BaseModel):
    """并发症监测输出模型。

    用于 LLM 结构化输出的并发症监测结果。

    Attributes:
        complications_detected: 检测到的并发症列表
        severity_levels: 严重程度等级列表
        recommended_actions: 推荐的应对措施列表
        requires_intervention: 是否需要立即干预
        confidence: 监测置信度
        reasoning: 监测推理说明
    """

    complications_detected: List[str] = Field(
        default_factory=list, description="检测到的并发症列表"
    )
    severity_levels: List[Severity] = Field(
        default_factory=list, description="严重程度等级列表"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="推荐的应对措施列表"
    )
    requires_intervention: bool = Field(default=False, description="是否需要立即干预")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="监测置信度")
    reasoning: str = Field(..., description="监测推理说明")


class EventHandlingOutput(BaseModel):
    """事件处理输出模型。

    用于 LLM 结构化输出的术中事件处理结果。

    Attributes:
        event_type: 事件类型
        event_severity: 事件严重程度
        handling_strategy: 处理策略
        alternative_actions: 替代行动列表
        impact_on_procedure: 对手术的影响
        recovery_plan: 恢复计划
        confidence: 处理置信度
        reasoning: 处理推理说明
    """

    event_type: str = Field(..., description="事件类型")
    event_severity: Severity = Field(..., description="事件严重程度")
    handling_strategy: str = Field(..., description="处理策略")
    alternative_actions: List[str] = Field(
        default_factory=list, description="替代行动列表"
    )
    impact_on_procedure: str = Field(..., description="对手术的影响")
    recovery_plan: Optional[str] = Field(None, description="恢复计划")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="处理置信度")
    reasoning: str = Field(..., description="处理推理说明")


# ==================== 术中执行节点 ====================


async def execute_procedure_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """执行术式节点。

    该节点负责：
    1. 基于手术方案执行术式步骤
    2. 跟踪步骤完成状态
    3. 记录使用的器械
    4. 更新执行进度

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含：
        - procedure_execution: 术中执行状态
        - reasoning_steps: 新增的推理步骤
        - error: 错误信息（如果有）

    Raises:
        ValueError: 如果缺少必要的手术方案

    Example:
        >>> state = {
        ...     "procedure_plan": {
        ...         "procedure_type": "PCI",
        ...         "steps": ["步骤1", "步骤2", "步骤3"],
        ...         "devices": [...]
        ...     },
        ...     "reasoning_steps": [],
        ... }
        >>> result = await execute_procedure_node(state)
        >>> assert "procedure_execution" in result
    """
    logger.info("[术中执行] 开始执行手术方案")

    # 获取手术方案
    procedure_plan = state.get("procedure_plan", {})
    reasoning_steps = state.get("reasoning_steps", [])

    procedure_execution = {}
    error = None

    try:
        # 检查手术方案是否存在
        if not procedure_plan:
            raise ValueError("缺少手术方案，无法执行术中步骤")

        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        # 提取手术方案信息
        if isinstance(procedure_plan, dict):
            procedure_type = procedure_plan.get("procedure_type", "未知手术")
            steps = procedure_plan.get("steps", [])
            devices = procedure_plan.get("devices", [])
            approach = procedure_plan.get("approach", "未知入路")
        else:
            # 假设是 ProcedurePlanModel
            procedure_type = str(procedure_plan.procedure_type)
            steps = procedure_plan.steps
            devices = [d.model_dump() for d in procedure_plan.devices]
            approach = procedure_plan.approach

        logger.info(
            f"[术中执行] 手术类型: {procedure_type}, "
            f"入路: {approach}, "
            f"步骤数: {len(steps)}, "
            f"器械数: {len(devices)}"
        )

        if llm:
            # 使用 LLM 模拟术中执行
            execution_output = await _simulate_execution_with_llm(
                llm, procedure_type, steps, devices, approach
            )
            procedure_execution = execution_output.model_dump()

            logger.info(
                f"[术中执行] LLM 模拟完成 | "
                f"状态: {execution_output.execution_status} | "
                f"完成步骤: {len(execution_output.completed_steps)}/{len(steps)}"
            )

        else:
            # 使用规则基础执行模拟
            execution_output = _simulate_execution_with_rules(
                procedure_type, steps, devices
            )
            procedure_execution = execution_output.model_dump()

            logger.info(
                f"[术中执行] 规则模拟完成 | "
                f"状态: {execution_output.execution_status} | "
                f"完成步骤: {len(execution_output.completed_steps)}/{len(steps)}"
            )

        # 创建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description=f"执行{procedure_type}手术方案",
            evidence=[
                f"手术类型: {procedure_type}",
                f"入路方式: {approach}",
                f"总步骤数: {len(steps)}",
            ],
            conclusion=f"执行状态: {procedure_execution['execution_status']}, "
            f"完成步骤: {len(procedure_execution.get('completed_steps', []))}",
        )

        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except ValueError as e:
        error = f"术中执行失败: {str(e)}"
        logger.error(f"[术中执行] 错误: {error}")

        # 记录错误推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description="执行手术方案",
            evidence=[],
            conclusion=f"执行失败: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except Exception as e:
        error = f"术中执行异常: {str(e)}"
        logger.error(f"[术中执行] 异常: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description="执行手术方案",
            evidence=[],
            conclusion=f"执行异常: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    return {
        "procedure_execution": procedure_execution,
        "reasoning_steps": reasoning_steps,
        "error": error,
    }


async def _simulate_execution_with_llm(
    llm: BaseChatModel,
    procedure_type: str,
    steps: List[str],
    devices: List[Dict[str, Any]],
    approach: str,
) -> ProcedureExecutionOutput:
    """使用 LLM 模拟术中执行。

    Args:
        llm: LLM 实例
        procedure_type: 手术类型
        steps: 手术步骤列表
        devices: 器械列表
        approach: 入路方式

    Returns:
        术中执行输出模型
    """
    # 构建执行提示
    devices_text = "\n".join(
        [
            f"- {d.get('device_type', 'N/A')}: {d.get('device_name', 'N/A')}"
            for d in devices[:5]
        ]
    )

    steps_text = "\n".join([f"{i + 1}. {step}" for i, step in enumerate(steps)])

    prompt = f"""请模拟以下介入手术的执行过程。

## 手术信息
- 手术类型: {procedure_type}
- 入路方式: {approach}

## 手术步骤
{steps_text}

## 所需器械
{devices_text}

## 执行模拟要求
请提供:
1. 执行状态（in_progress/completed/paused/aborted）
2. 已完成的步骤列表
3. 当前执行步骤
4. 下一步骤
5. 已使用的器械列表
6. 意外事件（如有）
7. 执行置信度（0-1）
8. 执行推理说明

假设手术正在进行中，模拟一个合理的执行进度（约30-50%完成）。
"""

    # 使用结构化输出
    structured_llm = llm.with_structured_output(ProcedureExecutionOutput)
    response: ProcedureExecutionOutput = await structured_llm.ainvoke(
        [
            SystemMessage(
                content="你是一个专业的介入手术执行模拟专家，"
                "擅长模拟各种介入手术的执行过程和术中状态。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    return response


def _simulate_execution_with_rules(
    procedure_type: str,
    steps: List[str],
    devices: List[Dict[str, Any]],
) -> ProcedureExecutionOutput:
    """使用规则模拟术中执行（后备方案）。

    Args:
        procedure_type: 手术类型
        steps: 手术步骤列表
        devices: 器械列表

    Returns:
        术中执行输出模型
    """
    # 计算执行进度（假设30-50%完成）
    total_steps = len(steps)
    completed_count = max(1, min(total_steps - 1, int(total_steps * 0.4)))

    completed_steps = steps[:completed_count]
    current_step = (
        steps[completed_count] if completed_count < total_steps else steps[-1]
    )
    next_step = (
        steps[completed_count + 1] if completed_count + 1 < total_steps else None
    )

    # 使用的器械（假设使用了前50%的器械）
    devices_used = devices[: max(1, len(devices) // 2)]

    return ProcedureExecutionOutput(
        execution_status="in_progress",
        completed_steps=completed_steps,
        current_step=current_step,
        next_step=next_step,
        devices_used=devices_used,
        unexpected_events=[],
        confidence=0.85,
        reasoning=f"基于规则模拟执行，已完成 {completed_count}/{total_steps} 步骤",
    )


# ==================== 并发症监测节点 ====================


async def monitor_complications_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """监测并发症节点。

    该节点负责：
    1. 基于患者风险因素和手术进度监测并发症
    2. 识别潜在并发症
    3. 评估严重程度
    4. 提供应对措施

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含：
        - complications_monitoring: 并发症监测结果
        - reasoning_steps: 新增的推理步骤
        - error: 错误信息（如果有）

    Example:
        >>> state = {
        ...     "risk_assessment": [...],
        ...     "procedure_execution": {...},
        ...     "patient_data": {...},
        ...     "reasoning_steps": [],
        ... }
        >>> result = await monitor_complications_node(state)
        >>> assert "complications_monitoring" in result
    """
    logger.info("[并发症监测] 开始监测术中并发症")

    # 获取相关数据
    risk_assessment = state.get("risk_assessment", [])
    procedure_execution = state.get("procedure_execution", {})
    patient_data = state.get("patient_data", {})
    reasoning_steps = state.get("reasoning_steps", [])

    complications_monitoring = {}
    error = None

    try:
        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        # 提取风险因素
        risk_factors = []
        for risk in risk_assessment:
            if isinstance(risk, dict):
                risk_factors.append(
                    f"{risk.get('category', '')}: {risk.get('factor', '')}"
                )
            elif isinstance(risk, RiskFactorModel):
                risk_factors.append(f"{risk.category}: {risk.factor}")

        # 提取手术进度
        current_step = (
            procedure_execution.get("current_step", "未知步骤")
            if isinstance(procedure_execution, dict)
            else "未知"
        )
        completed_steps = (
            procedure_execution.get("completed_steps", [])
            if isinstance(procedure_execution, dict)
            else []
        )

        # 提取患者信息
        age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0
        comorbidities = (
            patient_data.get("comorbidities", [])
            if isinstance(patient_data, dict)
            else []
        )

        if llm:
            # 使用 LLM 监测并发症
            monitoring_output = await _monitor_complications_with_llm(
                llm,
                risk_factors,
                current_step,
                completed_steps,
                age,
                comorbidities,
            )
            complications_monitoring = monitoring_output.model_dump()

            logger.info(
                f"[并发症监测] LLM 监测完成 | "
                f"并发症数: {len(monitoring_output.complications_detected)} | "
                f"需干预: {monitoring_output.requires_intervention}"
            )

        else:
            # 使用规则基础监测
            monitoring_output = _monitor_complications_with_rules(
                risk_factors, age, comorbidities
            )
            complications_monitoring = monitoring_output.model_dump()

            logger.info(
                f"[并发症监测] 规则监测完成 | "
                f"并发症数: {len(monitoring_output.complications_detected)} | "
                f"需干预: {monitoring_output.requires_intervention}"
            )

        # 创建推理步骤
        complications_list = complications_monitoring.get("complications_detected", [])
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description="监测术中并发症",
            evidence=[
                f"当前步骤: {current_step}",
                f"风险因素数: {len(risk_factors)}",
            ],
            conclusion=f"检测到 {len(complications_list)} 个潜在并发症，"
            f"需立即干预: {complications_monitoring.get('requires_intervention', False)}",
        )

        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except Exception as e:
        error = f"并发症监测失败: {str(e)}"
        logger.error(f"[并发症监测] 错误: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description="监测术中并发症",
            evidence=[],
            conclusion=f"监测失败: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    return {
        "complications_monitoring": complications_monitoring,
        "reasoning_steps": reasoning_steps,
        "error": error,
    }


async def _monitor_complications_with_llm(
    llm: BaseChatModel,
    risk_factors: List[str],
    current_step: str,
    completed_steps: List[str],
    age: int,
    comorbidities: List[str],
) -> ComplicationMonitoringOutput:
    """使用 LLM 监测并发症。

    Args:
        llm: LLM 实例
        risk_factors: 风险因素列表
        current_step: 当前步骤
        completed_steps: 已完成步骤
        age: 患者年龄
        comorbidities: 合并症列表

    Returns:
        并发症监测输出模型
    """
    # 构建监测提示
    risk_text = "\n".join([f"- {r}" for r in risk_factors[:5]])
    steps_text = "\n".join([f"  - {s}" for s in completed_steps[-3:]])

    prompt = f"""请基于以下信息监测介入手术中的潜在并发症。

## 手术进度
- 当前步骤: {current_step}
- 已完成步骤:
{steps_text if steps_text else "  无"}

## 患者风险因素
{risk_text if risk_text else "- 无明显风险因素"}

## 患者信息
- 年龄: {age}岁
- 合并症: {", ".join(comorbidities) if comorbidities else "无"}

## 监测要求
请识别可能发生的并发症:
1. 出血相关（穿刺部位出血、内脏出血等）
2. 血栓相关（急性血栓形成、栓塞等）
3. 血管相关（血管穿孔、夹层、痉挛等）
4. 心律失常相关
5. 对比剂相关（过敏反应、肾病等）
6. 器械相关（器械断裂、脱载等）

对每个检测到的并发症，请提供:
- 并发症名称和描述
- 严重程度（low/medium/high/critical）
- 推荐的应对措施
- 是否需要立即干预

请考虑患者具体情况和手术阶段，提供针对性的监测结果。
"""

    # 使用结构化输出
    structured_llm = llm.with_structured_output(ComplicationMonitoringOutput)
    response: ComplicationMonitoringOutput = await structured_llm.ainvoke(
        [
            SystemMessage(
                content="你是一个专业的介入手术并发症监测专家，"
                "擅长识别和评估术中各种潜在并发症。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    return response


def _monitor_complications_with_rules(
    risk_factors: List[str],
    age: int,
    comorbidities: List[str],
) -> ComplicationMonitoringOutput:
    """使用规则监测并发症（后备方案）。

    Args:
        risk_factors: 风险因素列表
        age: 患者年龄
        comorbidities: 合并症列表

    Returns:
        并发症监测输出模型
    """
    complications = []
    severity_levels = []
    actions = []

    # 基于风险因素的规则
    for risk in risk_factors:
        risk_lower = risk.lower()

        if "出血" in risk_lower or "hemorrhage" in risk_lower:
            complications.append("穿刺部位出血风险")
            severity_levels.append(Severity.MEDIUM)
            actions.append("密切监测穿刺部位，必要时压迫止血")

        if "血栓" in risk_lower or "thrombosis" in risk_lower:
            complications.append("急性血栓形成风险")
            severity_levels.append(Severity.HIGH)
            actions.append("确保充分抗凝，准备血栓抽吸器械")

        if "糖尿病" in risk_lower or "肾功能不全" in risk_lower:
            complications.append("对比剂肾病风险")
            severity_levels.append(Severity.MEDIUM)
            actions.append("水化治疗，最小化对比剂用量")

    # 基于年龄的规则
    if age > 75:
        complications.append("高龄相关并发症风险")
        severity_levels.append(Severity.MEDIUM)
        actions.append("加强监护，优化液体管理")

    # 基于合并症的规则
    for comorb in comorbidities:
        if "肾功能" in comorb:
            complications.append("造影剂肾病风险")
            severity_levels.append(Severity.HIGH)
            actions.append("充分水化，监测肾功能")

    # 如果没有检测到并发症，返回默认结果
    if not complications:
        return ComplicationMonitoringOutput(
            complications_detected=[],
            severity_levels=[],
            recommended_actions=["常规监测生命体征和影像"],
            requires_intervention=False,
            confidence=0.7,
            reasoning="基于当前风险因素评估，未检测到明显并发症",
        )

    return ComplicationMonitoringOutput(
        complications_detected=complications,
        severity_levels=severity_levels,
        recommended_actions=actions,
        requires_intervention=any(
            s == Severity.HIGH or s == Severity.CRITICAL for s in severity_levels
        ),
        confidence=0.75,
        reasoning=f"基于规则监测到 {len(complications)} 个潜在并发症",
    )


# ==================== 术中事件处理节点 ====================


async def handle_events_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """处理术中事件节点。

    该节点负责：
    1. 识别术中意外事件
    2. 评估事件严重程度
    3. 制定应对策略
    4. 提供恢复方案

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含：
        - event_handling: 事件处理结果
        - reasoning_steps: 新增的推理步骤
        - error: 错误信息（如果有）

    Example:
        >>> state = {
        ...     "procedure_execution": {...},
        ...     "complications_monitoring": {...},
        ...     "procedure_plan": {...},
        ...     "reasoning_steps": [],
        ... }
        >>> result = await handle_events_node(state)
        >>> assert "event_handling" in result
    """
    logger.info("[事件处理] 开始处理术中事件")

    # 获取相关数据
    procedure_execution = state.get("procedure_execution", {})
    complications_monitoring = state.get("complications_monitoring", {})
    procedure_plan = state.get("procedure_plan", {})
    reasoning_steps = state.get("reasoning_steps", [])

    event_handling = {}
    error = None

    try:
        # 检查是否有意外事件或并发症
        unexpected_events = (
            procedure_execution.get("unexpected_events", [])
            if isinstance(procedure_execution, dict)
            else []
        )

        complications = (
            complications_monitoring.get("complications_detected", [])
            if isinstance(complications_monitoring, dict)
            else []
        )

        if not unexpected_events and not complications:
            # 没有事件需要处理
            logger.info("[事件处理] 无术中事件需要处理")

            reasoning_step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase=Phase.INTRA_OP,
                description="处理术中事件",
                evidence=["无意外事件", "无并发症"],
                conclusion="手术顺利进行，无特殊事件需要处理",
            )

            return {
                "event_handling": {
                    "event_type": "none",
                    "handling_strategy": "继续按计划执行",
                    "confidence": 1.0,
                    "reasoning": "无术中事件需要处理",
                },
                "reasoning_steps": reasoning_steps + [reasoning_step.model_dump()],
            }

        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        # 确定要处理的事件
        target_events = unexpected_events if unexpected_events else complications[:1]

        if llm:
            # 使用 LLM 处理事件
            handling_output = await _handle_event_with_llm(
                llm,
                target_events[0] if target_events else "未知事件",
                procedure_plan,
                complications_monitoring,
            )
            event_handling = handling_output.model_dump()

            logger.info(
                f"[事件处理] LLM 处理完成 | "
                f"事件类型: {handling_output.event_type} | "
                f"严重程度: {handling_output.event_severity.value}"
            )

        else:
            # 使用规则基础处理
            handling_output = _handle_event_with_rules(
                target_events[0] if target_events else "未知事件"
            )
            event_handling = handling_output.model_dump()

            logger.info(
                f"[事件处理] 规则处理完成 | "
                f"事件类型: {handling_output.event_type} | "
                f"严重程度: {handling_output.event_severity.value}"
            )

        # 创建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description=f"处理术中事件: {event_handling.get('event_type', '未知')}",
            evidence=[
                f"事件: {target_events[0] if target_events else '无'}",
                f"严重程度: {event_handling.get('event_severity', 'unknown')}",
            ],
            conclusion=f"处理策略: {event_handling.get('handling_strategy', 'N/A')}",
        )

        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except Exception as e:
        error = f"事件处理失败: {str(e)}"
        logger.error(f"[事件处理] 错误: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.INTRA_OP,
            description="处理术中事件",
            evidence=[],
            conclusion=f"处理失败: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    return {
        "event_handling": event_handling,
        "reasoning_steps": reasoning_steps,
        "error": error,
    }


async def _handle_event_with_llm(
    llm: BaseChatModel,
    event: str,
    procedure_plan: Dict[str, Any],
    complications_monitoring: Dict[str, Any],
) -> EventHandlingOutput:
    """使用 LLM 处理术中事件。

    Args:
        llm: LLM 实例
        event: 事件描述
        procedure_plan: 手术方案
        complications_monitoring: 并发症监测结果

    Returns:
        事件处理输出模型
    """
    # 提取手术类型
    procedure_type = (
        procedure_plan.get("procedure_type", "未知手术")
        if isinstance(procedure_plan, dict)
        else "未知手术"
    )

    # 提取并发症列表
    complications = (
        complications_monitoring.get("complications_detected", [])
        if isinstance(complications_monitoring, dict)
        else []
    )

    # 构建处理提示
    complications_text = "\n".join([f"- {c}" for c in complications[:3]])

    prompt = f"""请为以下介入手术中的意外事件制定应对策略。

## 事件信息
- 事件类型/描述: {event}
- 手术类型: {procedure_type}

## 当前并发症监测结果
{complications_text if complications_text else "- 无明显并发症"}

## 处理要求
请提供:
1. 事件严重程度评估（low/medium/high/critical）
2. 主要处理策略
3. 替代应对措施（至少2个）
4. 对手术整体进程的影响评估
5. 恢复计划（如何恢复正常手术流程）
6. 处理置信度（0-1）
7. 处理推理说明

请考虑事件的具体性质、严重程度和对患者的影响，提供专业、可行的处理方案。
"""

    # 使用结构化输出
    structured_llm = llm.with_structured_output(EventHandlingOutput)
    response: EventHandlingOutput = await structured_llm.ainvoke(
        [
            SystemMessage(
                content="你是一个专业的介入手术事件处理专家，"
                "擅长应对各种术中意外事件和并发症。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    return response


def _handle_event_with_rules(event: str) -> EventHandlingOutput:
    """使用规则处理术中事件（后备方案）。

    Args:
        event: 事件描述

    Returns:
        事件处理输出模型
    """
    event_lower = event.lower()

    # 确定事件严重程度
    # 首先检查低严重程度的关键词（优先匹配）
    if any(keyword in event_lower for keyword in ["轻微", "轻度", "minor", "mild"]):
        severity = Severity.LOW
        strategy = "调整手术技术，继续手术"
        impact = "轻微影响，可继续手术"
        recovery_plan = "微调技术细节后继续"
    elif any(
        keyword in event_lower
        for keyword in ["大出血", "穿孔", "休克", "cardiac", "arrest"]
    ):
        severity = Severity.CRITICAL
        strategy = "立即暂停手术，紧急处理危及生命的状况"
        impact = "严重影响，需优先处理危及生命的状况"
        recovery_plan = "稳定生命体征后评估是否继续或中止手术"
    elif any(keyword in event_lower for keyword in ["血栓", "夹层", "dissection"]):
        severity = Severity.HIGH
        strategy = "针对性处理并发症，备选转换方案"
        impact = "显著影响，需调整手术策略"
        recovery_plan = "处理并发症后继续手术，必要时转换术式"
    elif any(
        keyword in event_lower for keyword in ["器械", "device", "failure", "痉挛"]
    ):
        severity = Severity.MEDIUM
        strategy = "更换器械或使用替代方案"
        impact = "中等影响，可能增加手术时间"
        recovery_plan = "更换器械后继续手术"
    else:
        severity = Severity.LOW
        strategy = "调整手术技术，继续手术"
        impact = "轻微影响，可继续手术"
        recovery_plan = "微调技术细节后继续"

    # 生成替代措施
    alternative_actions = []
    if severity == Severity.CRITICAL:
        alternative_actions = [
            "立即启动紧急抢救流程",
            "请相关科室会诊协助",
            "考虑体外循环支持",
        ]
    elif severity == Severity.HIGH:
        alternative_actions = [
            "使用药物或球囊处理并发症",
            "转换到备选手术方案",
            "中止手术并考虑外科处理",
        ]
    elif severity == Severity.MEDIUM:
        alternative_actions = [
            "使用备用器械",
            "调整手术入路或技术",
            "延长手术时间以妥善处理",
        ]
    else:
        alternative_actions = [
            "微调手术技术",
            "增加造影确认",
            "密切监测",
        ]

    return EventHandlingOutput(
        event_type=event,
        event_severity=severity,
        handling_strategy=strategy,
        alternative_actions=alternative_actions,
        impact_on_procedure=impact,
        recovery_plan=recovery_plan,
        confidence=0.75,
        reasoning=f"基于规则对'{event}'进行事件处理，严重程度: {severity.value}",
    )
