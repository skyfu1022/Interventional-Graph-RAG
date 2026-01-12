"""介入手术实体类型定义模块。

该模块定义了介入手术领域的所有实体类型，映射到 LightRAG 的实体类型系统。
所有实体类都继承自 Pydantic BaseModel，提供类型安全和序列化支持。

实体类型映射：
- ANATOMY: 解剖结构
- PATHOLOGY: 病理改变
- PROCEDURE: 手术操作
- DEVICE: 医疗器械
- GUIDELINE: 临床指南
- RISK_FACTOR: 风险因素
- COMPLICATION: 并发症
- CARE_PLAN: 诊疗计划
- EVENT: 术中事件
- IMAGE: 影像资料
- PATIENT: 患者数据

使用示例：
    >>> from src.graph.entities import AnatomyEntity, PathologyEntity
    >>>
    >>> # 创建解剖实体
    >>> anatomy = AnatomyEntity(
    ...     entity_name="Left ICA",
    ...     entity_type="ANATOMY",
    ...     description="左侧颈内动脉",
    ...     location="Neck",
    ...     laterality="Left"
    ... )
    >>>
    >>> # 创建病理实体
    >>> pathology = PathologyEntity(
    ...     entity_name="Severe Stenosis",
    ...     entity_type="PATHOLOGY",
    ...     description="重度狭窄",
    ...     severity="Severe",
    ...     stenosis_percentage=85
    ... )
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ========== 实体类型映射常量 ==========


class EntityType(str, Enum):
    """介入手术实体类型枚举。

    定义了介入手术领域的所有实体类型，映射到 LightRAG 的实体类型系统。
    """

    ANATOMY = "ANATOMY"  # 解剖结构
    PATHOLOGY = "PATHOLOGY"  # 病理改变
    PROCEDURE = "PROCEDURE"  # 手术操作
    DEVICE = "DEVICE"  # 医疗器械
    GUIDELINE = "GUIDELINE"  # 临床指南
    RISK_FACTOR = "RISK_FACTOR"  # 风险因素
    COMPLICATION = "COMPLICATION"  # 并发症
    CARE_PLAN = "CARE_PLAN"  # 诊疗计划
    EVENT = "EVENT"  # 术中事件
    IMAGE = "IMAGE"  # 影像资料
    PATIENT = "PATIENT"  # 患者数据


# 映射介入手术类型到 LightRAG 实体类型
ENTITY_TYPE_MAPPING: Dict[str, EntityType] = {
    # 解剖结构
    "anatomy": EntityType.ANATOMY,
    "vessel": EntityType.ANATOMY,
    "organ": EntityType.ANATOMY,
    "tissue": EntityType.ANATOMY,
    # 病理改变
    "pathology": EntityType.PATHOLOGY,
    "stenosis": EntityType.PATHOLOGY,
    "plaque": EntityType.PATHOLOGY,
    "thrombosis": EntityType.PATHOLOGY,
    # 手术操作
    "procedure": EntityType.PROCEDURE,
    "intervention": EntityType.PROCEDURE,
    "surgery": EntityType.PROCEDURE,
    # 医疗器械
    "device": EntityType.DEVICE,
    "stent": EntityType.DEVICE,
    "catheter": EntityType.DEVICE,
    "balloon": EntityType.DEVICE,
    "embolic": EntityType.DEVICE,
    # 临床指南
    "guideline": EntityType.GUIDELINE,
    "protocol": EntityType.GUIDELINE,
    "recommendation": EntityType.GUIDELINE,
    # 风险因素
    "risk_factor": EntityType.RISK_FACTOR,
    "comorbidity": EntityType.RISK_FACTOR,
    # 并发症
    "complication": EntityType.COMPLICATION,
    "adverse_event": EntityType.COMPLICATION,
    # 诊疗计划
    "care_plan": EntityType.CARE_PLAN,
    "postoperative_care": EntityType.CARE_PLAN,
    # 术中事件
    "event": EntityType.EVENT,
    "intraoperative_event": EntityType.EVENT,
    # 影像资料
    "image": EntityType.IMAGE,
    "angiography": EntityType.IMAGE,
    "ultrasound": EntityType.IMAGE,
    "ct_scan": EntityType.IMAGE,
    "mri": EntityType.IMAGE,
    # 患者数据
    "patient": EntityType.PATIENT,
    "patient_data": EntityType.PATIENT,
    "medical_history": EntityType.PATIENT,
}


# ========== 基础实体类 ==========


class BaseEntity(BaseModel):
    """基础实体类。

    所有介入手术实体的基类，提供通用属性和方法。

    Attributes:
        entity_id: 实体唯一标识符
        entity_name: 实体名称
        entity_type: 实体类型（使用 EntityType 枚举）
        description: 实体描述
        metadata: 额外的元数据字典
        sources: 数据来源列表
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    entity_id: Optional[str] = Field(None, description="实体唯一标识符")
    entity_name: str = Field(..., description="实体名称")
    entity_type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(None, description="实体描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    sources: List[str] = Field(default_factory=list, description="数据来源列表")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            包含模型所有字段的字典
        """
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            JSON 格式的字符串
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            BaseEntity 实例
        """
        return cls.model_validate(data)


# ========== 具体实体类 ==========


class AnatomyEntity(BaseEntity):
    """解剖结构实体。

    表示介入手术中涉及的解剖结构，如血管、器官、组织等。

    Attributes:
        entity_name: 解剖结构名称（如 "Left ICA", "Left Vertebral Artery"）
        entity_type: 实体类型，固定为 ANATOMY
        description: 解剖结构描述
        location: 所在位置（如 "Neck", "Brain", "Heart"）
        laterality: 侧别（Left/Right/Bilateral）
        dimensions: 尺寸信息（直径、长度等）
        variant: 解剖变异（如果有）
        metadata: 额外元数据
    """

    location: Optional[str] = Field(None, description="所在位置")
    laterality: Optional[str] = Field(None, description="侧别（Left/Right/Bilateral）")
    dimensions: Optional[Dict[str, float]] = Field(None, description="尺寸信息")
    variant: Optional[str] = Field(None, description="解剖变异")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 ANATOMY。"""
        if v != EntityType.ANATOMY:
            raise ValueError(f"AnatomyEntity 的 entity_type 必须为 ANATOMY，得到 {v}")
        return v

    @field_validator("laterality")
    @classmethod
    def validate_laterality(cls, v: Optional[str]) -> Optional[str]:
        """验证侧别字段。"""
        if v is not None and v not in ["Left", "Right", "Bilateral", None]:
            raise ValueError(f"laterality 必须为 Left/Right/Bilateral 之一，得到 {v}")
        return v


class PathologyEntity(BaseEntity):
    """病理改变实体。

    表示介入手术中涉及的病理改变，如狭窄、斑块、血栓等。

    Attributes:
        entity_name: 病理名称（如 "Severe Stenosis", "Active Plaque"）
        entity_type: 实体类型，固定为 PATHOLOGY
        description: 病理描述
        severity: 严重程度（Mild/Moderate/Severe）
        stenosis_percentage: 狭窄百分比（0-100）
        morphology: 形态学特征
        location: 所在解剖位置
        chronicity: 慢性程度（Acute/Chronic）
        metadata: 额外元数据
    """

    severity: Optional[str] = Field(None, description="严重程度")
    stenosis_percentage: Optional[float] = Field(
        None, ge=0, le=100, description="狭窄百分比"
    )
    morphology: Optional[str] = Field(None, description="形态学特征")
    location: Optional[str] = Field(None, description="所在解剖位置")
    chronicity: Optional[str] = Field(None, description="慢性程度")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 PATHOLOGY。"""
        if v != EntityType.PATHOLOGY:
            raise ValueError(
                f"PathologyEntity 的 entity_type 必须为 PATHOLOGY，得到 {v}"
            )
        return v


class ProcedureEntity(BaseEntity):
    """手术操作实体。

    表示介入手术的操作步骤和流程。

    Attributes:
        entity_name: 操作名称（如 "CAS", "Stent Deployment"）
        entity_type: 实体类型，固定为 PROCEDURE
        description: 操作描述
        procedure_category: 操作类别（Diagnostic/Therapeutic）
        indication: 适应症
        technique: 技术方法
        duration: 预计时长（分钟）
        steps: 操作步骤列表
        alternative_options: 备选方案
        metadata: 额外元数据
    """

    procedure_category: Optional[str] = Field(None, description="操作类别")
    indication: Optional[str] = Field(None, description="适应症")
    technique: Optional[str] = Field(None, description="技术方法")
    duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    steps: List[str] = Field(default_factory=list, description="操作步骤")
    alternative_options: List[str] = Field(default_factory=list, description="备选方案")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 PROCEDURE。"""
        if v != EntityType.PROCEDURE:
            raise ValueError(
                f"ProcedureEntity 的 entity_type 必须为 PROCEDURE，得到 {v}"
            )
        return v


class DeviceEntity(BaseEntity):
    """医疗器械实体。

    表示介入手术中使用的医疗器械。

    Attributes:
        entity_name: 器械名称（如 "Embolic Protection Device", "Stent"）
        entity_type: 实体类型，固定为 DEVICE
        description: 器械描述
        device_category: 器械类别（Stent/Catheter/Balloon/Embolic等）
        manufacturer: 制造商
        model: 型号
        size: 尺寸规格
        material: 材料
        fda_status: FDA 认证状态
        contraindications: 禁忌症列表
        metadata: 额外元数据
    """

    device_category: Optional[str] = Field(None, description="器械类别")
    manufacturer: Optional[str] = Field(None, description="制造商")
    model: Optional[str] = Field(None, description="型号")
    size: Optional[Dict[str, float]] = Field(None, description="尺寸规格")
    material: Optional[str] = Field(None, description="材料")
    fda_status: Optional[str] = Field(None, description="FDA 认证状态")
    contraindications: List[str] = Field(default_factory=list, description="禁忌症")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 DEVICE。"""
        if v != EntityType.DEVICE:
            raise ValueError(f"DeviceEntity 的 entity_type 必须为 DEVICE，得到 {v}")
        return v


class GuidelineEntity(BaseEntity):
    """临床指南实体。

    表示临床实践指南和专家共识。

    Attributes:
        entity_name: 指南名称（如 "ACC/AHA Guidelines for CAS"）
        entity_type: 实体类型，固定为 GUIDELINE
        description: 指南描述
        organization: 发布组织（如 "ACC/AHA", "NASCET"）
        year: 发布年份
        version: 版本
        recommendation_class: 推荐等级（Class I/IIa/IIb/III）
        evidence_level: 证据级别（Level A/B/C）
        url: 指南链接
        indications: 适应症列表
        contraindications: 禁忌症列表
        metadata: 额外元数据
    """

    organization: Optional[str] = Field(None, description="发布组织")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="发布年份")
    version: Optional[str] = Field(None, description="版本")
    recommendation_class: Optional[str] = Field(None, description="推荐等级")
    evidence_level: Optional[str] = Field(None, description="证据级别")
    url: Optional[str] = Field(None, description="指南链接")
    indications: List[str] = Field(default_factory=list, description="适应症")
    contraindications: List[str] = Field(default_factory=list, description="禁忌症")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 GUIDELINE。"""
        if v != EntityType.GUIDELINE:
            raise ValueError(
                f"GuidelineEntity 的 entity_type 必须为 GUIDELINE，得到 {v}"
            )
        return v


class RiskFactorEntity(BaseEntity):
    """风险因素实体。

    表示影响手术决策和预后的风险因素。

    Attributes:
        entity_name: 风险因素名称（如 "Age > 70", "Hypertension"）
        entity_type: 实体类型，固定为 RISK_FACTOR
        description: 风险因素描述
        category: 风险类别（Patient/Procedure/Anatomy）
        severity: 严重程度（Low/Medium/High）
        modifiable: 是否可修改
        impact: 对预后的影响
        mitigation_strategy: 缓解策略
        metadata: 额外元数据
    """

    category: Optional[str] = Field(None, description="风险类别")
    severity: Optional[str] = Field(None, description="严重程度")
    modifiable: Optional[bool] = Field(None, description="是否可修改")
    impact: Optional[str] = Field(None, description="对预后的影响")
    mitigation_strategy: Optional[str] = Field(None, description="缓解策略")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 RISK_FACTOR。"""
        if v != EntityType.RISK_FACTOR:
            raise ValueError(
                f"RiskFactorEntity 的 entity_type 必须为 RISK_FACTOR，得到 {v}"
            )
        return v


class ComplicationEntity(BaseEntity):
    """并发症实体。

    表示介入手术可能发生的并发症。

    Attributes:
        entity_name: 并发症名称（如 "Stroke", "Hemorrhage"）
        entity_type: 实体类型，固定为 COMPLICATION
        description: 并发症描述
        severity: 严重程度（Mild/Moderate/Severe/Life-threatening）
        incidence: 发生率
        onset_time: 发生时间（Intraoperative/Postoperative）
        prevention_strategy: 预防策略
        treatment: 处理方法
        metadata: 额外元数据
    """

    severity: Optional[str] = Field(None, description="严重程度")
    incidence: Optional[float] = Field(None, ge=0, le=100, description="发生率（%）")
    onset_time: Optional[str] = Field(None, description="发生时间")
    prevention_strategy: Optional[str] = Field(None, description="预防策略")
    treatment: Optional[str] = Field(None, description="处理方法")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 COMPLICATION。"""
        if v != EntityType.COMPLICATION:
            raise ValueError(
                f"ComplicationEntity 的 entity_type 必须为 COMPLICATION，得到 {v}"
            )
        return v


class PostoperativeCareEntity(BaseEntity):
    """术后管理计划实体。

    表示术后护理和随访计划。

    Attributes:
        entity_name: 计划名称（如 "Dual Antiplatelet Therapy"）
        entity_type: 实体类型，固定为 CARE_PLAN
        description: 计划描述
        duration: 持续时间
        medications: 药物列表
        follow_up_schedule: 随访计划
        monitoring_parameters: 监测指标
        lifestyle_modifications: 生活方式调整
        metadata: 额外元数据
    """

    duration: Optional[str] = Field(None, description="持续时间")
    medications: List[str] = Field(default_factory=list, description="药物列表")
    follow_up_schedule: List[str] = Field(default_factory=list, description="随访计划")
    monitoring_parameters: List[str] = Field(
        default_factory=list, description="监测指标"
    )
    lifestyle_modifications: List[str] = Field(
        default_factory=list, description="生活方式调整"
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 CARE_PLAN。"""
        if v != EntityType.CARE_PLAN:
            raise ValueError(
                f"PostoperativeCareEntity 的 entity_type 必须为 CARE_PLAN，得到 {v}"
            )
        return v


class IntraoperativeEventEntity(BaseEntity):
    """术中事件实体。

    表示手术过程中发生的事件。

    Attributes:
        entity_name: 事件名称（如 "EPD Deployment", "Stent Expansion"）
        entity_type: 实体类型，固定为 EVENT
        description: 事件描述
        event_type: 事件类型（Action/Complication/Decision）
        timestamp: 时间戳或顺序
        outcome: 结果
        required_response: 需要的响应
        alternative_actions: 备选操作
        metadata: 额外元数据
    """

    event_type: Optional[str] = Field(None, description="事件类型")
    timestamp: Optional[str] = Field(None, description="时间戳或顺序")
    outcome: Optional[str] = Field(None, description="结果")
    required_response: Optional[str] = Field(None, description="需要的响应")
    alternative_actions: List[str] = Field(default_factory=list, description="备选操作")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 EVENT。"""
        if v != EntityType.EVENT:
            raise ValueError(
                f"IntraoperativeEventEntity 的 entity_type 必须为 EVENT，得到 {v}"
            )
        return v


class ImageEntity(BaseEntity):
    """影像资料实体。

    表示医学影像检查和图像。

    Attributes:
        entity_name: 影像名称（如 "CT Angiography", "DSA"）
        entity_type: 实体类型，固定为 IMAGE
        description: 影像描述
        image_type: 影像类型（CT/MRI/DSA/Ultrasound等）
        acquisition_date: 获取日期
        findings: 影像发现
        pathology_seen: 显示的病理
        quality: 影像质量
        metadata: 额外元数据
    """

    image_type: Optional[str] = Field(None, description="影像类型")
    acquisition_date: Optional[str] = Field(None, description="获取日期")
    findings: List[str] = Field(default_factory=list, description="影像发现")
    pathology_seen: List[str] = Field(default_factory=list, description="显示的病理")
    quality: Optional[str] = Field(None, description="影像质量")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 IMAGE。"""
        if v != EntityType.IMAGE:
            raise ValueError(f"ImageEntity 的 entity_type 必须为 IMAGE，得到 {v}")
        return v


class PatientDataEntity(BaseEntity):
    """患者数据实体。

    表示患者的临床数据和病史。

    Attributes:
        entity_name: 数据类别（如 "Medical History", "Lab Results"）
        entity_type: 实体类型，固定为 PATIENT
        description: 数据描述
        age: 年龄
        gender: 性别
        comorbidities: 合并症列表
        medications: 当前用药
        allergies: 过敏史
        lab_results: 检查结果
        previous_procedures: 既往手术
        social_history: 社会史
        metadata: 额外元数据
    """

    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    gender: Optional[str] = Field(None, description="性别")
    comorbidities: List[str] = Field(default_factory=list, description="合并症")
    medications: List[str] = Field(default_factory=list, description="当前用药")
    allergies: List[str] = Field(default_factory=list, description="过敏史")
    lab_results: Dict[str, Any] = Field(default_factory=dict, description="检查结果")
    previous_procedures: List[str] = Field(default_factory=list, description="既往手术")
    social_history: List[str] = Field(default_factory=list, description="社会史")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: EntityType) -> EntityType:
        """验证实体类型为 PATIENT。"""
        if v != EntityType.PATIENT:
            raise ValueError(
                f"PatientDataEntity 的 entity_type 必须为 PATIENT，得到 {v}"
            )
        return v


# ========== 导出所有实体类 ==========


__all__ = [
    # 常量和映射
    "EntityType",
    "ENTITY_TYPE_MAPPING",
    # 基础类
    "BaseEntity",
    # 具体实体类
    "AnatomyEntity",
    "PathologyEntity",
    "ProcedureEntity",
    "DeviceEntity",
    "GuidelineEntity",
    "RiskFactorEntity",
    "ComplicationEntity",
    "PostoperativeCareEntity",
    "IntraoperativeEventEntity",
    "ImageEntity",
    "PatientDataEntity",
]
