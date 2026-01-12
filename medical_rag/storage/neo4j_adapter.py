"""
Neo4j 图存储适配器

将 LightRAG 的图存储接口适配到 Neo4j 图数据库。
基于 lightrag.base.BaseGraphStorage 接口实现。
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from lightrag.base import BaseGraphStorage
from lightrag.types import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
from lightrag.utils import logger

# 尝试导入 Neo4j 驱动
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
    from neo4j.exceptions import ServiceUnavailable, AuthError, ClientError
except ImportError:
    raise ImportError(
        "请安装 neo4j 包: pip install neo4j"
    )


# Neo4j 实体标签
BASE_ENTITY_LABEL = "__Entity__"

# Cypher 查询模板
NODE_PROPERTY_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
WITH label AS nodeLabels, collect({property:property, type:type}) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output
"""


@dataclass
class Neo4jGraphStorageAdapter(BaseGraphStorage):
    """
    Neo4j 图存储适配器

    实现 LightRAG BaseGraphStorage 接口,将图操作映射到 Neo4j 数据库。
    """

    def __post_init__(self):
        """初始化 Neo4j 连接配置"""
        # 从全局配置获取 Neo4j 连接参数
        neo4j_config = self.global_config.get("neo4j_config", {})

        self.uri = neo4j_config.get("uri", os.getenv("NEO4J_URI", "bolt://localhost:7687"))
        self.username = neo4j_config.get("username", os.getenv("NEO4J_USERNAME", "neo4j"))
        self.password = neo4j_config.get("password", os.getenv("NEO4J_PASSWORD", "password"))
        self.database = neo4j_config.get("database", os.getenv("NEO4J_DATABASE", "neo4j"))

        # 异步驱动和会话
        self._driver: Optional[AsyncDriver] = None
        self._session: Optional[AsyncSession] = None

        logger.info(f"Neo4j 适配器初始化: uri={self.uri}, database={self.database}, namespace={self.namespace}")

    async def initialize(self):
        """初始化存储连接"""
        try:
            # 创建异步驱动
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )

            # 验证连接
            await self._driver.verify_connectivity()

            # 创建约束以提高性能
            await self._create_constraints()

            logger.info(f"Neo4j 连接成功: namespace={self.namespace}")

        except ServiceUnavailable as e:
            raise ConnectionError(f"无法连接到 Neo4j 数据库: {e}")
        except AuthError as e:
            raise ConnectionError(f"Neo4j 认证失败: {e}")
        except Exception as e:
            logger.error(f"Neo4j 初始化失败: {e}")
            raise

    async def finalize(self):
        """关闭数据库连接"""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j 连接已关闭")

    async def _create_constraints(self):
        """创建唯一性约束以提高性能"""
        try:
            async with self._driver.session(database=self.database) as session:
                # 为基础实体标签创建约束
                await session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{BASE_ENTITY_LABEL}) "
                    "REQUIRE n.id IS UNIQUE"
                )
                logger.debug(f"创建约束: {BASE_ENTITY_LABEL}.id")
        except ClientError as e:
            # 如果约束已存在或 APOC 不可用,记录但不中断
            logger.warning(f"创建约束时出现问题: {e}")

    async def _execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行 Cypher 查询"""
        if parameters is None:
            parameters = {}

        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, parameters)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"查询执行失败: {e}\nQuery: {query}\nParams: {parameters}")
            raise

    async def has_node(self, node_id: str) -> bool:
        """检查节点是否存在"""
        query = f"""
        MATCH (n:{BASE_ENTITY_LABEL} {{id: $node_id}})
        RETURN count(n) > 0 AS exists
        """
        result = await self._execute_query(query, {"node_id": node_id})
        return result[0]["exists"] if result else False

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """检查边是否存在"""
        query = f"""
        MATCH (s:{BASE_ENTITY_LABEL} {{id: $source_id}})-[r]->(t:{BASE_ENTITY_LABEL} {{id: $target_id}})
        RETURN count(r) > 0 AS exists
        """
        result = await self._execute_query(
            query,
            {"source_id": source_node_id, "target_id": target_node_id}
        )
        return result[0]["exists"] if result else False

    async def node_degree(self, node_id: str) -> int:
        """获取节点的度数"""
        query = f"""
        MATCH (n:{BASE_ENTITY_LABEL} {{id: $node_id}})
        RETURN size((n)--()) AS degree
        """
        result = await self._execute_query(query, {"node_id": node_id})
        return result[0]["degree"] if result else 0

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        """获取边的度数(源节点和目标节点的度数之和)"""
        src_degree = await self.node_degree(src_id)
        tgt_degree = await self.node_degree(tgt_id)
        return src_degree + tgt_degree

    async def get_node(self, node_id: str) -> Optional[Dict[str, str]]:
        """获取节点属性"""
        query = f"""
        MATCH (n:{BASE_ENTITY_LABEL} {{id: $node_id}})
        RETURN properties(n) AS props
        """
        result = await self._execute_query(query, {"node_id": node_id})
        if result and result[0]["props"]:
            # 移除内部 id 字段,只返回业务属性
            props = dict(result[0]["props"])
            props.pop("id", None)
            return props
        return None

    async def get_edge(
        self,
        source_node_id: str,
        target_node_id: str
    ) -> Optional[Dict[str, str]]:
        """获取边属性"""
        query = f"""
        MATCH (s:{BASE_ENTITY_LABEL} {{id: $source_id}})-[r]->(t:{BASE_ENTITY_LABEL} {{id: $target_id}})
        RETURN properties(r) AS props, type(r) AS rel_type
        """
        result = await self._execute_query(
            query,
            {"source_id": source_node_id, "target_id": target_node_id}
        )
        if result:
            props = dict(result[0]["props"])
            props["type"] = result[0]["rel_type"]
            return props
        return None

    async def get_node_edges(self, source_node_id: str) -> Optional[List[Tuple[str, str]]]:
        """获取节点的所有边"""
        query = f"""
        MATCH (n:{BASE_ENTITY_LABEL} {{id: $node_id}})-[r]-(m:{BASE_ENTITY_LABEL})
        RETURN n.id AS source, m.id AS target
        """
        result = await self._execute_query(query, {"node_id": source_node_id})
        if result:
            return [(r["source"], r["target"]) for r in result]
        return None

    async def upsert_node(self, node_id: str, node_data: Dict[str, str]) -> None:
        """插入或更新节点"""
        # 准备节点属性
        properties = dict(node_data)
        properties["id"] = node_id

        query = f"""
        MERGE (n:{BASE_ENTITY_LABEL} {{id: $node_id}})
        SET n += $properties
        RETURN n
        """
        await self._execute_query(
            query,
            {"node_id": node_id, "properties": properties}
        )
        logger.debug(f"节点已插入/更新: {node_id}")

    async def upsert_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_data: Dict[str, str]
    ) -> None:
        """插入或更新边"""
        # 确保源节点和目标节点存在
        await self.upsert_node(source_node_id, {})
        await self.upsert_node(target_node_id, {})

        # 获取关系类型
        rel_type = edge_data.get("type", "RELATED_TO").replace(" ", "_").upper()

        # 准备边属性(移除 type 字段)
        properties = {k: v for k, v in edge_data.items() if k != "type"}

        query = f"""
        MATCH (s:{BASE_ENTITY_LABEL} {{id: $source_id}})
        MATCH (t:{BASE_ENTITY_LABEL} {{id: $target_id}})
        MERGE (s)-[r:{rel_type}]->(t)
        SET r += $properties
        RETURN r
        """
        await self._execute_query(
            query,
            {
                "source_id": source_node_id,
                "target_id": target_node_id,
                "properties": properties
            }
        )
        logger.debug(f"边已插入/更新: {source_node_id} -> {target_node_id}")

    async def delete_node(self, node_id: str) -> None:
        """删除节点及其所有关系"""
        query = f"""
        MATCH (n:{BASE_ENTITY_LABEL} {{id: $node_id}})
        DETACH DELETE n
        """
        await self._execute_query(query, {"node_id": node_id})
        logger.debug(f"节点已删除: {node_id}")

    async def remove_nodes(self, nodes: List[str]) -> None:
        """批量删除节点"""
        if not nodes:
            return

        query = f"""
        UNWIND $node_ids AS node_id
        MATCH (n:{BASE_ENTITY_LABEL} {{id: node_id}})
        DETACH DELETE n
        """
        await self._execute_query(query, {"node_ids": nodes})
        logger.debug(f"批量删除节点: {len(nodes)} 个")

    async def remove_edges(self, edges: List[Tuple[str, str]]) -> None:
        """批量删除边"""
        if not edges:
            return

        # 转换为字典列表
        edge_list = [{"source": src, "target": tgt} for src, tgt in edges]

        query = f"""
        UNWIND $edges AS edge
        MATCH (s:{BASE_ENTITY_LABEL} {{id: edge.source}})-[r]->(t:{BASE_ENTITY_LABEL} {{id: edge.target}})
        DELETE r
        """
        await self._execute_query(query, {"edges": edge_list})
        logger.debug(f"批量删除边: {len(edges)} 条")

    async def get_all_labels(self) -> List[str]:
        """获取所有节点标签"""
        query = """
        CALL db.labels()
        YIELD label
        WHERE label <> $base_label
        RETURN label
        ORDER BY label
        """
        result = await self._execute_query(query, {"base_label": BASE_ENTITY_LABEL})
        return [r["label"] for r in result]

    async def get_knowledge_graph(
        self,
        node_label: str,
        max_depth: int = 3,
        max_nodes: int = 1000
    ) -> KnowledgeGraph:
        """获取知识图谱子图"""
        # 如果标签为 *, 获取所有节点
        if node_label == "*":
            query = f"""
            MATCH (n:{BASE_ENTITY_LABEL})
            WITH n LIMIT $max_nodes
            OPTIONAL MATCH (n)-[r]->(m:{BASE_ENTITY_LABEL})
            RETURN n, r, m
            """
            params = {"max_nodes": max_nodes}
        else:
            # 获取包含指定标签的子图
            query = f"""
            MATCH path = (n:{BASE_ENTITY_LABEL})-[*1..{max_depth}]-(m:{BASE_ENTITY_LABEL})
            WHERE n.id CONTAINS $label OR n.entity_name CONTAINS $label
            WITH nodes(path) AS nodes, relationships(path) AS rels
            LIMIT $max_nodes
            UNWIND nodes AS n
            UNWIND rels AS r
            RETURN DISTINCT n, r, endNode(r) AS m
            """
            params = {"label": node_label, "max_nodes": max_nodes}

        result = await self._execute_query(query, params)

        # 构建知识图谱
        nodes_dict = {}
        edges_list = []

        for record in result:
            # 处理节点
            if record.get("n"):
                node_data = dict(record["n"])
                node_id = node_data.get("id")
                if node_id and node_id not in nodes_dict:
                    nodes_dict[node_id] = KnowledgeGraphNode(
                        id=node_id,
                        label=node_data.get("entity_name", node_id),
                        properties=node_data
                    )

            # 处理边
            if record.get("r") and record.get("m"):
                edge_data = dict(record["r"])
                target_data = dict(record["m"])
                target_id = target_data.get("id")

                if target_id and target_id not in nodes_dict:
                    nodes_dict[target_id] = KnowledgeGraphNode(
                        id=target_id,
                        label=target_data.get("entity_name", target_id),
                        properties=target_data
                    )

                source_id = node_data.get("id")
                if source_id and target_id:
                    edges_list.append(KnowledgeGraphEdge(
                        source=source_id,
                        target=target_id,
                        label=edge_data.get("type", "RELATED_TO"),
                        properties=edge_data
                    ))

        return KnowledgeGraph(
            nodes=list(nodes_dict.values()),
            edges=edges_list
        )

    async def index_done_callback(self) -> None:
        """索引完成回调 - Neo4j 自动持久化,无需额外操作"""
        logger.debug(f"索引完成: namespace={self.namespace}")

    async def drop(self) -> Dict[str, str]:
        """删除所有数据"""
        try:
            query = f"""
            MATCH (n:{BASE_ENTITY_LABEL})
            DETACH DELETE n
            """
            await self._execute_query(query)
            logger.info(f"已删除所有数据: namespace={self.namespace}")
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            return {"status": "error", "message": str(e)}

    # 批量操作优化方法

    async def get_nodes_batch(self, node_ids: List[str]) -> Dict[str, Dict]:
        """批量获取节点"""
        if not node_ids:
            return {}

        query = f"""
        UNWIND $node_ids AS node_id
        MATCH (n:{BASE_ENTITY_LABEL} {{id: node_id}})
        RETURN n.id AS id, properties(n) AS props
        """
        result = await self._execute_query(query, {"node_ids": node_ids})

        nodes = {}
        for r in result:
            node_id = r["id"]
            props = dict(r["props"])
            props.pop("id", None)
            nodes[node_id] = props

        return nodes

    async def node_degrees_batch(self, node_ids: List[str]) -> Dict[str, int]:
        """批量获取节点度数"""
        if not node_ids:
            return {}

        query = f"""
        UNWIND $node_ids AS node_id
        MATCH (n:{BASE_ENTITY_LABEL} {{id: node_id}})
        RETURN n.id AS id, size((n)--()) AS degree
        """
        result = await self._execute_query(query, {"node_ids": node_ids})

        return {r["id"]: r["degree"] for r in result}

    async def edge_degrees_batch(
        self,
        edge_pairs: List[Tuple[str, str]]
    ) -> Dict[Tuple[str, str], int]:
        """批量获取边度数"""
        if not edge_pairs:
            return {}

        # 先获取所有涉及的节点的度数
        all_node_ids = set()
        for src, tgt in edge_pairs:
            all_node_ids.add(src)
            all_node_ids.add(tgt)

        node_degrees = await self.node_degrees_batch(list(all_node_ids))

        # 计算每条边的度数
        edge_degrees = {}
        for src, tgt in edge_pairs:
            degree = node_degrees.get(src, 0) + node_degrees.get(tgt, 0)
            edge_degrees[(src, tgt)] = degree

        return edge_degrees

    async def get_edges_batch(
        self,
        pairs: List[Dict[str, str]]
    ) -> Dict[Tuple[str, str], Dict]:
        """批量获取边"""
        if not pairs:
            return {}

        query = f"""
        UNWIND $pairs AS pair
        MATCH (s:{BASE_ENTITY_LABEL} {{id: pair.src}})-[r]->(t:{BASE_ENTITY_LABEL} {{id: pair.tgt}})
        RETURN pair.src AS src, pair.tgt AS tgt, properties(r) AS props, type(r) AS rel_type
        """
        result = await self._execute_query(query, {"pairs": pairs})

        edges = {}
        for r in result:
            src = r["src"]
            tgt = r["tgt"]
            props = dict(r["props"])
            props["type"] = r["rel_type"]
            edges[(src, tgt)] = props

        return edges

    async def get_nodes_edges_batch(
        self,
        node_ids: List[str]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """批量获取节点的边"""
        if not node_ids:
            return {}

        query = f"""
        UNWIND $node_ids AS node_id
        MATCH (n:{BASE_ENTITY_LABEL} {{id: node_id}})-[r]-(m:{BASE_ENTITY_LABEL})
        RETURN n.id AS source, m.id AS target
        """
        result = await self._execute_query(query, {"node_ids": node_ids})

        # 组织结果
        node_edges = {node_id: [] for node_id in node_ids}
        for r in result:
            source = r["source"]
            target = r["target"]
            if source in node_edges:
                node_edges[source].append((source, target))

        return node_edges
