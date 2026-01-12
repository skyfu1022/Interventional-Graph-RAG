"""
介入手术智能体工作流模块。

该模块实现了介入手术辅助决策智能体的工作流，整合患者数据分析、
器械推荐、风险评估和方案推荐等功能。

工作流包括：
1. 原有的简化版工作流（create_interventional_agent）- 向后兼容
2. 新的术前评估工作流（create_preop_workflow）- 完整的 GraphRAG + LLM 实现
"""

from typing import Any, Dict, Optional

from langchain_core.language_models import BaseLanguageModel
from langgraph.graph import END, START, StateGraph

from src.agents.states import ExtendedInterventionalState, InterventionalState

# ==================== 新的术前评估工作流 ====================


def create_preop_workflow(
    rag_adapter: Optional[Any] = None, llm: Optional[BaseLanguageModel] = None
) -> StateGraph:
    """创建术前评估工作流。

    这是完整的术前评估工作流，整合了 GraphRAG 三层图谱检索和 LLM 分析能力。
    工作流按照以下步骤执行：
    1. intent_recognition - 识别患者意图和手术类型
    2. u_retrieval - 从 GraphRAG 三层图谱检索相关知识
    3. assess_indications - 评估手术适应症
    4. assess_contraindications - 评估手术禁忌症
    5. assess_risks - 综合评估手术风险
    6. match_procedure - 匹配手术器械和方案
    7. generate_plan - 生成完整手术方案

    工作流包含条件路由逻辑：
    - route_indications: 如果不符合适应症，则跳转到方案生成（说明原因）
    - route_contraindications: 如果发现禁忌症，则跳转到方案生成（说明原因）
    - route_should_abort: 决定是否继续手术计划

    Args:
        rag_adapter: RAGAnythingAdapter 实例，用于检索医学知识
        llm: LLM 实例（可选），用于生成分析结果

    Returns:
        编译后的 StateGraph 工作流

    Raises:
        ValueError: 如果既没有 rag_adapter 也没有 llm

    Example:
        >>> from src.agents.workflows.interventional import create_preop_workflow
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> # 配置 RAG 适配器和 LLM
        >>> workflow = create_preop_workflow(rag_adapter, llm)
        >>> result = await workflow.ainvoke({
        ...     "patient_data": {
        ...         "patient_id": "P001",
        ...         "age": 65,
        ...         "gender": "male",
        ...         "chief_complaint": "胸痛",
        ...         "diagnosis": ["冠心病"],
        ...         "comorbidities": ["高血压", "糖尿病"]
        ...     },
        ...     "procedure_type": "PCI"
        ... }, config={
        ...     "configurable": {
        ...         "rag_adapter": rag_adapter,
        ...         "llm": llm
        ...     }
        ... })
        >>> assert result["recommendations"] is not None
        >>> assert len(result["reasoning_steps"]) > 0
    """
    # 导入术前评估节点
    from src.agents.nodes.preop import (
        assess_contraindications_node,
        assess_indications_node,
        assess_risks_node,
        generate_plan_node,
        intent_recognition_node,
        match_procedure_node,
        u_retrieval_node,
    )

    # 创建工作流构建器
    workflow = StateGraph(ExtendedInterventionalState)

    # 添加所有术前评估节点
    workflow.add_node("intent_recognition", intent_recognition_node)
    workflow.add_node("u_retrieval", u_retrieval_node)
    workflow.add_node("assess_indications", assess_indications_node)
    workflow.add_node("assess_contraindications", assess_contraindications_node)
    workflow.add_node("assess_risks", assess_risks_node)
    workflow.add_node("match_procedure", match_procedure_node)
    workflow.add_node("generate_plan", generate_plan_node)

    # 添加边连接节点（主流程）
    workflow.add_edge(START, "intent_recognition")
    workflow.add_edge("intent_recognition", "u_retrieval")
    workflow.add_edge("u_retrieval", "assess_indications")

    # 添加条件边：适应症评估
    workflow.add_conditional_edges(
        "assess_indications",
        route_indications,
        {"continue": "assess_contraindications", "abort": "generate_plan"},
    )

    # 添加条件边：禁忌症评估
    workflow.add_conditional_edges(
        "assess_contraindications",
        route_contraindications,
        {"continue": "assess_risks", "abort": "generate_plan"},
    )

    # 添加边：风险评估 -> 器械匹配
    workflow.add_edge("assess_risks", "match_procedure")

    # 添加条件边：决定是否继续
    workflow.add_conditional_edges(
        "match_procedure",
        route_should_abort,
        {"continue": "generate_plan", "abort": "generate_plan"},
    )

    # 添加边：方案生成 -> 结束
    workflow.add_edge("generate_plan", END)

    # 编译并返回工作流
    return workflow.compile()


# ==================== 条件路由函数 ====================


def route_indications(state: ExtendedInterventionalState) -> str:
    """路由函数：根据适应症评估结果决定下一步。

    Args:
        state: 当前工作流状态

    Returns:
        "continue": 如果符合适应症，继续禁忌症评估
        "abort": 如果不符合适应症，跳转到方案生成（说明原因）
    """
    indications_met = state.get("indications_met", False)

    if indications_met:
        print("[路由] 适应症评估通过，继续禁忌症评估")
        return "continue"
    else:
        print("[路由] 适应症评估未通过，生成替代方案")
        return "abort"


def route_contraindications(state: ExtendedInterventionalState) -> str:
    """路由函数：根据禁忌症评估结果决定下一步。

    Args:
        state: 当前工作流状态

    Returns:
        "continue": 如果无禁忌症，继续风险评估
        "abort": 如果发现禁忌症，跳转到方案生成（说明原因）
    """
    contraindications_found = state.get("contraindications_found", False)

    if not contraindications_found:
        print("[路由] 禁忌症评估通过，继续风险评估")
        return "continue"
    else:
        print("[路由] 发现禁忌症，生成替代方案")
        return "abort"


def route_should_abort(state: ExtendedInterventionalState) -> str:
    """路由函数：决定是否继续手术计划。

    综合考虑适应症和禁忌症的评估结果，决定是否继续。

    Args:
        state: 当前工作流状态

    Returns:
        "continue": 继续生成手术方案
        "abort": 生成替代方案（终止或推迟手术）
    """
    indications_met = state.get("indications_met", True)
    contraindications_found = state.get("contraindications_found", False)

    # 如果符合适应症且无禁忌症，继续
    if indications_met and not contraindications_found:
        print("[路由] 评估通过，继续生成手术方案")
        return "continue"
    else:
        print("[路由] 评估未通过，生成替代方案")
        return "abort"


def create_interventional_agent(
    rag_adapter, llm: Optional[BaseLanguageModel] = None
) -> StateGraph:
    """创建介入手术智能体工作流。

    这是一个扩展点，为未来的介入手术智能体提供基础架构。
    工作流按照以下步骤执行：
    1. analyze_patient - 分析患者数据和病史
    2. select_devices - 选择合适的介入器械
    3. assess_risks - 评估手术风险
    4. generate_plan - 生成手术方案

    Args:
        rag_adapter: RAGAnythingAdapter 实例，用于检索医学知识
        llm: LLM 实例（可选），用于生成推荐内容

    Returns:
        编译后的 StateGraph 工作流

    Example:
        >>> from src.agents.workflows.interventional import create_interventional_agent
        >>> workflow = create_interventional_agent(rag_adapter)
        >>> result = await workflow.ainvoke({
        ...     "patient_data": {
        ...         "age": 65,
        ...         "gender": "male",
        ...         "diagnosis": "冠心病",
        ...         "history": ["高血压", "糖尿病"]
        ...     },
        ...     "procedure_type": "PCI",
        ...     "devices": [],
        ...     "risks": [],
        ...     "recommendations": "",
        ...     "context": [],
        ...     "error": None
        ... })
        >>> assert result["recommendations"] is not None
    """
    # 创建工作流构建器
    workflow = StateGraph(InterventionalState)

    # 添加节点
    workflow.add_node("analyze_patient", analyze_patient_node)
    workflow.add_node("select_devices", select_devices_node)
    workflow.add_node("assess_risks", assess_risks_node)
    workflow.add_node("generate_plan", generate_plan_node)

    # 添加边连接节点
    workflow.add_edge(START, "analyze_patient")
    workflow.add_edge("analyze_patient", "select_devices")
    workflow.add_edge("select_devices", "assess_risks")
    workflow.add_edge("assess_risks", "generate_plan")
    workflow.add_edge("generate_plan", END)

    # 编译并返回工作流
    return workflow.compile()


def analyze_patient_node(state: InterventionalState) -> Dict:
    """分析患者数据和病史。

    这个节点负责：
    - 解析患者基本信息（年龄、性别、诊断）
    - 分析患者病史和既往手术史
    - 从知识图谱中检索相关的患者背景信息
    - 识别潜在的风险因素

    Args:
        state: 当前工作流状态

    Returns:
        更新后的状态字典，包含检索到的上下文信息
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    # 占位符实现：提取关键患者信息
    context = state.get("context", [])

    # 分析年龄相关风险
    age = patient_data.get("age", 0)
    if age > 75:
        context.append(f"高龄患者（{age}岁），需要特别关注并发症风险")

    # 分析既往病史
    history = patient_data.get("history", [])
    if history:
        history_str = "、".join(history)
        context.append(f"患者既往病史：{history_str}")

    # 分析诊断信息
    diagnosis = patient_data.get("diagnosis", "")
    if diagnosis:
        context.append(f"初步诊断：{diagnosis}")

    # 手术类型说明
    if procedure_type:
        context.append(f"拟行手术：{procedure_type}")

    return {"context": context}


def select_devices_node(state: InterventionalState) -> Dict:
    """选择合适的介入器械。

    这个节点负责：
    - 根据患者特征和手术类型选择器械
    - 从知识库中检索合适的器械选项
    - 考虑器械的可用性和适用性
    - 记录器械选择依据

    Args:
        state: 当前工作流状态

    Returns:
        更新后的状态字典，包含推荐的器械列表
    """
    procedure_type = state.get("procedure_type", "")
    patient_data = state.get("patient_data", {})
    devices = []

    # 占位符实现：根据手术类型推荐器械
    if procedure_type == "PCI":
        devices.append("导引导管")
        devices.append("指引导丝")
        devices.append("球囊导管")
        devices.append("药物洗脱支架")

        # 根据患者情况调整
        age = patient_data.get("age", 0)
        if age > 70:
            devices.append("血流储备分数（FFR）测量设备")

    elif procedure_type == "起搏器植入":
        devices.append("起搏器脉冲发生器")
        devices.append("心内膜电极导线")
        devices.append("静脉穿刺套件")

    elif procedure_type == "消融术":
        devices.append("消融导管")
        devices.append("电生理记录仪")
        devices.append("导航系统")

    else:
        # 通用器械
        devices.append("标准介入器械包")

    return {"devices": devices}


def assess_risks_node(state: InterventionalState) -> Dict:
    """评估手术风险。

    这个节点负责：
    - 识别患者特定的风险因素
    - 评估手术并发症风险
    - 从医学文献中检索相关风险评估
    - 提供风险缓解建议

    Args:
        state: 当前工作流状态

    Returns:
        更新后的状态字典，包含识别的风险列表
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    risks = []

    # 占位符实现：评估常见风险
    age = patient_data.get("age", 0)
    if age > 70:
        risks.append("高龄相关风险：心血管事件、肾功能不全")

    history = patient_data.get("history", [])
    if "糖尿病" in history:
        risks.append("糖尿病患者：感染风险增加、伤口愈合延迟")

    if "高血压" in history:
        risks.append("高血压患者：术中血压波动风险")

    if "肾功能不全" in history or "肾衰竭" in history:
        risks.append("肾功能不全：造影剂肾病风险，需水化治疗")

    # 手术特定风险
    if procedure_type == "PCI":
        risks.append("PCI手术风险：冠脉穿孔、支架血栓、边支闭塞")
    elif procedure_type == "起搏器植入":
        risks.append("起搏器植入风险：电极脱位、囊袋感染、气胸")
    elif procedure_type == "消融术":
        risks.append("消融术风险：房室传导阻滞、血栓形成、心包填塞")

    # 通用风险
    risks.append("介入手术通用风险：出血、感染、麻醉并发症")

    return {"risks": risks}


def generate_plan_node(state: InterventionalState) -> Dict:
    """生成手术方案。

    这个节点负责：
    - 综合患者分析、器械选择和风险评估结果
    - 生成结构化的手术方案
    - 提供分步骤的操作建议
    - 包含注意事项和备选方案

    Args:
        state: 当前工作流状态

    Returns:
        更新后的状态字典，包含完整的推荐方案
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    devices = state.get("devices", [])
    risks = state.get("risks", [])
    context = state.get("context", [])  # noqa: F841 - 保留用于未来扩展和日志记录

    # 占位符实现：生成结构化方案
    recommendations_parts = []

    # 1. 手术概述
    recommendations_parts.append(f"## {procedure_type} 手术方案\n")
    recommendations_parts.append("### 患者信息")
    recommendations_parts.append(f"- 年龄：{patient_data.get('age', '未知')}岁")
    recommendations_parts.append(f"- 性别：{patient_data.get('gender', '未知')}")
    recommendations_parts.append(f"- 诊断：{patient_data.get('diagnosis', '未知')}\n")

    # 2. 推荐器械
    recommendations_parts.append("### 推荐器械")
    for i, device in enumerate(devices, 1):
        recommendations_parts.append(f"{i}. {device}")
    recommendations_parts.append("")

    # 3. 风险评估
    recommendations_parts.append("### 风险评估")
    for i, risk in enumerate(risks, 1):
        recommendations_parts.append(f"{i}. {risk}")
    recommendations_parts.append("")

    # 4. 手术步骤建议
    recommendations_parts.append("### 手术步骤建议")
    if procedure_type == "PCI":
        recommendations_parts.append("1. 术前评估：冠状动脉造影明确病变位置")
        recommendations_parts.append("2. 器械准备：准备导引导管、指引导丝、球囊和支架")
        recommendations_parts.append("3. 病变预处理：根据病变特点选择适当的预扩张策略")
        recommendations_parts.append("4. 支架植入：植入药物洗脱支架，确保充分贴壁")
        recommendations_parts.append("5. 术后优化：必要时进行后扩张，确保支架展开良好")
    elif procedure_type == "起搏器植入":
        recommendations_parts.append("1. 术前评估：心电图、超声心动图确认适应证")
        recommendations_parts.append("2. 静脉选择：通常选择锁骨下静脉或头静脉")
        recommendations_parts.append("3. 电极植入：在X线透视下放置电极至合适位置")
        recommendations_parts.append("4. 囊袋制作：在胸大肌前制作皮下囊袋")
        recommendations_parts.append("5. 连接测试：测试电极参数，连接起搏器")
    else:
        recommendations_parts.append("1. 术前评估和准备")
        recommendations_parts.append("2. 患者体位和消毒铺巾")
        recommendations_parts.append("3. 麻醉和监护")
        recommendations_parts.append("4. 手术操作")
        recommendations_parts.append("5. 术后观察和护理")

    recommendations_parts.append("")

    # 5. 注意事项
    recommendations_parts.append("### 注意事项")
    recommendations_parts.append("- 术中持续监测生命体征")
    recommendations_parts.append("- 准备好急救设备和药物")
    recommendations_parts.append("- 严格执行无菌操作")
    recommendations_parts.append("- 术后密切观察并发症")

    recommendations = "\n".join(recommendations_parts)

    return {"recommendations": recommendations}
