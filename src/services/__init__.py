"""
服务层模块。

该模块提供项目的核心服务层，包括：
- 图谱服务（graph.py）：图谱生命周期管理
- 摄入服务（ingestion.py）：文档摄入处理
- 查询服务（query.py）：知识图谱查询
- 排序服务（ranking.py）：结果排序和重排
- 多模态服务（multimodal.py）：多模态查询支持

使用示例：
    >>> from src.services import (
    ...     GraphService,
    ...     IngestionService,
    ...     QueryService,
    ...     ResultRanker,
    ...     MultimodalQueryService
    ... )
"""

from src.services.graph import GraphService, GraphInfo, EntityNode, RelationshipEdge
from src.services.ingestion import (
    IngestionService,
    BatchIngestResult,
    DocumentStatus,
    ProgressCallback,
)
from src.services.query import QueryService
from src.services.ranking import (
    ResultRanker,
    RankedResult,
    RankingConfig,
    RankingMethod,
    DedupMethod,
    create_ranker,
)
from src.services.multimodal import MultimodalQueryService, MultimodalQueryResult

__all__ = [
    "GraphService",
    "GraphInfo",
    "EntityNode",
    "RelationshipEdge",
    "IngestionService",
    "BatchIngestResult",
    "DocumentStatus",
    "ProgressCallback",
    "QueryService",
    "ResultRanker",
    "RankedResult",
    "RankingConfig",
    "RankingMethod",
    "DedupMethod",
    "create_ranker",
    "MultimodalQueryService",
    "MultimodalQueryResult",
]
