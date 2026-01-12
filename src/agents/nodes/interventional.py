"""
介入手术节点模块。

该模块实现了介入手术智能体工作流的核心节点，包括：
- 意图识别节点（LLM 实体识别）
- U-Retrieval 知识检索节点（Top-down + Bottom-up）
- 适应症评估节点
- 禁忌症评估节点

基于 LangGraph 和 LightRAG 实现三层图谱检索：
- 患者数据图谱（local 模式）
- 医学文献图谱（global 模式）
- 医学词典图谱（hybrid 模式）
"""

import json
from typing import Any, Dict, List, Optional, Literal, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from src.agents.states import ExtendedInterventionalState
from src.agents.models import (
    ReasoningStepModel,
    Phase,
    Severity,
    DeviceSelectionModel,
    GuidelineMatch,
    PatientDataModel,
    ProcedurePlanModel,
    RetrievedEntity,
    RetrievedRelationship,
    RiskFactorModel,
)
from src.core.adapters import RAGAnythingAdapter
from src.core.exceptions import QueryError, ValidationError
from src.core.logging import get_logger
from src.graph.relationships import RelationType

# 模块日志
logger = get_logger("src.agents.nodes.interventional")


# ==================== 意图识别和 U-Retrieval 数据模型 ====================


class ExtractedEntities(BaseModel):
    """提取的实体模型。

    表示从患者数据和手术描述中提取的结构化实体。

    Attributes:
        risk_factors: 风险因素列表（如 Age > 70, Hypertension, Hyperlipidemia）
        pathologies: 病理发现列表（如 重度狭窄85%, 活动性斑块）
        patient_data: 患者病史数据（如 TIA history）
        anatomy: 解剖结构列表（如 Left ICA, 起始部）
    """

    risk_factors: List[str] = Field(
        default_factory=list, description="识别的风险因素列表"
    )
    pathologies: List[str] = Field(
        default_factory=list, description="识别的病理发现列表"
    )
    patient_data: List[str] = Field(
        default_factory=list, description="患者病史数据列表"
    )
    anatomy: List[str] = Field(default_factory=list, description="解剖结构列表")


class StructuredQuery(BaseModel):
    """结构化查询模型。

    表示用于图谱检索的结构化查询参数。

    Attributes:
        procedure_type: 手术类型（PCI/CAS/TAVI）
        entities: 提取的实体
        query_text: 生成的查询文本
        filters: 查询过滤条件
    """

    procedure_type: str = Field(..., description="手术类型")
    entities: ExtractedEntities = Field(..., description="提取的实体")
    query_text: str = Field(..., description="生成的查询文本")
    filters: Dict[str, Any] = Field(default_factory=dict, description="查询过滤条件")


# ==================== 意图识别节点 ====================


async def intent_recognition_node(
    state: Dict[str, Any], config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """意图识别节点。

    使用 LLM 驱动的实体识别来分析患者数据和手术描述，
    提取关键实体信息并构建结构化查询参数。

    该节点负责：
    1. 识别手术类型（PCI/CAS/TAVI）
    2. LLM 驱动提取实体：
       - :RiskFactor (风险因素): Age > 70, Hypertension, Hyperlipidemia
       - :Pathology (病理): 重度狭窄85%, 活动性斑块
       - :PatientData (病史): TIA history
       - :Anatomy (解剖): Left ICA, 起始部
    3. 构建结构化查询参数（structured_query）
    4. 输出到状态 `extracted_entities` 和 `procedure_type`

    Args:
        state: 当前工作流状态，应包含：
            - patient_data: 患者数据字典
            - procedure_type: 手术类型（可选，将进行识别）
        config: 可选的配置信息，应包含 llm 用于实体识别

    Returns:
        更新后的状态字典，包含：
            - procedure_type: 识别的手术类型
            - extracted_entities: 提取的实体（ExtractedEntities 或字典）
            - structured_query: 构建的结构化查询

    Raises:
        ValidationError: 输入数据验证失败
        QueryError: LLM 调用失败

    Example:
        >>> state = {
        ...     "patient_data": {
        ...         "age": 75,
        ...         "gender": "male",
        ...         "diagnosis": "左侧颈内动脉重度狭窄",
        ...         "history": ["高血压", "TIA"]
        ...     },
        ...     "procedure_type": "CAS"
        ... }
        >>> result = await intent_recognition_node(state)
        >>> print(result["procedure_type"])  # "CAS"
        >>> print(result["extracted_entities"]["risk_factors"])
        # ["Age > 70", "Hypertension"]
    """
    logger.info("[意图识别] 开始实体识别和手术类型识别")

    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    try:
        # ========== 步骤 1: 识别手术类型 ==========
        if not procedure_type:
            procedure_type = _identify_procedure_type(patient_data)
            logger.info(f"[意图识别] 识别手术类型: {procedure_type}")
        else:
            logger.info(f"[意图识别] 使用指定手术类型: {procedure_type}")

        # ========== 步骤 2: 构建 LLM 提示 ==========
        prompt = _build_entity_extraction_prompt(patient_data, procedure_type)

        # ========== 步骤 3: 调用 LLM 提取实体 ==========
        llm = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if llm:
            extracted_entities = await _extract_entities_with_llm(
                llm, prompt, procedure_type
            )
        else:
            logger.warning("[意图识别] 未配置 LLM，使用规则提取实体")
            extracted_entities = _extract_entities_with_rules(
                patient_data, procedure_type
            )

        # ========== 步骤 4: 构建结构化查询 ==========
        structured_query = _build_structured_query(
            procedure_type, extracted_entities, patient_data
        )

        logger.info(
            f"[意图识别] 完成 | "
            f"手术类型: {procedure_type} | "
            f"风险因素: {len(extracted_entities.get('risk_factors', []))} | "
            f"病理: {len(extracted_entities.get('pathologies', []))}"
        )

        return {
            "procedure_type": procedure_type,
            "extracted_entities": extracted_entities,
            "structured_query": structured_query,
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[意图识别] 失败: {e}")
        raise QueryError(
            f"意图识别失败: {e}",
            query_text=str(patient_data),
            details={"procedure_type": procedure_type},
        ) from e


def _identify_procedure_type(patient_data: Dict[str, Any]) -> str:
    """识别手术类型。

    根据患者数据中的诊断、手术描述等信息识别手术类型。

    Args:
        patient_data: 患者数据字典

    Returns:
        识别的手术类型（PCI/CAS/TAVI/OTHER）

    Raises:
        ValidationError: 无法识别手术类型
    """
    diagnosis = patient_data.get("diagnosis", "").lower()
    description = patient_data.get("description", "").lower()
    combined_text = f"{diagnosis} {description}"

    # 手术类型关键词匹配
    procedure_keywords = {
        "PCI": ["pci", "经皮冠状动脉介入", "冠脉介入", "支架植入", "冠脉支架"],
        "CAS": ["cas", "颈动脉支架", "carotid stent", "颈动脉狭窄", "颈内动脉"],
        "TAVI": [
            "tavi",
            "tavr",
            "经导管主动脉瓣",
            "主动脉瓣置换",
            "aortic valve",
            "transcatheter",
        ],
    }

    # 匹配手术类型
    for proc_type, keywords in procedure_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            return proc_type

    # 默认返回 OTHER
    logger.warning("[手术类型识别] 未识别到具体类型，默认为 OTHER")
    return "OTHER"


def _build_entity_extraction_prompt(
    patient_data: Dict[str, Any], procedure_type: str
) -> str:
    """构建实体提取的 LLM 提示。

    Args:
        patient_data: 患者数据
        procedure_type: 手术类型

    Returns:
        LLM 提示字符串
    """
    # 格式化患者数据
    patient_info = []

    if "age" in patient_data:
        patient_info.append(f"年龄: {patient_data['age']}岁")

    if "gender" in patient_data:
        patient_info.append(f"性别: {patient_data['gender']}")

    if "diagnosis" in patient_data:
        patient_info.append(f"诊断: {patient_data['diagnosis']}")

    if "history" in patient_data and patient_data["history"]:
        patient_info.append(f"病史: {', '.join(patient_data['history'])}")

    if "comorbidities" in patient_data and patient_data["comorbidities"]:
        patient_info.append(f"合并症: {', '.join(patient_data['comorbidities'])}")

    if "lab_results" in patient_data and patient_data["lab_results"]:
        lab_str = json.dumps(patient_data["lab_results"], ensure_ascii=False)
        patient_info.append(f"实验室检查: {lab_str}")

    if "imaging_findings" in patient_data and patient_data["imaging_findings"]:
        imaging_str = "; ".join(patient_data["imaging_findings"])
        patient_info.append(f"影像学发现: {imaging_str}")

    patient_text = "\n".join(patient_info) if patient_info else "无详细患者信息"

    # 构建 LLM 提示
    prompt = f"""请从以下患者数据和手术描述中提取关键医学实体。

手术类型: {procedure_type}

患者信息:
{patient_text}

请提取以下四类实体:

1. **风险因素 (RiskFactor)**: 包括高龄、高血压、糖尿病、高脂血症、吸烟史、既往TIA/卒中史等
   - 例如: "Age > 70", "Hypertension", "Hyperlipidemia", "吸烟史", "TIA history"

2. **病理发现 (Pathology)**: 包括狭窄程度、斑块特征、病变类型等
   - 例如: "重度狭窄85%", "活动性斑块", "钙化病变", "血栓形成"

3. **病史数据 (PatientData)**: 包括既往病史、手术史、用药史等
   - 例如: "TIA history 3年前", "既往PCI术后", "长期服用阿司匹林"

4. **解剖结构 (Anatomy)**: 包括病变部位、血管名称、解剖位置等
   - 例如: "Left ICA", "起始部", "前降支近段", "主动脉瓣"

请以JSON格式返回，结构如下:
{{
    "risk_factors": ["...", "..."],
    "pathologies": ["...", "..."],
    "patient_data": ["...", "..."],
    "anatomy": ["...", "..."]
}}

注意:
- 只返回JSON，不要有其他说明文字
- 如果某个类别没有提取到实体，返回空列表 []
- 实体描述要简洁、准确，使用标准医学术语
"""

    return prompt


async def _extract_entities_with_llm(
    llm: BaseChatModel, prompt: str, procedure_type: str
) -> Dict[str, List[str]]:
    """使用 LLM 提取实体。

    Args:
        llm: LLM 实例
        prompt: 提取实体提示
        procedure_type: 手术类型

    Returns:
        提取的实体字典

    Raises:
        QueryError: LLM 调用失败或解析失败
    """
    try:
        logger.debug("[意图识别] 调用 LLM 提取实体")

        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="你是一个专业的医学实体提取助手，擅长从患者数据中提取"
                    "风险因素、病理发现、病史数据和解剖结构等关键信息。"
                ),
                HumanMessage(content=prompt),
            ]
        )

        response_text = response.content.strip()

        # 解析 JSON 响应
        try:
            # 尝试直接解析
            entities = json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 代码块
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                entities = json.loads(json_str)
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                entities = json.loads(json_str)
            else:
                raise ValueError(f"无法解析 LLM 响应为 JSON: {response_text[:200]}")

        # 验证实体结构
        required_keys = ["risk_factors", "pathologies", "patient_data", "anatomy"]
        for key in required_keys:
            if key not in entities:
                entities[key] = []
            if not isinstance(entities[key], list):
                entities[key] = []

        logger.info(
            f"[意图识别] LLM 提取实体成功 | "
            f"风险: {len(entities['risk_factors'])} | "
            f"病理: {len(entities['pathologies'])} | "
            f"病史: {len(entities['patient_data'])} | "
            f"解剖: {len(entities['anatomy'])}"
        )

        return entities

    except Exception as e:
        logger.error(f"[意图识别] LLM 实体提取失败: {e}")
        raise QueryError(
            f"LLM 实体提取失败: {e}",
            query_text=prompt[:200],
            details={"procedure_type": procedure_type},
        ) from e


def _extract_entities_with_rules(
    patient_data: Dict[str, Any], procedure_type: str
) -> Dict[str, List[str]]:
    """使用规则提取实体（后备方案）。

    Args:
        patient_data: 患者数据
        procedure_type: 手术类型

    Returns:
        提取的实体字典
    """
    entities = {
        "risk_factors": [],
        "pathologies": [],
        "patient_data": [],
        "anatomy": [],
    }

    # 提取风险因素
    age = patient_data.get("age", 0)
    if age > 70:
        entities["risk_factors"].append(f"Age > 70 ({age}岁)")

    history = patient_data.get("history", [])
    comorbidities = patient_data.get("comorbidities", [])

    risk_keywords = {
        "高血压": "Hypertension",
        "糖尿病": "Diabetes",
        "高脂血症": "Hyperlipidemia",
        "高血脂": "Hyperlipidemia",
        "吸烟": "吸烟史",
        "tia": "TIA history",
        "卒中": "Stroke history",
        "心肌梗死": "MI history",
    }

    for item in history + comorbidities:
        item_lower = item.lower()
        for keyword, standard_name in risk_keywords.items():
            if keyword in item_lower:
                if standard_name not in entities["risk_factors"]:
                    entities["risk_factors"].append(standard_name)

    # 提取病理发现
    diagnosis = patient_data.get("diagnosis", "")
    if "狭窄" in diagnosis:
        entities["pathologies"].append(diagnosis)

    imaging = patient_data.get("imaging_findings", [])
    for finding in imaging:
        if any(keyword in finding for keyword in ["狭窄", "斑块", "血栓", "钙化"]):
            entities["pathologies"].append(finding)

    # 提取病史数据
    for item in history:
        entities["patient_data"].append(f"病史: {item}")

    # 提取解剖结构
    if "左侧" in diagnosis or "右" in diagnosis:
        entities["anatomy"].append(diagnosis)

    for finding in imaging:
        if any(keyword in finding for keyword in ["动脉", "静脉", "段", "支"]):
            entities["anatomy"].append(finding)

    logger.info(
        f"[意图识别] 规则提取实体 | "
        f"风险: {len(entities['risk_factors'])} | "
        f"病理: {len(entities['pathologies'])} | "
        f"病史: {len(entities['patient_data'])} | "
        f"解剖: {len(entities['anatomy'])}"
    )

    return entities


def _build_structured_query(
    procedure_type: str,
    extracted_entities: Dict[str, List[str]],
    patient_data: Dict[str, Any],
) -> Dict[str, Any]:
    """构建结构化查询。

    Args:
        procedure_type: 手术类型
        extracted_entities: 提取的实体
        patient_data: 患者数据

    Returns:
        结构化查询字典
    """
    # 构建查询文本
    query_parts = [f"{procedure_type}手术"]

    if extracted_entities.get("risk_factors"):
        query_parts.append(
            "风险因素: " + ", ".join(extracted_entities["risk_factors"][:3])
        )

    if extracted_entities.get("pathologies"):
        query_parts.append("病理: " + ", ".join(extracted_entities["pathologies"][:3]))

    query_text = " | ".join(query_parts)

    # 构建过滤条件
    filters = {"procedure_type": procedure_type}

    age = patient_data.get("age", 0)
    if age > 0:
        filters["age_group"] = "elderly" if age > 70 else "adult"

    structured_query = {
        "procedure_type": procedure_type,
        "entities": extracted_entities,
        "query_text": query_text,
        "filters": filters,
    }

    logger.debug(f"[意图识别] 构建结构化查询: {query_text[:100]}...")

    return structured_query


# ==================== U-Retrieval 知识检索节点 ====================


async def u_retrieval_node(
    state: Dict[str, Any], config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """U-Retrieval 知识检索节点。

    实现双向检索策略：
    1. **Top-down（精确索引检索）**：
       - 从医学文献图谱（global 模式）检索权威指南 :Guideline
       - 提取推荐等级（Class I/IIa/IIb/III）和证据级别（A/B/C）
       - 提取适应症和禁忌症定义

    2. **Bottom-up（全局聚合检索）**：
       - 结合患者上下文（高龄、症状性）向上聚合检索
       - 从患者图谱（local）检索：既往病史、检查结果
       - 从医学词典图谱（hybrid）检索：器械规格、适应症

    该节点负责：
    - 执行 Top-down 检索（文献指南图谱）
    - 执行 Bottom-up 检索（患者 + 词典图谱）
    - 合并检索结果到状态
    - 记录来源图谱和检索模式

    Args:
        state: 当前工作流状态，应包含：
            - structured_query: 结构化查询参数
            - procedure_type: 手术类型
        config: 可选的配置信息，应包含 rag_adapter

    Returns:
        更新后的状态字典，包含：
            - guideline_context: 指南上下文（Top-down）
            - patient_context: 患者上下文（Bottom-up - local）
            - device_context: 器械上下文（Bottom-up - dictionary）
            - retrieval_mode: 使用的检索模式

    Raises:
        ValidationError: 输入数据验证失败
        QueryError: 检索执行失败

    Example:
        >>> state = {
        ...     "structured_query": {
        ...         "procedure_type": "CAS",
        ...         "query_text": "CAS手术 | 风险因素: Age > 70, Hypertension"
        ...     },
        ...     "procedure_type": "CAS"
        ... }
        >>> result = await u_retrieval_node(state)
        >>> print(result["guideline_context"])  # Top-down 检索结果
        >>> print(result["patient_context"])   # Bottom-up 患者数据
        >>> print(result["device_context"])    # Bottom-up 器械信息
    """
    logger.info("[U-Retrieval] 开始双向检索")

    structured_query = state.get("structured_query", {})
    procedure_type = state.get("procedure_type", "")

    if not structured_query:
        raise ValidationError(
            "缺少结构化查询参数",
            field="structured_query",
            value=structured_query,
        )

    query_text = structured_query.get("query_text", "")
    entities = structured_query.get("entities", {})
    filters = structured_query.get("filters", {})

    try:
        # ========== 获取 RAG 适配器 ==========
        rag_adapter = None
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")

        if not rag_adapter:
            logger.warning("[U-Retrieval] 未配置 RAG 适配器，使用空结果")

            return {
                "guideline_context": {},
                "patient_context": {},
                "device_context": {},
                "retrieval_mode": "none",
                "sources": ["无数据源"],
            }

        # ========== Top-down 检索：文献指南图谱 ==========
        logger.info("[U-Retrieval] Top-down: 检索文献指南图谱")
        guideline_context = await _topdown_retrieval(
            rag_adapter, query_text, procedure_type, entities
        )

        # ========== Bottom-up 检索：患者图谱 ==========
        logger.info("[U-Retrieval] Bottom-up: 检索患者图谱")
        patient_context = await _bottomup_patient_retrieval(
            rag_adapter, entities, filters
        )

        # ========== Bottom-up 检索：医学词典图谱 ==========
        logger.info("[U-Retrieval] Bottom-up: 检索医学词典图谱")
        device_context = await _bottomup_dictionary_retrieval(
            rag_adapter, procedure_type, entities
        )

        # ========== 合并来源信息 ==========
        sources = [
            f"literature_graph (global): {len(guideline_context.get('guidelines', []))} 条指南",
            f"patient_graph (local): {len(patient_context.get('history', []))} 条记录",
            f"dictionary_graph (hybrid): {len(device_context.get('devices', []))} 个器械",
        ]

        logger.info(
            f"[U-Retrieval] 完成 | "
            f"指南: {len(guideline_context.get('guidelines', []))} | "
            f"患者: {len(patient_context.get('history', []))} | "
            f"器械: {len(device_context.get('devices', []))}"
        )

        return {
            "guideline_context": guideline_context,
            "patient_context": patient_context,
            "device_context": device_context,
            "retrieval_mode": "u_retrieval",
            "sources": sources,
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[U-Retrieval] 失败: {e}")
        raise QueryError(
            f"U-Retrieval 检索失败: {e}",
            query_text=query_text,
            details={
                "procedure_type": procedure_type,
                "filters": filters,
            },
        ) from e


async def _topdown_retrieval(
    adapter: RAGAnythingAdapter,
    query_text: str,
    procedure_type: str,
    entities: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Top-down 精确索引检索。

    从医学文献图谱（global 模式）检索权威指南。

    Args:
        adapter: RAG 适配器
        query_text: 查询文本
        procedure_type: 手术类型
        entities: 提取的实体

    Returns:
        指南上下文字典
    """
    try:
        # 构建 Top-down 查询（专注于指南推荐）
        topdown_query = f"{procedure_type}指南 适应症 禁忌症 推荐"

        # 使用 global 模式检索（全局检索，关注实体间关系）
        result = await adapter.query(
            question=topdown_query,
            mode="global",
            top_k=5,
        )

        # 解析检索结果，提取指南信息
        guidelines = []
        evidence_levels = []
        recommendations = []

        if result.answer:
            # 简单解析（实际应用中可以使用更复杂的 NLP 解析）
            answer_lines = result.answer.split("\n")

            for line in answer_lines:
                line = line.strip()

                # 提取推荐等级
                if any(
                    level in line
                    for level in ["Class I", "Class IIa", "Class IIb", "Class III"]
                ):
                    recommendations.append(line)

                # 提取证据级别
                if any(level in line for level in ["Level A", "Level B", "Level C"]):
                    evidence_levels.append(line)

                # 提取适应症/禁忌症
                if any(
                    keyword in line
                    for keyword in [
                        "适应症",
                        "禁忌症",
                        "推荐",
                        "Indication",
                        "Contraindication",
                    ]
                ):
                    guidelines.append(line)

        guideline_context = {
            "guidelines": guidelines[:10],
            "evidence_levels": list(set(evidence_levels))[:5],
            "recommendations": recommendations[:10],
            "query_mode": "global",
            "source_graph": "literature",
            "answer_summary": result.answer[:500] if result.answer else "",
        }

        logger.info(
            f"[Top-down] 检索完成 | "
            f"指南: {len(guidelines)} | "
            f"推荐等级: {len(recommendations)}"
        )

        return guideline_context

    except Exception as e:
        logger.error(f"[Top-down] 检索失败: {e}")
        return {
            "guidelines": [],
            "evidence_levels": [],
            "recommendations": [],
            "query_mode": "global",
            "source_graph": "literature",
            "error": str(e),
        }


async def _bottomup_patient_retrieval(
    adapter: RAGAnythingAdapter, entities: Dict[str, List[str]], filters: Dict[str, Any]
) -> Dict[str, Any]:
    """Bottom-up 患者图谱检索。

    从患者图谱（local 模式）检索既往病史、检查结果。

    Args:
        adapter: RAG 适配器
        entities: 提取的实体
        filters: 过滤条件

    Returns:
        患者上下文字典
    """
    try:
        # 构建患者上下文查询
        query_parts = []

        if entities.get("risk_factors"):
            query_parts.append("风险因素: " + ", ".join(entities["risk_factors"][:3]))

        if entities.get("patient_data"):
            query_parts.append("病史: " + ", ".join(entities["patient_data"][:3]))

        if not query_parts:
            query_parts.append("患者病史 检查结果")

        patient_query = " | ".join(query_parts)

        # 使用 local 模式检索（局部检索，关注实体细节）
        result = await adapter.query(
            question=patient_query,
            mode="local",
            top_k=3,
        )

        # 解析患者数据
        history = entities.get("patient_data", [])
        risk_factors = entities.get("risk_factors", [])
        lab_results = []

        # 从 entities 中提取实验室检查相关（如果有）
        if entities.get("pathologies"):
            lab_results.extend(
                [
                    p
                    for p in entities["pathologies"]
                    if any(kw in p for kw in ["实验室", "检查", "指标"])
                ]
            )

        patient_context = {
            "history": history[:10],
            "risk_factors": risk_factors[:10],
            "lab_results": lab_results[:5],
            "query_mode": "local",
            "source_graph": "patient",
            "age_group": filters.get("age_group", "unknown"),
            "answer_summary": result.answer[:300] if result.answer else "",
        }

        logger.info(
            f"[Bottom-up-patient] 检索完成 | "
            f"病史: {len(history)} | "
            f"风险: {len(risk_factors)}"
        )

        return patient_context

    except Exception as e:
        logger.error(f"[Bottom-up-patient] 检索失败: {e}")
        return {
            "history": entities.get("patient_data", [])[:10],
            "risk_factors": entities.get("risk_factors", [])[:10],
            "lab_results": [],
            "query_mode": "local",
            "source_graph": "patient",
            "error": str(e),
        }


async def _bottomup_dictionary_retrieval(
    adapter: RAGAnythingAdapter, procedure_type: str, entities: Dict[str, List[str]]
) -> Dict[str, Any]:
    """Bottom-up 医学词典图谱检索。

    从医学词典图谱（hybrid 模式）检索器械规格、适应症。

    Args:
        adapter: RAG 适配器
        procedure_type: 手术类型
        entities: 提取的实体

    Returns:
        器械上下文字典
    """
    try:
        # 构建器械查询
        device_query = f"{procedure_type} 器械 规格 适应症 导管 支架"

        # 使用 hybrid 模式检索（混合检索）
        result = await adapter.query(
            question=device_query,
            mode="hybrid",
            top_k=3,
        )

        # 解析器械信息
        devices = []
        indications = []
        contraindications = []

        if result.answer:
            # 简单解析
            answer_lines = result.answer.split("\n")

            for line in answer_lines:
                line = line.strip()

                # 提取器械信息
                if any(
                    keyword in line
                    for keyword in [
                        "导管",
                        "支架",
                        "球囊",
                        "导丝",
                        "device",
                        "catheter",
                        "stent",
                    ]
                ):
                    devices.append(line)

                # 提取适应症
                if any(keyword in line for keyword in ["适应症", "适用", "indication"]):
                    indications.append(line)

                # 提取禁忌症
                if any(
                    keyword in line
                    for keyword in ["禁忌症", "不适用", "contraindication"]
                ):
                    contraindications.append(line)

        device_context = {
            "devices": devices[:10],
            "indications": indications[:5],
            "contraindications": contraindications[:5],
            "query_mode": "hybrid",
            "source_graph": "dictionary",
            "procedure_type": procedure_type,
            "answer_summary": result.answer[:300] if result.answer else "",
        }

        logger.info(
            f"[Bottom-up-dictionary] 检索完成 | "
            f"器械: {len(devices)} | "
            f"适应症: {len(indications)}"
        )

        return device_context

    except Exception as e:
        logger.error(f"[Bottom-up-dictionary] 检索失败: {e}")
        return {
            "devices": [],
            "indications": [],
            "contraindications": [],
            "query_mode": "hybrid",
            "source_graph": "dictionary",
            "procedure_type": procedure_type,
            "error": str(e),
        }


# ==================== 适应症评估输出模型 ====================


class IndicationAssessmentResult(BaseModel):
    """适应症评估结果模型。

    表示 LLM 对患者是否符合手术适应症的评估结果。

    Attributes:
        decision: 评估决策，可选值: indicated（符合适应症）、
                 not_indicated（不符合适应症）、uncertain（不确定）
        confidence: 决策置信度（0-1）
        guideline_evidence: 支持决策的指南依据列表
        reasoning: 详细推理过程
    """

    decision: Literal["indicated", "not_indicated", "uncertain"] = Field(
        ...,
        description="评估决策：indicated（符合）、not_indicated（不符合）、uncertain（不确定）",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="决策置信度")
    guideline_evidence: List[str] = Field(
        default_factory=list, description="支持决策的指南依据"
    )
    reasoning: str = Field(..., description="详细推理过程")


# ==================== 禁忌症评估输出模型 ====================


class ContraindicationAssessmentResult(BaseModel):
    """禁忌症评估结果模型。

    表示 LLM 对患者是否存在手术禁忌症的评估结果。

    Attributes:
        decision: 评估决策，可选值: proceed（可进行）、modify（需修改方案）、
                 abort（禁止手术）
        absolute_contraindications: 绝对禁忌症列表（Class III）
        relative_contraindications: 相对禁忌症列表（Class II）
        guideline_sources: 禁忌症来源指南列表
        reasoning: 详细推理过程
    """

    decision: Literal["proceed", "modify", "abort"] = Field(
        ...,
        description="评估决策：proceed（可进行）、modify（需修改）、abort（禁止）",
    )
    absolute_contraindications: List[str] = Field(
        default_factory=list, description="绝对禁忌症列表（Class III）"
    )
    relative_contraindications: List[str] = Field(
        default_factory=list, description="相对禁忌症列表（Class II）"
    )
    guideline_sources: List[str] = Field(
        default_factory=list, description="禁忌症来源指南"
    )
    reasoning: str = Field(..., description="详细推理过程")


# ==================== 适应症评估节点 ====================


async def assess_indications_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估手术适应症节点。

    该节点基于检索到的临床指南和患者数据，使用 LLM 分析患者是否符合
    手术适应症要求。

    主要功能：
    1. 使用已检索的指南上下文（不重复检索）
    2. LLM 驱动分析：
       - 判断是否符合手术适应症（基于指南推荐）
       - 引用指南依据（如 "症状性+重度狭窄>70% = Class I 推荐"）
    3. 输出路由决策：indicated / not_indicated / uncertain
    4. 记录推理步骤到 reasoning_chain

    Args:
        state: 当前工作流状态，应包含：
            - patient_analysis: 患者数据分析结果
            - matched_guidelines: 匹配的指南列表
            - literature_graph_context: 文献指南图谱上下文
            - reasoning_steps: 现有推理步骤列表
        config: 可选的配置信息，应包含 llm 用于 LLM 分析

    Returns:
        更新后的状态字典，包含：
            - reasoning_steps: 新增的推理步骤
            - literature_graph_context: 更新后的文献上下文（包含评估结果）
            - error: 错误信息（如果有）

    Example:
        >>> state = {
        ...     "patient_analysis": {"age": 65, "diagnosis": ["冠心病"]},
        ...     "matched_guidelines": [guideline_match],
        ...     "literature_graph_context": {},
        ...     "reasoning_steps": [],
        ... }
        >>> result = await assess_indications_node(state, config)
        >>> assert "reasoning_steps" in result
        >>> assert len(result["reasoning_steps"]) > 0
    """
    print("[适应症评估] 开始评估手术适应症")

    # 获取患者数据和指南
    patient_analysis = state.get("patient_analysis")
    matched_guidelines = state.get("matched_guidelines", [])
    literature_context = state.get("literature_graph_context", {})
    reasoning_steps = state.get("reasoning_steps", [])

    error = None
    assessment_result = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

            if llm and patient_analysis:
                # 构建评估提示
                prompt = _build_indication_assessment_prompt(
                    patient_analysis, matched_guidelines
                )

                # 使用 structured output 获取结构化结果
                structured_llm = llm.with_structured_output(IndicationAssessmentResult)

                response = await structured_llm.ainvoke(
                    [
                        SystemMessage(
                            content="你是一个专业的介入手术适应症评估专家，"
                            "擅长基于临床指南评估患者是否符合手术适应症。"
                        ),
                        HumanMessage(content=prompt),
                    ]
                )

                assessment_result = response
                print(
                    f"[适应症评估] 评估完成：决策={assessment_result.decision}, "
                    f"置信度={assessment_result.confidence:.2f}"
                )

            else:
                # 没有 LLM 或患者数据，使用启发式规则
                assessment_result = _heuristic_indication_assessment(
                    patient_analysis, matched_guidelines
                )
                print("[适应症评估] 使用启发式规则评估")

        else:
            # 没有 config，使用启发式规则
            assessment_result = _heuristic_indication_assessment(
                patient_analysis, matched_guidelines
            )
            print("[适应症评估] 使用启发式规则评估（未提供 config）")

        # 创建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.PRE_OP,
            description="评估手术适应症",
            evidence=assessment_result.guideline_evidence,
            conclusion=f"决策：{assessment_result.decision}，"
            f"置信度：{assessment_result.confidence:.2f}",
        )

        reasoning_steps = reasoning_steps + [reasoning_step]

        # 更新文献图谱上下文
        literature_context["indication_assessment"] = {
            "decision": assessment_result.decision,
            "confidence": assessment_result.confidence,
            "evidence_count": len(assessment_result.guideline_evidence),
            "reasoning": assessment_result.reasoning,
        }

        print(f"[适应症评估] 推理步骤已添加（总计：{len(reasoning_steps)} 步）")

    except Exception as e:
        error = f"适应症评估失败: {str(e)}"
        print(f"[适应症评估] 错误: {error}")

        # 即使出错也记录一个推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.PRE_OP,
            description="评估手术适应症",
            evidence=[],
            conclusion=f"评估失败：{error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step]

    return {
        "reasoning_steps": reasoning_steps,
        "literature_graph_context": literature_context,
        "error": error,
    }


def _build_indication_assessment_prompt(
    patient_analysis: Any, matched_guidelines: List[Any]
) -> str:
    """构建适应症评估提示。

    Args:
        patient_analysis: 患者数据分析结果
        matched_guidelines: 匹配的指南列表

    Returns:
        构建的提示字符串
    """
    # 提取患者信息
    if isinstance(patient_analysis, dict):
        age = patient_analysis.get("age", "未知")
        diagnosis = patient_analysis.get("diagnosis", [])
        comorbidities = patient_analysis.get("comorbidities", [])
        chief_complaint = patient_analysis.get("chief_complaint", "")
    else:
        # 假设是 Pydantic 模型
        age = getattr(patient_analysis, "age", "未知")
        diagnosis = getattr(patient_analysis, "diagnosis", [])
        comorbidities = getattr(patient_analysis, "comorbidities", [])
        chief_complaint = getattr(patient_analysis, "chief_complaint", "")

    # 构建指南文本
    guideline_text = ""
    if matched_guidelines:
        guideline_items = []
        for guide in matched_guidelines[:5]:  # 限制为前5个指南
            if isinstance(guide, dict):
                title = guide.get("title", "未知指南")
                recommendation = guide.get("recommendation", "")
                evidence_level = guide.get("evidence_level", "")
                indication = guide.get("indication", "")
            else:
                title = getattr(guide, "title", "未知指南")
                recommendation = getattr(guide, "recommendation", "")
                evidence_level = getattr(guide, "evidence_level", "")
                indication = getattr(guide, "indication", "")

            item = f"- {title}"
            if recommendation:
                item += f"\n  推荐：{recommendation}"
            if evidence_level:
                item += f"\n  证据等级：{evidence_level}"
            if indication:
                item += f"\n  适应症：{indication}"

            guideline_items.append(item)

        guideline_text = "\n\n".join(guideline_items)
    else:
        guideline_text = "（未提供具体指南）"

    # 构建完整提示
    prompt = f"""请基于以下患者信息和临床指南，评估患者是否符合介入手术适应症。

## 患者信息
- 年龄：{age}岁
- 主诉：{chief_complaint}
- 诊断：{", ".join(diagnosis) if diagnosis else "未指定"}
- 合并症：{", ".join(comorbidities) if comorbidities else "无"}

## 相关临床指南
{guideline_text}

## 评估要求
请基于以上信息，评估患者是否符合介入手术适应症：

1. **决策判断**：
   - indicated：符合适应症，推荐手术
   - not_indicated：不符合适应症，不推荐手术
   - uncertain：证据不足，需要进一步评估

2. **指南依据**：
   - 引用具体的指南推荐
   - 说明证据等级（如 Class I, IIa, IIb, III）
   - 引用相关标准（如狭窄程度、症状类型等）

3. **置信度评估**：
   - 0.9-1.0：高度确定（有明确的 Class I 推荐）
   - 0.7-0.9：较为确定（有 Class IIa 推荐）
   - 0.5-0.7：中等确定（有 Class IIb 推荐）
   - <0.5：不确定（证据不足或矛盾）

4. **推理过程**：
   - 说明判断依据
   - 考虑患者具体情况
   - 分析指南适用性

请以结构化的方式输出评估结果。
"""

    return prompt


def _heuristic_indication_assessment(
    patient_analysis: Any, matched_guidelines: List[Any]
) -> IndicationAssessmentResult:
    """启发式适应症评估（备用方案）。

    当没有 LLM 时使用简单的规则进行评估。

    Args:
        patient_analysis: 患者数据分析结果
        matched_guidelines: 匹配的指南列表

    Returns:
        评估结果
    """
    # 默认结果
    decision = "uncertain"
    confidence = 0.5
    guideline_evidence = []
    reasoning = "使用启发式规则评估，建议进行专业医学评估。"

    # 提取诊断信息
    if isinstance(patient_analysis, dict):
        diagnosis = patient_analysis.get("diagnosis", [])
    else:
        diagnosis = getattr(patient_analysis, "diagnosis", [])

    # 简单的规则匹配
    if matched_guidelines:
        high_quality_guides = [
            g
            for g in matched_guidelines
            if (isinstance(g, dict) and g.get("matching_score", 0) > 0.8)
            or (hasattr(g, "matching_score") and g.matching_score > 0.8)
        ]

        if high_quality_guides:
            decision = "indicated"
            confidence = 0.7
            guideline_evidence = [f"匹配到 {len(high_quality_guides)} 条高质量指南"]
            reasoning = "基于匹配的高质量临床指南，患者可能符合手术适应症。"

    # 特定诊断的规则
    if diagnosis:
        for diag in diagnosis:
            if "急性心肌梗死" in diag or "冠心病" in diag:
                decision = "indicated"
                confidence = 0.75
                guideline_evidence.append("诊断提示可能需要介入治疗")
                reasoning = f"患者诊断为 {diag}，可能符合介入手术适应症。"
                break

    return IndicationAssessmentResult(
        decision=decision,
        confidence=confidence,
        guideline_evidence=guideline_evidence,
        reasoning=reasoning,
    )


# ==================== 禁忌症评估节点 ====================


async def assess_contraindications_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估手术禁忌症节点。

    该节点基于检索到的临床指南和患者数据，使用 LLM 分析患者是否存在
    手术禁忌症。

    主要功能：
    1. 使用已检索的禁忌症信息（不重复检索）
    2. LLM 驱动分析：
       - 检查 Class III（绝对禁忌）
       - 检查 Class II（相对禁忌）
    3. 输出路由决策：proceed / modify / abort
    4. 记录推理步骤和来源指南

    Args:
        state: 当前工作流状态，应包含：
            - patient_analysis: 患者数据分析结果
            - matched_guidelines: 匹配的指南列表
            - literature_graph_context: 文献指南图谱上下文
            - reasoning_steps: 现有推理步骤列表
        config: 可选的配置信息，应包含 llm 用于 LLM 分析

    Returns:
        更新后的状态字典，包含：
            - reasoning_steps: 新增的推理步骤
            - literature_graph_context: 更新后的文献上下文（包含评估结果）
            - error: 错误信息（如果有）

    Example:
        >>> state = {
        ...     "patient_analysis": {"age": 65, "comorbidities": ["肾功能不全"]},
        ...     "matched_guidelines": [guideline_match],
        ...     "literature_graph_context": {},
        ...     "reasoning_steps": [],
        ... }
        >>> result = await assess_contraindications_node(state, config)
        >>> assert "reasoning_steps" in result
        >>> assert len(result["reasoning_steps"]) > 0
    """
    print("[禁忌症评估] 开始评估手术禁忌症")

    # 获取患者数据和指南
    patient_analysis = state.get("patient_analysis")
    matched_guidelines = state.get("matched_guidelines", [])
    literature_context = state.get("literature_graph_context", {})
    reasoning_steps = state.get("reasoning_steps", [])

    error = None
    assessment_result = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

            if llm and patient_analysis:
                # 构建评估提示
                prompt = _build_contraindication_assessment_prompt(
                    patient_analysis, matched_guidelines
                )

                # 使用 structured output 获取结构化结果
                structured_llm = llm.with_structured_output(
                    ContraindicationAssessmentResult
                )

                response = await structured_llm.ainvoke(
                    [
                        SystemMessage(
                            content="你是一个专业的介入手术禁忌症评估专家，"
                            "擅长识别患者是否存在手术禁忌症。"
                        ),
                        HumanMessage(content=prompt),
                    ]
                )

                assessment_result = response
                print(
                    f"[禁忌症评估] 评估完成：决策={assessment_result.decision}, "
                    f"绝对禁忌={len(assessment_result.absolute_contraindications)}, "
                    f"相对禁忌={len(assessment_result.relative_contraindications)}"
                )

            else:
                # 没有 LLM 或患者数据，使用启发式规则
                assessment_result = _heuristic_contraindication_assessment(
                    patient_analysis, matched_guidelines
                )
                print("[禁忌症评估] 使用启发式规则评估")

        else:
            # 没有 config，使用启发式规则
            assessment_result = _heuristic_contraindication_assessment(
                patient_analysis, matched_guidelines
            )
            print("[禁忌症评估] 使用启发式规则评估（未提供 config）")

        # 创建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.PRE_OP,
            description="评估手术禁忌症",
            evidence=assessment_result.guideline_sources,
            conclusion=_format_contraindication_conclusion(assessment_result),
        )

        reasoning_steps = reasoning_steps + [reasoning_step]

        # 更新文献图谱上下文
        literature_context["contraindication_assessment"] = {
            "decision": assessment_result.decision,
            "absolute_count": len(assessment_result.absolute_contraindications),
            "relative_count": len(assessment_result.relative_contraindications),
            "contraindications": {
                "absolute": assessment_result.absolute_contraindications,
                "relative": assessment_result.relative_contraindications,
            },
            "reasoning": assessment_result.reasoning,
        }

        print(f"[禁忌症评估] 推理步骤已添加（总计：{len(reasoning_steps)} 步）")

    except Exception as e:
        error = f"禁忌症评估失败: {str(e)}"
        print(f"[禁忌症评估] 错误: {error}")

        # 即使出错也记录一个推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=len(reasoning_steps) + 1,
            phase=Phase.PRE_OP,
            description="评估手术禁忌症",
            evidence=[],
            conclusion=f"评估失败：{error}",
        )
        reasoning_steps = reasoning_steps + [reasoning_step]

    return {
        "reasoning_steps": reasoning_steps,
        "literature_graph_context": literature_context,
        "error": error,
    }


def _build_contraindication_assessment_prompt(
    patient_analysis: Any, matched_guidelines: List[Any]
) -> str:
    """构建禁忌症评估提示。

    Args:
        patient_analysis: 患者数据分析结果
        matched_guidelines: 匹配的指南列表

    Returns:
        构建的提示字符串
    """
    # 提取患者信息
    if isinstance(patient_analysis, dict):
        age = patient_analysis.get("age", "未知")
        diagnosis = patient_analysis.get("diagnosis", [])
        comorbidities = patient_analysis.get("comorbidities", [])
        medications = patient_analysis.get("medications", [])
        allergies = patient_analysis.get("allergies", [])
        lab_results = patient_analysis.get("lab_results", {})
    else:
        # 假设是 Pydantic 模型
        age = getattr(patient_analysis, "age", "未知")
        diagnosis = getattr(patient_analysis, "diagnosis", [])
        comorbidities = getattr(patient_analysis, "comorbidities", [])
        medications = getattr(patient_analysis, "medications", [])
        allergies = getattr(patient_analysis, "allergies", [])
        lab_results = getattr(patient_analysis, "lab_results", {})

    # 构建指南文本
    guideline_text = ""
    if matched_guidelines:
        guideline_items = []
        for guide in matched_guidelines[:5]:  # 限制为前5个指南
            if isinstance(guide, dict):
                title = guide.get("title", "未知指南")
                contraindication = guide.get("contraindication", "")
                evidence_level = guide.get("evidence_level", "")
            else:
                title = getattr(guide, "title", "未知指南")
                contraindication = getattr(guide, "contraindication", "")
                evidence_level = getattr(guide, "evidence_level", "")

            item = f"- {title}"
            if contraindication:
                item += f"\n  禁忌症：{contraindication}"
            if evidence_level:
                item += f"\n  证据等级：{evidence_level}"

            guideline_items.append(item)

        guideline_text = "\n\n".join(guideline_items)
    else:
        guideline_text = "（未提供具体指南）"

    # 构建完整提示
    prompt = f"""请基于以下患者信息和临床指南，评估患者是否存在介入手术禁忌症。

## 患者信息
- 年龄：{age}岁
- 诊断：{", ".join(diagnosis) if diagnosis else "未指定"}
- 合并症：{", ".join(comorbidities) if comorbidities else "无"}
- 用药：{", ".join(medications) if medications else "无"}
- 过敏史：{", ".join(allergies) if allergies else "无"}
- 实验室检查：{_format_lab_results(lab_results)}

## 相关临床指南
{guideline_text}

## 评估要求
请基于以上信息，评估患者是否存在介入手术禁忌症：

1. **决策判断**：
   - proceed：无禁忌症，可按计划进行手术
   - modify：存在相对禁忌症，需修改手术方案或采取预防措施
   - abort：存在绝对禁忌症，禁止进行手术

2. **禁忌症分类**：
   - **绝对禁忌症（Class III）**：
     * 已证实风险大于收益
     * 明确禁止手术的情况
     * 如：活动性出血、严重凝血功能障碍等

   - **相对禁忌症（Class II）**：
     * 风险收益比不确定
     * 需要谨慎评估
     * 如：中度肾功能不全、对比剂过敏等

3. **来源指南**：
   - 引用具体的指南推荐
   - 说明证据等级
   - 标注禁忌症类型

4. **推理过程**：
   - 分析每个禁忌症的严重程度
   - 评估对手术的影响
   - 提供应对建议

请以结构化的方式输出评估结果。
"""

    return prompt


def _format_lab_results(lab_results: Dict[str, Any]) -> str:
    """格式化实验室检查结果。

    Args:
        lab_results: 实验室检查结果字典

    Returns:
        格式化的字符串
    """
    if not lab_results:
        return "未提供"

    formatted = []
    for key, value in lab_results.items():
        if isinstance(value, (int, float)):
            formatted.append(f"{key}：{value}")
        elif isinstance(value, str):
            formatted.append(f"{key}：{value}")
        else:
            formatted.append(f"{key}：{str(value)}")

    return ", ".join(formatted) if formatted else "未提供"


def _format_contraindication_conclusion(
    assessment_result: ContraindicationAssessmentResult,
) -> str:
    """格式化禁忌症评估结论。

    Args:
        assessment_result: 禁忌症评估结果

    Returns:
        格式化的结论字符串
    """
    parts = [
        f"决策：{assessment_result.decision}",
        f"绝对禁忌：{len(assessment_result.absolute_contraindications)} 项",
        f"相对禁忌：{len(assessment_result.relative_contraindications)} 项",
    ]

    if assessment_result.absolute_contraindications:
        parts.append(
            f"绝对禁忌：{', '.join(assessment_result.absolute_contraindications)}"
        )

    if assessment_result.relative_contraindications:
        parts.append(
            f"相对禁忌：{', '.join(assessment_result.relative_contraindications)}"
        )

    return "，".join(parts)


def _heuristic_contraindication_assessment(
    patient_analysis: Any, matched_guidelines: List[Any]
) -> ContraindicationAssessmentResult:
    """启发式禁忌症评估（备用方案）。

    当没有 LLM 时使用简单的规则进行评估。

    Args:
        patient_analysis: 患者数据分析结果
        matched_guidelines: 匹配的指南列表

    Returns:
        评估结果
    """
    # 默认结果
    decision = "proceed"
    absolute_contraindications = []
    relative_contraindications = []
    guideline_sources = []
    reasoning = "使用启发式规则评估，建议进行专业医学评估。"

    # 提取患者信息
    if isinstance(patient_analysis, dict):
        comorbidities = patient_analysis.get("comorbidities", [])
        allergies = patient_analysis.get("allergies", [])
        lab_results = patient_analysis.get("lab_results", {})
    else:
        comorbidities = getattr(patient_analysis, "comorbidities", [])
        allergies = getattr(patient_analysis, "allergies", [])
        lab_results = getattr(patient_analysis, "lab_results", {})

    # 检查常见的绝对禁忌症
    if "活动性出血" in comorbidities:
        absolute_contraindications.append("活动性出血")
        decision = "abort"

    if "严重凝血功能障碍" in comorbidities:
        absolute_contraindications.append("严重凝血功能障碍")
        decision = "abort"

    # 检查常见的相对禁忌症
    if "肾功能不全" in comorbidities or "肾衰竭" in comorbidities:
        relative_contraindications.append("肾功能不全（需水化治疗）")
        if decision == "proceed":
            decision = "modify"

    if "对比剂过敏" in allergies:
        relative_contraindications.append("对比剂过敏（需预处理）")
        if decision == "proceed":
            decision = "modify"

    if "糖尿病" in comorbidities:
        relative_contraindications.append("糖尿病（感染风险增加）")
        if decision == "proceed":
            decision = "modify"

    # 检查实验室指标
    if lab_results:
        # 假设有肌酐清除率等指标
        if "肌酐清除率" in lab_results:
            creatinine_clearance = lab_results["肌酐清除率"]
            if (
                isinstance(creatinine_clearance, (int, float))
                and creatinine_clearance < 30
            ):
                relative_contraindications.append(
                    "严重肾功能不全（肌酐清除率<30ml/min）"
                )
                if decision == "proceed":
                    decision = "modify"

    # 构建推理说明
    if absolute_contraindications:
        reasoning = f"患者存在绝对禁忌症：{', '.join(absolute_contraindications)}，禁止进行手术。"
    elif relative_contraindications:
        reasoning = f"患者存在相对禁忌症：{', '.join(relative_contraindications)}，需要修改手术方案或采取预防措施。"
    else:
        reasoning = "未发现明显禁忌症，可按计划进行手术。"

    # 添加指南来源
    if matched_guidelines:
        guideline_sources.append(f"参考了 {len(matched_guidelines)} 条临床指南")

    return ContraindicationAssessmentResult(
        decision=decision,
        absolute_contraindications=absolute_contraindications,
        relative_contraindications=relative_contraindications,
        guideline_sources=guideline_sources,
        reasoning=reasoning,
    )


# ==================== 风险评估和术式匹配输出模型 ====================


class RiskAssessmentOutput(BaseModel):
    """风险评估输出模型。

    用于 LLM 结构化输出的风险评估结果。

    Attributes:
        overall_risk_level: 整体风险等级
        primary_risk_factors: 主要风险因素列表
        risk_mitigation_strategies: 风险缓解策略列表
        confidence: 评估置信度
        reasoning: 评估推理说明
    """

    overall_risk_level: Severity = Field(..., description="整体风险等级")
    primary_risk_factors: List[RiskFactorModel] = Field(
        default_factory=list, description="主要风险因素列表"
    )
    risk_mitigation_strategies: List[str] = Field(
        default_factory=list, description="风险缓解策略列表"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="评估置信度")
    reasoning: str = Field(..., description="评估推理说明")


class ProcedureMatchOutput(BaseModel):
    """术式匹配输出模型。

    用于 LLM 结构化输出的术式匹配结果。

    Attributes:
        primary_procedure: 首选手术方案
        alternative_procedures: 备选手术方案列表
        required_devices: 所需器械列表
        contraindicated_devices: 禁忌器械列表
        key_decision_points: 关键决策点列表
        traversal_path: 图谱遍历路径
        confidence: 匹配置信度
    """

    primary_procedure: ProcedurePlanModel = Field(..., description="首选手术方案")
    alternative_procedures: List[ProcedurePlanModel] = Field(
        default_factory=list, description="备选手术方案列表"
    )
    required_devices: List[DeviceSelectionModel] = Field(
        default_factory=list, description="所需器械列表"
    )
    contraindicated_devices: List[str] = Field(
        default_factory=list, description="禁忌器械列表"
    )
    key_decision_points: List[str] = Field(
        default_factory=list, description="关键决策点列表"
    )
    traversal_path: List[str] = Field(default_factory=list, description="图谱遍历路径")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="匹配置信度")


# ==================== 风险评估节点 ====================


async def assess_risks_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """评估风险节点。

    使用已检索的风险因素数据进行 LLM 驱动的风险评估。
    分析患者风险因素、评估风险等级、识别主要风险因素并提出缓解措施。

    该节点：
    1. 使用已检索的风险因素数据（不重复检索）
    2. LLM 驱动分析风险等级（低/中/高/极高）
    3. 识别主要风险因素（高龄、活动性斑块、凝血功能等）
    4. 提出风险缓解措施（术前优化、药物调整）
    5. 输出结构化风险评估到 risk_assessment
    6. 记录来源图谱和置信度

    Args:
        state: 扩展的介入手术智能体状态
        config: 可选的配置信息，应包含 llm

    Returns:
        更新后的状态字典，包含 risk_assessment 和 reasoning_steps

    Raises:
        ValueError: 如果缺少必要的状态数据
    """
    logger.info("[评估风险] 开始风险评估")

    # 获取已检索的数据
    retrieved_entities: List[Union[RetrievedEntity, Dict]] = state.get(
        "retrieved_entities", []
    )
    retrieved_relationships: List[Union[RetrievedRelationship, Dict]] = state.get(
        "retrieved_relationships", []
    )
    matched_guidelines: List[Union[GuidelineMatch, Dict]] = state.get(
        "matched_guidelines", []
    )
    patient_analysis: Optional[Union[PatientDataModel, Dict]] = state.get(
        "patient_analysis"
    )

    # 检查必要数据
    if not retrieved_entities and not retrieved_relationships:
        logger.warning("[评估风险] 缺少检索数据，无法进行风险评估")
        return {
            "risk_assessment": [],
            "reasoning_steps": [],
            "error": "缺少检索数据，无法进行风险评估",
        }

    try:
        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if not llm:
            logger.warning("[评估风险] 未配置 LLM，使用规则基础评估")
            risk_assessment = _rule_based_risk_assessment(
                retrieved_entities, retrieved_relationships
            )
            return {
                "risk_assessment": [r.model_dump() for r in risk_assessment],
                "reasoning_steps": [],
            }

        # 提取风险因素相关信息
        risk_context = _extract_risk_context(
            retrieved_entities,
            retrieved_relationships,
            matched_guidelines,
            patient_analysis,
        )

        # 构建 LLM 提示
        prompt = _build_risk_assessment_prompt(risk_context)

        # 使用结构化输出调用 LLM
        structured_llm = llm.with_structured_output(RiskAssessmentOutput)
        response: RiskAssessmentOutput = await structured_llm.ainvoke(
            [
                SystemMessage(
                    content="你是一个专业的介入手术风险评估专家，擅长基于患者临床数据和指南推荐进行全面的手术风险评估。"
                ),
                HumanMessage(content=prompt),
            ]
        )

        logger.info(
            f"[评估风险] 风险等级: {response.overall_risk_level}, "
            f"风险因素数: {len(response.primary_risk_factors)}, "
            f"置信度: {response.confidence:.2f}"
        )

        # 构建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=1,
            phase=Phase.PRE_OP,
            description="风险评估分析",
            evidence=[r.factor for r in response.primary_risk_factors],
            conclusion=response.reasoning,
        )

        # 转换为字典格式
        risk_assessment_dicts = [r.model_dump() for r in response.primary_risk_factors]

        return {
            "risk_assessment": risk_assessment_dicts,
            "reasoning_steps": [reasoning_step.model_dump()],
        }

    except Exception as e:
        logger.error(f"[评估风险] 风险评估失败: {str(e)}")
        return {
            "risk_assessment": [],
            "reasoning_steps": [],
            "error": f"风险评估失败: {str(e)}",
        }


def _extract_risk_context(
    retrieved_entities: List[Union[RetrievedEntity, Dict]],
    retrieved_relationships: List[Union[RetrievedRelationship, Dict]],
    matched_guidelines: List[Union[GuidelineMatch, Dict]],
    patient_analysis: Optional[Union[PatientDataModel, Dict]],
) -> Dict[str, Any]:
    """提取风险相关上下文。

    Args:
        retrieved_entities: 检索到的实体列表
        retrieved_relationships: 检索到的关系列表
        matched_guidelines: 匹配的指南列表
        patient_analysis: 患者数据分析结果

    Returns:
        风险上下文字典
    """
    context = {
        "risk_factors": [],
        "contraindications": [],
        "guideline_warnings": [],
        "patient_info": {},
    }

    # 提取风险因素实体
    for entity in retrieved_entities:
        if isinstance(entity, dict):
            entity_type = entity.get("entity_type", "")
            if "risk" in entity_type.lower() or "factor" in entity_type.lower():
                context["risk_factors"].append(entity)
        elif isinstance(entity, RetrievedEntity):
            if (
                "risk" in entity.entity_type.lower()
                or "factor" in entity.entity_type.lower()
            ):
                context["risk_factors"].append(entity.model_dump())

    # 提取禁忌关系
    for rel in retrieved_relationships:
        if isinstance(rel, dict):
            rel_type = rel.get("relationship_type", "")
            if rel_type == "CONTRAINDICATES":
                context["contraindications"].append(rel)
        elif isinstance(rel, RetrievedRelationship):
            if rel.relationship_type == RelationType.CONTRAINDICATES:
                context["contraindications"].append(rel.model_dump())

    # 提取指南警告
    for guideline in matched_guidelines:
        if isinstance(guideline, dict):
            contraindication = guideline.get("contraindication")
            if contraindication:
                context["guideline_warnings"].append(contraindication)
        elif isinstance(guideline, GuidelineMatch):
            if guideline.contraindication:
                context["guideline_warnings"].append(guideline.contraindication)

    # 提取患者信息
    if patient_analysis:
        if isinstance(patient_analysis, dict):
            context["patient_info"] = {
                "age": patient_analysis.get("age"),
                "comorbidities": patient_analysis.get("comorbidities", []),
                "medications": patient_analysis.get("medications", []),
            }
        elif isinstance(patient_analysis, PatientDataModel):
            context["patient_info"] = {
                "age": patient_analysis.age,
                "comorbidities": patient_analysis.comorbidities,
                "medications": patient_analysis.medications,
            }

    return context


def _build_risk_assessment_prompt(risk_context: Dict[str, Any]) -> str:
    """构建风险评估提示。

    Args:
        risk_context: 风险上下文字典

    Returns:
        LLM 提示字符串
    """
    prompt_parts = [
        "请基于以下检索到的临床数据和指南信息，进行介入手术风险评估：\n",
    ]

    # 添加风险因素
    if risk_context["risk_factors"]:
        prompt_parts.append("## 检索到的风险因素\n")
        for i, factor in enumerate(risk_context["risk_factors"][:5], 1):
            if isinstance(factor, dict):
                name = factor.get("name", "未知")
                desc = factor.get("description", "")
                prompt_parts.append(f"{i}. {name}: {desc}\n")

    # 添加禁忌信息
    if risk_context["contraindications"]:
        prompt_parts.append("\n## 检索到的禁忌关系\n")
        for i, contr in enumerate(risk_context["contraindications"][:3], 1):
            if isinstance(contr, dict):
                desc = contr.get("description", "未知禁忌")
                prompt_parts.append(f"{i}. {desc}\n")

    # 添加指南警告
    if risk_context["guideline_warnings"]:
        prompt_parts.append("\n## 指南警告\n")
        for i, warning in enumerate(risk_context["guideline_warnings"][:3], 1):
            prompt_parts.append(f"{i}. {warning}\n")

    # 添加患者信息
    if risk_context["patient_info"]:
        patient_info = risk_context["patient_info"]
        prompt_parts.append("\n## 患者基本信息\n")
        if patient_info.get("age"):
            prompt_parts.append(f"年龄: {patient_info['age']}岁\n")
        if patient_info.get("comorbidities"):
            prompt_parts.append(f"合并症: {', '.join(patient_info['comorbidities'])}\n")
        if patient_info.get("medications"):
            prompt_parts.append(
                f"当前用药: {', '.join(patient_info['medications'][:5])}\n"
            )

    # 添加评估要求
    prompt_parts.append(
        "\n## 评估要求\n"
        "请提供:\n"
        "1. 整体风险等级（低危/中危/高危/极高危）\n"
        "2. 主要风险因素列表（每个包括风险名称、类别、严重程度、缓解策略）\n"
        "3. 风险缓解策略列表\n"
        "4. 评估置信度（0-1）\n"
        "5. 评估推理说明\n"
    )

    return "".join(prompt_parts)


def _rule_based_risk_assessment(
    retrieved_entities: List[Union[RetrievedEntity, Dict]],
    retrieved_relationships: List[Union[RetrievedRelationship, Dict]],
) -> List[RiskFactorModel]:
    """基于规则的风险评估（备用方案）。

    Args:
        retrieved_entities: 检索到的实体列表
        retrieved_relationships: 检索到的关系列表

    Returns:
        风险因素模型列表
    """
    risks = []

    # 简单规则：提取风险因素实体
    for entity in retrieved_entities:
        if isinstance(entity, dict):
            entity_type = entity.get("entity_type", "")
            if "risk" in entity_type.lower():
                risks.append(
                    RiskFactorModel(
                        factor=entity.get("name", "未知风险"),
                        category=entity.get("entity_type", "未知类别"),
                        impact=Severity.MEDIUM,
                        mitigation_strategy="请参考临床指南",
                    )
                )

    return risks


# ==================== 术式匹配节点 ====================


async def match_procedure_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """术式匹配节点。

    使用图谱遍历和 LLM 推理匹配最佳手术方案。
    沿关系链推理首选方案、识别关键分支点、考虑器械禁忌关系。

    该节点：
    1. 图谱遍历逻辑（沿关系链推理）：
       - (:Guideline)-[:BASED_ON_GUIDELINE]->(:Procedure) 首选术式
       - (:Procedure)-[:HAS_STEP]->(:IntraoperativeEvent) 所需步骤
       - (:Event)-[:USES_DEVICE]->(:Device) 所需器械
       - (:Device)-[:CONTRAINDICATES]->(:RiskFactor) 器械禁忌
       - (:Procedure)-[:REQUIRES_RESCUE]->(:Procedure) 备选方案
    2. LLM + Graph Traversal 结合：
       - 根据检索到的关系链推理首选方案
       - 识别关键分支点（如 EPD 部署失败时的备选）
       - 考虑器械禁忌关系
    3. 输出到状态 procedure_plan（含首选方案和备选方案）
    4. 记录遍历路径和推理依据

    Args:
        state: 扩展的介入手术智能体状态
        config: 可选的配置信息，应包含 llm

    Returns:
        更新后的状态字典，包含 procedure_plan 和 reasoning_steps

    Raises:
        ValueError: 如果缺少必要的状态数据
    """
    logger.info("[术式匹配] 开始术式匹配")

    # 获取已检索的数据
    retrieved_entities: List[Union[RetrievedEntity, Dict]] = state.get(
        "retrieved_entities", []
    )
    retrieved_relationships: List[Union[RetrievedRelationship, Dict]] = state.get(
        "retrieved_relationships", []
    )
    matched_guidelines: List[Union[GuidelineMatch, Dict]] = state.get(
        "matched_guidelines", []
    )
    risk_assessment: List[Union[RiskFactorModel, Dict]] = state.get(
        "risk_assessment", []
    )

    # 检查必要数据
    if not retrieved_relationships:
        logger.warning("[术式匹配] 缺少关系数据，无法进行术式匹配")
        return {
            "procedure_plan": {},
            "reasoning_steps": [],
            "error": "缺少关系数据，无法进行术式匹配",
        }

    try:
        # 执行图谱遍历
        traversal_result = _traverse_procedure_graph(
            retrieved_entities, retrieved_relationships, matched_guidelines
        )

        # 从 config 中获取 LLM
        llm: Optional[BaseChatModel] = None
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")

        if not llm:
            logger.warning("[术式匹配] 未配置 LLM，使用图谱遍历结果")
            procedure_plan = {
                "primary_procedure": traversal_result.get("primary_procedure", {}),
                "traversal_path": traversal_result.get("traversal_path", []),
                "confidence": 0.7,
            }
            return {
                "procedure_plan": procedure_plan,
                "reasoning_steps": [],
            }

        # 提取风险上下文
        risk_context = _extract_risk_factors_for_procedure(risk_assessment)

        # 构建 LLM 提示
        prompt = _build_procedure_match_prompt(traversal_result, risk_context)

        # 使用结构化输出调用 LLM
        structured_llm = llm.with_structured_output(ProcedureMatchOutput)
        response: ProcedureMatchOutput = await structured_llm.ainvoke(
            [
                SystemMessage(
                    content="你是一个专业的介入手术方案制定专家，擅长基于临床指南、患者风险因素和图谱关系链推理最佳手术方案。"
                ),
                HumanMessage(content=prompt),
            ]
        )

        logger.info(
            f"[术式匹配] 首选方案: {response.primary_procedure.procedure_type}, "
            f"备选方案数: {len(response.alternative_procedures)}, "
            f"置信度: {response.confidence:.2f}"
        )

        # 构建推理步骤
        reasoning_step = ReasoningStepModel(
            step_number=2,
            phase=Phase.PRE_OP,
            description="术式匹配分析",
            evidence=response.traversal_path,
            conclusion=f"选择 {response.primary_procedure.procedure_type} 作为首选方案",
        )

        # 转换为字典格式
        procedure_plan_dict = {
            "primary_procedure": response.primary_procedure.model_dump(),
            "alternative_procedures": [
                p.model_dump() for p in response.alternative_procedures
            ],
            "required_devices": [d.model_dump() for d in response.required_devices],
            "contraindicated_devices": response.contraindicated_devices,
            "key_decision_points": response.key_decision_points,
            "traversal_path": response.traversal_path,
            "confidence": response.confidence,
        }

        return {
            "procedure_plan": procedure_plan_dict,
            "reasoning_steps": [reasoning_step.model_dump()],
        }

    except Exception as e:
        logger.error(f"[术式匹配] 术式匹配失败: {str(e)}")
        return {
            "procedure_plan": {},
            "reasoning_steps": [],
            "error": f"术式匹配失败: {str(e)}",
        }


def _traverse_procedure_graph(
    retrieved_entities: List[Union[RetrievedEntity, Dict]],
    retrieved_relationships: List[Union[RetrievedRelationship, Dict]],
    matched_guidelines: List[Union[GuidelineMatch, Dict]],
) -> Dict[str, Any]:
    """遍历手术图谱。

    沿关系链推理：
    1. Guideline -> Procedure (BASED_ON_GUIDELINE)
    2. Procedure -> Event (HAS_STEP)
    3. Event -> Device (USES_DEVICE)
    4. Device -> RiskFactor (CONTRAINDICATES)
    5. Procedure -> Procedure (REQUIRES_RESCUE)

    Args:
        retrieved_entities: 检索到的实体列表
        retrieved_relationships: 检索到的关系列表
        matched_guidelines: 匹配的指南列表

    Returns:
        遍历结果字典
    """
    result = {
        "primary_procedures": [],
        "procedure_steps": {},
        "required_devices": [],
        "contraindications": [],
        "rescue_procedures": [],
        "traversal_path": [],
    }

    # 构建关系索引
    relations_by_type: Dict[str, List[Dict]] = {}
    for rel in retrieved_relationships:
        if isinstance(rel, dict):
            rel_type = rel.get("relationship_type", "")
            if rel_type not in relations_by_type:
                relations_by_type[rel_type] = []
            relations_by_type[rel_type].append(rel)
        elif isinstance(rel, RetrievedRelationship):
            rel_type = rel.relationship_type.value
            if rel_type not in relations_by_type:
                relations_by_type[rel_type] = []
            relations_by_type[rel_type].append(rel.model_dump())

    # 1. Guideline -> Procedure (BASED_ON_GUIDELINE)
    guideline_relations = relations_by_type.get("BASED_ON_GUIDELINE", [])
    for rel in guideline_relations:
        target_id = rel.get("target_entity_id", "")
        result["primary_procedures"].append(target_id)
        result["traversal_path"].append(
            f"Guideline -> Procedure ({rel.get('description', '')})"
        )

    # 2. Procedure -> Event (HAS_STEP)
    step_relations = relations_by_type.get("HAS_STEP", [])
    for rel in step_relations:
        source_id = rel.get("source_entity_id", "")
        target_id = rel.get("target_entity_id", "")
        if source_id not in result["procedure_steps"]:
            result["procedure_steps"][source_id] = []
        result["procedure_steps"][source_id].append(target_id)
        result["traversal_path"].append(f"Procedure {source_id} -> Step {target_id}")

    # 3. Event -> Device (USES_DEVICE)
    device_relations = relations_by_type.get("USES_DEVICE", [])
    for rel in device_relations:
        target_id = rel.get("target_entity_id", "")
        result["required_devices"].append(target_id)
        result["traversal_path"].append(f"Event -> Device {rel.get('description', '')}")

    # 4. Device -> RiskFactor (CONTRAINDICATES)
    contraindication_relations = relations_by_type.get("CONTRAINDICATES", [])
    for rel in contraindication_relations:
        source_id = rel.get("source_entity_id", "")
        target_id = rel.get("target_entity_id", "")
        result["contraindications"].append(
            {"device": source_id, "risk_factor": target_id}
        )
        result["traversal_path"].append(
            f"Device {source_id} -> Contraindicated for {target_id}"
        )

    # 5. Procedure -> Procedure (REQUIRES_RESCUE)
    rescue_relations = relations_by_type.get("REQUIRES_RESCUE", [])
    for rel in rescue_relations:
        source_id = rel.get("source_entity_id", "")
        target_id = rel.get("target_entity_id", "")
        result["rescue_procedures"].append({"primary": source_id, "rescue": target_id})
        result["traversal_path"].append(f"Procedure {source_id} -> Rescue {target_id}")

    return result


def _extract_risk_factors_for_procedure(
    risk_assessment: List[Union[RiskFactorModel, Dict]],
) -> List[str]:
    """提取术式匹配相关的风险因素。

    Args:
        risk_assessment: 风险评估列表

    Returns:
        风险因素描述列表
    """
    risk_factors = []

    for risk in risk_assessment:
        if isinstance(risk, dict):
            factor = risk.get("factor", "")
            category = risk.get("category", "")
            if factor:
                risk_factors.append(f"{category}: {factor}")
        elif isinstance(risk, RiskFactorModel):
            risk_factors.append(f"{risk.category}: {risk.factor}")

    return risk_factors


def _build_procedure_match_prompt(
    traversal_result: Dict[str, Any], risk_context: List[str]
) -> str:
    """构建术式匹配提示。

    Args:
        traversal_result: 图谱遍历结果
        risk_context: 风险上下文列表

    Returns:
        LLM 提示字符串
    """
    prompt_parts = [
        "请基于以下图谱遍历结果和患者风险因素，推荐最佳介入手术方案：\n",
    ]

    # 添加首选术式
    if traversal_result["primary_procedures"]:
        prompt_parts.append("## 推荐的首选术式\n")
        for i, proc in enumerate(traversal_result["primary_procedures"], 1):
            prompt_parts.append(f"{i}. {proc}\n")

    # 添加手术步骤
    if traversal_result["procedure_steps"]:
        prompt_parts.append("\n## 手术步骤\n")
        for proc, steps in traversal_result["procedure_steps"].items():
            prompt_parts.append(f"{proc}:\n")
            for step in steps:
                prompt_parts.append(f"  - {step}\n")

    # 添加所需器械
    if traversal_result["required_devices"]:
        prompt_parts.append("\n## 所需器械\n")
        for device in traversal_result["required_devices"][:5]:
            prompt_parts.append(f"- {device}\n")

    # 添加禁忌信息
    if traversal_result["contraindications"]:
        prompt_parts.append("\n## 器械禁忌\n")
        for contr in traversal_result["contraindications"]:
            device = contr.get("device", "未知")
            risk = contr.get("risk_factor", "未知")
            prompt_parts.append(f"- {device} 禁忌于 {risk}\n")

    # 添加备选方案
    if traversal_result["rescue_procedures"]:
        prompt_parts.append("\n## 备选方案\n")
        for rescue in traversal_result["rescue_procedures"]:
            primary = rescue.get("primary", "未知")
            rescue_proc = rescue.get("rescue", "未知")
            prompt_parts.append(f"- {primary} 的备选: {rescue_proc}\n")

    # 添加风险因素
    if risk_context:
        prompt_parts.append("\n## 患者风险因素\n")
        for risk in risk_context[:5]:
            prompt_parts.append(f"- {risk}\n")

    # 添加遍历路径
    if traversal_result["traversal_path"]:
        prompt_parts.append("\n## 图谱遍历路径\n")
        for path in traversal_result["traversal_path"][:10]:
            prompt_parts.append(f"- {path}\n")

    # 添加匹配要求
    prompt_parts.append(
        "\n## 匹配要求\n"
        "请提供:\n"
        "1. 首选手术方案（包括手术类型、入路方式、步骤、预估时长、成功概率）\n"
        "2. 备选手术方案列表\n"
        "3. 所需器械列表（包括类型、名称、规格、选择理由）\n"
        "4. 禁忌器械列表\n"
        "5. 关键决策点列表（如 EPD 部署失败时的备选）\n"
        "6. 图谱遍历路径\n"
        "7. 匹配置信度（0-1）\n"
    )

    return "".join(prompt_parts)


# ==================== 方案综合节点 ====================


async def generate_plan_node(
    state: ExtendedInterventionalState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """生成手术方案节点。

    整合所有检索和分析结果，使用 LLM 综合生成完整的手术方案。

    该节点不执行额外的检索，而是利用状态中已有的：
    - GraphRAG 检索结果（实体、关系、指南匹配）
    - 三层图谱上下文
    - LLM 分析结果（患者分析、器械推荐、风险评估等）

    Args:
        state: 扩展的介入手术智能体状态
        config: 可选的配置信息，应包含 llm

    Returns:
        更新后的状态字典，包含：
        - recommendations: 结构化推荐方案（JSON 字符串）
        - confidence_score: 综合置信度分数（0-1）
        - reasoning_steps: 推理步骤列表（追加到现有列表）
    """
    print("[方案综合] 开始综合生成手术方案")

    # 从状态中提取所有相关信息
    patient_analysis = state.get("patient_analysis")
    device_recommendations = state.get("device_recommendations", [])
    risk_assessment = state.get("risk_assessment", [])
    retrieved_entities = state.get("retrieved_entities", [])
    retrieved_relationships = state.get("retrieved_relationships", [])
    matched_guidelines = state.get("matched_guidelines", [])
    patient_graph_context = state.get("patient_graph_context", {})
    literature_graph_context = state.get("literature_graph_context", {})
    dictionary_graph_context = state.get("dictionary_graph_context", {})

    recommendations = ""
    confidence_score = 0.0
    reasoning_steps: List[Dict[str, Any]] = []
    error = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                # 构建综合提示
                prompt = _build_synthesis_prompt(
                    patient_analysis=patient_analysis,
                    device_recommendations=device_recommendations,
                    risk_assessment=risk_assessment,
                    matched_guidelines=matched_guidelines,
                    retrieved_entities=retrieved_entities,
                    retrieved_relationships=retrieved_relationships,
                    patient_graph_context=patient_graph_context,
                    literature_graph_context=literature_graph_context,
                    dictionary_graph_context=dictionary_graph_context,
                )

                # 使用结构化输出确保格式正确
                structured_llm = llm.with_structured_output(_PlanRecommendation)

                response = await structured_llm.ainvoke(
                    [
                        SystemMessage(
                            content="你是一个专业的介入手术方案制定专家，擅长整合多源信息制定个性化手术方案。"
                        ),
                        HumanMessage(content=prompt),
                    ]
                )

                # 将 Pydantic 模型转换为字典
                recommendations_dict = response.model_dump()
                recommendations = json.dumps(
                    recommendations_dict, ensure_ascii=False, indent=2
                )

                # 计算综合置信度分数
                confidence_score = _calculate_confidence_score(
                    guideline_count=len(matched_guidelines),
                    entity_count=len(retrieved_entities),
                    relationship_count=len(retrieved_relationships),
                    device_count=len(device_recommendations),
                    risk_count=len(risk_assessment),
                    plan_quality=recommendations_dict,
                )

                # 生成推理步骤
                reasoning_steps = _generate_reasoning_steps(
                    recommendations_dict, matched_guidelines, retrieved_entities
                )

                print(f"[方案综合] 已生成方案，置信度: {confidence_score:.2f}")
                print(f"[方案综合] 推理步骤数: {len(reasoning_steps)}")

            else:
                print("[方案综合] 警告: 未配置 LLM")
                error = "未配置 LLM，无法生成综合方案"
        else:
            print("[方案综合] 警告: 未提供 config")
            error = "未提供 config，无法生成综合方案"

    except Exception as e:
        error = f"方案综合失败: {str(e)}"
        print(f"[方案综合] 错误: {error}")

    # 将推理步骤添加到现有列表（如果存在）
    existing_reasoning = state.get("reasoning_steps", [])
    all_reasoning_steps = existing_reasoning + reasoning_steps

    return {
        "recommendations": recommendations,
        "confidence_score": confidence_score,
        "reasoning_steps": all_reasoning_steps,
        "error": error,
    }


def _build_synthesis_prompt(
    patient_analysis: Optional[Any],
    device_recommendations: List[Any],
    risk_assessment: List[Any],
    matched_guidelines: List[Any],
    retrieved_entities: List[Any],
    retrieved_relationships: List[Any],
    patient_graph_context: Dict[str, Any],
    literature_graph_context: Dict[str, Any],
    dictionary_graph_context: Dict[str, Any],
) -> str:
    """构建方案综合提示词。

    Args:
        patient_analysis: 患者数据分析结果
        device_recommendations: 器械推荐列表
        risk_assessment: 风险评估列表
        matched_guidelines: 匹配的指南列表
        retrieved_entities: 检索到的实体列表
        retrieved_relationships: 检索到的关系列表
        patient_graph_context: 患者数据图谱上下文
        literature_graph_context: 文献指南图谱上下文
        dictionary_graph_context: 医学词典图谱上下文

    Returns:
        构建好的提示词字符串
    """
    # 提取患者分析信息
    patient_info = ""
    if isinstance(patient_analysis, PatientDataModel):
        patient_info = f"""
患者基本信息:
- 患者 ID: {patient_analysis.patient_id}
- 年龄: {patient_analysis.age}
- 性别: {patient_analysis.gender}
- 主诉: {patient_analysis.chief_complaint}
- 诊断: {", ".join(patient_analysis.diagnosis)}
- 合并症: {", ".join(patient_analysis.comorbidities)}
- 用药: {", ".join(patient_analysis.medications)}
"""
    elif isinstance(patient_analysis, dict):
        patient_info = f"""
患者基本信息:
{json.dumps(patient_analysis, ensure_ascii=False, indent=2)}
"""

    # 提取器械推荐信息
    device_info = ""
    if device_recommendations:
        device_list = []
        for device in device_recommendations[:5]:  # 限制数量
            if isinstance(device, DeviceSelectionModel):
                device_list.append(
                    f"- {device.device_name} ({device.device_type}): {device.rationale}"
                )
            elif isinstance(device, dict):
                device_list.append(
                    f"- {device.get('device_name', 'N/A')} ({device.get('device_type', 'N/A')}): {device.get('rationale', 'N/A')}"
                )
        device_info = "\n推荐器械:\n" + "\n".join(device_list)

    # 提取风险评估信息
    risk_info = ""
    if risk_assessment:
        risk_list = []
        for risk in risk_assessment[:5]:  # 限制数量
            if isinstance(risk, RiskFactorModel):
                risk_list.append(
                    f"- {risk.factor} ({risk.category}): 影响={risk.impact.value}"
                )
            elif isinstance(risk, dict):
                risk_list.append(
                    f"- {risk.get('factor', 'N/A')} ({risk.get('category', 'N/A')}): 影响={risk.get('impact', 'N/A')}"
                )
        risk_info = "\n风险评估:\n" + "\n".join(risk_list)

    # 提取指南匹配信息
    guideline_info = ""
    if matched_guidelines:
        guideline_list = []
        for guideline in matched_guidelines[:3]:  # 限制数量
            if isinstance(guideline, GuidelineMatch):
                guideline_list.append(
                    f"- [{guideline.source} {guideline.year}] {guideline.title}: {guideline.recommendation} (证据等级: {guideline.evidence_level}, 匹配度: {guideline.matching_score:.2f})"
                )
            elif isinstance(guideline, dict):
                guideline_list.append(
                    f"- [{guideline.get('source', 'N/A')} {guideline.get('year', 'N/A')}] {guideline.get('title', 'N/A')}: {guideline.get('recommendation', 'N/A')}"
                )
        guideline_info = "\n匹配的临床指南:\n" + "\n".join(guideline_list)

    # 提取实体和关系信息
    entity_info = f"\n检索到的相关实体: {len(retrieved_entities)} 个"
    relationship_info = f"\n检索到的相关关系: {len(retrieved_relationships)} 个"

    # 构建完整提示
    prompt = f"""基于以下多维信息，制定完整的介入手术方案。

{patient_info}{device_info}{risk_info}{guideline_info}{entity_info}{relationship_info}

请制定包含以下内容的完整手术方案:

1. **首选方案 (Plan A)**
   - 手术类型和具体术式
   - 手术步骤（详细步骤列表）
   - 器械选择（类型、规格、数量）
   - 入路方式
   - 选择理由（基于指南、患者情况、解剖特点）

2. **备选方案 (Plan B)**
   - 应急处理方案
   - 方案转换条件和时机
   - 替代器械选项

3. **风险提示**
   - 主要风险因素（按严重程度排序）
   - 并发症预防措施
   - 风险监控要点

4. **推荐理由**
   - 引用的指南来源和证据等级
   - 基于图谱关系的支持证据
   - 个体化考虑因素

请确保方案基于循证医学证据，并充分考虑患者的具体情况。"""

    return prompt


def _calculate_confidence_score(
    guideline_count: int,
    entity_count: int,
    relationship_count: int,
    device_count: int,
    risk_count: int,
    plan_quality: Dict[str, Any],
) -> float:
    """计算综合置信度分数。

    综合考虑多个因素计算方案的置信度：
    - 指南匹配数量和相关性
    - 实体和关系数量
    - 器械推荐完整性
    - 风险评估全面性
    - 方案质量指标

    Args:
        guideline_count: 匹配的指南数量
        entity_count: 检索到的实体数量
        relationship_count: 检索到的关系数量
        device_count: 推荐的器械数量
        risk_count: 识别的风险数量
        plan_quality: 方案质量指标

    Returns:
        置信度分数（0-1）
    """
    score = 0.0

    # 1. 指南支持（最高 0.4 分）
    if guideline_count > 0:
        guideline_score = min(guideline_count * 0.1, 0.4)
        score += guideline_score

    # 2. 知识图谱支持（最高 0.2 分）
    graph_score = min((entity_count + relationship_count) * 0.01, 0.2)
    score += graph_score

    # 3. 器械推荐完整性（最高 0.15 分）
    if device_count >= 3:
        score += 0.15
    elif device_count >= 2:
        score += 0.1
    elif device_count >= 1:
        score += 0.05

    # 4. 风险评估全面性（最高 0.15 分）
    if risk_count >= 5:
        score += 0.15
    elif risk_count >= 3:
        score += 0.1
    elif risk_count >= 1:
        score += 0.05

    # 5. 方案质量指标（最高 0.1 分）
    if "primary_plan" in plan_quality:
        primary_plan = plan_quality["primary_plan"]
        if isinstance(primary_plan, dict):
            # 检查是否包含关键要素
            if primary_plan.get("procedure_type"):
                score += 0.03
            if primary_plan.get("steps") and len(primary_plan.get("steps", [])) >= 3:
                score += 0.03
            if primary_plan.get("rationale"):
                score += 0.04

    # 确保分数在 0-1 范围内
    return min(max(score, 0.0), 1.0)


def _generate_reasoning_steps(
    recommendations: Dict[str, Any],
    matched_guidelines: List[Any],
    retrieved_entities: List[Any],
) -> List[Dict[str, Any]]:
    """生成推理步骤。

    基于方案和证据生成推理链。

    Args:
        recommendations: 推荐方案字典
        matched_guidelines: 匹配的指南列表
        retrieved_entities: 检索到的实体列表

    Returns:
        推理步骤字典列表
    """
    steps = []

    # 步骤 1: 患者情况分析
    steps.append(
        {
            "step_number": 1,
            "phase": "pre_op",
            "description": "分析患者基本信息、病史、检查结果",
            "evidence": ["患者数据图谱"],
            "conclusion": "明确患者诊断和手术适应症",
        }
    )

    # 步骤 2: 指南匹配
    if matched_guidelines:
        guideline_sources = [
            f"{g.source if isinstance(g, GuidelineMatch) else g.get('source', 'N/A')} "
            f"{g.year if isinstance(g, GuidelineMatch) else g.get('year', 'N/A')}"
            for g in matched_guidelines[:3]
        ]
        steps.append(
            {
                "step_number": 2,
                "phase": "pre_op",
                "description": "匹配相关临床指南和循证医学证据",
                "evidence": guideline_sources,
                "conclusion": f"找到 {len(matched_guidelines)} 条相关指南支持",
            }
        )

    # 步骤 3: 器械选择
    if "primary_plan" in recommendations:
        primary_plan = recommendations["primary_plan"]
        if isinstance(primary_plan, dict) and "devices" in primary_plan:
            devices = primary_plan["devices"]
            if isinstance(devices, list) and devices:
                device_names = [
                    d.get("device_name", "N/A") if isinstance(d, dict) else str(d)
                    for d in devices[:3]
                ]
                steps.append(
                    {
                        "step_number": 3,
                        "phase": "intra_op",
                        "description": "根据患者解剖特点和指南推荐选择器械",
                        "evidence": ["医学词典图谱", "器械规格参数"],
                        "conclusion": f"推荐使用: {', '.join(device_names)}",
                    }
                )

    # 步骤 4: 风险评估
    if "risk_alerts" in recommendations:
        risk_alerts = recommendations["risk_alerts"]
        if isinstance(risk_alerts, list) and risk_alerts:
            steps.append(
                {
                    "step_number": 4,
                    "phase": "pre_op",
                    "description": "识别和评估手术相关风险",
                    "evidence": ["患者合并症", "文献指南风险提示"],
                    "conclusion": f"识别到 {len(risk_alerts)} 个主要风险因素",
                }
            )

    # 步骤 5: 方案制定
    steps.append(
        {
            "step_number": 5,
            "phase": "pre_op",
            "description": "综合以上信息制定个性化手术方案",
            "evidence": ["指南推荐", "患者特点", "器械可用性"],
            "conclusion": "制定首选方案和备选方案",
        }
    )

    return steps


# ==================== 条件路由函数 ====================


def route_indications(state: ExtendedInterventionalState) -> Literal["continue", "end"]:
    """适应症路由函数。

    根据适应症分析结果决定是否继续手术流程。

    路由逻辑:
    - 如果有明确的适应症支持 → "continue"
    - 如果缺乏适应症或证据不足 → "end"

    Args:
        state: 扩展的介入手术智能体状态

    Returns:
        路由决策: "continue" 或 "end"
    """
    print("[适应症路由] 评估手术适应症")

    # 检查是否有匹配的指南
    matched_guidelines = state.get("matched_guidelines", [])

    # 检查患者分析结果
    patient_analysis = state.get("patient_analysis")

    # 决策逻辑
    has_indication = False

    # 1. 检查指南支持
    for guideline in matched_guidelines:
        if isinstance(guideline, GuidelineMatch):
            if guideline.indication and guideline.matching_score > 0.5:
                has_indication = True
                break
        elif isinstance(guideline, dict):
            indication = guideline.get("indication")
            matching_score = guideline.get("matching_score", 0.0)
            if indication and matching_score > 0.5:
                has_indication = True
                break

    # 2. 检查患者诊断
    if not has_indication and patient_analysis:
        if isinstance(patient_analysis, PatientDataModel):
            if patient_analysis.diagnosis:
                has_indication = True
        elif isinstance(patient_analysis, dict):
            diagnoses = patient_analysis.get("diagnosis", [])
            if diagnoses:
                has_indication = True

    if has_indication:
        print("[适应症路由] 存在明确适应症，继续流程")
        return "continue"
    else:
        print("[适应症路由] 缺乏明确适应症，结束流程")
        return "end"


def route_contraindications(
    state: ExtendedInterventionalState,
) -> Literal["proceed", "modify", "abort"]:
    """禁忌症路由函数。

    根据禁忌症分析结果决定如何处理手术流程。

    路由逻辑:
    - 无禁忌症或禁忌症可控 → "proceed"
    - 存在相对禁忌症可调整方案 → "modify"
    - 存在绝对禁忌症 → "abort"

    Args:
        state: 扩展的介入手术智能体状态

    Returns:
        路由决策: "proceed", "modify", 或 "abort"
    """
    print("[禁忌症路由] 评估手术禁忌症")

    # 检查匹配的指南中的禁忌症
    matched_guidelines = state.get("matched_guidelines", [])

    # 检查风险评估
    risk_assessment = state.get("risk_assessment", [])

    # 检查患者分析
    patient_analysis = state.get("patient_analysis")

    has_absolute_contraindication = False
    has_relative_contraindication = False

    # 1. 检查指南中的禁忌症
    for guideline in matched_guidelines:
        if isinstance(guideline, GuidelineMatch):
            contraindication = guideline.contraindication
            if contraindication:
                # 简单的关键词判断（实际应用中需要更复杂的NLP分析）
                absolute_keywords = ["绝对禁忌", "严禁", "禁止", "不推荐"]
                relative_keywords = ["谨慎", "慎重", "风险评估", "相对禁忌"]

                if any(keyword in contraindication for keyword in absolute_keywords):
                    has_absolute_contraindication = True
                    break
                elif any(keyword in contraindication for keyword in relative_keywords):
                    has_relative_contraindication = True
        elif isinstance(guideline, dict):
            contraindication = guideline.get("contraindication")
            if contraindication:
                absolute_keywords = ["绝对禁忌", "严禁", "禁止", "不推荐"]
                relative_keywords = ["谨慎", "慎重", "风险评估", "相对禁忌"]

                if any(keyword in contraindication for keyword in absolute_keywords):
                    has_absolute_contraindication = True
                    break
                elif any(keyword in contraindication for keyword in relative_keywords):
                    has_relative_contraindication = True

    # 2. 检查患者合并症和过敏史
    if patient_analysis:
        if isinstance(patient_analysis, PatientDataModel):
            # 检查过敏史
            if patient_analysis.allergies:
                # 严重的过敏可能构成禁忌症
                severe_allergies = [
                    allergy
                    for allergy in patient_analysis.allergies
                    if "严重" in allergy or "休克" in allergy
                ]
                if severe_allergies:
                    has_relative_contraindication = True
        elif isinstance(patient_analysis, dict):
            allergies = patient_analysis.get("allergies", [])
            if allergies:
                severe_allergies = [
                    allergy
                    for allergy in allergies
                    if "严重" in allergy or "休克" in allergy
                ]
                if severe_allergies:
                    has_relative_contraindication = True

    # 3. 检查高危风险因素
    for risk in risk_assessment:
        if isinstance(risk, RiskFactorModel):
            if risk.impact.value in ["high", "critical"]:
                # 高危风险可能需要修改方案
                has_relative_contraindication = True
                break
        elif isinstance(risk, dict):
            impact = risk.get("impact", "")
            if impact in ["high", "critical"]:
                has_relative_contraindication = True
                break

    # 路由决策
    if has_absolute_contraindication:
        print("[禁忌症路由] 发现绝对禁忌症，终止流程")
        return "abort"
    elif has_relative_contraindication:
        print("[禁忌症路由] 发现相对禁忌症或高危因素，需调整方案")
        return "modify"
    else:
        print("[禁忌症路由] 无禁忌症，按原计划进行")
        return "proceed"


def route_should_abort(state: ExtendedInterventionalState) -> bool:
    """终止条件判断函数。

    判断是否应该终止整个工作流。

    终止条件:
    - 发生严重错误
    - 缺乏必要的患者数据
    - 置信度过低
    - 用户明确要求终止

    Args:
        state: 扩展的介入手术智能体状态

    Returns:
        True 表示应该终止，False 表示可以继续
    """
    print("[终止判断] 评估是否需要终止工作流")

    # 1. 检查是否有严重错误
    error = state.get("error")
    if error:
        # 判断错误严重程度
        severe_error_keywords = ["致命", "严重", "失败", "异常", "中断"]
        if any(keyword in error for keyword in severe_error_keywords):
            print(f"[终止判断] 发现严重错误: {error}")
            return True

    # 2. 检查患者数据是否充足
    patient_analysis = state.get("patient_analysis")
    if not patient_analysis:
        print("[终止判断] 缺乏患者数据，无法继续")
        return True

    # 3. 检查置信度
    confidence_score = state.get("confidence_score", 0.0)
    if confidence_score < 0.3:
        print(f"[终止判断] 置信度过低 ({confidence_score:.2f})，建议终止")
        return True

    # 4. 检查是否有检索结果
    retrieved_entities = state.get("retrieved_entities", [])
    matched_guidelines = state.get("matched_guidelines", [])

    if not retrieved_entities and not matched_guidelines:
        print("[终止判断] 无任何检索结果，无法生成可靠方案")
        return True

    print("[终止判断] 满足继续条件，工作流可以继续")
    return False


# ==================== 辅助数据模型 ====================


class _PrimaryPlan(BaseModel):
    """首选方案模型（内部使用）。"""

    procedure_type: str = Field(..., description="手术类型")
    approach: str = Field(..., description="入路方式")
    steps: List[str] = Field(..., description="手术步骤")
    devices: List[Dict[str, str]] = Field(..., description="所需器械")
    rationale: str = Field(..., description="选择理由")


class _AlternativePlan(BaseModel):
    """备选方案模型（内部使用）。"""

    name: str = Field(..., description="备选方案名称")
    scenario: str = Field(..., description="适用场景")
    conversion_condition: str = Field(..., description="转换条件")
    modifications: List[str] = Field(..., description="调整内容")


class _RiskAlert(BaseModel):
    """风险提示模型（内部使用）。"""

    risk_factor: str = Field(..., description="风险因素")
    severity: str = Field(..., description="严重程度")
    prevention: str = Field(..., description="预防措施")


class _RecommendationRationale(BaseModel):
    """推荐理由模型（内部使用）。"""

    guideline_sources: List[str] = Field(..., description="指南来源")
    evidence_level: str = Field(..., description="证据等级")
    graph_evidence: List[str] = Field(..., description="图谱证据")
    individual_considerations: List[str] = Field(..., description="个体化考虑")


class _PlanRecommendation(BaseModel):
    """方案推荐模型（内部使用）。

    用于 LLM 结构化输出，确保生成的方案符合预期格式。
    """

    primary_plan: _PrimaryPlan = Field(..., description="首选方案")
    alternative_plan: Optional[_AlternativePlan] = Field(None, description="备选方案")
    risk_alerts: List[_RiskAlert] = Field(..., description="风险提示")
    recommendation_rationale: _RecommendationRationale = Field(
        ..., description="推荐理由"
    )
