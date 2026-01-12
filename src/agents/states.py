"""
LangGraph 智能体状态管理模块。

该模块定义了用于 LangGraph 工作流的状态结构和状态转换。
"""

from operator import add
from typing import Annotated, Any, Dict, List, Optional, TypedDict, Union

from langgraph.graph.message import AnyMessage, add_messages
from typing_extensions import Required

# 导入扩展数据模型
from src.agents.models import (
    DeviceSelectionModel,
    GuidelineMatch,
    PatientDataModel,
    PostOpPlanModel,
    ProcedurePlanModel,
    ReasoningStepModel,
    RetrievedEntity,
    RetrievedRelationship,
    RiskFactorModel,
)


class QueryState(TypedDict):
    """查询工作流状态。

    用于管理基于图谱的查询流程，包括查询分析、上下文检索、答案生成等步骤。
    支持多层检索策略和错误重试机制。

    Attributes:
        query: 用户查询
        graph_id: 目标图谱 ID
        query_complexity: 查询复杂度，可选值: simple, medium, complex
        context: 检索到的上下文列表
        answer: 生成的答案
        sources: 答案来源列表
        retrieval_count: 检索次数计数器
        max_retries: 最大重试次数
        error: 错误信息
    """

    query: Required[str]
    graph_id: Required[str]
    query_complexity: str
    context: Annotated[List[str], add]
    answer: str
    sources: List[str]
    retrieval_count: int
    max_retries: int
    error: Optional[str]


class BuildState(TypedDict):
    """图谱构建工作流状态。

    用于管理从文档构建知识图谱的完整流程，包括文档加载、实体抽取、关系构建、
    节点合并等步骤。支持处理单个文档或批量文档。

    Attributes:
        file_path: 文档路径
        graph_id: 目标图谱 ID
        merge_enabled: 是否启用节点合并
        status: 构建状态，可选值: pending, loading, extracting, building,
                 merging, completed, failed
        entity_count: 提取的实体数量
        relationship_count: 提取的关系数量
        document_count: 处理的文档数量
        error: 错误信息
    """

    file_path: Required[str]
    graph_id: Required[str]
    merge_enabled: bool
    status: str
    entity_count: int
    relationship_count: int
    document_count: int
    error: Optional[str]


class InterventionalState(TypedDict):
    """介入手术智能体工作流状态。

    用于介入手术辅助决策智能体的状态管理，整合患者数据分析、器械推荐、
    风险评估和方案推荐等功能。

    Attributes:
        patient_data: 患者数据字典
        procedure_type: 手术类型，如 PCI、支架植入等
        devices: 推荐的器械列表
        risks: 识别的风险列表
        recommendations: 推荐方案描述
        context: 检索到的相关上下文
        error: 错误信息
    """

    patient_data: Required[Dict]
    procedure_type: Required[str]
    devices: Annotated[List[str], add]
    risks: Annotated[List[str], add]
    recommendations: str
    context: Annotated[List[str], add]
    error: Optional[str]


class BaseAgentState(TypedDict):
    """基础智能体状态。

    提供消息历史管理的基础状态类，可用于需要对话记忆的智能体。

    Attributes:
        messages: 消息历史列表，使用 add_messages reducer 实现自动追加
        graph_id: 关联的图谱 ID
        error: 错误信息
    """

    messages: Annotated[List[AnyMessage], add_messages]
    graph_id: str
    error: Optional[str]


class RAGState(TypedDict):
    """检索增强生成（RAG）工作流状态。

    用于管理 RAG 流程，结合知识图谱检索和生成能力。

    Attributes:
        query: 用户查询
        retrieved_entities: 检索到的实体
        retrieved_relationships: 检索到的关系
        retrieved_context: 检索到的上下文
        generation: 生成的内容
        sources: 来源列表
        error: 错误信息
    """

    query: Required[str]
    retrieved_entities: Annotated[List[Dict], add]
    retrieved_relationships: Annotated[List[Dict], add]
    retrieved_context: Annotated[List[str], add]
    generation: str
    sources: List[str]
    error: Optional[str]


class ExtendedInterventionalState(TypedDict):
    """扩展的介入手术智能体工作流状态。

    用于介入手术辅助决策智能体的状态管理，整合 GraphRAG 三层图谱检索、
    LLM 分析结果和临床决策支持功能。

    该状态类型继承并扩展了基础 InterventionalState，增加了：
    - GraphRAG 检索结果（实体、关系、指南匹配）
    - 三层图谱上下文（患者数据、文献指南、医学词典）
    - LLM 分析结果（患者分析、器械推荐、风险评估、手术方案）
    - 推理链追踪和术后计划

    Attributes:
        # === GraphRAG 检索结果（累加器） ===
        retrieved_entities: 检索到的实体列表，支持累加
        retrieved_relationships: 检索到的关系列表，支持累加
        matched_guidelines: 匹配的指南列表，支持累加

        # === 三层图谱上下文 ===
        patient_graph_context: 患者数据图谱上下文字典
        literature_graph_context: 文献指南图谱上下文字典
        dictionary_graph_context: 医学词典图谱上下文字典

        # === LLM 分析结果 ===
        patient_analysis: 患者数据分析结果（PatientDataModel 或字典）
        device_recommendations: 器械推荐列表（DeviceSelectionModel 列表）
        risk_assessment: 风险评估列表（RiskFactorModel 列表）
        procedure_plan: 手术方案（ProcedurePlanModel 或字典）
        reasoning_steps: 推理步骤列表（ReasoningStepModel 列表）
        post_op_plan: 术后管理计划（PostOpPlanModel 或字典）

        # === 元数据 ===
        retrieval_mode: 检索模式（如 "hybrid", "semantic", "keyword"）
        sources: 数据来源列表
        current_phase: 当前手术阶段（pre_op, intra_op, post_op）
        error: 错误信息
    """

    # === GraphRAG 检索结果（使用累加器） ===
    retrieved_entities: Annotated[List[Union[RetrievedEntity, Dict]], add]  # 支持累加
    retrieved_relationships: Annotated[
        List[Union[RetrievedRelationship, Dict]], add
    ]  # 支持累加
    matched_guidelines: Annotated[List[Union[GuidelineMatch, Dict]], add]  # 支持累加

    # === 三层图谱上下文 ===
    patient_graph_context: Dict[str, Any]  # 患者数据图谱上下文
    literature_graph_context: Dict[str, Any]  # 文献指南图谱上下文
    dictionary_graph_context: Dict[str, Any]  # 医学词典图谱上下文

    # === LLM 分析结果 ===
    patient_analysis: Optional[Union[PatientDataModel, Dict]]  # 患者数据分析结果
    device_recommendations: List[Union[DeviceSelectionModel, Dict]]  # 器械推荐列表
    risk_assessment: List[Union[RiskFactorModel, Dict]]  # 风险评估列表
    procedure_plan: Optional[Union[ProcedurePlanModel, Dict]]  # 手术方案
    reasoning_steps: List[Union[ReasoningStepModel, Dict]]  # 推理步骤列表
    post_op_plan: Optional[Union[PostOpPlanModel, Dict]]  # 术后管理计划

    # === 元数据 ===
    retrieval_mode: Optional[str]  # 检索模式
    sources: List[str]  # 数据来源列表
    current_phase: Optional[str]  # 当前手术阶段
    error: Optional[str]  # 错误信息
    recommendations: Optional[str]  # 生成的推荐方案描述
    patient_data: Required[Dict[str, Any]]  # 患者数据
    procedure_type: Required[str]  # 手术类型
    indications_met: bool  # 适应症评估结果
    contraindications_found: bool  # 禁忌症评估结果
    contraindications: List[str]  # 禁忌症列表
