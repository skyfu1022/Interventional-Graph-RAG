"""
LangGraph 智能体状态管理模块。

该模块定义了用于 LangGraph 工作流的状态结构和状态转换。
"""

from typing import TypedDict, List, Optional, Annotated, Dict
from typing_extensions import Required
from operator import add
from langgraph.graph.message import add_messages, AnyMessage


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
