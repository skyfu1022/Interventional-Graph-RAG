"""介入手术关系类型定义模块。

该模块定义了介入手术领域的所有关系类型，映射到 LightRAG 的关系类型系统。
所有关系类都继承自 Pydantic BaseModel，提供类型安全和序列化支持。

关系类型定义了介入手术实体之间的语义连接，包括：
- HAS_RISK: 风险因素关系
- HAS_EXAM_RESULT: 检查结果关系
- SHOWS: 显示关系（影像到病理）
- BASED_ON_GUIDELINE: 基于指南关系
- CONTRAINDICATES: 禁忌关系
- HAS_STEP: 包含步骤关系
- USES_DEVICE: 使用器械关系
- LEADS_TO_COMPLICATION: 导致并发症关系
- REQUIRES_RESCUE: 需要补救关系
- MEASURES: 测量关系
- PRESCRIBES: 处方关系
- RECEIVED_CARE: 接受护理关系
- OBSERVED_OUTCOME: 观察结果关系
- LINKED_TO: 链接关系

使用示例：
    >>> from src.graph.relationships import HasRiskRelation, BasedOnGuidelineRelation
    >>>
    >>> # 创建风险关系
    >>> risk_rel = HasRiskRelation(
    ...     source_entity_id="patient-001",
    ...     target_entity_id="hypertension",
    ...     severity="High",
    ...     description="患者有高血压病史"
    ... )
    >>>
    >>> # 创建指南关系
    >>> guideline_rel = BasedOnGuidelineRelation(
    ...     source_entity_id="cas-procedure",
    ...     target_entity_id="acc-aha-guideline",
    ...     recommendation_class="Class I",
    ...     evidence_level="Level A"
    ... )
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ========== 关系类型枚举 ==========


class RelationType(str, Enum):
    """介入手术关系类型枚举。

    定义了介入手术领域的所有关系类型。
    """

    HAS_RISK = "HAS_RISK"  # 有风险因素
    HAS_EXAM_RESULT = "HAS_EXAM_RESULT"  # 有检查结果
    SHOWS = "SHOWS"  # 显示（影像到病理）
    BASED_ON_GUIDELINE = "BASED_ON_GUIDELINE"  # 基于指南
    CONTRAINDICATES = "CONTRAINDICATES"  # 禁忌
    HAS_STEP = "HAS_STEP"  # 包含步骤
    USES_DEVICE = "USES_DEVICE"  # 使用器械
    LEADS_TO_COMPLICATION = "LEADS_TO_COMPLICATION"  # 导致并发症
    REQUIRES_RESCUE = "REQUIRES_RESCUE"  # 需要补救
    MEASURES = "MEASURES"  # 测量
    PRESCRIBES = "PRESCRIBES"  # 处方
    RECEIVED_CARE = "RECEIVED_CARE"  # 接受护理
    OBSERVED_OUTCOME = "OBSERVED_OUTCOME"  # 观察结果
    LINKED_TO = "LINKED_TO"  # 链接到


# ========== 基础关系类 ==========


class BaseRelation(BaseModel):
    """基础关系类。

    所有介入手术关系的基类，提供通用属性和方法。

    Attributes:
        relation_id: 关系唯一标识符
        source_entity_id: 源实体 ID
        target_entity_id: 目标实体 ID
        relation_type: 关系类型（使用 RelationType 枚举）
        description: 关系描述
        weight: 关系权重（用于相关性评分）
        confidence: 置信度（0-1）
        metadata: 额外的元数据字典
        sources: 数据来源列表
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    relation_id: Optional[str] = Field(None, description="关系唯一标识符")
    source_entity_id: str = Field(..., description="源实体 ID")
    target_entity_id: str = Field(..., description="目标实体 ID")
    relation_type: RelationType = Field(..., description="关系类型")
    description: Optional[str] = Field(None, description="关系描述")
    weight: float = Field(default=1.0, ge=0.0, description="关系权重")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
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
    def from_dict(cls, data: Dict[str, Any]) -> "BaseRelation":
        """从字典创建实例。

        Args:
            data: 包含模型数据的字典

        Returns:
            BaseRelation 实例
        """
        return cls.model_validate(data)


# ========== 具体关系类 ==========


class HasRiskRelation(BaseRelation):
    """风险因素关系。

    表示实体具有某种风险因素。

    Attributes:
        source_entity_id: 源实体 ID（通常是患者或病理）
        target_entity_id: 目标实体 ID（风险因素）
        relation_type: 关系类型，固定为 HAS_RISK
        description: 关系描述
        severity: 风险严重程度（Low/Medium/High/Critical）
        impact_on_outcome: 对预后的影响
        modifiable: 是否可修改
        mitigation_strategies: 缓解策略列表
        clinical_significance: 临床意义
    """

    severity: Optional[str] = Field(None, description="风险严重程度")
    impact_on_outcome: Optional[str] = Field(None, description="对预后的影响")
    modifiable: Optional[bool] = Field(None, description="是否可修改")
    mitigation_strategies: List[str] = Field(
        default_factory=list, description="缓解策略"
    )
    clinical_significance: Optional[str] = Field(None, description="临床意义")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 HAS_RISK。"""
        if v != RelationType.HAS_RISK:
            raise ValueError(
                f"HASRiskRelation 的 relation_type 必须为 HAS_RISK，得到 {v}"
            )
        return v


class HasExamResultRelation(BaseRelation):
    """检查结果关系。

    表示实体的检查结果。

    Attributes:
        source_entity_id: 源实体 ID（患者或解剖结构）
        target_entity_id: 目标实体 ID（检查结果）
        relation_type: 关系类型，固定为 HAS_EXAM_RESULT
        description: 关系描述
        exam_type: 检查类型（Laboratory/Imaging/Physiological）
        exam_date: 检查日期
        result_value: 结果值
        normal_range: 正常范围
        abnormal: 是否异常
        clinical_implication: 临床意义
    """

    exam_type: Optional[str] = Field(None, description="检查类型")
    exam_date: Optional[str] = Field(None, description="检查日期")
    result_value: Optional[str] = Field(None, description="结果值")
    normal_range: Optional[str] = Field(None, description="正常范围")
    abnormal: Optional[bool] = Field(None, description="是否异常")
    clinical_implication: Optional[str] = Field(None, description="临床意义")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 HAS_EXAM_RESULT。"""
        if v != RelationType.HAS_EXAM_RESULT:
            raise ValueError(
                f"HasExamResultRelation 的 relation_type 必须为 HAS_EXAM_RESULT，得到 {v}"
            )
        return v


class ShowsRelation(BaseRelation):
    """显示关系。

    表示影像资料显示的病理改变。

    Attributes:
        source_entity_id: 源实体 ID（影像）
        target_entity_id: 目标实体 ID（病理或解剖）
        relation_type: 关系类型，固定为 SHOWS
        description: 关系描述
        visibility: 可见度（Clear/Partially Clear/Unclear）
        confidence: 发现的置信度
        image_region: 影像区域
        quantitative_measures: 定量测量
        description_of_finding: 发现描述
    """

    visibility: Optional[str] = Field(None, description="可见度")
    image_region: Optional[str] = Field(None, description="影像区域")
    quantitative_measures: Dict[str, Any] = Field(
        default_factory=dict, description="定量测量"
    )
    description_of_finding: Optional[str] = Field(None, description="发现描述")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 SHOWS。"""
        if v != RelationType.SHOWS:
            raise ValueError(f"ShowsRelation 的 relation_type 必须为 SHOWS，得到 {v}")
        return v


class BasedOnGuidelineRelation(BaseRelation):
    """基于指南关系。

    表示手术方案或决策基于临床指南。

    Attributes:
        source_entity_id: 源实体 ID（手术方案或决策）
        target_entity_id: 目标实体 ID（指南）
        relation_type: 关系类型，固定为 BASED_ON_GUIDELINE
        description: 关系描述
        recommendation_class: 推荐等级（Class I/IIa/IIb/III）
        evidence_level: 证据级别（Level A/B/C）
        guideline_year: 指南年份
        applicability: 适用性
        specific_conditions: 特定条件
        strength_of_recommendation: 推荐强度
    """

    recommendation_class: Optional[str] = Field(None, description="推荐等级")
    evidence_level: Optional[str] = Field(None, description="证据级别")
    guideline_year: Optional[int] = Field(
        None, ge=1900, le=2100, description="指南年份"
    )
    applicability: Optional[str] = Field(None, description="适用性")
    specific_conditions: List[str] = Field(default_factory=list, description="特定条件")
    strength_of_recommendation: Optional[str] = Field(None, description="推荐强度")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 BASED_ON_GUIDELINE。"""
        if v != RelationType.BASED_ON_GUIDELINE:
            raise ValueError(
                f"BasedOnGuidelineRelation 的 relation_type 必须为 BASED_ON_GUIDELINE，得到 {v}"
            )
        return v


class ContraindicatesRelation(BaseRelation):
    """禁忌关系。

    表示某种情况或器械对另一个实体的禁忌。

    Attributes:
        source_entity_id: 源实体 ID（器械、手术或病理）
        target_entity_id: 目标实体 ID（患者情况或风险因素）
        relation_type: 关系类型，固定为 CONTRAINDICATES
        description: 关系描述
        contraindication_type: 禁忌类型（Absolute/Relative）
        severity: 严重程度
        clinical_rationale: 临床理由
        alternative_options: 替代方案
        warning_level: 警告级别
    """

    contraindication_type: Optional[str] = Field(None, description="禁忌类型")
    severity: Optional[str] = Field(None, description="严重程度")
    clinical_rationale: Optional[str] = Field(None, description="临床理由")
    alternative_options: List[str] = Field(default_factory=list, description="替代方案")
    warning_level: Optional[str] = Field(None, description="警告级别")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 CONTRAINDICATES。"""
        if v != RelationType.CONTRAINDICATES:
            raise ValueError(
                f"ContraindicatesRelation 的 relation_type 必须为 CONTRAINDICATES，得到 {v}"
            )
        return v


class HasStepRelation(BaseRelation):
    """包含步骤关系。

    表示手术操作包含的步骤。

    Attributes:
        source_entity_id: 源实体 ID（手术操作）
        target_entity_id: 目标实体 ID（步骤或事件）
        relation_type: 关系类型，固定为 HAS_STEP
        description: 关系描述
        step_order: 步骤顺序
        step_type: 步骤类型（Preparation/Execution/Completion）
        duration: 预计时长
        critical: 是否关键步骤
        prerequisites: 前提条件
        potential_complications: 潜在并发症
    """

    step_order: Optional[int] = Field(None, ge=1, description="步骤顺序")
    step_type: Optional[str] = Field(None, description="步骤类型")
    duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    critical: Optional[bool] = Field(None, description="是否关键步骤")
    prerequisites: List[str] = Field(default_factory=list, description="前提条件")
    potential_complications: List[str] = Field(
        default_factory=list, description="潜在并发症"
    )

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 HAS_STEP。"""
        if v != RelationType.HAS_STEP:
            raise ValueError(
                f"HasStepRelation 的 relation_type 必须为 HAS_STEP，得到 {v}"
            )
        return v


class UsesDeviceRelation(BaseRelation):
    """使用器械关系。

    表示手术操作或步骤使用的器械。

    Attributes:
        source_entity_id: 源实体 ID（手术操作或步骤）
        target_entity_id: 目标实体 ID（器械）
        relation_type: 关系类型，固定为 USES_DEVICE
        description: 关系描述
        usage_phase: 使用阶段
        quantity: 数量
        specifications: 规格要求
        alternative_devices: 替代器械
        device_preparation: 器械准备
        usage_technique: 使用技术
    """

    usage_phase: Optional[str] = Field(None, description="使用阶段")
    quantity: Optional[int] = Field(None, ge=1, description="数量")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="规格要求")
    alternative_devices: List[str] = Field(default_factory=list, description="替代器械")
    device_preparation: Optional[str] = Field(None, description="器械准备")
    usage_technique: Optional[str] = Field(None, description="使用技术")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 USES_DEVICE。"""
        if v != RelationType.USES_DEVICE:
            raise ValueError(
                f"UsesDeviceRelation 的 relation_type 必须为 USES_DEVICE，得到 {v}"
            )
        return v


class LeadsToComplicationRelation(BaseRelation):
    """导致并发症关系。

    表示某操作或情况可能导致并发症。

    Attributes:
        source_entity_id: 源实体 ID（手术、步骤或风险因素）
        target_entity_id: 目标实体 ID（并发症）
        relation_type: 关系类型，固定为 LEADS_TO_COMPLICATION
        description: 关系描述
        likelihood: 发生可能性（Rare/Uncommon/Common/Likely）
        severity: 严重程度
        timing: 发生时间（Intraoperative/Postoperative）
        risk_factors: 风险因素
        prevention_methods: 预防方法
        treatment: 处理方法
    """

    likelihood: Optional[str] = Field(None, description="发生可能性")
    severity: Optional[str] = Field(None, description="严重程度")
    timing: Optional[str] = Field(None, description="发生时间")
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    prevention_methods: List[str] = Field(default_factory=list, description="预防方法")
    treatment: Optional[str] = Field(None, description="处理方法")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 LEADS_TO_COMPLICATION。"""
        if v != RelationType.LEADS_TO_COMPLICATION:
            raise ValueError(
                f"LeadsToComplicationRelation 的 relation_type 必须为 LEADS_TO_COMPLICATION，得到 {v}"
            )
        return v


class RequiresRescueRelation(BaseRelation):
    """需要补救关系。

    表示当某步骤失败时需要的补救措施。

    Attributes:
        source_entity_id: 源实体 ID（失败的步骤）
        target_entity_id: 目标实体 ID（补救措施或备选方案）
        relation_type: 关系类型，固定为 REQUIRES_RESCUE
        description: 关系描述
        trigger_condition: 触发条件
        urgency: 紧急程度
        success_rate: 成功率
        time_window: 时间窗口
        required_resources: 所需资源
        decision_criteria: 决策标准
    """

    trigger_condition: Optional[str] = Field(None, description="触发条件")
    urgency: Optional[str] = Field(None, description="紧急程度")
    success_rate: Optional[float] = Field(None, ge=0, le=100, description="成功率（%）")
    time_window: Optional[str] = Field(None, description="时间窗口")
    required_resources: List[str] = Field(default_factory=list, description="所需资源")
    decision_criteria: List[str] = Field(default_factory=list, description="决策标准")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 REQUIRES_RESCUE。"""
        if v != RelationType.REQUIRES_RESCUE:
            raise ValueError(
                f"RequiresRescueRelation 的 relation_type 必须为 REQUIRES_RESCUE，得到 {v}"
            )
        return v


class MeasuresRelation(BaseRelation):
    """测量关系。

    表示某测量指标与解剖结构或病理的关系。

    Attributes:
        source_entity_id: 源实体 ID（测量或检查）
        target_entity_id: 目标实体 ID（解剖结构或病理）
        relation_type: 关系类型，固定为 MEASURES
        description: 关系描述
        measurement_type: 测量类型（Diameter/Area/Volume/Percentage）
        value: 测量值
        unit: 单位
        method: 测量方法
        normal_range: 正常范围
        clinical_significance: 临床意义
    """

    measurement_type: Optional[str] = Field(None, description="测量类型")
    value: Optional[float] = Field(None, description="测量值")
    unit: Optional[str] = Field(None, description="单位")
    method: Optional[str] = Field(None, description="测量方法")
    normal_range: Optional[str] = Field(None, description="正常范围")
    clinical_significance: Optional[str] = Field(None, description="临床意义")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 MEASURES。"""
        if v != RelationType.MEASURES:
            raise ValueError(
                f"MeasuresRelation 的 relation_type 必须为 MEASURES，得到 {v}"
            )
        return v


class PrescribesRelation(BaseRelation):
    """处方关系。

    表示术后护理或药物治疗方案。

    Attributes:
        source_entity_id: 源实体 ID（护理计划或医生）
        target_entity_id: 目标实体 ID（药物或护理措施）
        relation_type: 关系类型，固定为 PRESCRIBES
        description: 关系描述
        medication_type: 药物类型
        dosage: 剂量
        frequency: 频率
        duration: 持续时间
        route: 给药途径
        indications: 适应症
        contraindications: 禁忌症
        side_effects: 副作用
    """

    medication_type: Optional[str] = Field(None, description="药物类型")
    dosage: Optional[str] = Field(None, description="剂量")
    frequency: Optional[str] = Field(None, description="频率")
    duration: Optional[str] = Field(None, description="持续时间")
    route: Optional[str] = Field(None, description="给药途径")
    indications: List[str] = Field(default_factory=list, description="适应症")
    contraindications: List[str] = Field(default_factory=list, description="禁忌症")
    side_effects: List[str] = Field(default_factory=list, description="副作用")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 PRESCRIBES。"""
        if v != RelationType.PRESCRIBES:
            raise ValueError(
                f"PrescribesRelation 的 relation_type 必须为 PRESCRIBES，得到 {v}"
            )
        return v


class ReceivedCareRelation(BaseRelation):
    """接受护理关系。

    表示患者接受的术后护理。

    Attributes:
        source_entity_id: 源实体 ID（患者）
        target_entity_id: 目标实体 ID（护理计划或措施）
        relation_type: 关系类型，固定为 RECEIVED_CARE
        description: 关系描述
        care_type: 护理类型
        start_date: 开始日期
        end_date: 结束日期
        provider: 提供者
        adherence: 依从性
        outcomes: 结局
        follow_up_required: 是否需要随访
    """

    care_type: Optional[str] = Field(None, description="护理类型")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    provider: Optional[str] = Field(None, description="提供者")
    adherence: Optional[str] = Field(None, description="依从性")
    outcomes: List[str] = Field(default_factory=list, description="结局")
    follow_up_required: Optional[bool] = Field(None, description="是否需要随访")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 RECEIVED_CARE。"""
        if v != RelationType.RECEIVED_CARE:
            raise ValueError(
                f"ReceivedCareRelation 的 relation_type 必须为 RECEIVED_CARE，得到 {v}"
            )
        return v


class ObservedOutcomeRelation(BaseRelation):
    """观察结果关系。

    表示术后观察到的结果或预后。

    Attributes:
        source_entity_id: 源实体 ID（手术或护理）
        target_entity_id: 目标实体 ID（结果）
        relation_type: 关系类型，固定为 OBSERVED_OUTCOME
        description: 关系描述
        outcome_type: 结果类型（Success/Complication/Recurrence）
        time_frame: 时间框架
        outcome_measures: 结果指标
        satisfaction: 满意度
        quality_of_life: 生活质量
        notes: 备注
    """

    outcome_type: Optional[str] = Field(None, description="结果类型")
    time_frame: Optional[str] = Field(None, description="时间框架")
    outcome_measures: Dict[str, Any] = Field(
        default_factory=dict, description="结果指标"
    )
    satisfaction: Optional[str] = Field(None, description="满意度")
    quality_of_life: Optional[str] = Field(None, description="生活质量")
    notes: List[str] = Field(default_factory=list, description="备注")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 OBSERVED_OUTCOME。"""
        if v != RelationType.OBSERVED_OUTCOME:
            raise ValueError(
                f"ObservedOutcomeRelation 的 relation_type 必须为 OBSERVED_OUTCOME，得到 {v}"
            )
        return v


class LinkedToRelation(BaseRelation):
    """链接关系。

    表示实体之间的通用链接关系。

    Attributes:
        source_entity_id: 源实体 ID
        target_entity_id: 目标实体 ID
        relation_type: 关系类型，固定为 LINKED_TO
        description: 关系描述
        link_type: 链接类型（Association/Correlation/Reference）
        strength: 链接强度
        temporal: 时间关系
        directionality: 方向性
        context: 上下文
    """

    link_type: Optional[str] = Field(None, description="链接类型")
    strength: Optional[str] = Field(None, description="链接强度")
    temporal: Optional[str] = Field(None, description="时间关系")
    directionality: Optional[str] = Field(None, description="方向性")
    context: Optional[str] = Field(None, description="上下文")

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: RelationType) -> RelationType:
        """验证关系类型为 LINKED_TO。"""
        if v != RelationType.LINKED_TO:
            raise ValueError(
                f"LinkedToRelation 的 relation_type 必须为 LINKED_TO，得到 {v}"
            )
        return v


# ========== 导出所有关系类 ==========


__all__ = [
    # 枚举
    "RelationType",
    # 基础类
    "BaseRelation",
    # 具体关系类
    "HasRiskRelation",
    "HasExamResultRelation",
    "ShowsRelation",
    "BasedOnGuidelineRelation",
    "ContraindicatesRelation",
    "HasStepRelation",
    "UsesDeviceRelation",
    "LeadsToComplicationRelation",
    "RequiresRescueRelation",
    "MeasuresRelation",
    "PrescribesRelation",
    "ReceivedCareRelation",
    "ObservedOutcomeRelation",
    "LinkedToRelation",
]
