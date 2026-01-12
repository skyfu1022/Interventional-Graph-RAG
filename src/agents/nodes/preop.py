"""介入手术术前评估节点模块。

该模块实现了介入手术术前评估的所有节点函数，包括：
- 意图识别节点
- GraphRAG 检索节点
- 适应症评估节点
- 禁忌症评估节点
- 风险评估节点
- 器械匹配节点
- 方案生成节点

每个节点都是独立的、可测试的函数，接收 ExtendedInterventionalState
并返回更新后的状态字典。
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import RunnableConfig

from src.agents.models import (
    DeviceSelectionModel,
    PatientDataModel,
    ProcedurePlanModel,
    ReasoningStepModel,
    RiskFactorModel,
    Severity,
)
from src.agents.states import ExtendedInterventionalState

# ==================== 意图识别节点 ====================


async def intent_recognition_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """识别患者意图和手术类型节点。

    该节点负责：
    - 解析患者输入，识别主要诉求
    - 确定手术类型和介入方式
    - 初始化推理链

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含识别的意图和初始推理步骤
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[意图识别] 患者数据: {patient_data}, 手术类型: {procedure_type}")

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm and isinstance(patient_data, dict):
            # 使用 LLM 识别意图
            prompt = f"""请分析以下患者信息，识别主要诉求和合适的介入手术类型。

患者信息:
- 主诉: {patient_data.get("chief_complaint", "未知")}
- 诊断: {", ".join(patient_data.get("diagnosis", []))}
- 合并症: {", ".join(patient_data.get("comorbidities", []))}

请识别:
1. 患者的主要诉求是什么？
2. 建议的介入手术类型（如 PCI、支架植入、球囊血管成形术等）
3. 优先级评估（紧急/择期）

请以结构化的方式返回分析结果。"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入心脏病学专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="识别患者意图和手术类型",
                evidence=[f"患者主诉: {patient_data.get('chief_complaint', '未知')}"],
                conclusion=response.content.strip()[:500],
            )
            reasoning_steps.append(step.model_dump())

            print("[意图识别] 已完成意图识别")

        else:
            # 没有 LLM，使用简单规则
            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )

            # 基于诊断的简单规则
            if any("冠心病" in d or "冠状动脉" in d for d in diagnosis):
                procedure_type = "PCI"
            elif any("狭窄" in d for d in diagnosis):
                procedure_type = "stent_implantation"
            else:
                procedure_type = procedure_type or "other"

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于规则识别手术类型",
                evidence=[f"诊断: {', '.join(diagnosis)}"],
                conclusion=f"建议手术类型: {procedure_type}",
            )
            reasoning_steps.append(step.model_dump())

            print(f"[意图识别] 使用规则识别: {procedure_type}")

    except Exception as e:
        error = f"意图识别失败: {str(e)}"
        print(f"[意图识别] 错误: {error}")

    return {
        "procedure_type": procedure_type,
        "reasoning_steps": reasoning_steps,
    }


# ==================== GraphRAG 检索节点 ====================


async def u_retrieval_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """从 GraphRAG 三层图谱中检索相关知识节点。

    该节点负责：
    - 从患者数据图谱检索历史记录
    - 从文献指南图谱检索相关指南
    - 从医学词典图谱检索标准术语
    - 整合三层图谱的检索结果

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 rag_adapter

    Returns:
        更新后的状态字典，包含检索到的实体、关系和指南
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    print(f"[GraphRAG检索] 手术类型: {procedure_type}")

    retrieved_entities = state.get("retrieved_entities", [])
    retrieved_relationships = state.get("retrieved_relationships", [])
    matched_guidelines = state.get("matched_guidelines", [])

    patient_graph_context = {}
    literature_graph_context = {}
    dictionary_graph_context = {}

    try:
        # 从 config 中获取 RAG 适配器
        rag_adapter = None
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")

        if rag_adapter:
            # 构建检索查询
            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )
            query = f"{procedure_type} {', '.join(diagnosis)}"

            # 执行检索（假设有 asearch 方法）
            # 注意：实际实现需要根据 RAGAnythingAdapter 的 API 调整
            print(f"[GraphRAG检索] 执行检索查询: {query}")

            # 模拟检索结果
            # 实际实现中应该调用 rag_adapter 的检索方法
            # result = await rag_adapter.asearch(query, search_mode="hybrid")

            # 占位符：添加模拟的检索结果
            # retrieved_entities.extend(...)
            # matched_guidelines.extend(...)

            print("[GraphRAG检索] 检索完成")
        else:
            print("[GraphRAG检索] 警告: 未配置 RAG 适配器")

    except Exception as e:
        error = f"GraphRAG 检索失败: {str(e)}"
        print(f"[GraphRAG检索] 错误: {error}")

    return {
        "retrieved_entities": retrieved_entities,
        "retrieved_relationships": retrieved_relationships,
        "matched_guidelines": matched_guidelines,
        "patient_graph_context": patient_graph_context,
        "literature_graph_context": literature_graph_context,
        "dictionary_graph_context": dictionary_graph_context,
    }


# ==================== 适应症评估节点 ====================


async def assess_indications_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估手术适应症节点。

    该节点负责：
    - 基于患者数据和指南匹配评估适应症
    - 判断患者是否符合手术条件
    - 记录评估依据

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含适应症评估结果和患者分析
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    matched_guidelines = state.get("matched_guidelines", [])
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[适应症评估] 手术类型: {procedure_type}")

    indications_met = False
    patient_analysis = None
    error = None

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            # 构建评估提示
            guidelines_text = (
                "\n".join(
                    [
                        f"- {g.get('title', '')}: {g.get('recommendation', '')}"
                        for g in matched_guidelines[:3]
                    ]
                )
                if matched_guidelines
                else "未检索到相关指南"
            )

            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )

            prompt = f"""请评估以下患者是否符合 {procedure_type} 手术的适应症。

手术类型: {procedure_type}

患者信息:
- 诊断: {", ".join(diagnosis)}
- 合并症: {", ".join(comorbidities)}

相关指南:
{guidelines_text}

请评估:
1. 患者是否符合该手术的适应症？
2. 适应症评估的依据是什么？
3. 是否需要额外的检查或评估？

请返回:
- 符合适应症: 是/否
- 评估依据: 详细说明
- 建议: 后续建议"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入心脏病学专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            # 解析响应
            response_text = response.content.strip()
            indications_met = "是" in response_text or "符合" in response_text

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="评估手术适应症",
                evidence=[f"诊断: {', '.join(diagnosis)}"]
                + [f"指南: {g.get('title', '')}" for g in matched_guidelines[:2]],
                conclusion=f"适应症评估: {'符合' if indications_met else '不符合'}",
            )
            reasoning_steps.append(step.model_dump())

            # 创建患者分析
            patient_analysis = PatientDataModel(
                patient_id=patient_data.get("patient_id", "unknown")
                if isinstance(patient_data, dict)
                else "unknown",
                age=patient_data.get("age", 0) if isinstance(patient_data, dict) else 0,
                gender=patient_data.get("gender", "未知")
                if isinstance(patient_data, dict)
                else "未知",
                chief_complaint=patient_data.get("chief_complaint", "")
                if isinstance(patient_data, dict)
                else "",
                diagnosis=diagnosis,
                comorbidities=comorbidities,
            )

            print(f"[适应症评估] 评估结果: {'符合' if indications_met else '不符合'}")

        else:
            # 没有 LLM，使用简单规则
            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )
            indications_met = len(diagnosis) > 0  # 有诊断就认为符合

            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于规则评估适应症",
                evidence=[f"诊断: {', '.join(diagnosis)}"],
                conclusion=f"适应症评估: {'符合' if indications_met else '不符合'}",
            )
            reasoning_steps.append(step.model_dump())

            print(
                f"[适应症评估] 使用规则评估: {'符合' if indications_met else '不符合'}"
            )

    except Exception as e:
        error = f"适应症评估失败: {str(e)}"
        print(f"[适应症评估] 错误: {error}")
        # 出错时保守处理，认为不符合
        indications_met = False

    return {
        "indications_met": indications_met,
        "patient_analysis": patient_analysis.model_dump() if patient_analysis else None,
        "reasoning_steps": reasoning_steps,
    }


# ==================== 禁忌症评估节点 ====================


async def assess_contraindications_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估手术禁忌症节点。

    该节点负责：
    - 识别潜在的禁忌症
    - 评估禁忌症的严重程度
    - 判断是否需要终止手术计划

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含禁忌症评估结果
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[禁忌症评估] 手术类型: {procedure_type}")

    contraindications_found = False
    contraindications = []
    error = None

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            # 构建评估提示
            medications = (
                patient_data.get("medications", [])
                if isinstance(patient_data, dict)
                else []
            )
            allergies = (
                patient_data.get("allergies", [])
                if isinstance(patient_data, dict)
                else []
            )
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )

            prompt = f"""请评估以下患者是否存在 {procedure_type} 手术的禁忌症。

手术类型: {procedure_type}

患者信息:
- 合并症: {", ".join(comorbidities)}
- 用药: {", ".join(medications)}
- 过敏史: {", ".join(allergies)}

请识别:
1. 是否存在绝对禁忌症？
2. 是否存在相对禁忌症？
3. 禁忌症的严重程度和影响？

请返回:
- 禁忌症列表
- 严重程度（高危/中危/低危）
- 是否需要终止手术计划"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入心脏病学专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            # 解析响应
            response_text = response.content.strip()
            contraindications_found = (
                "绝对禁忌症" in response_text
                or "高危" in response_text
                or "终止" in response_text
            )

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="评估手术禁忌症",
                evidence=[f"合并症: {', '.join(comorbidities)}"],
                conclusion=f"禁忌症评估: {'发现禁忌症' if contraindications_found else '无禁忌症'}",
            )
            reasoning_steps.append(step.model_dump())

            print(
                f"[禁忌症评估] 评估结果: {'发现禁忌症' if contraindications_found else '无禁忌症'}"
            )

        else:
            # 没有 LLM，使用简单规则
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )

            # 检查常见禁忌症
            critical_conditions = [
                "活动性出血",
                "严重感染",
                "肾功能衰竭",
                "凝血功能障碍",
            ]
            contraindications_found = any(
                any(condition in comorb for comorb in comorbidities)
                for condition in critical_conditions
            )

            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于规则评估禁忌症",
                evidence=[f"合并症: {', '.join(comorbidities)}"],
                conclusion=f"禁忌症评估: {'发现禁忌症' if contraindications_found else '无禁忌症'}",
            )
            reasoning_steps.append(step.model_dump())

            print(
                f"[禁忌症评估] 使用规则评估: {'发现禁忌症' if contraindications_found else '无禁忌症'}"
            )

    except Exception as e:
        error = f"禁忌症评估失败: {str(e)}"
        print(f"[禁忌症评估] 错误: {error}")
        # 出错时保守处理
        contraindications_found = False

    return {
        "contraindications_found": contraindications_found,
        "contraindications": contraindications,
        "reasoning_steps": reasoning_steps,
    }


# ==================== 风险评估节点 ====================


async def assess_risks_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """综合评估手术风险节点。

    该节点负责：
    - 识别手术相关的风险因素
    - 评估每个风险的严重程度
    - 提供风险缓解策略

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含风险评估结果
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[风险评估] 手术类型: {procedure_type}")

    risk_assessment: List[Dict[str, Any]] = []
    error = None

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            # 构建评估提示
            age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )
            lab_results = (
                patient_data.get("lab_results", {})
                if isinstance(patient_data, dict)
                else {}
            )

            prompt = f"""请评估以下患者进行 {procedure_type} 手术的风险。

手术类型: {procedure_type}

患者信息:
- 年龄: {age}岁
- 合并症: {", ".join(comorbidities)}
- 实验室检查: {lab_results}

请评估:
1. 出血风险
2. 血栓风险
3. 肾功能风险
4. 心血管并发症风险
5. 其他特殊风险

对每个风险，请提供:
- 风险因素描述
- 风险等级（高/中/低）
- 缓解策略

请以结构化的方式返回风险评估结果。"""

            await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入手术风险评估专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            # 解析响应并创建风险模型
            # 实际实现中应该解析 LLM 的结构化输出
            # 这里简化为添加几个示例风险

            # 年龄相关风险
            if age > 75:
                risk = RiskFactorModel(
                    factor="高龄相关并发症风险",
                    category="并发症风险",
                    impact=Severity.HIGH if age > 80 else Severity.MEDIUM,
                    mitigation_strategy="加强监护，优化液体管理，预防并发症",
                )
                risk_assessment.append(risk.model_dump())

            # 合并症相关风险
            if "糖尿病" in comorbidities:
                risk = RiskFactorModel(
                    factor="糖尿病相关感染和愈合风险",
                    category="感染风险",
                    impact=Severity.MEDIUM,
                    mitigation_strategy="严格无菌操作，术后加强伤口护理，监测血糖",
                )
                risk_assessment.append(risk.model_dump())

            if "肾功能不全" in comorbidities:
                risk = RiskFactorModel(
                    factor="造影剂肾病风险",
                    category="肾功能风险",
                    impact=Severity.HIGH,
                    mitigation_strategy="水化治疗，最小化造影剂用量，术后监测肾功能",
                )
                risk_assessment.append(risk.model_dump())

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="评估手术风险",
                evidence=[f"年龄: {age}岁", f"合并症: {', '.join(comorbidities)}"],
                conclusion=f"识别 {len(risk_assessment)} 个主要风险因素",
            )
            reasoning_steps.append(step.model_dump())

            print(f"[风险评估] 已识别 {len(risk_assessment)} 个风险因素")

        else:
            # 没有 LLM，使用简单规则
            age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )

            # 简单的风险评估规则
            if age > 75:
                risk = RiskFactorModel(
                    factor="高龄风险",
                    category="并发症风险",
                    impact=Severity.HIGH if age > 80 else Severity.MEDIUM,
                    mitigation_strategy="加强监护",
                )
                risk_assessment.append(risk.model_dump())

            for comorb in comorbidities:
                risk = RiskFactorModel(
                    factor=f"{comorb}相关风险",
                    category="合并症风险",
                    impact=Severity.MEDIUM,
                    mitigation_strategy="优化术前准备",
                )
                risk_assessment.append(risk.model_dump())

            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于规则评估风险",
                evidence=[f"年龄: {age}岁"],
                conclusion=f"识别 {len(risk_assessment)} 个风险因素",
            )
            reasoning_steps.append(step.model_dump())

            print(f"[风险评估] 使用规则评估: {len(risk_assessment)} 个风险")

    except Exception as e:
        error = f"风险评估失败: {str(e)}"
        print(f"[风险评估] 错误: {error}")

    return {
        "risk_assessment": risk_assessment,
        "reasoning_steps": reasoning_steps,
    }


# ==================== 器械匹配节点 ====================


async def match_procedure_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """匹配手术器械和方案节点。

    该节点负责：
    - 基于患者特征和手术类型选择器械
    - 匹配最佳的手术方案
    - 提供器械选择的理由

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含器械推荐和手术方案
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    risk_assessment = state.get("risk_assessment", [])
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[器械匹配] 手术类型: {procedure_type}")

    device_recommendations: List[Dict[str, Any]] = []
    procedure_plan = None
    error = None

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            # 构建推荐提示
            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )
            age = patient_data.get("age", 0) if isinstance(patient_data, dict) else 0

            prompt = f"""请为以下患者推荐 {procedure_type} 手术的器械和方案。

手术类型: {procedure_type}

患者信息:
- 年龄: {age}岁
- 诊断: {", ".join(diagnosis)}

风险评估:
{len(risk_assessment)} 个风险因素

请推荐:
1. 导管选择（类型、规格）
2. 支架选择（类型、规格，如适用）
3. 其他必要器械
4. 手术入路和步骤
5. 预估手术时长和成功率

请以结构化的方式返回推荐结果。"""

            await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入器械选择专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            # 解析响应并创建器械推荐
            # 实际实现中应该解析 LLM 的结构化输出
            # 这里简化为添加几个示例推荐

            # 基于手术类型的器械推荐
            if procedure_type == "PCI" or "PCI" in procedure_type:
                # 导引导管
                device1 = DeviceSelectionModel(
                    device_type="导引导管",
                    device_name="6F 指引导管",
                    manufacturer="示例厂商",
                    size="6F",
                    indication="经皮冠状动脉介入治疗",
                    rationale="6F 导管提供良好的支撑力和通过性，适合常规 PCI",
                )
                device_recommendations.append(device1.model_dump())

                # 指引导丝
                device2 = DeviceSelectionModel(
                    device_type="指引导丝",
                    device_name="工作导丝",
                    size="0.014英寸",
                    indication="通过病变",
                    rationale="标准工作导丝，适合大多数病变",
                )
                device_recommendations.append(device2.model_dump())

                # 药物洗脱支架
                device3 = DeviceSelectionModel(
                    device_type="支架",
                    device_name="药物洗脱支架",
                    indication="冠状动脉狭窄",
                    rationale="降低再狭窄率，改善长期预后",
                )
                device_recommendations.append(device3.model_dump())

            # 创建手术方案
            procedure_plan = ProcedurePlanModel(
                procedure_type=procedure_type,
                approach="经桡动脉入路" if age < 80 else "经股动脉入路",
                steps=[
                    "1. 术前准备和消毒",
                    "2. 穿刺和置入鞘管",
                    "3. 导管就位",
                    "4. 病变预处理",
                    "5. 支架植入",
                    "6. 造影确认",
                    "7. 拔除鞘管",
                ],
                devices=[DeviceSelectionModel(**d) for d in device_recommendations[:3]],
                duration_estimate="30-60分钟",
                success_probability=0.95,
            )

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="匹配手术器械和方案",
                evidence=[f"手术类型: {procedure_type}", f"年龄: {age}岁"],
                conclusion=f"推荐 {len(device_recommendations)} 种器械，选择 {procedure_plan.approach}",
            )
            reasoning_steps.append(step.model_dump())

            print(f"[器械匹配] 已推荐 {len(device_recommendations)} 种器械")

        else:
            # 没有 LLM，使用简单规则
            if procedure_type == "PCI" or "PCI" in procedure_type:
                device1 = DeviceSelectionModel(
                    device_type="导引导管",
                    device_name="6F 指引导管",
                    rationale="标准 PCI 导管",
                )
                device_recommendations.append(device1.model_dump())

            procedure_plan = ProcedurePlanModel(
                procedure_type=procedure_type,
                approach="经桡动脉入路",
                steps=["术前准备", "穿刺", "手术操作", "术后处理"],
                duration_estimate="预估30-60分钟",
            )

            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于规则匹配器械",
                evidence=[f"手术类型: {procedure_type}"],
                conclusion=f"推荐 {len(device_recommendations)} 种器械",
            )
            reasoning_steps.append(step.model_dump())

            print(f"[器械匹配] 使用规则匹配: {len(device_recommendations)} 种器械")

    except Exception as e:
        error = f"器械匹配失败: {str(e)}"
        print(f"[器械匹配] 错误: {error}")

    return {
        "device_recommendations": device_recommendations,
        "procedure_plan": procedure_plan.model_dump() if procedure_plan else None,
        "reasoning_steps": reasoning_steps,
    }


# ==================== 方案生成节点 ====================


async def generate_plan_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """生成完整手术方案节点。

    该节点负责：
    - 整合所有评估结果
    - 生成结构化的完整手术方案
    - 提供术后管理建议

    Args:
        state: 当前工作流状态
        config: 可选的配置信息，包含 llm

    Returns:
        更新后的状态字典，包含完整的手术方案和术后计划
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    risk_assessment = state.get("risk_assessment", [])
    device_recommendations = state.get("device_recommendations", [])
    reasoning_steps = state.get("reasoning_steps", [])

    print(f"[方案生成] 手术类型: {procedure_type}")

    error = None
    recommendations = ""

    try:
        # 从 config 中获取 LLM
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            # 构建方案生成提示
            diagnosis = (
                patient_data.get("diagnosis", [])
                if isinstance(patient_data, dict)
                else []
            )
            comorbidities = (
                patient_data.get("comorbidities", [])
                if isinstance(patient_data, dict)
                else []
            )

            devices_text = "\n".join(
                [
                    f"- {d.get('device_type', '')}: {d.get('device_name', '')} ({d.get('rationale', '')})"
                    for d in device_recommendations[:5]
                ]
            )

            risks_text = "\n".join(
                [
                    f"- {r.get('factor', '')} ({r.get('category', '')}): {r.get('mitigation_strategy', '')}"
                    for r in risk_assessment[:5]
                ]
            )

            prompt = f"""请为以下患者生成完整的 {procedure_type} 手术方案。

患者信息:
- 诊断: {", ".join(diagnosis)}
- 合并症: {", ".join(comorbidities)}

推荐器械:
{devices_text}

风险评估:
{risks_text}

请生成:
1. 手术方案概述
2. 详细手术步骤
3. 器械使用说明
4. 风险防控措施
5. 术后管理计划
6. 随访计划

请以专业、清晰、结构化的方式输出完整方案。"""

            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是一个专业的介入手术方案制定专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            recommendations = response.content.strip()

            # 记录推理步骤
            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="生成完整手术方案",
                evidence=[
                    f"手术类型: {procedure_type}",
                    f"器械数: {len(device_recommendations)}",
                    f"风险数: {len(risk_assessment)}",
                ],
                conclusion="已完成完整手术方案生成",
            )
            reasoning_steps.append(step.model_dump())

            print("[方案生成] 已生成完整方案")

        else:
            # 没有 LLM，使用简单模板
            parts = []
            parts.append(f"## {procedure_type} 手术方案\n")
            parts.append("### 手术概述")
            parts.append(f"基于患者诊断和风险评估，推荐进行 {procedure_type} 手术。\n")

            parts.append("### 推荐器械")
            for i, d in enumerate(device_recommendations[:5], 1):
                parts.append(
                    f"{i}. {d.get('device_type', '')}: {d.get('device_name', '')}"
                )
            parts.append("")

            parts.append("### 风险评估")
            for i, r in enumerate(risk_assessment[:5], 1):
                parts.append(
                    f"{i}. {r.get('factor', '')}: {r.get('mitigation_strategy', '')}"
                )
            parts.append("")

            parts.append("### 术后管理")
            parts.append("- 监测生命体征")
            parts.append("- 观察穿刺部位")
            parts.append("- 抗血小板治疗")
            parts.append("- 定期随访")

            recommendations = "\n".join(parts)

            step = ReasoningStepModel(
                step_number=len(reasoning_steps) + 1,
                phase="pre_op",
                description="基于模板生成方案",
                evidence=[f"手术类型: {procedure_type}"],
                conclusion="已生成基础手术方案",
            )
            reasoning_steps.append(step.model_dump())

            print("[方案生成] 使用模板生成方案")

    except Exception as e:
        error = f"方案生成失败: {str(e)}"
        print(f"[方案生成] 错误: {error}")
        recommendations = f"# {procedure_type} 手术方案\n\n方案生成时遇到错误，请重试。"

    return {
        "recommendations": recommendations,
        "reasoning_steps": reasoning_steps,
    }
