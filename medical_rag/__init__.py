"""
Medical RAG - 基于 RAG Anything 的医疗知识图谱 RAG 系统
"""

__version__ = "0.1.0"

from .config import MedicalRAGConfig, load_config
from .graphrag import MedicalRAG, GraphRAG, QueryParam
from .three_layer import (
    ThreeLayerGraph,
    LayerConfig,
    LayerQueryResult,
    create_three_layer_graph
)

__all__ = [
    "MedicalRAGConfig",
    "load_config",
    "MedicalRAG",
    "GraphRAG",  # 兼容别名
    "QueryParam",
    "ThreeLayerGraph",
    "LayerConfig",
    "LayerQueryResult",
    "create_three_layer_graph",
]
