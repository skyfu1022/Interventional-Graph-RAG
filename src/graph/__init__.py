"""图谱模块。

该模块提供了介入手术领域的图谱 Schema 定义，包括实体类型、关系类型和图谱管理功能。

主要功能：
- 定义介入手术实体类型（映射到 LightRAG）
- 定义介入手术关系类型
- 提供图谱 Schema 管理

使用示例：
    >>> from src.graph.entities import AnatomyEntity, PathologyEntity, EntityType
    >>> from src.graph.relationships import HasRiskRelation, BasedOnGuidelineRelation
    >>>
    >>> # 创建实体
    >>> anatomy = AnatomyEntity(
    ...     entity_name="Left ICA",
    ...     entity_type=EntityType.ANATOMY,
    ...     description="左侧颈内动脉",
    ...     location="Neck",
    ...     laterality="Left"
    ... )
    >>>
    >>> # 创建关系
    >>> risk_rel = HasRiskRelation(
    ...     source_entity_id="patient-001",
    ...     target_entity_id="hypertension",
    ...     severity="High",
    ...     description="患者有高血压病史"
    ... )
"""

from src.graph.entities import (
    # 枚举和映射
    EntityType,
    ENTITY_TYPE_MAPPING,
    # 基础类
    BaseEntity,
    # 具体实体类
    AnatomyEntity,
    PathologyEntity,
    ProcedureEntity,
    DeviceEntity,
    GuidelineEntity,
    RiskFactorEntity,
    ComplicationEntity,
    PostoperativeCareEntity,
    IntraoperativeEventEntity,
    ImageEntity,
    PatientDataEntity,
)

from src.graph.relationships import (
    # 枚举
    RelationType,
    # 基础类
    BaseRelation,
    # 具体关系类
    HasRiskRelation,
    HasExamResultRelation,
    ShowsRelation,
    BasedOnGuidelineRelation,
    ContraindicatesRelation,
    HasStepRelation,
    UsesDeviceRelation,
    LeadsToComplicationRelation,
    RequiresRescueRelation,
    MeasuresRelation,
    PrescribesRelation,
    ReceivedCareRelation,
    ObservedOutcomeRelation,
    LinkedToRelation,
)

__all__ = [
    # ========== 实体类 ==========
    # 枚举和映射
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
    # ========== 关系类 ==========
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
