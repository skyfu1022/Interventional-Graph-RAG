"""
Milvus Vector Storage Adapter - Milvus 向量存储适配器

此模块实现了向量存储接口，将向量存储操作适配到 Milvus。
复用现有的 camel/storages/vectordb_storages/milvus.py 接口。
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from hashlib import md5
from typing import Any, Dict, List, Optional

import numpy as np

from camel.storages.vectordb_storages import VectorRecord, MilvusStorage

logger = logging.getLogger(__name__)


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """
    计算内容的 MD5 哈希 ID

    Args:
        content: 要哈希的内容
        prefix: ID 前缀

    Returns:
        带前缀的哈希 ID
    """
    return prefix + md5(content.encode()).hexdigest()


@dataclass
class MilvusVectorStorageAdapter:
    """
    Milvus 向量存储适配器

    实现向量存储接口，使用 Milvus 作为后端存储。
    复用 CAMEL 框架中已有的 MilvusStorage 实现。

    Attributes:
        namespace: 存储命名空间（用于区分不同的集合）
        global_config: 全局配置字典
        embedding_func: 嵌入函数（可调用对象）
        cosine_better_than_threshold: 余弦相似度阈值
        meta_fields: 元数据字段集合
    """

    # 需要在 __post_init__ 之前定义的属性
    namespace: str
    global_config: Dict[str, Any]
    embedding_func: Any
    cosine_better_than_threshold: float = 0.2
    meta_fields: Optional[set] = None

    def __post_init__(self):
        """初始化 Milvus 客户端和相关配置"""
        # 初始化基础属性
        self._client: Optional[MilvusStorage] = None

        # 设置 meta_fields 默认值
        if self.meta_fields is None:
            self.meta_fields = set()

        # 从全局配置中获取参数
        kwargs = self.global_config.get("vector_db_storage_cls_kwargs", {})

        # 设置余弦相似度阈值
        cosine_threshold = kwargs.get("cosine_better_than_threshold")
        if cosine_threshold is None:
            # 使用默认值
            self.cosine_better_than_threshold = 0.2
            logger.warning(
                f"cosine_better_than_threshold not specified, using default: "
                f"{self.cosine_better_than_threshold}"
            )
        else:
            self.cosine_better_than_threshold = cosine_threshold

        # 获取 Milvus 连接配置
        milvus_config = self.global_config.get("milvus_config", {})
        host = milvus_config.get("host", os.getenv("MILVUS_HOST", "localhost"))
        port = milvus_config.get("port", int(os.getenv("MILVUS_PORT", "19530")))
        token = milvus_config.get("token", os.getenv("MILVUS_TOKEN", ""))

        # 构建 URL 和 API key
        url = f"{host}:{port}"
        api_key = token if token else ""

        # 集合名称（使用命名空间区分）
        collection_name = f"{self.namespace}_{milvus_config.get('collection_name', 'vectors')}"

        # 获取向量维度
        vector_dim = self.embedding_func.embedding_dim

        # 批处理大小
        self._max_batch_size = self.global_config.get("embedding_batch_num", 32)

        # 创建 MilvusStorage 客户端
        try:
            self._client = MilvusStorage(
                vector_dim=vector_dim,
                url_and_api_key=(url, api_key),
                collection_name=collection_name,
            )
            logger.info(
                f"Milvus adapter initialized: collection={collection_name}, "
                f"dim={vector_dim}, url={url}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Milvus client: {e}")
            raise

    async def initialize(self):
        """初始化存储"""
        # Milvus 在 __post_init__ 中已经初始化，这里可以执行额外的设置
        try:
            if self._client:
                # 加载集合到内存（如果使用云服务）
                self._client.load()
                logger.info(f"Milvus collection loaded: {self._client.collection_name}")
        except Exception as e:
            logger.warning(f"Failed to load Milvus collection: {e}")

    async def finalize(self):
        """清理存储资源"""
        # Milvus 客户端不需要显式关闭
        logger.info(f"Milvus adapter finalized for namespace: {self.namespace}")

    async def upsert(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        插入或更新向量数据

        Args:
            data: 字典，键为向量ID，值为包含 'content' 和其他元数据的字典
        """
        logger.debug(f"Upserting {len(data)} vectors to {self.namespace}")
        if not data:
            return

        try:
            current_time = int(time.time())

            # 准备数据列表
            list_data = [
                {
                    "__id__": k,
                    "__created_at__": current_time,
                    **{k1: v1 for k1, v1 in v.items() if k1 in self.meta_fields},
                }
                for k, v in data.items()
            ]

            # 提取内容用于嵌入
            contents = [v["content"] for v in data.values()]

            # 分批进行嵌入（避免单次请求过大）
            batches = [
                contents[i : i + self._max_batch_size]
                for i in range(0, len(contents), self._max_batch_size)
            ]

            # 并发执行嵌入
            embedding_tasks = [self.embedding_func(batch) for batch in batches]
            embeddings_list = await asyncio.gather(*embedding_tasks)

            # 合并嵌入结果
            embeddings = np.concatenate(embeddings_list)

            if len(embeddings) != len(list_data):
                logger.error(
                    f"Embedding count mismatch: {len(embeddings)} != {len(list_data)}"
                )
                return

            # 转换为 VectorRecord 格式
            records = []
            for i, d in enumerate(list_data):
                # 构建 payload（元数据）
                payload = {k: v for k, v in d.items() if k not in ["__id__", "__vector__"]}

                record = VectorRecord(
                    id=d["__id__"],
                    vector=embeddings[i].tolist(),
                    payload=payload
                )
                records.append(record)

            # 批量插入到 Milvus
            self._client.add(records)

            logger.debug(
                f"Successfully upserted {len(records)} vectors to {self.namespace}"
            )

        except Exception as e:
            logger.error(f"Error upserting vectors to {self.namespace}: {e}")
            raise

    async def query(
        self, query: str, top_k: int, ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        查询相似向量

        Args:
            query: 查询文本
            top_k: 返回的最相似结果数量
            ids: 可选的ID过滤列表（当前实现不支持）

        Returns:
            相似向量结果列表
        """
        try:
            # 生成查询嵌入（高优先级）
            embedding = await self.embedding_func([query], _priority=5)
            query_vector = embedding[0].tolist()

            # 执行向量搜索
            from camel.storages.vectordb_storages import VectorDBQuery

            db_query = VectorDBQuery(
                query_vector=query_vector,
                top_k=top_k
            )

            search_results = self._client.query(db_query)

            # 转换结果格式以匹配 LightRAG 期望的格式
            results = []
            for result in search_results:
                # 过滤低于阈值的结果
                if result.similarity < self.cosine_better_than_threshold:
                    continue

                # 构建结果字典
                result_dict = {
                    "id": result.id,
                    "distance": result.similarity,
                    "__metrics__": result.similarity,
                    "__id__": result.id,
                }

                # 添加 payload 中的字段
                if result.payload:
                    result_dict.update(result.payload)

                results.append(result_dict)

            logger.debug(
                f"Query returned {len(results)} results for namespace {self.namespace}"
            )
            return results

        except Exception as e:
            logger.error(f"Error querying vectors from {self.namespace}: {e}")
            raise

    async def delete(self, ids: List[str]) -> None:
        """
        删除指定ID的向量

        Args:
            ids: 要删除的向量ID列表
        """
        try:
            if not ids:
                return

            self._client.delete(ids)
            logger.debug(
                f"Successfully deleted {len(ids)} vectors from {self.namespace}"
            )

        except Exception as e:
            logger.error(f"Error deleting vectors from {self.namespace}: {e}")
            raise

    async def delete_entity(self, entity_name: str) -> None:
        """
        删除实体向量

        Args:
            entity_name: 实体名称
        """
        try:
            # 计算实体ID
            entity_id = compute_mdhash_id(entity_name, prefix="ent-")
            logger.debug(
                f"Attempting to delete entity {entity_name} with ID {entity_id}"
            )

            # 检查实体是否存在
            existing = await self.get_by_id(entity_id)
            if existing:
                await self.delete([entity_id])
                logger.debug(f"Successfully deleted entity {entity_name}")
            else:
                logger.debug(f"Entity {entity_name} not found in storage")

        except Exception as e:
            logger.error(f"Error deleting entity {entity_name}: {e}")
            raise

    async def delete_entity_relation(self, entity_name: str) -> None:
        """
        删除与实体相关的所有关系

        Args:
            entity_name: 实体名称
        """
        try:
            # 注意：由于 Milvus 不直接支持基于字段的复杂查询删除，
            # 这里需要先查询再删除
            # 这是一个简化实现，可能需要根据实际的元数据结构调整

            logger.warning(
                f"delete_entity_relation for {entity_name}: "
                "Milvus implementation requires custom metadata query logic"
            )

            # TODO: 实现基于元数据的关系查询和删除
            # 由于 MilvusStorage 的当前接口限制，这需要额外的实现

        except Exception as e:
            logger.error(f"Error deleting relations for {entity_name}: {e}")
            raise

    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取向量数据

        Args:
            id: 向量ID

        Returns:
            向量数据字典，如果不存在则返回 None
        """
        try:
            # 注意：当前 MilvusStorage 实现没有直接的 get_by_id 方法
            # 这里使用查询方法的变通实现
            # 如果需要精确的 ID 查询，可能需要扩展 MilvusStorage

            # 临时实现：返回 None（需要后续优化）
            logger.warning(
                f"get_by_id({id}): Direct ID lookup not implemented in current "
                "MilvusStorage, returning None"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting vector by ID {id}: {e}")
            return None

    async def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        根据ID列表获取多个向量数据

        Args:
            ids: 向量ID列表

        Returns:
            向量数据字典列表
        """
        try:
            if not ids:
                return []

            # 并发获取多个ID的数据
            tasks = [self.get_by_id(id) for id in ids]
            results = await asyncio.gather(*tasks)

            # 过滤掉 None 结果
            return [r for r in results if r is not None]

        except Exception as e:
            logger.error(f"Error getting vectors by IDs: {e}")
            return []

    async def index_done_callback(self) -> bool:
        """
        索引完成回调

        Milvus 是实时数据库，不需要显式的持久化操作。

        Returns:
            True 表示成功
        """
        try:
            logger.debug(f"Index done callback for {self.namespace}")
            # Milvus 自动持久化，无需额外操作
            return True
        except Exception as e:
            logger.error(f"Error in index_done_callback for {self.namespace}: {e}")
            return False

    async def drop(self) -> Dict[str, str]:
        """
        删除所有向量数据并清理资源

        Returns:
            操作状态字典
        """
        try:
            # 清空 Milvus 集合
            self._client.clear()

            logger.info(
                f"Successfully dropped all data from {self.namespace} "
                f"(collection: {self._client.collection_name})"
            )
            return {"status": "success", "message": "data dropped"}

        except Exception as e:
            logger.error(f"Error dropping {self.namespace}: {e}")
            return {"status": "error", "message": str(e)}
