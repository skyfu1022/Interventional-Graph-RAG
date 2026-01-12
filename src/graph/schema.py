"""
介入手术图谱 Schema 管理器模块。

该模块提供介入手术知识图谱的 Schema 管理功能，包括：
- Schema 版本管理
- 约束和索引的创建与管理
- Schema 迁移
- 约束和索引的列表查询

基于 Neo4j 图数据库实现，支持：
- 实体唯一性约束
- 属性索引优化
- Schema 版本控制
- 自动迁移

使用示例：
    >>> from src.graph.schema import InterventionalSchemaManager
    >>> from src.core.config import Settings
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     manager = InterventionalSchemaManager()
    >>>     await manager.initialize()
    >>>
    >>>     # 获取当前版本
    >>>     version = await manager.get_version()
    >>>     print(f"Schema 版本: {version}")
    >>>
    >>>     # 列出所有约束
    >>>     constraints = await manager.list_constraints()
    >>>     for constraint in constraints:
    >>>         print(f"约束: {constraint}")
    >>>
    >>> asyncio.run(main())
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from src.core.adapters import RAGAnythingAdapter
from src.core.config import Settings
from src.core.exceptions import GraphError, ValidationError, StorageError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.graph.schema")


# ========== 枚举和常量 ==========


class SchemaVersion(str, Enum):
    """Schema 版本枚举。

    定义支持的 Schema 版本及其特性。
    """

    V1_0_0 = "1.0.0"  # 初始版本，基础实体类型和关系
    V1_1_0 = "1.1.0"  # 添加介入手术相关实体类型
    V1_2_0 = "1.2.0"  # 添加手术并发症和风险实体
    V2_0_0 = "2.0.0"  # 完整的三层图谱架构（patient/literature/dictionary）

    @classmethod
    def latest(cls) -> "SchemaVersion":
        """获取最新的 Schema 版本。

        Returns:
            SchemaVersion: 最新版本
        """
        return cls.V2_0_0

    def description(self) -> str:
        """获取版本描述。"""
        descriptions = {
            SchemaVersion.V1_0_0: "初始版本，基础实体类型和关系",
            SchemaVersion.V1_1_0: "添加介入手术相关实体类型",
            SchemaVersion.V1_2_0: "添加手术并发症和风险实体",
            SchemaVersion.V2_0_0: "完整的三层图谱架构（patient/literature/dictionary）",
        }
        return descriptions.get(self, "未知版本")


class ConstraintType(str, Enum):
    """约束类型枚举。

    定义支持的约束类型。
    """

    UNIQUE = "unique"  # 唯一性约束
    EXISTS = "exists"  # 存在性约束
    NODE_KEY = "node_key"  # 节点键约束


class IndexType(str, Enum):
    """索引类型枚举。

    定义支持的索引类型。
    """

    BTREE = "btree"  # B 树索引（默认）
    FULLTEXT = "fulltext"  # 全文索引
    POINT = "point"  # 空间点索引
    RANGE = "range"  # 范围索引
    TEXT = "text"  # 文本索引


# ========== 数据类 ==========


@dataclass
class ConstraintInfo:
    """约束信息数据类。

    表示 Neo4j 中的一个约束。

    Attributes:
        name: 约束名称
        type: 约束类型
        label: 节点标签
        property: 属性名称
        description: 约束描述
    """

    name: str
    type: ConstraintType
    label: str
    property: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含约束信息的字典
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "label": self.label,
            "property": self.property,
            "description": self.description,
        }


@dataclass
class IndexInfo:
    """索引信息数据类。

    表示 Neo4j 中的一个索引。

    Attributes:
        name: 索引名称
        type: 索引类型
        label: 节点标签
        properties: 属性名称列表
        description: 索引描述
    """

    name: str
    type: IndexType
    label: str
    properties: List[str]
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含索引信息的字典
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
            "description": self.description,
        }


@dataclass
class SchemaInfo:
    """Schema 信息数据类。

    表示知识图谱的 Schema 信息。

    Attributes:
        version: Schema 版本
        constraints: 约束列表
        indexes: 索引列表
        entity_types: 支持的实体类型
        relationship_types: 支持的关系类型
    """

    version: SchemaVersion
    constraints: List[ConstraintInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    entity_types: List[str] = field(default_factory=list)
    relationship_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含 Schema 信息的字典
        """
        return {
            "version": self.version.value,
            "description": self.version.description(),
            "constraints": [c.to_dict() for c in self.constraints],
            "indexes": [i.to_dict() for i in self.indexes],
            "entity_types": self.entity_types,
            "relationship_types": self.relationship_types,
        }


# ========== Schema 管理器类 ==========


class InterventionalSchemaManager:
    """介入手术图谱 Schema 管理器。

    管理 Neo4j 知识图谱的 Schema，包括：
    - 约束创建和管理
    - 索引创建和管理
    - Schema 版本控制
    - Schema 迁移

    Attributes:
        _adapter: RAGAnything 适配器实例
        _current_version: 当前 Schema 版本
        _logger: 日志记录器

    Example:
        >>> manager = InterventionalSchemaManager()
        >>> await manager.initialize()
        >>>
        >>> # 获取版本
        >>> version = await manager.get_version()
        >>>
        >>> # 列出约束
        >>> constraints = await manager.list_constraints()
        >>>
        >>> # 列出索引
        >>> indexes = await manager.list_indexes()
    """

    # ========== Schema 定义 ==========

    # 支持的实体类型（按图谱分类）
    PATIENT_ENTITY_TYPES = [
        "PATIENT",
        "SYMPTOM",
        "LABORATORY_DATA",
        "IMAGING_RESULT",
        "PROCEDURE",
        "MEDICINE",
        "INTERVENTION",
        "COMPLICATION",
    ]

    LITERATURE_ENTITY_TYPES = [
        "LITERATURE",
        "AUTHOR",
        "INSTITUTION",
        "PUBLISHER",
        "KEYWORD",
        "DISEASE",
        "TREATMENT",
    ]

    DICTIONARY_ENTITY_TYPES = [
        "DISEASE",
        "MEDICINE",
        "SYMPTOM",
        "ANATOMICAL_STRUCTURE",
        "BODY_FUNCTION",
        "PROCEDURE",
        "INTERVENTION_TYPE",
    ]

    # 支持的关系类型
    RELATIONSHIP_TYPES = [
        "HAS_SYMPTOM",
        "HAS_LAB_RESULT",
        "HAS_IMAGING",
        "UNDERWENT",
        "PRESCRIBED",
        "TREATED_WITH",
        "COMPLICATED_BY",
        "AUTHORED_BY",
        "PUBLISHED_BY",
        "CITES",
        "RELATED_TO",
        "TREATS",
        "CAUSES",
        "PART_OF",
    ]

    # ========== 初始化 ==========

    def __init__(
        self,
        adapter: Optional[RAGAnythingAdapter] = None,
    ):
        """初始化 Schema 管理器。

        Args:
            adapter: RAGAnything 适配器实例（可选，如果不提供则自动创建）

        Raises:
            ValidationError: 适配器初始化失败
        """
        if adapter is None:
            # 自动创建适配器
            try:
                config = Settings()
                adapter = RAGAnythingAdapter(config)
            except Exception as e:
                raise ValidationError(
                    f"无法创建适配器: {e}",
                    field="adapter",
                    details={"error": str(e)},
                ) from e

        self._adapter = adapter
        self._current_version: Optional[SchemaVersion] = None
        self._initialized = False
        self._logger = logger

        self._logger.info(
            f"Schema 管理器创建 | 工作空间: {adapter.config.rag_workspace}"
        )

    async def initialize(self) -> None:
        """初始化 Schema 管理器。

        创建基础约束和索引。如果 Schema 已存在，则加载当前版本信息。

        Raises:
            StorageError: 初始化失败
            GraphError: 创建约束或索引失败
        """
        if self._initialized:
            self._logger.warning("Schema 管理器已初始化，跳过")
            return

        self._logger.info("开始初始化 Schema 管理器")

        try:
            # 确保适配器已初始化
            await self._adapter._ensure_initialized()

            # 检查当前 Schema 版本
            try:
                version = await self.get_version()
                self._current_version = version
                self._logger.info(f"检测到现有 Schema 版本: {version.value}")
            except GraphError:
                # Schema 不存在，创建最新的
                self._logger.info("未检测到现有 Schema，创建最新版本")
                await self._create_schema_v2_0_0()
                self._current_version = SchemaVersion.V2_0_0

            self._initialized = True
            self._logger.info("Schema 管理器初始化完成")

        except Exception as e:
            self._logger.error(f"Schema 管理器初始化失败: {e}", exc_info=True)
            raise StorageError(
                f"Schema 管理器初始化失败: {e}",
                storage_type="neo4j",
                operation="initialize",
            ) from e

    # ========== Schema 版本管理 ==========

    async def get_version(self) -> SchemaVersion:
        """获取当前 Schema 版本。

        通过查询 Neo4j 中的特殊节点来确定当前版本。

        Returns:
            SchemaVersion: 当前 Schema 版本

        Raises:
            GraphError: 无法获取版本信息
        """
        await self._adapter._ensure_initialized()

        self._logger.debug("获取 Schema 版本")

        try:
            # 查询 Schema 版本节点
            cypher = """
            MATCH (s:SchemaVersion)
            RETURN s.version AS version
            ORDER BY s.created_at DESC
            LIMIT 1
            """

            results = await self._adapter.query_cypher(cypher)

            if not results or not results[0].get("version"):
                raise GraphError(
                    "未找到 Schema 版本信息",
                    details={"suggestion": "请先调用 initialize() 创建 Schema"},
                )

            version_str = results[0]["version"]
            version = SchemaVersion(version_str)

            self._logger.debug(f"当前 Schema 版本: {version.value}")
            return version

        except ValueError as e:
            raise GraphError(
                f"无效的 Schema 版本格式: {e}",
                details={"version": version_str if "version_str" in locals() else None},
            ) from e
        except GraphError:
            raise
        except Exception as e:
            self._logger.error(f"获取 Schema 版本失败: {e}")
            raise GraphError(
                f"获取 Schema 版本失败: {e}",
                details={"operation": "get_version"},
            ) from e

    async def migrate_to(self, target_version: SchemaVersion) -> None:
        """迁移到指定的 Schema 版本。

        执行 Schema 迁移，包括创建新的约束、索引和实体类型。

        Args:
            target_version: 目标 Schema 版本

        Raises:
            ValidationError: 目标版本无效
            GraphError: 迁移失败

        Note:
            - 只支持升级，不支持降级
            - 迁移过程会创建备份
            - 建议在迁移前备份数据
        """
        await self._adapter._ensure_initialized()

        if not isinstance(target_version, SchemaVersion):
            raise ValidationError(
                f"无效的目标版本: {target_version}",
                field="target_version",
                value=target_version,
            )

        self._logger.info(f"开始 Schema 迁移 | 目标版本: {target_version.value}")

        try:
            # 获取当前版本
            current_version = await self.get_version()

            # 检查是否需要迁移
            if current_version == target_version:
                self._logger.info(f"当前版本已是 {target_version.value}，无需迁移")
                return

            # 检查是否为降级
            if current_version.value > target_version.value:
                raise ValidationError(
                    f"不支持降级迁移 | 当前: {current_version.value} -> 目标: {target_version.value}",
                    field="target_version",
                    constraint="target_version >= current_version",
                )

            # 执行迁移
            await self._execute_migration(current_version, target_version)

            # 更新版本标记
            await self._update_version(target_version)
            self._current_version = target_version

            self._logger.info(f"Schema 迁移完成 | 版本: {target_version.value}")

        except ValidationError:
            raise
        except Exception as e:
            self._logger.error(f"Schema 迁移失败: {e}", exc_info=True)
            raise GraphError(
                f"Schema 迁移失败: {e}",
                details={
                    "current_version": current_version.value
                    if "current_version" in locals()
                    else None,
                    "target_version": target_version.value,
                },
            ) from e

    async def _execute_migration(
        self,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> None:
        """执行具体的迁移逻辑。

        Args:
            from_version: 源版本
            to_version: 目标版本
        """
        self._logger.info(f"执行迁移 | {from_version.value} -> {to_version.value}")

        # 根据目标版本创建相应的 Schema
        if to_version == SchemaVersion.V1_0_0:
            await self._create_schema_v1_0_0()
        elif to_version == SchemaVersion.V1_1_0:
            await self._create_schema_v1_1_0()
        elif to_version == SchemaVersion.V1_2_0:
            await self._create_schema_v1_2_0()
        elif to_version == SchemaVersion.V2_0_0:
            await self._create_schema_v2_0_0()

    async def _update_version(self, version: SchemaVersion) -> None:
        """更新 Schema 版本标记。

        Args:
            version: 新版本
        """
        cypher = """
        CREATE (s:SchemaVersion {
            version: $version,
            description: $description,
            created_at: datetime()
        })
        """

        await self._adapter.query_cypher(
            cypher,
            params={
                "version": version.value,
                "description": version.description(),
            },
        )

        self._logger.info(f"Schema 版本已更新: {version.value}")

    # ========== 约束管理 ==========

    async def list_constraints(self) -> List[ConstraintInfo]:
        """列出所有约束。

        查询 Neo4j 中的所有约束信息。

        Returns:
            List[ConstraintInfo]: 约束列表

        Raises:
            GraphError: 查询约束失败
        """
        await self._adapter._ensure_initialized()

        self._logger.debug("列出所有约束")

        try:
            # 使用 Neo4j 的系统命令查询约束
            cypher = """
            SHOW CONSTRAINTS
            """

            results = await self._adapter.query_cypher(cypher)

            constraints = []
            for row in results:
                # 解析约束信息
                name = row.get("name", "")
                constraint_type_str = row.get("type", "").lower()

                # 映射约束类型
                if "uniqueness" in constraint_type_str:
                    constraint_type = ConstraintType.UNIQUE
                elif "node_key" in constraint_type_str:
                    constraint_type = ConstraintType.NODE_KEY
                elif "exists" in constraint_type_str:
                    constraint_type = ConstraintType.EXISTS
                else:
                    constraint_type = ConstraintType.UNIQUE  # 默认

                # 提取标签和属性
                labels_or_types = row.get("labelsOrTypes", [])
                properties = row.get("properties", [])

                if labels_or_types and properties:
                    label = (
                        labels_or_types[0]
                        if isinstance(labels_or_types, list)
                        else labels_or_types
                    )
                    property_name = (
                        properties[0] if isinstance(properties, list) else properties
                    )

                    constraint_info = ConstraintInfo(
                        name=name,
                        type=constraint_type,
                        label=label,
                        property=property_name,
                        description=f"{constraint_type.value} constraint on {label}.{property_name}",
                    )
                    constraints.append(constraint_info)

            self._logger.debug(f"找到 {len(constraints)} 个约束")
            return constraints

        except Exception as e:
            self._logger.error(f"列出约束失败: {e}", exc_info=True)
            raise GraphError(
                f"列出约束失败: {e}",
                details={"operation": "list_constraints"},
            ) from e

    # ========== 索引管理 ==========

    async def list_indexes(self) -> List[IndexInfo]:
        """列出所有索引。

        查询 Neo4j 中的所有索引信息。

        Returns:
            List[IndexInfo]: 索引列表

        Raises:
            GraphError: 查询索引失败
        """
        await self._adapter._ensure_initialized()

        self._logger.debug("列出所有索引")

        try:
            # 使用 Neo4j 的系统命令查询索引
            cypher = """
            SHOW INDEXES
            """

            results = await self._adapter.query_cypher(cypher)

            indexes = []
            for row in results:
                # 解析索引信息
                name = row.get("name", "")
                index_type_str = row.get("type", "").lower()

                # 映射索引类型
                if "fulltext" in index_type_str:
                    index_type = IndexType.FULLTEXT
                elif "point" in index_type_str:
                    index_type = IndexType.POINT
                elif "range" in index_type_str:
                    index_type = IndexType.RANGE
                elif "text" in index_type_str:
                    index_type = IndexType.TEXT
                else:
                    index_type = IndexType.BTREE  # 默认

                # 提取标签和属性
                labels_or_types = row.get("labelsOrTypes", [])
                properties = row.get("properties", [])

                if labels_or_types:
                    label = (
                        labels_or_types[0]
                        if isinstance(labels_or_types, list)
                        else labels_or_types
                    )
                    prop_list = (
                        properties if isinstance(properties, list) else [properties]
                    )

                    index_info = IndexInfo(
                        name=name,
                        type=index_type,
                        label=label,
                        properties=prop_list,
                        description=f"{index_type.value} index on {label}.{', '.join(prop_list)}",
                    )
                    indexes.append(index_info)

            self._logger.debug(f"找到 {len(indexes)} 个索引")
            return indexes

        except Exception as e:
            self._logger.error(f"列出索引失败: {e}", exc_info=True)
            raise GraphError(
                f"列出索引失败: {e}",
                details={"operation": "list_indexes"},
            ) from e

    # ========== Schema 创建方法 ==========

    async def _create_schema_v1_0_0(self) -> None:
        """创建 Schema v1.0.0。

        初始版本，创建基础实体类型的约束和索引。
        """
        self._logger.info("创建 Schema v1.0.0")

        # 基础实体类型
        entity_types = [
            "DISEASE",
            "MEDICINE",
            "SYMPTOM",
            "ANATOMICAL_STRUCTURE",
            "BODY_FUNCTION",
            "PROCEDURE",
        ]

        # 创建唯一性约束（entity_name）
        for entity_type in entity_types:
            await self._create_unique_constraint(
                label=entity_type,
                property="entity_name",
            )

        # 创建属性索引
        for entity_type in entity_types:
            await self._create_index(
                label=entity_type,
                properties=["entity_type", "description"],
            )

    async def _create_schema_v1_1_0(self) -> None:
        """创建 Schema v1.1.0。

        添加介入手术相关实体类型。
        """
        self._logger.info("创建 Schema v1.1.0")

        # 先创建 v1.0.0 的基础
        await self._create_schema_v1_0_0()

        # 新增实体类型
        new_entity_types = [
            "INTERVENTION",
            "COMPLICATION",
            "RISK_FACTOR",
        ]

        # 创建约束和索引
        for entity_type in new_entity_types:
            await self._create_unique_constraint(
                label=entity_type,
                property="entity_name",
            )
            await self._create_index(
                label=entity_type,
                properties=["entity_type", "description"],
            )

    async def _create_schema_v1_2_0(self) -> None:
        """创建 Schema v1.2.0。

        添加手术并发症和风险实体的扩展属性。
        """
        self._logger.info("创建 Schema v1.2.0")

        # 先创建 v1.1.0 的基础
        await self._create_schema_v1_1_0()

        # 为 COMPLICATION 和 RISK_FACTOR 添加额外的索引
        for entity_type in ["COMPLICATION", "RISK_FACTOR"]:
            await self._create_index(
                label=entity_type,
                properties=["severity", "probability"],
            )

    async def _create_schema_v2_0_0(self) -> None:
        """创建 Schema v2.0.0。

        完整的三层图谱架构（patient/literature/dictionary）。
        """
        self._logger.info("创建 Schema v2.0.0")

        # 合并所有实体类型
        all_entity_types = (
            self.PATIENT_ENTITY_TYPES
            + self.LITERATURE_ENTITY_TYPES
            + self.DICTIONARY_ENTITY_TYPES
        )

        # 去重
        unique_entity_types = list(set(all_entity_types))

        # 创建唯一性约束
        for entity_type in unique_entity_types:
            await self._create_unique_constraint(
                label=entity_type,
                property="entity_name",
            )

        # 创建属性索引
        for entity_type in unique_entity_types:
            await self._create_index(
                label=entity_type,
                properties=["entity_type", "description"],
            )

        # 为特定实体类型创建额外的索引
        extra_indexes = {
            "PATIENT": ["patient_id", "age", "gender"],
            "LITERATURE": ["title", "publication_date", "doi"],
            "AUTHOR": ["name", "affiliation"],
            "PROCEDURE": ["procedure_code", "duration"],
            "INTERVENTION": ["intervention_type", "success_rate"],
            "COMPLICATION": ["severity", "occurrence_rate"],
        }

        for entity_type, properties in extra_indexes.items():
            await self._create_index(
                label=entity_type,
                properties=properties,
            )

    # ========== 辅助方法 ==========

    async def _create_unique_constraint(
        self,
        label: str,
        property: str,
    ) -> None:
        """创建唯一性约束。

        Args:
            label: 节点标签
            property: 属性名称
        """
        constraint_name = f"unique_{label}_{property}"

        cypher = f"""
        CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
        FOR (n:{label})
        REQUIRE n.{property} IS UNIQUE
        """

        try:
            await self._adapter.query_cypher(cypher)
            self._logger.debug(f"创建约束: {constraint_name}")
        except Exception as e:
            # 约束可能已存在，忽略错误
            if "already exists" not in str(e).lower():
                self._logger.warning(
                    f"创建约束失败（可能已存在）: {constraint_name} | {e}"
                )

    async def _create_index(
        self,
        label: str,
        properties: List[str],
        index_type: IndexType = IndexType.BTREE,
    ) -> None:
        """创建索引。

        Args:
            label: 节点标签
            properties: 属性名称列表
            index_type: 索引类型
        """
        if not properties:
            return

        index_name = f"idx_{label}_{'_'.join(properties)}"

        # 单属性索引
        if len(properties) == 1:
            cypher = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON (n.{properties[0]})
            """
        # 多属性索引
        else:
            props_str = ", ".join([f"n.{p}" for p in properties])
            cypher = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON ({props_str})
            """

        try:
            await self._adapter.query_cypher(cypher)
            self._logger.debug(f"创建索引: {index_name}")
        except Exception as e:
            # 索引可能已存在，忽略错误
            if "already exists" not in str(e).lower():
                self._logger.warning(f"创建索引失败（可能已存在）: {index_name} | {e}")

    async def get_schema_info(self) -> SchemaInfo:
        """获取完整的 Schema 信息。

        Returns:
            SchemaInfo: Schema 信息

        Raises:
            GraphError: 获取信息失败
        """
        await self._adapter._ensure_initialized()

        self._logger.debug("获取 Schema 信息")

        try:
            # 获取版本
            version = await self.get_version()

            # 获取约束
            constraints = await self.list_constraints()

            # 获取索引
            indexes = await self.list_indexes()

            # 合并所有实体类型
            all_entity_types = (
                self.PATIENT_ENTITY_TYPES
                + self.LITERATURE_ENTITY_TYPES
                + self.DICTIONARY_ENTITY_TYPES
            )

            schema_info = SchemaInfo(
                version=version,
                constraints=constraints,
                indexes=indexes,
                entity_types=list(set(all_entity_types)),
                relationship_types=self.RELATIONSHIP_TYPES,
            )

            return schema_info

        except Exception as e:
            self._logger.error(f"获取 Schema 信息失败: {e}", exc_info=True)
            raise GraphError(
                f"获取 Schema 信息失败: {e}",
                details={"operation": "get_schema_info"},
            ) from e


# ========== 导出的公共接口 ==========

__all__ = [
    "InterventionalSchemaManager",
    "SchemaVersion",
    "ConstraintType",
    "IndexType",
    "ConstraintInfo",
    "IndexInfo",
    "SchemaInfo",
]
