"""
Storage Factory - 存储工厂类

此模块实现了存储适配器的工厂模式，用于根据配置创建和管理存储实例。
支持：
1. 图存储（Neo4j）和向量存储（Milvus）的创建
2. 单例模式和连接池管理
3. 异步初始化和健康检查
4. 配置验证和错误处理
5. 优雅关闭和资源清理
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .neo4j_adapter import Neo4jGraphStorageAdapter
from .milvus_adapter import MilvusVectorStorageAdapter

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """存储类型枚举"""
    GRAPH = "graph"
    VECTOR = "vector"


class StorageStatus(Enum):
    """存储状态枚举"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class StorageInstance:
    """
    存储实例包装类

    封装存储实例及其状态信息。
    """
    instance: Any
    storage_type: StorageType
    status: StorageStatus = StorageStatus.NOT_INITIALIZED
    error: Optional[Exception] = None
    config: Dict[str, Any] = field(default_factory=dict)

    async def initialize(self) -> bool:
        """
        初始化存储实例

        Returns:
            初始化是否成功
        """
        if self.status == StorageStatus.READY:
            return True

        try:
            self.status = StorageStatus.INITIALIZING
            logger.info(f"正在初始化 {self.storage_type.value} 存储...")

            if hasattr(self.instance, 'initialize'):
                await self.instance.initialize()

            self.status = StorageStatus.READY
            self.error = None
            logger.info(f"{self.storage_type.value} 存储初始化成功")
            return True

        except Exception as e:
            self.status = StorageStatus.ERROR
            self.error = e
            logger.error(f"{self.storage_type.value} 存储初始化失败: {e}")
            return False

    async def health_check(self) -> bool:
        """
        检查存储实例健康状态

        Returns:
            是否健康
        """
        if self.status != StorageStatus.READY:
            return False

        try:
            # Neo4j 健康检查
            if self.storage_type == StorageType.GRAPH:
                if hasattr(self.instance, '_driver') and self.instance._driver:
                    await self.instance._driver.verify_connectivity()
                    return True
                return False

            # Milvus 健康检查
            elif self.storage_type == StorageType.VECTOR:
                if hasattr(self.instance, '_client') and self.instance._client:
                    # 简单检查客户端是否存在
                    return True
                return False

            return False

        except Exception as e:
            logger.warning(f"{self.storage_type.value} 健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭存储实例并释放资源"""
        try:
            if hasattr(self.instance, 'finalize'):
                await self.instance.finalize()
            self.status = StorageStatus.CLOSED
            logger.info(f"{self.storage_type.value} 存储已关闭")
        except Exception as e:
            logger.error(f"关闭 {self.storage_type.value} 存储时出错: {e}")


class StorageFactory:
    """
    存储工厂类

    负责创建和管理存储适配器实例，支持单例模式和连接池管理。
    """

    # 类变量，用于单例模式
    _instances: Dict[str, StorageInstance] = {}
    _lock = asyncio.Lock()

    def __init__(self):
        """初始化工厂"""
        self._namespace: Optional[str] = None

    @classmethod
    async def create_graph_storage(
        cls,
        config: Dict[str, Any],
        namespace: str = "default"
    ) -> Neo4jGraphStorageAdapter:
        """
        创建 Neo4j 图存储适配器

        Args:
            config: 配置字典，应包含 neo4j_config
            namespace: 命名空间，用于多租户隔离

        Returns:
            Neo4j 图存储适配器实例

        Raises:
            ValueError: 配置验证失败
            ConnectionError: 连接失败
        """
        # 验证配置
        neo4j_config = config.get("neo4j_config", {})
        if not neo4j_config.get("uri"):
            raise ValueError("Neo4j URI 未配置")

        # 构建全局配置
        global_config = {
            "neo4j_config": neo4j_config,
        }

        # 创建实例键
        instance_key = f"graph_{namespace}"

        # 检查是否已存在
        if instance_key in cls._instances:
            instance_wrapper = cls._instances[instance_key]
            if instance_wrapper.status == StorageStatus.READY:
                logger.info(f"返回已存在的 Neo4j 图存储实例: {namespace}")
                return instance_wrapper.instance
            elif instance_wrapper.status == StorageStatus.ERROR:
                logger.warning(f"重新初始化错误状态的 Neo4j 图存储实例: {namespace}")
                del cls._instances[instance_key]

        # 创建新实例
        try:
            adapter = Neo4jGraphStorageAdapter(
                namespace=namespace,
                global_config=global_config,
                embedding_func=config.get("embedding_func"),
            )

            # 包装实例
            instance_wrapper = StorageInstance(
                instance=adapter,
                storage_type=StorageType.GRAPH,
                config=global_config
            )

            # 初始化
            success = await instance_wrapper.initialize()
            if not success:
                raise instance_wrapper.error or Exception("初始化失败")

            # 缓存实例
            cls._instances[instance_key] = instance_wrapper

            logger.info(f"Neo4j 图存储实例创建成功: {namespace}")
            return adapter

        except Exception as e:
            logger.error(f"创建 Neo4j 图存储失败: {e}")
            raise ConnectionError(f"无法创建 Neo4j 图存储: {e}")

    @classmethod
    async def create_vector_storage(
        cls,
        config: Dict[str, Any],
        namespace: str = "default",
        embedding_func: Optional[Any] = None
    ) -> MilvusVectorStorageAdapter:
        """
        创建 Milvus 向量存储适配器

        Args:
            config: 配置字典，应包含 milvus_config
            namespace: 命名空间
            embedding_func: 嵌入函数

        Returns:
            Milvus 向量存储适配器实例

        Raises:
            ValueError: 配置验证失败
            ConnectionError: 连接失败
        """
        # 验证配置
        milvus_config = config.get("milvus_config", {})
        if not milvus_config.get("host"):
            raise ValueError("Milvus host 未配置")

        # 验证嵌入函数
        if not embedding_func:
            embedding_func = config.get("embedding_func")
        if not embedding_func:
            raise ValueError("embedding_func 未配置")

        # 构建全局配置
        global_config = {
            "milvus_config": milvus_config,
            "vector_db_storage_cls_kwargs": {
                "cosine_better_than_threshold": config.get(
                    "cosine_better_than_threshold", 0.2
                )
            },
            "embedding_batch_num": config.get("embedding_batch_num", 32),
        }

        # 创建实例键
        instance_key = f"vector_{namespace}"

        # 检查是否已存在
        if instance_key in cls._instances:
            instance_wrapper = cls._instances[instance_key]
            if instance_wrapper.status == StorageStatus.READY:
                logger.info(f"返回已存在的 Milvus 向量存储实例: {namespace}")
                return instance_wrapper.instance
            elif instance_wrapper.status == StorageStatus.ERROR:
                logger.warning(f"重新初始化错误状态的 Milvus 向量存储实例: {namespace}")
                del cls._instances[instance_key]

        # 创建新实例
        try:
            adapter = MilvusVectorStorageAdapter(
                namespace=namespace,
                global_config=global_config,
                embedding_func=embedding_func,
            )

            # 包装实例
            instance_wrapper = StorageInstance(
                instance=adapter,
                storage_type=StorageType.VECTOR,
                config=global_config
            )

            # 初始化
            success = await instance_wrapper.initialize()
            if not success:
                raise instance_wrapper.error or Exception("初始化失败")

            # 缓存实例
            cls._instances[instance_key] = instance_wrapper

            logger.info(f"Milvus 向量存储实例创建成功: {namespace}")
            return adapter

        except Exception as e:
            logger.error(f"创建 Milvus 向量存储失败: {e}")
            raise ConnectionError(f"无法创建 Milvus 向量存储: {e}")

    @classmethod
    async def create_all_storages(
        cls,
        config: Dict[str, Any],
        namespace: str = "default",
        embedding_func: Optional[Any] = None
    ) -> Tuple[Neo4jGraphStorageAdapter, MilvusVectorStorageAdapter]:
        """
        同时创建所有存储适配器

        Args:
            config: 完整配置字典
            namespace: 命名空间
            embedding_func: 嵌入函数

        Returns:
            (图存储, 向量存储) 元组

        Raises:
            Exception: 任一存储创建失败
        """
        logger.info(f"正在创建所有存储实例: {namespace}")

        # 并发创建存储
        graph_storage_task = cls.create_graph_storage(config, namespace)
        vector_storage_task = cls.create_vector_storage(
            config, namespace, embedding_func
        )

        try:
            graph_storage, vector_storage = await asyncio.gather(
                graph_storage_task,
                vector_storage_task,
                return_exceptions=True
            )

            # 检查是否有错误
            if isinstance(graph_storage, Exception):
                raise graph_storage
            if isinstance(vector_storage, Exception):
                raise vector_storage

            logger.info(f"所有存储实例创建成功: {namespace}")
            return graph_storage, vector_storage

        except Exception as e:
            logger.error(f"创建存储实例失败: {e}")
            # 清理已创建的实例
            await cls.close_storage(namespace, StorageType.GRAPH)
            await cls.close_storage(namespace, StorageType.VECTOR)
            raise

    @classmethod
    async def get_storage(
        cls,
        storage_type: StorageType,
        namespace: str = "default"
    ) -> Optional[Any]:
        """
        获取已创建的存储实例

        Args:
            storage_type: 存储类型
            namespace: 命名空间

        Returns:
            存储实例，如果不存在则返回 None
        """
        instance_key = f"{storage_type.value}_{namespace}"
        instance_wrapper = cls._instances.get(instance_key)

        if instance_wrapper and instance_wrapper.status == StorageStatus.READY:
            return instance_wrapper.instance

        return None

    @classmethod
    async def health_check_all(cls) -> Dict[str, bool]:
        """
        检查所有存储实例的健康状态

        Returns:
            {instance_key: is_healthy} 字典
        """
        results = {}

        for key, instance_wrapper in cls._instances.items():
            is_healthy = await instance_wrapper.health_check()
            results[key] = is_healthy

        return results

    @classmethod
    async def close_storage(
        cls,
        namespace: str,
        storage_type: Optional[StorageType] = None
    ) -> None:
        """
        关闭指定的存储实例

        Args:
            namespace: 命名空间
            storage_type: 存储类型，如果为 None 则关闭该命名空间的所有存储
        """
        if storage_type:
            instance_key = f"{storage_type.value}_{namespace}"
            if instance_key in cls._instances:
                await cls._instances[instance_key].close()
                del cls._instances[instance_key]
        else:
            # 关闭该命名空间的所有存储
            keys_to_close = [
                key for key in cls._instances.keys()
                if key.endswith(f"_{namespace}")
            ]
            for key in keys_to_close:
                await cls._instances[key].close()
                del cls._instances[key]

    @classmethod
    async def close_all(cls) -> None:
        """关闭所有存储实例"""
        logger.info("正在关闭所有存储实例...")

        # 并发关闭所有实例
        close_tasks = [
            instance_wrapper.close()
            for instance_wrapper in cls._instances.values()
        ]

        await asyncio.gather(*close_tasks, return_exceptions=True)

        cls._instances.clear()
        logger.info("所有存储实例已关闭")

    @classmethod
    def get_instance_count(cls) -> Dict[str, int]:
        """
        获取实例统计信息

        Returns:
            按类型统计的实例数量
        """
        stats = {
            "graph": 0,
            "vector": 0,
            "total": len(cls._instances)
        }

        for key in cls._instances.keys():
            if key.startswith("graph_"):
                stats["graph"] += 1
            elif key.startswith("vector_"):
                stats["vector"] += 1

        return stats

    @classmethod
    async def validate_config(cls, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            (是否有效, 错误列表) 元组
        """
        errors = []

        # 验证 Neo4j 配置
        neo4j_config = config.get("neo4j_config", {})
        if not neo4j_config.get("uri"):
            errors.append("Neo4j URI 未配置")
        else:
            uri = neo4j_config["uri"]
            if not uri.startswith(('bolt://', 'neo4j://', 'bolt+s://', 'neo4j+s://')):
                errors.append(f"无效的 Neo4j URI: {uri}")

        # 验证 Milvus 配置
        milvus_config = config.get("milvus_config", {})
        if not milvus_config.get("host"):
            errors.append("Milvus host 未配置")

        port = milvus_config.get("port")
        if port and not (1 <= port <= 65535):
            errors.append(f"无效的 Milvus 端口: {port}")

        # 验证嵌入函数
        if not config.get("embedding_func"):
            errors.append("embedding_func 未配置")

        return len(errors) == 0, errors


# 便捷函数
async def create_graph_storage(
    config: Dict[str, Any],
    namespace: str = "default"
) -> Neo4jGraphStorageAdapter:
    """便捷函数：创建图存储"""
    return await StorageFactory.create_graph_storage(config, namespace)


async def create_vector_storage(
    config: Dict[str, Any],
    namespace: str = "default",
    embedding_func: Optional[Any] = None
) -> MilvusVectorStorageAdapter:
    """便捷函数：创建向量存储"""
    return await StorageFactory.create_vector_storage(config, namespace, embedding_func)


async def create_all_storages(
    config: Dict[str, Any],
    namespace: str = "default",
    embedding_func: Optional[Any] = None
) -> Tuple[Neo4jGraphStorageAdapter, MilvusVectorStorageAdapter]:
    """便捷函数：创建所有存储"""
    return await StorageFactory.create_all_storages(config, namespace, embedding_func)
