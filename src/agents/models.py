"""
扩展数据模型模块。

该模块定义了用于介入手术智能体的扩展 Pydantic 模型和枚举类型，
包括 GraphRAG 检索结果、三层图谱上下文、LLM 分析结果等数据结构。
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ==================== 枚举类型 ====================


class GraphSource(str, Enum):
    """图谱来源枚举。

    定义知识图谱的三个来源层：
    - PATIENT_DATA: 患者数据图谱（病史、检查结果等）
    - LITERATURE: 文献指南图谱（临床指南、研究文献等）
    - DICTIONARY: 医学词典图谱（标准术语、药物信息等）
    """

    PATIENT_DATA = "patient_data"
    LITERATURE = "literature"
    DICTIONARY = "dictionary"


class ProcedureType(str, Enum):
    """手术类型枚举。

    定义常见的介入手术类型。
    """

    PCI = "PCI"  # 经皮冠状动脉介入治疗
    STENT_IMPLANTATION = "stent_implantation"  # 支架植入
    BALLOON_ANGIOPLASTY = "balloon_angioplasty"  # 球囊血管成形术
    THROMBECTOMY = "thrombectomy"  # 血栓切除术
    ATHERECTOMY = "atherectomy"  # 动脉切除术
    OTHER = "other"


class Severity(str, Enum):
    """严重程度枚举。

    定义风险或病症的严重程度级别。
    """

    LOW = "low"  # 低危
    MEDIUM = "medium"  # 中危
    HIGH = "high"  # 高危
    CRITICAL = "critical"  # 危急


class Phase(str, Enum):
    """手术阶段枚举。

    定义介入手术的三个阶段。
    """

    PRE_OP = "pre_op"  # 术前
    INTRA_OP = "intra_op"  # 术中
    POST_OP = "post_op"  # 术后


# ==================== GraphRAG 检索结果模型 ====================


class RetrievedEntity(BaseModel):
    """检索到的实体模型。

    表示从知识图谱中检索到的实体节点，
    包含实体信息及其来源图谱。

    Attributes:
        entity_id: 实体唯一标识符
        entity_type: 实体类型（如疾病、症状、药物等）
        name: 实体名称
        description: 实体描述
        properties: 实体属性字典
        source_graph: 来源图谱类型
        confidence: 检索置信度（0-1）
    """

    entity_id: str = Field(..., description="实体唯一标识符")
    entity_type: str = Field(..., description="实体类型")
    name: str = Field(..., description="实体名称")
    description: Optional[str] = Field(None, description="实体描述")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    source_graph: GraphSource = Field(..., description="来源图谱类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="检索置信度")


class RetrievedRelationship(BaseModel):
    """检索到的关系模型。

    表示从知识图谱中检索到的实体间关系，
    包含关系信息及其来源图谱。

    Attributes:
        relationship_id: 关系唯一标识符
        source_entity_id: 源实体 ID
        target_entity_id: 目标实体 ID
        relationship_type: 关系类型
        properties: 关系属性字典
        source_graph: 来源图谱类型
        confidence: 检索置信度（0-1）
    """

    relationship_id: str = Field(..., description="关系唯一标识符")
    source_entity_id: str = Field(..., description="源实体 ID")
    target_entity_id: str = Field(..., description="目标实体 ID")
    relationship_type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    source_graph: GraphSource = Field(..., description="来源图谱类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="检索置信度")


class GuidelineMatch(BaseModel):
    """指南匹配模型。

    表示从文献指南图谱中检索到的与患者情况匹配的指南条目。

    Attributes:
        guideline_id: 指南唯一标识符
        title: 指南标题
        recommendation: 推荐内容
        evidence_level: 证据等级（如 Ia, Ib, IIa, IIb, III）
        indication: 适应症
        contraindication: 禁忌症
        matching_score: 匹配度评分（0-1）
        source: 来源（如 ESC, AHA, CN）
        year: 发布年份
    """

    guideline_id: str = Field(..., description="指南唯一标识符")
    title: str = Field(..., description="指南标题")
    recommendation: str = Field(..., description="推荐内容")
    evidence_level: Optional[str] = Field(None, description="证据等级")
    indication: Optional[str] = Field(None, description="适应症")
    contraindication: Optional[str] = Field(None, description="禁忌症")
    matching_score: float = Field(..., ge=0.0, le=1.0, description="匹配度评分")
    source: str = Field(..., description="来源")
    year: Optional[int] = Field(None, description="发布年份")


# ==================== LLM 分析结果模型 ====================


class AnatomyFindingModel(BaseModel):
    """解剖发现模型。

    表示从影像或检查中提取的解剖结构发现。

    Attributes:
        structure: 解剖结构名称
        finding: 发现描述
        severity: 严重程度
        clinical_significance: 临床意义
    """

    structure: str = Field(..., description="解剖结构名称")
    finding: str = Field(..., description="发现描述")
    severity: Severity = Field(default=Severity.MEDIUM, description="严重程度")
    clinical_significance: Optional[str] = Field(None, description="临床意义")


class PathologyFindingModel(BaseModel):
    """病理发现模型。

    表示从检查中提取的病理学发现。

    Attributes:
        pathology: 病理名称
        description: 描述
        severity: 严重程度
        urgency: 紧急程度
    """

    pathology: str = Field(..., description="病理名称")
    description: str = Field(..., description="描述")
    severity: Severity = Field(default=Severity.MEDIUM, description="严重程度")
    urgency: Optional[str] = Field(None, description="紧急程度")


class RiskFactorModel(BaseModel):
    """风险因素模型。

    表示识别的风险因素。

    Attributes:
        factor: 风险因素名称
        category: 风险类别（如出血风险、血栓风险等）
        impact: 影响程度
        mitigation_strategy: 缓解策略
    """

    factor: str = Field(..., description="风险因素名称")
    category: str = Field(..., description="风险类别")
    impact: Severity = Field(default=Severity.MEDIUM, description="影响程度")
    mitigation_strategy: Optional[str] = Field(None, description="缓解策略")


class PatientDataModel(BaseModel):
    """患者数据模型。

    表示患者的基本信息和临床数据。

    Attributes:
        patient_id: 患者唯一标识符
        age: 年龄
        gender: 性别
        chief_complaint: 主诉
        diagnosis: 诊断列表
        comorbidities: 合并症列表
        medications: 用药列表
        allergies: 过敏史
        vital_signs: 生命体征
        lab_results: 实验室检查结果
        imaging_findings: 影像学发现
        anatomy_findings: 解剖发现列表
        pathology_findings: 病理发现列表
    """

    patient_id: str = Field(..., description="患者唯一标识符")
    age: int = Field(..., ge=0, le=150, description="年龄")
    gender: str = Field(..., description="性别")
    chief_complaint: str = Field(..., description="主诉")
    diagnosis: List[str] = Field(default_factory=list, description="诊断列表")
    comorbidities: List[str] = Field(default_factory=list, description="合并症列表")
    medications: List[str] = Field(default_factory=list, description="用药列表")
    allergies: List[str] = Field(default_factory=list, description="过敏史")
    vital_signs: Dict[str, Any] = Field(default_factory=dict, description="生命体征")
    lab_results: Dict[str, Any] = Field(
        default_factory=dict, description="实验室检查结果"
    )
    imaging_findings: List[str] = Field(default_factory=list, description="影像学发现")
    anatomy_findings: List[AnatomyFindingModel] = Field(
        default_factory=list, description="解剖发现列表"
    )
    pathology_findings: List[PathologyFindingModel] = Field(
        default_factory=list, description="病理发现列表"
    )


class DeviceSelectionModel(BaseModel):
    """器械选择模型。

    表示推荐的介入手术器械选择。

    Attributes:
        device_type: 器械类型（如支架、球囊、导丝等）
        device_name: 器械名称
        manufacturer: 制造商
        size: 规格
        indication: 适应症
        contraindication: 禁忌症
        rationale: 选择理由
        alternatives: 替代方案
    """

    device_type: str = Field(..., description="器械类型")
    device_name: str = Field(..., description="器械名称")
    manufacturer: Optional[str] = Field(None, description="制造商")
    size: Optional[str] = Field(None, description="规格")
    indication: Optional[str] = Field(None, description="适应症")
    contraindication: Optional[str] = Field(None, description="禁忌症")
    rationale: str = Field(..., description="选择理由")
    alternatives: List[str] = Field(default_factory=list, description="替代方案")


class ProcedurePlanModel(BaseModel):
    """手术方案模型。

    表示推荐的介入手术方案。

    Attributes:
        procedure_type: 手术类型
        approach: 入路方式
        steps: 手术步骤列表
        devices: 所需器械列表
        duration_estimate: 预估时长
        success_probability: 成功概率
    """

    procedure_type: ProcedureType = Field(..., description="手术类型")
    approach: str = Field(..., description="入路方式")
    steps: List[str] = Field(default_factory=list, description="手术步骤列表")
    devices: List[DeviceSelectionModel] = Field(
        default_factory=list, description="所需器械列表"
    )
    duration_estimate: Optional[str] = Field(None, description="预估时长")
    success_probability: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="成功概率"
    )


class ReasoningStepModel(BaseModel):
    """推理步骤模型。

    表示 LLM 推理链中的一个步骤。

    Attributes:
        step_number: 步骤编号
        phase: 所属阶段（术前、术中、术后）
        description: 步骤描述
        evidence: 支持证据
        conclusion: 结论
    """

    step_number: int = Field(..., ge=1, description="步骤编号")
    phase: Phase = Field(..., description="所属阶段")
    description: str = Field(..., description="步骤描述")
    evidence: List[str] = Field(default_factory=list, description="支持证据")
    conclusion: Optional[str] = Field(None, description="结论")


class PostOpPlanModel(BaseModel):
    """术后计划模型。

    表示术后管理计划。

    Attributes:
        monitoring: 监测计划
        medications: 用药计划
        follow_up: 随访计划
    """

    monitoring: List[str] = Field(default_factory=list, description="监测计划")
    medications: List[str] = Field(default_factory=list, description="用药计划")
    follow_up: List[str] = Field(default_factory=list, description="随访计划")
