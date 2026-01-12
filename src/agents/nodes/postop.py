"""介入手术术后管理节点模块。

该模块实现了介入手术术后管理的所有节点函数，包括：
- plan_postop_care_node(): 规划术后管理
- generate_discharge_plan_node(): 生成出院计划

每个节点都是独立的、可测试的函数，接收 ExtendedInterventionalState
并返回更新后的状态字典。
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from src.agents.states import ExtendedInterventionalState
from src.agents.models import (
    ReasoningStepModel,
    RiskFactorModel,
    Phase,
)
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.agents.nodes.postop")


# ==================== 术后管理输出模型 ====================


class PostOpCareOutput(BaseModel):
    """术后管理输出模型。

    用于 LLM 结构化输出的术后管理计划。

    Attributes:
        monitoring_plan: 监测计划列表
        medication_plan: 用药计划列表
        wound_care: 伤口护理说明
        activity_restrictions: 活动限制列表
        diet_recommendations: 饮食建议
        follow_up_schedule: 随访计划
        warning_signs: 警示体征列表
        confidence: 计划置信度
        reasoning: 规划推理说明
    """

    monitoring_plan: List[str] = Field(default_factory=list, description="监测计划列表")
    medication_plan: List[str] = Field(default_factory=list, description="用药计划列表")
    wound_care: List[str] = Field(default_factory=list, description="伤口护理说明")
    activity_restrictions: List[str] = Field(
        default_factory=list, description="活动限制列表"
    )
    diet_recommendations: List[str] = Field(
        default_factory=list, description="饮食建议"
    )
    follow_up_schedule: List[str] = Field(default_factory=list, description="随访计划")
    warning_signs: List[str] = Field(default_factory=list, description="警示体征列表")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="计划置信度")
    reasoning: str = Field(..., description="规划推理说明")


class DischargePlanOutput(BaseModel):
    """出院计划输出模型。

    用于 LLM 结构化输出的出院计划。

    Attributes:
        discharge_criteria: 出院标准列表
        home_care_instructions: 居家护理说明
        medication_at_discharge: 出院带药列表
        activity_guidelines: 活动指导
        emergency_contacts: 紧急联系方式
        follow_up_arrangements: 随访安排
    patient_education: 患者教育要点
    discharge_timing: 预计出院时间
    confidence: 计划置信度
    reasoning: 规划推理说明
    """

    discharge_criteria: List[str] = Field(
        default_factory=list, description="出院标准列表"
    )
    home_care_instructions: List[str] = Field(
        default_factory=list, description="居家护理说明"
    )
    medication_at_discharge: List[str] = Field(
        default_factory=list, description="出院带药列表"
    )
    activity_guidelines: List[str] = Field(default_factory=list, description="活动指导")
    emergency_contacts: List[str] = Field(
        default_factory=list, description="紧急联系方式"
    )
    follow_up_arrangements: List[str] = Field(
        default_factory=list, description="随访安排"
    )
    patient_education: List[str] = Field(
        default_factory=list, description="患者教育要点"
    )
    discharge_timing: str = Field(..., description="预计出院时间")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="计划置信度")
    reasoning: str = Field(..., description="规划推理说明")


# ==================== 术后管理规划节点 ====================


async def plan_postop_care_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """规划术后管理节点。

    该节点负责：
    1. 基于手术类型和患者情况制定术后管理计划
    2. 包括监测、用药、伤口护理、活动限制等
    3. 提供警示体征识别
    4. 制定随访计划

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含：
        - post_op_plan: 术后管理计划
        - reasoning_steps: 新增的推理步骤
        - error: 错误信息（如果有）

    Raises:
        ValueError: 如果缺少必要的患者或手术信息

    Example:
        >>> state = {
        ...     "patient_data": {...},
        ...     "procedure_plan": {...},
        ...     "procedure_execution": {...},
        ...     "risk_assessment": [...],
        ...     "reasoning_steps": [],
        ... }
        >>> result = await plan_postop_care_node(state)
        >>> assert "post_op_plan" in result
    """
    logger.info("[术后管理规划] 开始制定术后管理计划")

    # 获取相关数据
    patient_data = state.get("patient_data", {})
    procedure_plan = state.get("procedure_plan", {})
    procedure_execution = state.get("procedure_execution", {})
    risk_assessment = state.get("risk_assessment", [])
    reasoning_steps = state.get("reasoning_steps", [])

    post_op_plan = {}
    error = None

    try:
        # 检查必要数据
        if not patient_data:
            raise ValueError("缺少患者数据，无法制定术后管理计划")

        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        # 提取手术信息
        if isinstance(procedure_plan, dict):
            procedure_type = procedure_plan.get("procedure_type", "未知手术")
            approach = procedure_plan.get("approach", "未知入路")
        else:
            procedure_type = str(getattr(procedure_plan, "procedure_type", "未知手术"))
            approach = getattr(procedure_plan, "approach", "未知入路")

        # 提取患者信息
        age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0
        comorbidities = (
            patient_data.get("comorbidities", [])
            if isinstance(patient_data, dict)
            else []
        )
        medications = (
            patient_data.get("medications", [])
            if isinstance(patient_data, dict)
            else []
        )
        allergies = (
            patient_data.get("allergies", []) if isinstance(patient_data, dict) else []
        )

        # 提取风险因素
        risk_factors = []
        for risk in risk_assessment:
            if isinstance(risk, dict):
                risk_factors.append(
                    f"{risk.get('category', '')}: {risk.get('factor', '')}"
                )
            elif isinstance(risk, RiskFactorModel):
                risk_factors.append(f"{risk.category}: {risk.factor}")

        # 提取手术执行情况
        execution_status = (
            procedure_execution.get("execution_status", "unknown")
            if isinstance(procedure_execution, dict)
            else "unknown"
        )

        logger.info(
            f"[术后管理规划] 手术类型: {procedure_type}, "
            f"入路: {approach}, "
            f"执行状态: {execution_status}, "
            f"患者年龄: {age}, "
            f"风险因素数: {len(risk_factors)}"
        )

        if llm:
            # 使用 LLM 制定术后管理计划
            care_output = await _plan_care_with_llm(
                llm,
                procedure_type,
                approach,
                age,
                comorbidities,
                medications,
                allergies,
                risk_factors,
                execution_status,
            )
            post_op_plan = _convert_care_output_to_model(care_output)

            logger.info(
                f"[术后管理规划] LLM 规划完成 | "
                f"监测项: {len(care_output.monitoring_plan)} | "
                f"用药项: {len(care_output.medication_plan)} | "
                f"置信度: {care_output.confidence:.2f}"
            )

        else:
            # 使用规则基础规划
            care_output = _plan_care_with_rules(
                procedure_type, approach, age, comorbidities, risk_factors
            )
            post_op_plan = _convert_care_output_to_model(care_output)

            logger.info(
                f"[术后管理规划] 规则规划完成 | "
                f"监测项: {len(care_output.monitoring_plan)} | "
                f"用药项: {len(care_output.medication_plan)} | "
                f"置信度: {care_output.confidence:.2f}"
            )

        # 创建推理步骤
        monitoring_count = len(care_output.monitoring_plan)
        medication_count = len(care_output.medication_plan)
        warning_count = len(care_output.warning_signs)

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description=f"制定{procedure_type}术后管理计划",
            evidence=[
                f"手术类型: {procedure_type}",
                f"入路: {approach}",
                f"患者年龄: {age}岁",
                f"风险因素: {len(risk_factors)}个",
            ],
            conclusion=f"制定监测计划{monitoring_count}项、用药计划{medication_count}项、"
            f"警示体征{warning_count}项",
        )

        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except ValueError as e:
        error = f"术后管理规划失败: {str(e)}"
        logger.error(f"[术后管理规划] 错误: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description="制定术后管理计划",
            evidence=[],
            conclusion=f"规划失败: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except Exception as e:
        error = f"术后管理规划异常: {str(e)}"
        logger.error(f"[术后管理规划] 异常: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description="制定术后管理计划",
            evidence=[],
            conclusion=f"规划异常: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    return {
        "post_op_plan": post_op_plan,
        "reasoning_steps": reasoning_steps,
        "error": error,
    }


async def _plan_care_with_llm(
    llm: BaseChatModel,
    procedure_type: str,
    approach: str,
    age: int,
    comorbidities: List[str],
    medications: List[str],
    allergies: List[str],
    risk_factors: List[str],
    execution_status: str,
) -> PostOpCareOutput:
    """使用 LLM 制定术后管理计划。

    Args:
        llm: LLM 实例
        procedure_type: 手术类型
        approach: 入路方式
        age: 患者年龄
        comorbidities: 合并症列表
        medications: 用药列表
        allergies: 过敏史
        risk_factors: 风险因素列表
        execution_status: 手术执行状态

    Returns:
        术后管理输出模型
    """
    # 构建规划提示
    risk_text = "\n".join([f"- {r}" for r in risk_factors[:5]])
    comorbidities_text = ", ".join(comorbidities) if comorbidities else "无"
    medications_text = ", ".join(medications) if medications else "无"
    allergies_text = ", ".join(allergies) if allergies else "无"

    prompt = f"""请为以下患者制定详细的介入手术后管理计划。

## 手术信息
- 手术类型: {procedure_type}
- 入路方式: {approach}
- 手术状态: {execution_status}

## 患者信息
- 年龄: {age}岁
- 合并症: {comorbidities_text}
- 当前用药: {medications_text}
- 过敏史: {allergies_text}

## 识别的风险因素
{risk_text if risk_text else "- 无明显风险因素"}

## 术后管理规划要求
请制定全面的术后管理计划，包括:

### 1. 监测计划
- 生命体征监测频率和项目
- 穿刺部位观察要点
- 实验室检查项目和时机
- 影像学随访安排

### 2. 用药计划
- 抗血小板治疗方案
- 抗凝治疗方案
- 其他必要药物
- 药物相互作用注意事项
- 过敏风险规避

### 3. 伤口护理
- 穿刺部位护理
- 伤口观察要点
- 更换敷料指导

### 4. 活动限制
- 卧床时间要求
- 活动恢复进度
- 禁止的活动
- 逐步恢复计划

### 5. 饮食建议
- 术后饮食要求
- 液体摄入指导
- 特殊饮食限制

### 6. 随访计划
- 门诊随访时间
- 随访检查项目
- 电话随访安排

### 7. 警示体征
- 需要立即就医的体征
- 需要联系医生的征象
- 正常恢复过程中的预期症状

请基于患者具体情况（年龄、合并症、风险因素）制定个体化的术后管理计划。
"""

    # 使用结构化输出
    structured_llm = llm.with_structured_output(PostOpCareOutput)
    response: PostOpCareOutput = await structured_llm.ainvoke(
        [
            SystemMessage(
                content="你是一个专业的介入手术术后管理专家，"
                "擅长制定全面、个体化的术后管理计划。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    return response


def _plan_care_with_rules(
    procedure_type: str,
    approach: str,
    age: int,
    comorbidities: List[str],
    risk_factors: List[str],
) -> PostOpCareOutput:
    """使用规则制定术后管理计划（后备方案）。

    Args:
        procedure_type: 手术类型
        approach: 入路方式
        age: 患者年龄
        comorbidities: 合并症列表
        risk_factors: 风险因素列表

    Returns:
        术后管理输出模型
    """
    # 监测计划
    monitoring_plan = [
        "生命体征监测（血压、心率、呼吸、体温）q4h x 24h",
        "穿刺部位观察每小时 x 6h，然后q4h x 24h",
        "心电图监测持续24小时",
        "术后即刻、6小时、24小时查心肌损伤标志物",
        "术后24小时复查超声心动图（如适用）",
        "每日评估足背动脉搏动",
    ]

    # 用药计划
    medication_plan = [
        "阿司匹林 100mg qd（终身，除非禁忌）",
        "氯吡格雷 75mg qd（至少12个月）",
        "他汀类药物（阿托伐他汀 40-80mg qn）",
        "质子泵抑制剂预防应激性溃疡",
        "根据肾功能调整造影剂肾病预防",
    ]

    # 伤口护理
    wound_care = [
        "保持穿刺部位干燥清洁",
        "避免穿刺部位受压或摩擦",
        "观察有无渗血、血肿、感染征象",
        "按医嘱更换敷料",
    ]

    # 活动限制
    activity_restrictions = [
        f"术后卧床{6}小时（经桡动脉入路）或12小时（经股动脉入路）",
        "穿刺侧肢体避免屈曲和用力",
        "逐渐增加活动量，避免剧烈运动",
        "避免提重物（>5kg）至少1周",
    ]

    # 饮食建议
    diet_recommendations = [
        "术后可正常饮食，避免过饱",
        "鼓励饮水（心功能正常者）以促进造影剂排泄",
        "低盐低脂饮食",
        "糖尿病者严格糖尿病饮食",
    ]

    # 随访计划
    follow_up_schedule = [
        "术后1个月门诊随访",
        "术后3个月、6个月、12个月常规随访",
        "必要时电话随访（术后3-7天）",
        "随访内容包括：临床症状评估、心电图、实验室检查",
    ]

    # 警示体征
    warning_signs = [
        "穿刺部位持续出血或血肿迅速扩大",
        "穿刺侧肢体肿胀、疼痛、皮温升高",
        "胸痛、胸闷、呼吸困难",
        "心悸、头晕、晕厥",
        "发热（体温>38℃）",
        "穿刺部位红肿、渗出",
        "恶心、呕吐、腹痛（疑有内脏出血）",
    ]

    # 根据合并症调整
    if "肾功能不全" in comorbidities:
        monitoring_plan.extend(
            [
                "监测肾功能（肌酐、尿素氮）每日 x 3天",
                "记录尿量",
                "避免肾毒性药物",
            ]
        )
        medication_plan.extend(
            [
                "根据肾功能调整药物剂量",
            ]
        )

    if "糖尿病" in comorbidities:
        monitoring_plan.extend(
            [
                "监测血糖q6h（不稳定者）",
                "评估有无感染征象",
            ]
        )
        diet_recommendations.extend(
            [
                "糖尿病饮食指导",
                "血糖监测和调整",
            ]
        )

    if age > 75:
        monitoring_plan.extend(
            [
                "加强认知功能评估",
                "评估跌倒风险",
            ]
        )
        activity_restrictions.extend(
            [
                "高龄患者活动需有人陪同",
            ]
        )

    return PostOpCareOutput(
        monitoring_plan=monitoring_plan,
        medication_plan=medication_plan,
        wound_care=wound_care,
        activity_restrictions=activity_restrictions,
        diet_recommendations=diet_recommendations,
        follow_up_schedule=follow_up_schedule,
        warning_signs=warning_signs,
        confidence=0.75,
        reasoning=f"基于规则为{procedure_type}手术制定术后管理计划，已考虑患者年龄({age}岁)和合并症",
    )


def _convert_care_output_to_model(care_output: PostOpCareOutput) -> Dict[str, Any]:
    """将术后管理输出转换为术后计划模型格式。

    Args:
        care_output: 术后管理输出模型

    Returns:
        术后计划字典
    """
    return {
        "monitoring": care_output.monitoring_plan,
        "medications": care_output.medication_plan,
        "wound_care": care_output.wound_care,
        "activity_restrictions": care_output.activity_restrictions,
        "diet_recommendations": care_output.diet_recommendations,
        "follow_up": care_output.follow_up_schedule,
        "warning_signs": care_output.warning_signs,
        "confidence": care_output.confidence,
        "reasoning": care_output.reasoning,
    }


# ==================== 出院计划生成节点 ====================


async def generate_discharge_plan_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """生成出院计划节点。

    该节点负责：
    1. 基于术后管理计划制定出院计划
    2. 确定出院标准和时机
    3. 提供居家护理指导
    4. 安排随访和紧急联系方式

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含：
        - discharge_plan: 出院计划
        - reasoning_steps: 新增的推理步骤
        - error: 错误信息（如果有）

    Raises:
        ValueError: 如果缺少必要的术后管理计划

    Example:
        >>> state = {
        ...     "post_op_plan": {...},
        ...     "patient_data": {...},
        ...     "procedure_plan": {...},
        ...     "reasoning_steps": [],
        ... }
        >>> result = await generate_discharge_plan_node(state)
        >>> assert "discharge_plan" in result
    """
    logger.info("[出院计划] 开始生成出院计划")

    # 获取相关数据
    post_op_plan = state.get("post_op_plan", {})
    patient_data = state.get("patient_data", {})
    procedure_plan = state.get("procedure_plan", {})
    reasoning_steps = state.get("reasoning_steps", [])

    discharge_plan = {}
    error = None

    try:
        # 检查必要数据
        if not post_op_plan:
            raise ValueError("缺少术后管理计划，无法制定出院计划")

        if not patient_data:
            raise ValueError("缺少患者数据，无法制定出院计划")

        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        # 提取手术信息
        if isinstance(procedure_plan, dict):
            procedure_type = procedure_plan.get("procedure_type", "未知手术")
            approach = procedure_plan.get("approach", "未知入路")
        else:
            procedure_type = str(getattr(procedure_plan, "procedure_type", "未知手术"))
            approach = getattr(procedure_plan, "approach", "未知入路")

        # 提取患者信息
        age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0
        comorbidities = (
            patient_data.get("comorbidities", [])
            if isinstance(patient_data, dict)
            else []
        )
        living_situation = (
            patient_data.get("living_situation", "与家人同住")
            if isinstance(patient_data, dict)
            else "与家人同住"
        )

        # 提取术后管理信息
        if isinstance(post_op_plan, dict):
            monitoring = post_op_plan.get("monitoring", [])
            medications = post_op_plan.get("medications", [])
            warning_signs = post_op_plan.get("warning_signs", [])
            follow_up = post_op_plan.get("follow_up", [])
        else:
            monitoring = []
            medications = []
            warning_signs = []
            follow_up = []

        logger.info(
            f"[出院计划] 手术类型: {procedure_type}, "
            f"患者年龄: {age}, "
            f"居住情况: {living_situation}, "
            f"监测项: {len(monitoring)}, "
            f"用药项: {len(medications)}"
        )

        if llm:
            # 使用 LLM 制定出院计划
            discharge_output = await _generate_discharge_plan_with_llm(
                llm,
                procedure_type,
                approach,
                age,
                comorbidities,
                living_situation,
                monitoring,
                medications,
                warning_signs,
                follow_up,
            )
            discharge_plan = discharge_output.model_dump()

            logger.info(
                f"[出院计划] LLM 生成完成 | "
                f"出院时间: {discharge_output.discharge_timing} | "
                f"置信度: {discharge_output.confidence:.2f}"
            )

        else:
            # 使用规则基础出院计划
            discharge_output = _generate_discharge_plan_with_rules(
                procedure_type,
                age,
                comorbidities,
                living_situation,
                monitoring,
                medications,
            )
            discharge_plan = discharge_output.model_dump()

            logger.info(
                f"[出院计划] 规则生成完成 | "
                f"出院时间: {discharge_output.discharge_timing} | "
                f"置信度: {discharge_output.confidence:.2f}"
            )

        # 创建推理步骤
        criteria_count = len(discharge_plan.get("discharge_criteria", []))
        education_count = len(discharge_plan.get("patient_education", []))

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description=f"制定{procedure_type}出院计划",
            evidence=[
                f"手术类型: {procedure_type}",
                f"患者年龄: {age}岁",
                f"居住情况: {living_situation}",
                f"合并症: {len(comorbidities)}个",
            ],
            conclusion=f"出院标准{criteria_count}项、患者教育{education_count}项、"
            f"预计出院时间: {discharge_plan.get('discharge_timing', '未定')}",
        )

        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except ValueError as e:
        error = f"出院计划生成失败: {str(e)}"
        logger.error(f"[出院计划] 错误: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description="制定出院计划",
            evidence=[],
            conclusion=f"生成失败: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    except Exception as e:
        error = f"出院计划生成异常: {str(e)}"
        logger.error(f"[出院计划] 异常: {error}")

        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.POST_OP,
            description="制定出院计划",
            evidence=[],
            conclusion=f"生成异常: {error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step.model_dump()]

    return {
        "discharge_plan": discharge_plan,
        "reasoning_steps": reasoning_steps,
        "error": error,
    }


async def _generate_discharge_plan_with_llm(
    llm: BaseChatModel,
    procedure_type: str,
    approach: str,
    age: int,
    comorbidities: List[str],
    living_situation: str,
    monitoring: List[str],
    medications: List[str],
    warning_signs: List[str],
    follow_up: List[str],
) -> DischargePlanOutput:
    """使用 LLM 生成出院计划。

    Args:
        llm: LLM 实例
        procedure_type: 手术类型
        approach: 入路方式
        age: 患者年龄
        comorbidities: 合并症列表
        living_situation: 居住情况
        monitoring: 监测计划
        medications: 用药计划
        warning_signs: 警示体征
        follow_up: 随访计划

    Returns:
        出院计划输出模型
    """
    # 构建出院计划提示
    monitoring_text = "\n".join([f"- {m}" for m in monitoring[:5]])
    medications_text = "\n".join([f"- {m}" for m in medications[:5]])
    warning_text = "\n".join([f"- {w}" for w in warning_signs[:5]])
    follow_up_text = "\n".join([f"- {f}" for f in follow_up[:3]])
    comorbidities_text = ", ".join(comorbidities) if comorbidities else "无"

    prompt = f"""请为以下患者制定详细的出院计划。

## 手术信息
- 手术类型: {procedure_type}
- 入路方式: {approach}

## 患者信息
- 年龄: {age}岁
- 合并症: {comorbidities_text}
- 居住情况: {living_situation}

## 术后管理计划摘要

### 监测计划
{monitoring_text if monitoring_text else "- 常规生命体征监测"}

### 用药计划
{medications_text if medications_text else "- 标准抗血小板治疗"}

### 警示体征
{warning_text if warning_text else "- 无特殊警示"}

### 随访计划
{follow_up_text if follow_up_text else "- 常规随访"}

## 出院计划要求
请制定全面的出院计划，包括:

### 1. 出院标准
明确患者可以出院的条件和标准

### 2. 居家护理说明
- 日常护理指导
- 活动指导
- 饮食指导
- 伤口护理
- 用药指导

### 3. 出院带药
列出所有出院时需要带回家的药物

### 4. 活动指导
详细说明出院后的活动限制和恢复进度

### 5. 紧急联系方式
提供需要时联系的医疗资源

### 6. 随访安排
明确出院后的随访时间、地点和内容

### 7. 患者教育要点
患者和家属需要了解的关键信息

### 8. 预计出院时间
基于手术类型和患者情况评估出院时机

请考虑患者年龄、合并症和居住情况，制定个体化的出院计划。
"""

    # 使用结构化输出
    structured_llm = llm.with_structured_output(DischargePlanOutput)
    response: DischargePlanOutput = await structured_llm.ainvoke(
        [
            SystemMessage(
                content="你是一个专业的介入手术出院计划制定专家，"
                "擅长制定全面、个体化的出院计划和患者教育方案。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    return response


def _generate_discharge_plan_with_rules(
    procedure_type: str,
    age: int,
    comorbidities: List[str],
    living_situation: str,
    monitoring: List[str],
    medications: List[str],
) -> DischargePlanOutput:
    """使用规则生成出院计划（后备方案）。

    Args:
        procedure_type: 手术类型
        age: 患者年龄
        comorbidities: 合并症列表
        living_situation: 居住情况
        monitoring: 监测计划
        medications: 用药计划

    Returns:
        出院计划输出模型
    """
    # 出院标准
    discharge_criteria = [
        "生命体征稳定（血压、心率、呼吸、体温正常）",
        "穿刺部位无活动性出血、血肿或感染征象",
        "无心绞痛、胸闷、呼吸困难等症状",
        "心电图无明显缺血改变或心律失常",
        "心肌损伤标志物无上升趋势",
        "能够自理或家属能够协助护理",
        "了解出院带药用法和警示体征",
    ]

    # 居家护理说明
    home_care_instructions = [
        "保持穿刺部位干燥清洁，按医嘱更换敷料",
        "观察穿刺部位有无红肿、渗出、疼痛",
        "按医嘱规律服药，不得随意停药或更改剂量",
        "避免剧烈运动和提重物（>5kg）至少1周",
        "保持健康生活方式：戒烟、限酒、低盐低脂饮食",
        "控制体重，规律作息",
        "保持情绪稳定，避免过度激动",
    ]

    # 出院带药
    medication_at_discharge = [
        "阿司匹林 100mg 每日1次（终身服用）",
        "氯吡格雷 75mg 每日1次（至少服用12个月）",
        "阿托伐他汀 40-80mg 每晚1次",
        "质子泵抑制剂（如需要）",
    ]

    # 活动指导
    activity_guidelines = [
        "术后第1-3天：轻度活动，室内行走",
        "术后第4-7天：逐渐增加活动量，可上下楼梯",
        "术后2周后：可恢复日常活动，避免剧烈运动",
        "术后4周后：可逐步恢复运动（散步、太极拳等）",
        "术后3个月后：经医生评估后可恢复更强活动",
    ]

    # 紧急联系方式
    emergency_contacts = [
        "急诊科电话：120或当地急诊电话",
        "心内科病房电话：[需填写具体号码]",
        "主治医生电话：[需填写具体号码]",
        "如出现胸痛、胸闷、呼吸困难、穿刺部位大出血等，立即就医",
    ]

    # 随访安排
    follow_up_arrangements = [
        "术后1个月：门诊随访，评估恢复情况，调整用药",
        "术后3个月：门诊随访，心电图、实验室检查",
        "术后6个月：门诊随访，评估疗效，调整治疗方案",
        "术后12个月：门诊随访，全面评估",
        "必要时电话随访（术后3-7天）",
    ]

    # 患者教育要点
    patient_education = [
        "了解疾病性质和手术意义",
        "认识坚持服药的重要性",
        "识别警示体征，知道何时就医",
        "了解危险因素控制（血压、血脂、血糖）",
        "掌握健康生活方式",
        "了解随访计划的重要性",
        "了解急救联系方式",
    ]

    # 预计出院时间
    if age > 75 or len(comorbidities) > 2:
        discharge_timing = "术后2-3天（需延长观察）"
    elif age > 65 or len(comorbidities) > 0:
        discharge_timing = "术后1-2天"
    else:
        discharge_timing = "术后24-48小时"

    # 根据合并症调整
    if "糖尿病" in comorbidities:
        patient_education.extend(
            [
                "糖尿病饮食指导",
                "血糖监测和记录",
                "识别低血糖症状",
            ]
        )

    if living_situation == "独居":
        home_care_instructions.extend(
            [
                "建议与家人或社区医疗服务联系",
                "安装紧急呼叫设备",
                "考虑短期护理服务",
            ]
        )

    return DischargePlanOutput(
        discharge_criteria=discharge_criteria,
        home_care_instructions=home_care_instructions,
        medication_at_discharge=medication_at_discharge,
        activity_guidelines=activity_guidelines,
        emergency_contacts=emergency_contacts,
        follow_up_arrangements=follow_up_arrangements,
        patient_education=patient_education,
        discharge_timing=discharge_timing,
        confidence=0.75,
        reasoning=f"基于规则为{procedure_type}手术制定出院计划，"
        f"已考虑患者年龄({age}岁)、合并症({len(comorbidities)}个)和居住情况",
    )
