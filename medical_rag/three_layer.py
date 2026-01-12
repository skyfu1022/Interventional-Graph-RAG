"""
Three Layer Architecture - 三层架构实现

此模块实现医疗知识图谱的三层层次化架构：
1. 顶层（Top Layer）：私有数据层 - 用户个人数据、笔记等
2. 中层（Middle Layer）：书籍和论文层 - 公开的医学书籍、论文等
3. 底层（Bottom Layer）：字典数据层 - 医学字典、术语表等基础数据

每一层都是独立的 LightRAG 实例，通过 namespace 实现数据隔离。
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

from lightrag import LightRAG, QueryParam

from .config import MedicalRAGConfig


logger = logging.getLogger(__name__)


# 全局变量用于延迟导入和缓存
_openai_complete_func = None
_openai_embedding_func = None


@dataclass
class LayerConfig:
    """层级配置"""

    name: str
    """层级名称"""

    description: str
    """层级描述"""

    priority: int
    """查询优先级（数字越小优先级越高）"""

    namespace: str
    """命名空间前缀，用于数据隔离"""

    working_dir: str
    """工作目录"""

    enabled: bool = True
    """是否启用此层级"""


@dataclass
class LayerQueryResult:
    """层级查询结果"""

    layer_name: str
    """层级名称"""

    result: str
    """查询结果"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """元数据"""

    score: float = 0.0
    """相似度分数"""

    sources: List[str] = field(default_factory=list)
    """来源文档列表"""


class ThreeLayerGraph:
    """
    三层层次化图谱结构

    在 LightRAG 之上实现三层架构，每一层都是独立的 LightRAG 实例。
    支持跨层查询、层级管理和数据隔离。
    """

    # 默认层级配置
    DEFAULT_LAYERS = {
        "top": LayerConfig(
            name="top",
            description="私有数据层 - 用户个人数据、笔记等",
            priority=1,
            namespace="private",
            working_dir="./rag_storage/top_layer"
        ),
        "middle": LayerConfig(
            name="middle",
            description="书籍和论文层 - 公开的医学书籍、论文等",
            priority=2,
            namespace="books_papers",
            working_dir="./rag_storage/middle_layer"
        ),
        "bottom": LayerConfig(
            name="bottom",
            description="字典数据层 - 医学字典、术语表等基础数据",
            priority=3,
            namespace="dictionary",
            working_dir="./rag_storage/bottom_layer"
        )
    }

    def __init__(
        self,
        config: Optional[MedicalRAGConfig] = None,
        layer_configs: Optional[Dict[str, LayerConfig]] = None,
        llm_model_func: Optional[Any] = None,
        embedding_func: Optional[Any] = None
    ):
        """
        初始化三层图谱

        Args:
            config: MedicalRAG 配置对象
            layer_configs: 自定义层级配置（可选，默认使用 DEFAULT_LAYERS）
            llm_model_func: LLM 模型函数
            embedding_func: 嵌入函数
        """
        self.config = config or MedicalRAGConfig()
        self.layer_configs = layer_configs or self.DEFAULT_LAYERS.copy()

        # 初始化 LLM 和嵌入函数
        self.llm_model_func = llm_model_func or self._default_llm_func()
        self.embedding_func = embedding_func or self._default_embedding_func()

        # 存储三层 LightRAG 实例
        self.layers: Dict[str, LightRAG] = {}

        # 存储层级状态
        self.layer_stats: Dict[str, Dict[str, Any]] = {}

        # 初始化三层
        self._initialized = False

    def _default_llm_func(self):
        """获取默认 LLM 函数"""
        global _openai_complete_func
        if _openai_complete_func is None:
            try:
                from lightrag.llm import openai_complete_if_cache
                _openai_complete_func = openai_complete_if_cache
            except (ImportError, TypeError) as e:
                logger.warning(f"无法导入默认 LLM 函数: {e}")
                _openai_complete_func = None
        return _openai_complete_func

    def _default_embedding_func(self):
        """获取默认嵌入函数"""
        global _openai_embedding_func
        if _openai_embedding_func is None:
            try:
                from lightrag.llm import openai_embedding
                _openai_embedding_func = openai_embedding
            except (ImportError, TypeError) as e:
                logger.warning(f"无法导入默认嵌入函数: {e}")
                _openai_embedding_func = None
        return _openai_embedding_func

    async def initialize(self):
        """
        初始化三层图谱

        创建三层独立的 LightRAG 实例，每层使用不同的 namespace 和工作目录。
        """
        if self._initialized:
            logger.warning("ThreeLayerGraph 已经初始化，跳过")
            return

        logger.info("开始初始化三层图谱...")

        # 获取 LightRAG 初始化参数
        lightrag_kwargs = self.config.to_lightrag_kwargs()

        # 为每一层创建独立的 LightRAG 实例
        for layer_key, layer_config in self.layer_configs.items():
            if not layer_config.enabled:
                logger.info(f"跳过禁用的层级: {layer_key}")
                continue

            try:
                # 创建层级特定的工作目录
                working_dir = Path(layer_config.working_dir)
                working_dir.mkdir(parents=True, exist_ok=True)

                logger.info(
                    f"初始化 {layer_config.name} 层: "
                    f"namespace={layer_config.namespace}, "
                    f"working_dir={working_dir}"
                )

                # 创建 LightRAG 实例
                rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=self.llm_model_func,
                    embedding_func=self.embedding_func,
                    # 使用 namespace 实现数据隔离
                    namespace_prefix=layer_config.namespace,
                    # 其他配置参数
                    chunk_token_size=lightrag_kwargs.get("chunk_token_size", 1200),
                    chunk_overlap_token_size=lightrag_kwargs.get("chunk_overlap_token_size", 100),
                    tiktoken_model_name=lightrag_kwargs.get("tiktoken_model_name", "gpt-4o"),
                    max_token_size=lightrag_kwargs.get("max_token_size", 8192),
                    enable_llm_cache=lightrag_kwargs.get("enable_llm_cache", True),
                    # 自动管理存储状态
                    auto_manage_storages_states=True,
                )

                # 初始化存储
                await rag.initialize_storages()

                # 存储实例
                self.layers[layer_key] = rag

                # 初始化层级统计
                self.layer_stats[layer_key] = {
                    "config": layer_config,
                    "document_count": 0,
                    "entity_count": 0,
                    "query_count": 0,
                    "status": "initialized"
                }

                logger.info(f"{layer_config.name} 层初始化完成")

            except Exception as e:
                logger.error(f"初始化 {layer_config.name} 层失败: {e}")
                raise

        self._initialized = True
        logger.info(f"三层图谱初始化完成，共初始化 {len(self.layers)} 层")

    async def finalize(self):
        """清理三层图谱资源"""
        logger.info("开始清理三层图谱资源...")

        for layer_key, rag in self.layers.items():
            try:
                await rag.finalize_storages()
                logger.info(f"{layer_key} 层资源清理完成")
            except Exception as e:
                logger.error(f"清理 {layer_key} 层资源失败: {e}")

        self.layers.clear()
        self._initialized = False

        logger.info("三层图谱资源清理完成")

    def _ensure_initialized(self):
        """确保三层图谱已初始化"""
        if not self._initialized:
            raise RuntimeError(
                "ThreeLayerGraph 未初始化，请先调用 await initialize()"
            )

    # ==================== 阶段 4.1: 三层图谱结构 ====================

    def get_layer(self, layer_name: str) -> Optional[LightRAG]:
        """
        获取指定层级的 LightRAG 实例

        Args:
            layer_name: 层级名称（top, middle, bottom）

        Returns:
            LightRAG 实例，如果层级不存在则返回 None
        """
        self._ensure_initialized()
        return self.layers.get(layer_name)

    def list_layers(self) -> List[str]:
        """
        列出所有可用的层级

        Returns:
            层级名称列表
        """
        self._ensure_initialized()
        return list(self.layers.keys())

    def get_layer_config(self, layer_name: str) -> Optional[LayerConfig]:
        """
        获取指定层级的配置

        Args:
            layer_name: 层级名称

        Returns:
            层级配置，如果层级不存在则返回 None
        """
        return self.layer_configs.get(layer_name)

    # ==================== 阶段 4.2: 跨层查询 ====================

    async def query_all_layers(
        self,
        query: str,
        mode: str = "hybrid",
        only_layers: Optional[List[str]] = None,
        top_k: int = 5,
        merge_results: bool = True
    ) -> Union[List[LayerQueryResult], str]:
        """
        跨层查询 - 同时查询所有层级并合并结果

        Args:
            query: 查询字符串
            mode: 查询模式（local, global, hybrid, naive）
            only_layers: 只查询指定的层级（可选）
            top_k: 每层返回的结果数量
            merge_results: 是否合并结果（True 返回合并的字符串，False 返回分层结果列表）

        Returns:
            如果 merge_results=True，返回合并后的查询结果字符串
            如果 merge_results=False，返回分层查询结果列表
        """
        self._ensure_initialized()

        # 确定要查询的层级
        layers_to_query = only_layers if only_layers else self.list_layers()

        # 按优先级排序
        sorted_layers = sorted(
            layers_to_query,
            key=lambda x: self.layer_configs[x].priority if x in self.layer_configs else 999
        )

        logger.info(
            f"开始跨层查询: query='{query}', mode={mode}, "
            f"layers={sorted_layers}, merge={merge_results}"
        )

        # 并发查询所有层级
        query_tasks = []
        for layer_key in sorted_layers:
            if layer_key in self.layers:
                task = self._query_single_layer(
                    layer_key=layer_key,
                    query=query,
                    mode=mode
                )
                query_tasks.append(task)

        # 等待所有查询完成
        layer_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for result in layer_results:
            if isinstance(result, Exception):
                logger.error(f"层级查询失败: {result}")
            elif result is not None:
                valid_results.append(result)

        # 更新查询统计
        for result in valid_results:
            layer_name = result.layer_name
            if layer_name in self.layer_stats:
                self.layer_stats[layer_name]["query_count"] += 1

        logger.info(
            f"跨层查询完成: 成功查询 {len(valid_results)} 层"
        )

        # 根据参数决定返回格式
        if merge_results:
            return self._merge_query_results(valid_results, query)
        else:
            return valid_results

    async def _query_single_layer(
        self,
        layer_key: str,
        query: str,
        mode: str
    ) -> Optional[LayerQueryResult]:
        """
        查询单个层级

        Args:
            layer_key: 层级键名
            query: 查询字符串
            mode: 查询模式

        Returns:
            层级查询结果
        """
        if layer_key not in self.layers:
            logger.warning(f"层级不存在: {layer_key}")
            return None

        rag = self.layers[layer_key]
        layer_config = self.layer_configs[layer_key]

        try:
            # 执行查询
            param = QueryParam(mode=mode, only_need_context=False)
            result = await rag.aquery(query, param=param)

            # 构建结果对象
            layer_result = LayerQueryResult(
                layer_name=layer_config.name,
                result=result,
                metadata={
                    "layer_key": layer_key,
                    "layer_description": layer_config.description,
                    "priority": layer_config.priority,
                    "namespace": layer_config.namespace
                },
                score=0.0,  # LightRAG 目前不直接返回分数
                sources=[]  # 可以后续从结果中提取来源
            )

            logger.info(
                f"{layer_config.name} 层查询成功: "
                f"result_length={len(result)}"
            )

            return layer_result

        except Exception as e:
            logger.error(f"{layer_config.name} 层查询失败: {e}")
            return None

    def _merge_query_results(
        self,
        results: List[LayerQueryResult],
        original_query: str
    ) -> str:
        """
        合并多层级查询结果

        Args:
            results: 分层查询结果列表
            original_query: 原始查询字符串

        Returns:
            合并后的结果字符串
        """
        if not results:
            return "未找到相关结果"

        # 按优先级排序结果
        sorted_results = sorted(
            results,
            key=lambda x: x.metadata.get("priority", 999)
        )

        # 构建合并结果
        merged_parts = []

        # 添加标题
        merged_parts.append(f"# 跨层查询结果\n")
        merged_parts.append(f"**查询**: {original_query}\n")
        merged_parts.append(f"**查询层级数**: {len(results)}\n\n")

        # 添加各层级结果
        for i, result in enumerate(sorted_results, 1):
            layer_name = result.metadata.get("layer_description", result.layer_name)
            merged_parts.append(f"## 层级 {i}: {layer_name}\n\n")
            merged_parts.append(f"{result.result}\n\n")

        # 合并
        merged_result = "".join(merged_parts)

        logger.info(f"结果合并完成: total_length={len(merged_result)}")

        return merged_result

    async def query_by_priority(
        self,
        query: str,
        mode: str = "hybrid",
        stop_at_first_result: bool = False,
        min_confidence: float = 0.0
    ) -> Optional[LayerQueryResult]:
        """
        按优先级查询 - 从最高优先级开始查询，直到找到满意的结果

        Args:
            query: 查询字符串
            mode: 查询模式
            stop_at_first_result: 是否在找到第一个结果后停止
            min_confidence: 最小置信度阈值

        Returns:
            查询结果，如果没有找到结果则返回 None
        """
        self._ensure_initialized()

        # 按优先级排序
        sorted_layers = sorted(
            self.list_layers(),
            key=lambda x: self.layer_configs[x].priority if x in self.layer_configs else 999
        )

        for layer_key in sorted_layers:
            result = await self._query_single_layer(layer_key, query, mode)

            if result:
                # 如果需要，可以在这里添加置信度检查
                # LightRAG 目前不直接返回置信度，可以基于结果长度等指标判断

                if stop_at_first_result:
                    logger.info(f"在 {layer_key} 层找到结果，停止查询")
                    return result

        logger.info("未在任何层级找到满意的结果")
        return None

    # ==================== 阶段 4.3: 层级管理 ====================

    async def insert_to_layer(
        self,
        layer_name: str,
        documents: Union[str, List[str]],
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        向指定层级插入文档

        Args:
            layer_name: 层级名称（top, middle, bottom）
            documents: 文档内容（字符串或字符串列表）
            skip_existing: 是否跳过已存在的文档

        Returns:
            插入结果字典，包含成功/失败/跳过的文档数量
        """
        self._ensure_initialized()

        if layer_name not in self.layers:
            raise ValueError(f"层级不存在: {layer_name}")

        rag = self.layers[layer_name]
        layer_config = self.layer_configs[layer_name]

        # 标准化为列表
        if isinstance(documents, str):
            documents = [documents]

        logger.info(
            f"开始向 {layer_config.name} 层插入文档: "
            f"count={len(documents)}, skip_existing={skip_existing}"
        )

        results = {
            "total": len(documents),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        # 批量插入
        for i, doc in enumerate(documents):
            try:
                if skip_existing:
                    # TODO: 实现文档存在性检查
                    # 目前 LightRAG 没有直接的文档检查 API
                    pass

                # 插入文档
                await rag.ainsert(doc)
                results["success"] += 1

                # 更新统计
                self.layer_stats[layer_name]["document_count"] += 1

                logger.debug(
                    f"文档插入成功: layer={layer_name}, "
                    f"doc_index={i+1}/{len(documents)}"
                )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "doc_index": i,
                    "error": str(e)
                })
                logger.error(
                    f"文档插入失败: layer={layer_name}, "
                    f"doc_index={i+1}, error={e}"
                )

        logger.info(
            f"文档插入完成: layer={layer_name}, "
            f"success={results['success']}, "
            f"failed={results['failed']}, "
            f"skipped={results['skipped']}"
        )

        return results

    def get_layer_stats(self, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取层级统计信息

        Args:
            layer_name: 层级名称（可选），如果为 None 则返回所有层级统计

        Returns:
            统计信息字典
        """
        self._ensure_initialized()

        if layer_name:
            if layer_name not in self.layer_stats:
                raise ValueError(f"层级不存在: {layer_name}")
            return self._format_layer_stats(layer_name)

        # 返回所有层级统计
        all_stats = {}
        for layer_key in self.layer_stats:
            all_stats[layer_key] = self._format_layer_stats(layer_key)

        return all_stats

    def _format_layer_stats(self, layer_name: str) -> Dict[str, Any]:
        """格式化层级统计信息"""
        stats = self.layer_stats.get(layer_name, {})
        config = self.layer_configs.get(layer_name)

        return {
            "name": config.name if config else layer_name,
            "description": config.description if config else "",
            "priority": config.priority if config else 0,
            "namespace": config.namespace if config else "",
            "document_count": stats.get("document_count", 0),
            "entity_count": stats.get("entity_count", 0),
            "query_count": stats.get("query_count", 0),
            "status": stats.get("status", "unknown"),
            "working_dir": config.working_dir if config else ""
        }

    async def clear_layer(self, layer_name: str) -> bool:
        """
        清空指定层级的所有数据

        Args:
            layer_name: 层级名称

        Returns:
            是否清空成功
        """
        self._ensure_initialized()

        if layer_name not in self.layers:
            raise ValueError(f"层级不存在: {layer_name}")

        logger.warning(f"准备清空 {layer_name} 层的所有数据")

        try:
            rag = self.layers[layer_name]

            # TODO: LightRAG 没有直接的清空 API
            # 可能需要删除工作目录并重新初始化
            # 暂时只更新统计

            self.layer_stats[layer_name] = {
                "config": self.layer_configs[layer_name],
                "document_count": 0,
                "entity_count": 0,
                "query_count": 0,
                "status": "cleared"
            }

            logger.info(f"{layer_name} 层数据已清空")
            return True

        except Exception as e:
            logger.error(f"清空 {layer_name} 层数据失败: {e}")
            return False

    async def rebuild_layer(self, layer_name: str) -> bool:
        """
        重建指定层级（重新初始化存储）

        Args:
            layer_name: 层级名称

        Returns:
            是否重建成功
        """
        self._ensure_initialized()

        if layer_name not in self.layers:
            raise ValueError(f"层级不存在: {layer_name}")

        logger.info(f"准备重建 {layer_name} 层")

        try:
            # 清理现有实例
            rag = self.layers[layer_name]
            await rag.finalize_storages()

            # 重新初始化
            await rag.initialize_storages()

            # 重置统计
            self.layer_stats[layer_name] = {
                "config": self.layer_configs[layer_name],
                "document_count": 0,
                "entity_count": 0,
                "query_count": 0,
                "status": "rebuilt"
            }

            logger.info(f"{layer_name} 层重建完成")
            return True

        except Exception as e:
            logger.error(f"重建 {layer_name} 层失败: {e}")
            return False

    def update_layer_config(
        self,
        layer_name: str,
        **kwargs
    ) -> bool:
        """
        更新层级配置（仅影响下次初始化）

        Args:
            layer_name: 层级名称
            **kwargs: 要更新的配置参数

        Returns:
            是否更新成功
        """
        if layer_name not in self.layer_configs:
            raise ValueError(f"层级不存在: {layer_name}")

        try:
            config = self.layer_configs[layer_name]

            # 更新配置
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    logger.warning(
                        f"配置项不存在: {key}, "
                        f"layer={layer_name}"
                    )

            logger.info(f"{layer_name} 层配置已更新: {kwargs}")
            return True

        except Exception as e:
            logger.error(f"更新 {layer_name} 层配置失败: {e}")
            return False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.finalize()

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"ThreeLayerGraph("
            f"layers={list(self.layers.keys())}, "
            f"initialized={self._initialized}"
            f")"
        )


# 便捷函数

async def create_three_layer_graph(
    config: Optional[MedicalRAGConfig] = None,
    auto_init: bool = True
) -> ThreeLayerGraph:
    """
    创建并初始化三层图谱

    Args:
        config: MedicalRAG 配置
        auto_init: 是否自动初始化

    Returns:
        初始化后的 ThreeLayerGraph 实例
    """
    graph = ThreeLayerGraph(config=config)

    if auto_init:
        await graph.initialize()

    return graph
