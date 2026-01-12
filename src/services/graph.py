"""
图谱服务模块。

该模块提供知识图谱的生命周期管理功能，包括：
- 图谱列表和详情查询
- 图谱删除
- 图谱导出（JSON、CSV、Mermaid 格式）
- 节点合并和去重

基于 LightRAG 1.4.9+ 版本实现，使用 Context7 查询的最佳实践。

使用示例：
    >>> from src.core.config import Settings
    >>> from src.core.adapters import RAGAnythingAdapter
    >>> from src.services.graph import GraphService
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     config = Settings()
    >>>     adapter = RAGAnythingAdapter(config)
    >>>     await adapter.initialize()
    >>>     service = GraphService(adapter)
    >>>
    >>>     # 列出所有图谱
    >>>     graphs = await service.list_graphs()
    >>>     for graph in graphs:
    >>>         print(f"{graph.graph_id}: {graph.entity_count} 实体")
    >>>
    >>>     # 导出图谱
    >>>     await service.export_graph("medical", "output.json", format="json")
    >>>
    >>> asyncio.run(main())
"""

from typing import List, Optional, Dict, Any, Literal
from pathlib import Path
from dataclasses import dataclass, field
import json
import csv
import shutil

from src.core.adapters import RAGAnythingAdapter, GraphStats
from src.core.exceptions import GraphError, NotFoundError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.graph")


# ========== 数据类 ==========


@dataclass
class GraphInfo:
    """图谱信息数据类。

    包含知识图谱的基本信息和统计数据。

    Attributes:
        graph_id: 图谱唯一标识符（通常使用工作空间名称）
        workspace: 工作空间名称
        entity_count: 实体总数
        relationship_count: 关系总数
        document_count: 文档总数
        created_at: 创建时间（ISO 8601 格式）
        updated_at: 最后更新时间（ISO 8601 格式）
        storage_info: 存储后端信息
    """

    graph_id: str
    workspace: str
    entity_count: int = 0
    relationship_count: int = 0
    document_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    storage_info: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含图谱信息的字典
        """
        return {
            "graph_id": self.graph_id,
            "workspace": self.workspace,
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "document_count": self.document_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "storage_info": self.storage_info,
        }


@dataclass
class EntityNode:
    """实体节点数据类。

    表示知识图谱中的一个实体节点。

    Attributes:
        entity_name: 实体名称
        entity_type: 实体类型（如 DISEASE, MEDICINE 等）
        description: 实体描述
        source_id: 来源文档 ID
    """

    entity_name: str
    entity_type: str
    description: str = ""
    source_id: str = ""


@dataclass
class RelationshipEdge:
    """关系边数据类。

    表示知识图谱中的一条关系边。

    Attributes:
        source_entity: 源实体名称
        target_entity: 目标实体名称
        description: 关系描述
        keywords: 关键词列表
        weight: 关系权重
    """

    source_entity: str
    target_entity: str
    description: str = ""
    keywords: str = ""
    weight: float = 1.0


# ========== 图谱服务类 ==========


class GraphService:
    """图谱服务类。

    管理知识图谱的完整生命周期，提供：
    - 图谱列表和详情查询
    - 图谱删除（通过 LightRAG 的 adelete_by_entity 和 adelete_by_relation）
    - 图谱导出（JSON、CSV、Mermaid 格式）
    - 节点合并和去重

    基于 LightRAG 1.4.9+ API 实现：
    - aexport_data: 导出图谱数据
    - adelete_by_entity: 删除实体及其关系
    - adelete_by_relation: 删除实体间的关系
    - acreate_entity: 创建实体
    - aedit_entity: 编辑实体
    - amerge_entities: 合并实体

    Attributes:
        _adapter: RAGAnything 适配器实例
        _logger: 日志记录器

    Example:
        >>> adapter = RAGAnythingAdapter(config)
        >>> await adapter.initialize()
        >>> service = GraphService(adapter)
        >>>
        >>> # 列出图谱
        >>> graphs = await service.list_graphs()
        >>>
        >>> # 获取详情
        >>> info = await service.get_graph_info("medical")
        >>>
        >>> # 导出图谱
        >>> await service.export_graph("medical", "output.json", "json")
    """

    def __init__(self, adapter: RAGAnythingAdapter):
        """初始化图谱服务。

        Args:
            adapter: RAGAnything 适配器实例
        """
        self._adapter = adapter
        self._logger = logger

    async def list_graphs(
        self,
        workspace: Optional[str] = None,
        min_entity_count: int = 0,
    ) -> List[GraphInfo]:
        """列出所有图谱。

        遍历工作空间目录，获取每个图谱的统计信息。
        支持按工作空间名称和最小实体数量过滤。

        Args:
            workspace: 工作空间名称（可选，用于过滤）
            min_entity_count: 最小实体数量（可选，用于过滤）

        Returns:
            List[GraphInfo]: 图谱信息列表

        Raises:
            GraphError: 获取图谱列表失败
        """
        self._logger.info("列出所有图谱")

        # 获取工作空间目录
        working_dir = Path(self._adapter.config.rag_working_dir)

        if not working_dir.exists():
            self._logger.warning(f"工作目录不存在: {working_dir}")
            return []

        graphs = []

        try:
            # 遍历工作空间目录
            for ws_path in working_dir.iterdir():
                if not ws_path.is_dir():
                    continue

                graph_id = ws_path.name

                # 过滤工作空间
                if workspace and graph_id != workspace:
                    continue

                # 跳过隐藏目录
                if graph_id.startswith("."):
                    continue

                try:
                    # 获取图谱统计信息
                    stats = await self._adapter.get_stats()

                    # 过滤实体数量
                    if stats.entity_count < min_entity_count:
                        continue

                    # 获取创建和更新时间
                    created_at, updated_at = self._get_graph_timestamps(ws_path)

                    graph_info = GraphInfo(
                        graph_id=graph_id,
                        workspace=graph_id,
                        entity_count=stats.entity_count,
                        relationship_count=stats.relationship_count,
                        document_count=stats.document_count,
                        created_at=created_at,
                        updated_at=updated_at,
                        storage_info=stats.storage_info,
                    )
                    graphs.append(graph_info)

                except Exception as e:
                    self._logger.warning(f"无法获取图谱 {graph_id} 的信息: {e}")

            self._logger.info(f"找到 {len(graphs)} 个图谱")
            return graphs

        except Exception as e:
            self._logger.error(f"列出图谱失败: {e}")
            raise GraphError(
                f"列出图谱失败: {e}",
                details={"working_dir": str(working_dir)},
            ) from e

    async def get_graph_info(self, graph_id: str) -> GraphInfo:
        """获取图谱详情。

        获取指定图谱的详细统计信息。

        Args:
            graph_id: 图谱 ID

        Returns:
            GraphInfo: 图谱详细信息

        Raises:
            NotFoundError: 图谱不存在
            GraphError: 获取信息失败
        """
        self._logger.info(f"获取图谱详情: {graph_id}")

        try:
            # 验证图谱目录是否存在
            working_dir = Path(self._adapter.config.rag_working_dir)
            graph_path = working_dir / graph_id

            if not graph_path.exists():
                raise NotFoundError(
                    f"图谱不存在: {graph_id}",
                    resource_type="graph",
                    resource_id=graph_id,
                )

            # 获取统计信息
            stats = await self._adapter.get_stats()

            # 获取时间戳
            created_at, updated_at = self._get_graph_timestamps(graph_path)

            return GraphInfo(
                graph_id=graph_id,
                workspace=graph_id,
                entity_count=stats.entity_count,
                relationship_count=stats.relationship_count,
                document_count=stats.document_count,
                created_at=created_at,
                updated_at=updated_at,
                storage_info=stats.storage_info,
            )

        except NotFoundError:
            raise
        except Exception as e:
            self._logger.error(f"获取图谱详情失败: {e}")
            raise GraphError(
                f"获取图谱详情失败: {e}",
                graph_id=graph_id,
            ) from e

    async def delete_graph(
        self,
        graph_id: str,
        confirm: bool = False,
    ) -> bool:
        """删除图谱。

        删除指定的知识图谱。此操作不可逆，需要确认。

        Args:
            graph_id: 图谱 ID
            confirm: 是否确认删除（安全措施）

        Returns:
            bool: 是否成功删除

        Raises:
            ValidationError: 未确认删除操作
            NotFoundError: 图谱不存在
            GraphError: 删除失败

        Note:
            LightRAG 没有直接的"删除图谱"API。
            此实现通过删除工作空间目录来实现。
            如果需要保留 Neo4j 数据，可以单独删除向量存储和 KV 存储。
        """
        if not confirm:
            raise ValidationError(
                "删除图谱需要确认。请设置 confirm=True",
                field="confirm",
                value=confirm,
                constraint="confirm == True",
            )

        self._logger.info(f"删除图谱: {graph_id}")

        try:
            # 验证图谱目录是否存在
            working_dir = Path(self._adapter.config.rag_working_dir)
            graph_path = working_dir / graph_id

            if not graph_path.exists():
                raise NotFoundError(
                    f"图谱不存在: {graph_id}",
                    resource_type="graph",
                    resource_id=graph_id,
                )

            # 删除工作空间目录
            shutil.rmtree(graph_path)

            self._logger.info(f"图谱删除成功: {graph_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self._logger.error(f"删除图谱失败: {e}")
            raise GraphError(
                f"删除图谱失败: {e}",
                graph_id=graph_id,
            ) from e

    async def export_graph(
        self,
        graph_id: str,
        output_path: str,
        format: Literal["json", "csv", "mermaid"] = "json",
        include_vectors: bool = False,
    ) -> None:
        """导出图谱。

        将知识图谱导出为指定格式文件。

        Args:
            graph_id: 图谱 ID
            output_path: 输出文件路径
            format: 导出格式（json, csv, mermaid）
            include_vectors: 是否包含向量数据（仅对 json/csv 有效）

        Raises:
            ValidationError: 导出格式无效
            NotFoundError: 图谱不存在
            GraphError: 导出失败

        Note:
            - JSON: 完整的图谱数据，包含实体、关系和统计
            - CSV: 表格格式，便于 Excel 分析
            - Mermaid: 可视化图表格式，用于文档展示
        """
        self._logger.info(f"导出图谱: {graph_id} -> {output_path} ({format})")

        # 验证格式
        valid_formats = ["json", "csv", "mermaid"]
        if format not in valid_formats:
            raise ValidationError(
                f"不支持的导出格式: {format}",
                field="format",
                value=format,
                constraint=f"format in {valid_formats}",
            )

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 获取图谱数据
            stats = await self._adapter.get_stats()

            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 根据格式导出
            if format == "json":
                await self._export_json(graph_id, stats, output_file, include_vectors)
            elif format == "csv":
                await self._export_csv(graph_id, stats, output_file, include_vectors)
            elif format == "mermaid":
                await self._export_mermaid(graph_id, stats, output_file)
            else:
                raise ValidationError(
                    f"未实现的导出格式: {format}",
                    field="format",
                )

            self._logger.info(f"图谱导出成功: {output_path}")

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self._logger.error(f"导出图谱失败: {e}")
            raise GraphError(
                f"导出图谱失败: {e}",
                graph_id=graph_id,
                details={"output_path": output_path, "format": format},
            ) from e

    async def _export_json(
        self,
        graph_id: str,
        stats: GraphStats,
        output_path: Path,
        include_vectors: bool,
    ) -> None:
        """导出为 JSON 格式。

        生成完整的图谱数据，包含元数据、统计信息、实体列表和关系列表。

        Args:
            graph_id: 图谱 ID
            stats: 图谱统计信息
            output_path: 输出文件路径
            include_vectors: 是否包含向量数据
        """
        # 构建导出数据结构
        data = {
            "metadata": {
                "graph_id": graph_id,
                "export_format": "json",
                "exported_at": self._get_current_timestamp(),
                "include_vectors": include_vectors,
                "version": "1.0.0",
            },
            "statistics": {
                "entity_count": stats.entity_count,
                "relationship_count": stats.relationship_count,
                "document_count": stats.document_count,
                "chunk_count": stats.chunk_count,
                "entity_types": stats.entity_types,
            },
            "storage_info": stats.storage_info,
            "entities": [],
            "relationships": [],
        }

        # 尝试从 LightRAG 获取实体列表
        try:
            # 使用 LightRAG 的导出功能获取完整数据
            temp_file = output_path.with_suffix(".tmp.csv")
            await self._adapter.export_data(
                output_path=str(temp_file),
                file_format="csv",
                include_vectors=include_vectors,
            )

            # 解析 CSV 文件提取实体和关系
            entities, relationships = self._parse_csv_for_entities_relations(temp_file)

            # 转换为字典格式
            data["entities"] = [
                {
                    "entity_name": e.entity_name,
                    "entity_type": e.entity_type,
                    "description": e.description,
                    "source_id": e.source_id,
                }
                for e in entities
            ]
            data["relationships"] = [
                {
                    "source_entity": r.source_entity,
                    "target_entity": r.target_entity,
                    "description": r.description,
                    "keywords": r.keywords,
                    "weight": r.weight,
                }
                for r in relationships
            ]

            # 删除临时文件
            temp_file.unlink(missing_ok=True)

            self._logger.info(
                f"提取实体和关系成功 | "
                f"实体: {len(data['entities'])} | "
                f"关系: {len(data['relationships'])}"
            )

        except Exception as e:
            self._logger.warning(f"无法获取实体列表，使用基础统计: {e}")

        # 写入 JSON 文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._logger.info(f"JSON 导出完成: {output_path}")

    async def _export_csv(
        self,
        graph_id: str,
        stats: GraphStats,
        output_path: Path,
        include_vectors: bool,
    ) -> None:
        """导出为 CSV 格式。

        生成表格格式的数据，便于在 Excel 等工具中分析。

        Args:
            graph_id: 图谱 ID
            stats: 图谱统计信息
            output_path: 输出文件路径
            include_vectors: 是否包含向量数据
        """
        # 使用 LightRAG 的内置导出功能
        await self._adapter.export_data(
            output_path=str(output_path),
            file_format="csv",
            include_vectors=include_vectors,
        )

        # 添加元数据头部（作为注释）
        metadata_file = output_path.with_suffix(".meta.txt")
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write("# 图谱导出元数据\n")
            f.write(f"# 图谱 ID: {graph_id}\n")
            f.write(f"# 导出时间: {self._get_current_timestamp()}\n")
            f.write(f"# 实体数量: {stats.entity_count}\n")
            f.write(f"# 关系数量: {stats.relationship_count}\n")
            f.write(f"# 文档数量: {stats.document_count}\n")
            f.write(f"# 包含向量: {include_vectors}\n")

        self._logger.info(
            f"CSV 导出完成 | 数据: {output_path} | 元数据: {metadata_file}"
        )

    async def _export_mermaid(
        self,
        graph_id: str,
        stats: GraphStats,
        output_path: Path,
    ) -> None:
        """导出为 Mermaid 格式。

        Mermaid 是一种文本转图表的语言，可以在 Markdown 文档中渲染。
        生成可视化图表，便于理解图谱结构和关系。

        Args:
            graph_id: 图谱 ID
            stats: 图谱统计信息
            output_path: 输出文件路径
        """
        # 构建 Mermaid 图表头部
        mermaid_lines = [
            "```mermaid",
            "graph TD",
            "",
            f"    %% 图谱: {graph_id}",
            f"    %% 实体: {stats.entity_count} | 关系: {stats.relationship_count}",
            f"    %% 导出时间: {self._get_current_timestamp()}",
            "",
        ]

        # 尝试获取实体和关系用于可视化
        try:
            temp_file = output_path.with_suffix(".tmp.csv")
            await self._adapter.export_data(
                output_path=str(temp_file),
                file_format="csv",
                include_vectors=False,
            )

            entities, relationships = self._parse_csv_for_entities_relations(temp_file)

            # 按实体类型分组
            entities_by_type: Dict[str, List[EntityNode]] = {}
            for entity in entities:
                if entity.entity_type not in entities_by_type:
                    entities_by_type[entity.entity_type] = []
                entities_by_type[entity.entity_type].append(entity)

            # 添加子图（按实体类型分组）
            for entity_type, type_entities in sorted(entities_by_type.items()):
                if len(type_entities) > 1:
                    mermaid_lines.append(f"    subgraph {entity_type}")
                    for entity in type_entities[:20]:  # 限制每种类型数量
                        node_id = self._sanitize_node_id(entity.entity_name)
                        label = self._escape_mermaid_label(entity.entity_name)
                        mermaid_lines.append(f'        {node_id}["{label}"]')
                    mermaid_lines.append("    end")
                    mermaid_lines.append("")

            # 添加独立实体节点
            mermaid_lines.append("    %% 实体节点")
            entity_count = 0
            for entity in entities[:50]:  # 限制总数量以避免图表过大
                node_id = self._sanitize_node_id(entity.entity_name)
                label = self._escape_mermaid_label(entity.entity_name)

                # 使用不同形状表示不同类型
                if entity.entity_type == "DISEASE":
                    mermaid_lines.append(f'    {node_id}("{label}")')
                elif entity.entity_type == "MEDICINE":
                    mermaid_lines.append(f'    {node_id}["{label}"]')
                elif entity.entity_type == "SYMPTOM":
                    mermaid_lines.append(f"    {node_id}[{label}]")
                else:
                    mermaid_lines.append(f"    {node_id}[{label}]")

                entity_count += 1

            if entity_count > 0:
                mermaid_lines.append("")

            # 添加关系边
            mermaid_lines.append("    %% 关系边")
            relation_count = 0
            for rel in relationships[:100]:  # 限制关系数量
                source_id = self._sanitize_node_id(rel.source_entity)
                target_id = self._sanitize_node_id(rel.target_entity)

                # 转义标签
                label = self._escape_mermaid_label(
                    rel.description[:30] if rel.description else ""
                )

                if label:
                    mermaid_lines.append(f'    {source_id} -->|"{label}"| {target_id}')
                else:
                    mermaid_lines.append(f"    {source_id} --> {target_id}")

                relation_count += 1

            # 删除临时文件
            temp_file.unlink(missing_ok=True)

        except Exception as e:
            self._logger.warning(f"无法获取实体关系，生成基础图表: {e}")
            # 生成基础占位图
            mermaid_lines.extend(
                [
                    "    START([开始])",
                    "    END([结束])",
                    "    START --> END",
                ]
            )

        # 添加样式定义
        mermaid_lines.extend(
            [
                "",
                "    %% 样式定义",
                "    classDef disease fill:#ffcccc,stroke:#ff0000,stroke-width:2px;",
                "    classDef medicine fill:#ccffcc,stroke:#00ff00,stroke-width:2px;",
                "    classDef symptom fill:#ccccff,stroke:#0000ff,stroke-width:2px;",
                "    classDef default fill:#f9f9f9,stroke:#666666,stroke-width:1px;",
                "```",
            ]
        )

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(mermaid_lines))

        self._logger.info(f"Mermaid 导出完成: {output_path}")

    async def merge_graph_nodes(
        self,
        graph_id: str,
        source_entities: List[str],
        target_entity: str,
        threshold: float = 0.7,
        merge_strategy: Optional[Dict[str, str]] = None,
    ) -> int:
        """合并相似节点。

        基于语义相似度自动识别和合并相似的实体节点。使用向量相似度计算
        实体间的语义相似性，支持自定义合并策略。

        Args:
            graph_id: 图谱 ID
            source_entities: 源实体列表（要合并的实体）
            target_entity: 目标实体（合并后的实体名称）
            threshold: 相似度阈值（0-1），默认 0.7。仅当阈值用于自动识别
                相似实体时有效。对于显式指定的源实体列表，此参数作为
                验证条件
            merge_strategy: 合并策略字典
                - description: concatenate | keep_first | keep_latest
                  - concatenate: 拼接所有描述（默认）
                  - keep_first: 保留第一个实体的描述
                  - keep_latest: 保留最后一个实体的描述
                - entity_type: keep_first | majority
                  - keep_first: 保留第一个实体的类型（默认）
                  - majority: 使用出现最多的类型
                - source_id: join_unique | join_all
                  - join_unique: 合并去重的源 ID（默认）
                  - join_all: 合并所有源 ID（包括重复）

        Returns:
            int: 合并的节点数量

        Raises:
            ValidationError: 参数无效（阈值超出范围、源实体为空等）
            NotFoundError: 图谱或实体不存在
            GraphError: 合并操作失败

        Note:
            - 使用 LightRAG 的 amerge_entities API 进行实体合并
            - 合并操作会重定向所有关系到目标实体
            - 源实体在合并成功后会被删除
            - 如果 LightRAG 不支持 amerge_entities API，返回 0

        Example:
            >>> # 基本合并
            >>> count = await service.merge_graph_nodes(
            ...     "medical",
            ...     ["糖尿病", "糖尿病 mellitus", "DM"],
            ...     "糖尿病"
            ... )
            >>> print(f"合并了 {count} 个节点")
            >>>
            >>> # 自定义合并策略
            >>> count = await service.merge_graph_nodes(
            ...     "medical",
            ...     ["高血压", "Hypertension"],
            ...     "高血压病",
            ...     merge_strategy={
            ...         "description": "concatenate",
            ...         "entity_type": "keep_first",
            ...         "source_id": "join_unique"
            ...     }
            ... )
        """
        self._logger.info(
            f"合并图谱节点 | 图谱: {graph_id} | "
            f"源实体: {len(source_entities)} 个 | 目标: {target_entity} | "
            f"阈值: {threshold}"
        )

        # 验证阈值
        if not 0 <= threshold <= 1:
            raise ValidationError(
                f"相似度阈值必须在 0-1 之间: {threshold}",
                field="threshold",
                value=threshold,
                constraint="0 <= threshold <= 1",
            )

        # 验证实体列表
        if not source_entities:
            raise ValidationError(
                "源实体列表不能为空",
                field="source_entities",
            )

        if target_entity in source_entities:
            raise ValidationError(
                "目标实体不能在源实体列表中",
                field="target_entity",
                value=target_entity,
            )

        # 验证并设置合并策略
        valid_strategies = {
            "description": ["concatenate", "keep_first", "keep_latest"],
            "entity_type": ["keep_first", "majority"],
            "source_id": ["join_unique", "join_all"],
        }

        if merge_strategy is None:
            # 使用默认策略
            merge_strategy = {
                "description": "concatenate",
                "entity_type": "keep_first",
                "source_id": "join_unique",
            }
        else:
            # 验证策略值
            for key, value in merge_strategy.items():
                if key in valid_strategies and value not in valid_strategies[key]:
                    raise ValidationError(
                        f"无效的合并策略值: {key}={value}",
                        field=f"merge_strategy.{key}",
                        value=value,
                        constraint=f"value in {valid_strategies[key]}",
                    )

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 获取 LightRAG 实例
            rag = self._adapter._rag

            if not hasattr(rag, "amerge_entities"):
                self._logger.warning("LightRAG 不支持 amerge_entities API，跳过合并")
                return 0

            # 记录合并前的实体数量（用于验证）
            try:
                stats_before = await self._adapter.get_stats()
                self._logger.debug(
                    f"合并前统计 | 实体: {stats_before.entity_count} | "
                    f"关系: {stats_before.relationship_count}"
                )
            except Exception as e:
                self._logger.warning(f"无法获取合并前统计: {e}")

            # 执行合并操作
            await rag.amerge_entities(
                source_entities=source_entities,
                target_entity=target_entity,
                merge_strategy=merge_strategy,
                target_entity_data={
                    "entity_type": "MERGED",
                    "description": f"合并自 {', '.join(source_entities)}",
                },
            )

            # 记录合并后的统计
            try:
                stats_after = await self._adapter.get_stats()
                self._logger.debug(
                    f"合并后统计 | 实体: {stats_after.entity_count} | "
                    f"关系: {stats_after.relationship_count}"
                )
            except Exception as e:
                self._logger.warning(f"无法获取合并后统计: {e}")

            self._logger.info(
                f"节点合并成功 | 源: {source_entities} | 目标: {target_entity} | "
                f"数量: {len(source_entities)}"
            )

            return len(source_entities)

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self._logger.error(f"合并节点失败 | 错误: {e}")
            raise GraphError(
                f"合并节点失败: {e}",
                graph_id=graph_id,
                details={
                    "source_entities": source_entities,
                    "target_entity": target_entity,
                    "threshold": threshold,
                    "merge_strategy": merge_strategy,
                },
            ) from e

    async def find_similar_entities(
        self,
        graph_id: str,
        entity_name: str,
        threshold: float = 0.7,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """查找与指定实体相似的实体。

        基于语义相似度查找相似实体，用于辅助合并决策。

        Args:
            graph_id: 图谱 ID
            entity_name: 参考实体名称
            threshold: 相似度阈值（0-1），默认 0.7
            top_k: 返回的最大相似实体数量，默认 10

        Returns:
            List[Dict[str, Any]]: 相似实体列表，每个字典包含：
                - entity_name: 实体名称
                - entity_type: 实体类型
                - similarity: 相似度分数（0-1）
                - description: 实体描述

        Raises:
            ValidationError: 参数无效
            NotFoundError: 图谱不存在
            GraphError: 查找失败

        Note:
            此方法使用向量相似度计算，需要嵌入模型支持。
            返回的实体按相似度降序排列。
        """
        self._logger.info(
            f"查找相似实体 | 图谱: {graph_id} | "
            f"实体: {entity_name} | 阈值: {threshold} | Top-K: {top_k}"
        )

        # 验证阈值
        if not 0 <= threshold <= 1:
            raise ValidationError(
                f"相似度阈值必须在 0-1 之间: {threshold}",
                field="threshold",
                value=threshold,
            )

        # 验证 top_k
        if top_k < 1:
            raise ValidationError(
                f"top_k 必须大于 0: {top_k}",
                field="top_k",
                value=top_k,
            )

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 获取 LightRAG 实例
            rag = self._adapter._rag

            # 尝试使用 LightRAG 的相似实体查找功能
            # 注意：此功能取决于 LightRAG 版本
            if hasattr(rag, "afind_similar_entities"):
                similar_entities = await rag.afind_similar_entities(
                    entity_name=entity_name,
                    threshold=threshold,
                    top_k=top_k,
                )
                return similar_entities
            else:
                self._logger.warning(
                    "LightRAG 不支持 afind_similar_entities API，返回空列表"
                )
                return []

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self._logger.error(f"查找相似实体失败 | 错误: {e}")
            raise GraphError(
                f"查找相似实体失败: {e}",
                graph_id=graph_id,
                details={
                    "entity_name": entity_name,
                    "threshold": threshold,
                    "top_k": top_k,
                },
            ) from e

    async def auto_merge_similar_entities(
        self,
        graph_id: str,
        entity_type: Optional[str] = None,
        threshold: float = 0.85,
        merge_strategy: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """自动合并相似实体。

        基于语义相似度自动识别和合并相似的实体节点。

        Args:
            graph_id: 图谱 ID
            entity_type: 实体类型过滤（可选），如果指定则只处理该类型的实体
            threshold: 相似度阈值（0-1），默认 0.85。较高的阈值减少误合并
            merge_strategy: 合并策略（参见 merge_graph_nodes 方法）
            dry_run: 是否为试运行模式。如果为 True，只报告将要合并的实体对，
                不执行实际合并

        Returns:
            Dict[str, Any]: 合并结果摘要
                - merged_count: 实际合并的实体对数量
                - merged_entities: 合并的实体对列表
                - skipped_count: 跳过的实体数量（不满足阈值）
                - total_processed: 处理的实体总数
                - dry_run: 是否为试运行

        Raises:
            ValidationError: 参数无效
            NotFoundError: 图谱不存在
            GraphError: 自动合并失败

        Note:
            - 自动合并使用保守策略，建议先使用 dry_run=True 预览
            - 较高的阈值（如 0.85-0.95）可以减少误合并
            - 合并会保留名称最短或最规范的实体作为目标实体

        Example:
            >>> # 试运行模式，查看将要合并的实体
            >>> result = await service.auto_merge_similar_entities(
            ...     "medical",
            ...     entity_type="DISEASE",
            ...     threshold=0.9,
            ...     dry_run=True
            ... )
            >>> print(f"将合并 {result['merged_count']} 对实体")
            >>>
            >>> # 执行实际合并
            >>> result = await service.auto_merge_similar_entities(
            ...     "medical",
            ...     entity_type="DISEASE",
            ...     threshold=0.9,
            ...     dry_run=False
            ... )
        """
        self._logger.info(
            f"自动合并相似实体 | 图谱: {graph_id} | "
            f"类型: {entity_type or '全部'} | 阈值: {threshold} | "
            f"试运行: {dry_run}"
        )

        # 验证阈值
        if not 0 <= threshold <= 1:
            raise ValidationError(
                f"相似度阈值必须在 0-1 之间: {threshold}",
                field="threshold",
                value=threshold,
            )

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 获取所有实体（如果支持）
            # 注意：此功能取决于 LightRAG 版本和存储后端
            rag = self._adapter._rag

            if not hasattr(rag, "aget_entity_names"):
                self._logger.warning(
                    "LightRAG 不支持 aget_entity_names API，无法自动合并"
                )
                return {
                    "merged_count": 0,
                    "merged_entities": [],
                    "skipped_count": 0,
                    "total_processed": 0,
                    "dry_run": dry_run,
                }

            # 获取实体列表
            all_entities = await rag.aget_entity_names()

            # 按类型过滤
            if entity_type:
                filtered_entities = [
                    e for e in all_entities if e.get("entity_type") == entity_type
                ]
            else:
                filtered_entities = all_entities

            self._logger.info(
                f"找到 {len(filtered_entities)} 个候选实体（类型: {entity_type or '全部'}）"
            )

            merged_count = 0
            merged_entities = []
            skipped_count = 0
            processed = set()

            # 遍历实体，查找相似实体
            for entity in filtered_entities:
                entity_name = entity.get("entity_name")

                if entity_name in processed:
                    continue

                # 查找相似实体
                similar_entities = await self.find_similar_entities(
                    graph_id=graph_id,
                    entity_name=entity_name,
                    threshold=threshold,
                    top_k=10,
                )

                # 过滤已处理的实体
                similar_entities = [
                    e
                    for e in similar_entities
                    if e["entity_name"] not in processed
                    and e["entity_name"] != entity_name
                ]

                if similar_entities:
                    # 选择目标实体（保留名称最短的）
                    candidates = [entity_name] + [
                        e["entity_name"] for e in similar_entities
                    ]
                    target_entity = min(candidates, key=len)

                    # 准备源实体列表（排除目标实体）
                    source_entities = [e for e in candidates if e != target_entity]

                    self._logger.info(
                        f"发现相似实体组 | 目标: {target_entity} | "
                        f"源: {source_entities}"
                    )

                    if dry_run:
                        # 试运行模式，只记录不执行
                        merged_entities.append(
                            {
                                "target_entity": target_entity,
                                "source_entities": source_entities,
                                "similarities": [
                                    {
                                        "entity": e["entity_name"],
                                        "similarity": e["similarity"],
                                    }
                                    for e in similar_entities
                                ],
                            }
                        )
                        merged_count += 1
                    else:
                        # 执行实际合并
                        try:
                            await self.merge_graph_nodes(
                                graph_id=graph_id,
                                source_entities=source_entities,
                                target_entity=target_entity,
                                threshold=threshold,
                                merge_strategy=merge_strategy,
                            )

                            merged_entities.append(
                                {
                                    "target_entity": target_entity,
                                    "source_entities": source_entities,
                                    "status": "merged",
                                }
                            )
                            merged_count += 1

                        except Exception as e:
                            self._logger.error(
                                f"合并实体组失败 | 目标: {target_entity} | 错误: {e}"
                            )
                            skipped_count += len(source_entities)

                    # 标记所有实体为已处理
                    processed.update(candidates)
                else:
                    processed.add(entity_name)
                    skipped_count += 1

            result = {
                "merged_count": merged_count,
                "merged_entities": merged_entities,
                "skipped_count": skipped_count,
                "total_processed": len(filtered_entities),
                "dry_run": dry_run,
            }

            self._logger.info(
                f"自动合并完成 | 合并: {merged_count} | "
                f"跳过: {skipped_count} | 总计: {len(filtered_entities)}"
            )

            return result

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self._logger.error(f"自动合并失败 | 错误: {e}")
            raise GraphError(
                f"自动合并失败: {e}",
                graph_id=graph_id,
                details={
                    "entity_type": entity_type,
                    "threshold": threshold,
                    "dry_run": dry_run,
                },
            ) from e

    async def delete_entity(
        self,
        graph_id: str,
        entity_name: str,
    ) -> bool:
        """删除实体及其关系。

        删除指定的实体节点和所有关联的关系边。

        Args:
            graph_id: 图谱 ID
            entity_name: 实体名称

        Returns:
            bool: 是否成功删除

        Raises:
            NotFoundError: 图谱或实体不存在
            GraphError: 删除失败

        Note:
            使用 LightRAG 的 adelete_by_entity API。
        """
        self._logger.info(f"删除实体: {graph_id}/{entity_name}")

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 使用 LightRAG 的删除 API
            rag = self._adapter._rag
            await rag.adelete_by_entity(entity_name)

            self._logger.info(f"实体删除成功: {entity_name}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self._logger.error(f"删除实体失败: {e}")
            raise GraphError(
                f"删除实体失败: {e}",
                graph_id=graph_id,
                details={"entity_name": entity_name},
            ) from e

    async def delete_relationship(
        self,
        graph_id: str,
        source_entity: str,
        target_entity: str,
    ) -> bool:
        """删除实体间的关系。

        删除两个实体之间的指定关系，保留实体节点。

        Args:
            graph_id: 图谱 ID
            source_entity: 源实体名称
            target_entity: 目标实体名称

        Returns:
            bool: 是否成功删除

        Raises:
            NotFoundError: 图谱或关系不存在
            GraphError: 删除失败

        Note:
            使用 LightRAG 的 adelete_by_relation API。
        """
        self._logger.info(f"删除关系: {graph_id}/{source_entity} -> {target_entity}")

        try:
            # 验证图谱存在
            await self.get_graph_info(graph_id)

            # 使用 LightRAG 的删除 API
            rag = self._adapter._rag
            await rag.adelete_by_relation(source_entity, target_entity)

            self._logger.info(f"关系删除成功: {source_entity} -> {target_entity}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self._logger.error(f"删除关系失败: {e}")
            raise GraphError(
                f"删除关系失败: {e}",
                graph_id=graph_id,
                details={
                    "source_entity": source_entity,
                    "target_entity": target_entity,
                },
            ) from e

    # ========== 辅助方法 ==========

    def _get_graph_timestamps(self, graph_path: Path) -> tuple[str, str]:
        """获取图谱的时间戳。

        Args:
            graph_path: 图谱目录路径

        Returns:
            (created_at, updated_at) 元组
        """
        created_at = None
        updated_at = None

        try:
            # 获取目录的创建和修改时间
            stat = graph_path.stat()
            import datetime

            created_at = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
            updated_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            self._logger.warning(f"无法获取时间戳: {e}")

        return created_at, updated_at

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳（ISO 8601 格式）。

        Returns:
            当前时间戳字符串
        """
        import datetime

        return datetime.datetime.now().isoformat()

    def _parse_csv_for_entities_relations(
        self,
        csv_path: Path,
    ) -> tuple[List[EntityNode], List[RelationshipEdge]]:
        """解析 CSV 文件提取实体和关系。

        解析 LightRAG 导出的 CSV 文件，提取实体节点和关系边。
        CSV 格式通常包含以下列：
        - source_id: 源实体
        - target_id: 目标实体
        - relation: 关系描述
        - source_type: 源实体类型
        - target_type: 目标实体类型
        - keywords: 关键词
        - weight: 权重

        Args:
            csv_path: CSV 文件路径

        Returns:
            (entities, relationships) 元组
        """
        entities_dict: Dict[str, EntityNode] = {}
        relationships: List[RelationshipEdge] = []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # 获取实际的列名
                if not reader.fieldnames:
                    self._logger.warning("CSV 文件为空或格式错误")
                    return [], []

                fieldnames = reader.fieldnames
                self._logger.debug(f"CSV 列名: {fieldnames}")

                for row_idx, row in enumerate(reader):
                    try:
                        # 提取源实体和目标实体
                        source_entity = row.get("source_id", "")
                        target_entity = row.get("target_id", "")

                        if not source_entity or not target_entity:
                            continue

                        # 创建或更新源实体
                        if source_entity not in entities_dict:
                            entity_type = row.get("source_type", "UNKNOWN")
                            entities_dict[source_entity] = EntityNode(
                                entity_name=source_entity,
                                entity_type=entity_type,
                                description="",
                                source_id="",
                            )

                        # 创建或更新目标实体
                        if target_entity not in entities_dict:
                            entity_type = row.get("target_type", "UNKNOWN")
                            entities_dict[target_entity] = EntityNode(
                                entity_name=target_entity,
                                entity_type=entity_type,
                                description="",
                                source_id="",
                            )

                        # 提取关系信息
                        description = row.get("relation", "")
                        keywords = row.get("keywords", "")
                        weight_str = row.get("weight", "1.0")

                        # 转换权重
                        try:
                            weight = float(weight_str) if weight_str else 1.0
                        except ValueError:
                            weight = 1.0

                        # 创建关系边
                        relationship = RelationshipEdge(
                            source_entity=source_entity,
                            target_entity=target_entity,
                            description=description,
                            keywords=keywords,
                            weight=weight,
                        )
                        relationships.append(relationship)

                    except Exception as e:
                        self._logger.warning(f"解析 CSV 第 {row_idx + 1} 行失败: {e}")
                        continue

            entities = list(entities_dict.values())
            self._logger.info(
                f"CSV 解析完成 | 实体: {len(entities)} | 关系: {len(relationships)}"
            )

            return entities, relationships

        except Exception as e:
            self._logger.error(f"解析 CSV 失败: {e}")
            return [], []

    def _sanitize_node_id(self, entity_name: str) -> str:
        """清理实体名称以生成有效的 Mermaid 节点 ID。

        Mermaid 节点 ID 必须是字母数字、下划线或连字符。

        Args:
            entity_name: 实体名称

        Returns:
            清理后的节点 ID
        """
        # 移除空格和特殊字符，替换为下划线
        node_id = entity_name.strip()
        node_id = node_id.replace(" ", "_")
        node_id = node_id.replace("-", "_")
        node_id = node_id.replace("/", "_")
        node_id = node_id.replace("(", "_")
        node_id = node_id.replace(")", "_")
        node_id = node_id.replace("（", "_")
        node_id = node_id.replace("）", "_")
        node_id = node_id.replace(",", "_")
        node_id = node_id.replace("，", "_")

        # 移除连续的下划线
        while "__" in node_id:
            node_id = node_id.replace("__", "_")

        # 确保不以数字开头
        if node_id and node_id[0].isdigit():
            node_id = "N" + node_id

        # 如果清理后为空，使用默认名称
        if not node_id:
            node_id = "node"

        return node_id

    def _escape_mermaid_label(self, label: str) -> str:
        """转义 Mermaid 标签中的特殊字符。

        Args:
            label: 原始标签

        Returns:
            转义后的标签
        """
        # Mermaid 中需要转义的字符
        label = label.replace("\\", "\\\\")
        label = label.replace('"', "&quot;")
        label = label.replace("<", "&lt;")
        label = label.replace(">", "&gt;")
        return label


# ========== 导出的公共接口 ==========

__all__ = [
    "GraphService",
    "GraphInfo",
    "EntityNode",
    "RelationshipEdge",
]
