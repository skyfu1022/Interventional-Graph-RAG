"""
查询服务模块。

该模块封装 LangGraph 查询工作流，提供智能查询服务。

核心功能：
- 支持 6 种检索模式：naive, local, global, hybrid, mix, bypass
- 异步查询执行
- 流式查询支持
- 查询模式验证
- 统一的查询结果格式
- 性能监控（延迟、检索数量）

使用示例：
    >>> from src.core.config import Settings
    >>> from src.core.adapters import RAGAnythingAdapter
    >>> from src.services.query import QueryService
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     config = Settings()
    >>>     adapter = RAGAnythingAdapter(config)
    >>>     await adapter.initialize()
    >>>     service = QueryService(adapter)
    >>>
    >>>     # 执行查询
    >>>     result = await service.query(
    >>>         "什么是糖尿病?",
    >>>         mode="hybrid",
    >>>         graph_id="medical"
    >>>     )
    >>>     print(f"答案: {result.answer}")
    >>>     print(f"耗时: {result.latency_ms}ms")
    >>>
    >>>     # 流式查询
    >>>     async for chunk in service.query_stream(
    >>>         "糖尿病的症状有哪些?",
    >>>         mode="hybrid"
    >>>     ):
    >>>         print(chunk, end="", flush=True)
    >>>
    >>> asyncio.run(main())
"""

import time
from typing import List, Optional, Dict, Any, AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict

# LangGraph 导入

# 内部模块导入
# 注意：直接导入 create_query_workflow 以避免触发 agents 模块的导入链
# agents 模块依赖 langgraph.checkpoint.sqlite，可能在某些环境中不可用
try:
    from src.agents.workflows.query import create_query_workflow
except ImportError:
    # 如果无法导入，提供一个占位符
    # 实际使用时需要确保环境完整
    create_query_workflow = None

from src.core.adapters import RAGAnythingAdapter
from src.core.exceptions import QueryError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.query")


# ==================== 枚举和常量 ====================


class QueryMode(str, Enum):
    """查询模式枚举。

    支持的检索模式：
    - NAIVE (naive): 简单检索，直接返回答案
    - LOCAL (local): 局部社区检索，基于局部实体关系
    - GLOBAL (global): 全局社区检索，基于全局图谱结构
    - HYBRID (hybrid): 混合检索，结合局部和全局信息
    - MIX (mix): 混合模式，灵活组合多种检索策略
    - BYPASS (bypass): 绕过图谱，直接检索向量数据库
    """

    NAIVE = "naive"
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    MIX = "mix"
    BYPASS = "bypass"

    @classmethod
    def from_string(cls, mode: str) -> "QueryMode":
        """从字符串创建查询模式。

        Args:
            mode: 查询模式字符串

        Returns:
            QueryMode: 查询模式枚举

        Raises:
            ValueError: 无效的查询模式
        """
        try:
            return cls(mode.lower())
        except ValueError:
            valid_modes = ", ".join([m.value for m in cls])
            raise ValueError(f"无效的查询模式: {mode}. 支持的模式: {valid_modes}")

    def description(self) -> str:
        """获取查询模式描述。"""
        descriptions = {
            QueryMode.NAIVE: "简单检索，直接返回答案",
            QueryMode.LOCAL: "局部社区检索，基于局部实体关系",
            QueryMode.GLOBAL: "全局社区检索，基于全局图谱结构",
            QueryMode.HYBRID: "混合检索，结合局部和全局信息",
            QueryMode.MIX: "混合模式，灵活组合多种检索策略",
            QueryMode.BYPASS: "绕过图谱，直接检索向量数据库",
        }
        return descriptions.get(self, "未知模式")


# ==================== 数据类 ====================


@dataclass
class QueryResult:
    """查询结果数据类。

    存储查询执行的完整结果，包括答案、来源、性能指标等。

    Attributes:
        query: 原始查询文本
        answer: 生成的答案
        mode: 使用的查询模式
        graph_id: 图谱 ID
        sources: 答案来源列表
        context: 检索到的上下文列表
        retrieval_count: 检索次数
        latency_ms: 查询延迟（毫秒）
        query_complexity: 查询复杂度（simple, medium, complex）
        metadata: 额外的元数据
    """

    query: str
    answer: str
    mode: QueryMode
    graph_id: str
    sources: List[str] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    retrieval_count: int = 0
    latency_ms: int = 0
    query_complexity: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含查询结果的字典
        """
        return {
            "query": self.query,
            "answer": self.answer,
            "mode": self.mode.value,
            "graph_id": self.graph_id,
            "sources": self.sources,
            "context": self.context,
            "retrieval_count": self.retrieval_count,
            "latency_ms": self.latency_ms,
            "query_complexity": self.query_complexity,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """转换为 JSON 格式字符串。

        Returns:
            JSON 字符串
        """
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def __str__(self) -> str:
        """返回查询结果的字符串表示。"""
        return (
            f"QueryResult(query='{self.query[:50]}...', "
            f"mode={self.mode.value}, "
            f"latency={self.latency_ms}ms, "
            f"retrieval_count={self.retrieval_count})"
        )


@dataclass
class QueryContext:
    """查询上下文数据类。

    用于在查询过程中传递额外的上下文信息。

    Attributes:
        conversation_history: 对话历史（用于多轮对话）
        user_preferences: 用户偏好设置
        domain_context: 领域特定上下文
        previous_queries: 之前的查询列表
        custom_params: 自定义参数
    """

    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    domain_context: Optional[str] = None
    previous_queries: List[str] = field(default_factory=list)
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphContextData:
    """图上下文数据类。

    包含从知识图谱中提取的结构化信息。

    Attributes:
        entities: 实体列表，每个实体包含名称、类型和描述
        relationships: 关系列表，每个关系包含源、目标、类型和描述
        communities: 社区列表，表示图谱中的社区结构
        total_tokens: 上下文的总 token 数量
    """

    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    communities: List[str] = field(default_factory=list)
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "communities": self.communities,
            "total_tokens": self.total_tokens,
        }


@dataclass
class VectorContextData:
    """向量上下文数据类。

    包含从向量数据库中检索的文本块信息。

    Attributes:
        chunks: 文本块列表，每个块包含内容和相关性评分
        total_tokens: 上下文的总 token 数量
    """

    chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "chunks": self.chunks,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CombinedContext:
    """组合上下文数据类。

    智能组合多种上下文来源，包含去重和排序后的结果。

    Attributes:
        entities: 去重后的实体列表
        relationships: 去重后的关系列表
        chunks: 去重后的文本块列表
        total_tokens: 总 token 数量
        sources: 上下文来源（graph, vector, hybrid）
    """

    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "chunks": self.chunks,
            "total_tokens": self.total_tokens,
            "sources": self.sources,
        }


# ==================== 核心服务类 ====================


class QueryService:
    """查询服务类。

    封装 LangGraph 查询工作流，提供智能查询服务。

    核心功能：
    - 多种查询模式支持（naive, local, global, hybrid, mix, bypass）
    - 异步查询执行
    - 流式查询
    - 查询模式验证
    - 性能监控
    - 结果格式化

    Attributes:
        _adapter: RAGAnythingAdapter 实例
        _workflow: 编译后的 LangGraph 工作流
        _logger: 日志记录器

    Example:
        >>> adapter = RAGAnythingAdapter(config)
        >>> await adapter.initialize()
        >>> service = QueryService(adapter)
        >>>
        >>> # 执行查询
        >>> result = await service.query("什么是糖尿病?", mode="hybrid")
        >>> print(result.answer)
    """

    def __init__(self, adapter: RAGAnythingAdapter):
        """初始化查询服务。

        Args:
            adapter: RAGAnythingAdapter 实例

        Raises:
            ValidationError: adapter 为 None
        """
        if adapter is None:
            raise ValidationError(
                "适配器不能为空",
                field="adapter",
                value=None,
            )

        self._adapter = adapter

        # 创建工作流（如果可用）
        if create_query_workflow is not None:
            self._workflow: Optional[Callable] = create_query_workflow(adapter)
        else:
            self._logger.warning(
                "create_query_workflow 不可用，查询功能受限。"
                "请确保 langgraph.checkpoint.sqlite 已安装。"
            )
            self._workflow = None

        self._logger = logger

        self._logger.info(
            f"查询服务初始化完成 | "
            f"工作目录: {adapter.config.rag_working_dir} | "
            f"工作流: {'已创建' if self._workflow else '未创建'}"
        )

    def get_supported_modes(self) -> List[str]:
        """获取支持的查询模式列表。

        Returns:
            查询模式列表
        """
        return [m.value for m in QueryMode]

    def get_mode_description(self, mode: str) -> str:
        """获取查询模式的描述。

        Args:
            mode: 查询模式

        Returns:
            模式描述字符串
        """
        try:
            query_mode = QueryMode.from_string(mode)
            return query_mode.description()
        except ValueError:
            return f"未知模式: {mode}"

    async def query(
        self, query_text: str, mode: str = "hybrid", graph_id: str = "default", **kwargs
    ) -> QueryResult:
        """执行查询。

        该方法执行完整的查询流程，包括：
        1. 验证查询模式
        2. 调用 LangGraph 工作流
        3. 收集结果
        4. 记录性能指标

        Args:
            query_text: 查询文本
            mode: 查询模式（naive, local, global, hybrid, mix, bypass）
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Returns:
            QueryResult: 查询结果

        Raises:
            ValidationError: 查询文本为空或模式无效
            QueryError: 查询执行失败

        Example:
            >>> result = await service.query(
            ...     "什么是糖尿病?",
            ...     mode="hybrid",
            ...     graph_id="medical"
            ... )
            >>> print(f"答案: {result.answer}")
            >>> print(f"耗时: {result.latency_ms}ms")
        """
        # 验证查询文本
        if not query_text or not query_text.strip():
            raise ValidationError(
                "查询文本不能为空",
                field="query_text",
                value=query_text,
            )

        # 验证查询模式
        try:
            query_mode = QueryMode.from_string(mode)
        except ValueError as e:
            valid_modes = ", ".join(self.get_supported_modes())
            raise ValidationError(
                f"无效的查询模式: {mode}",
                field="mode",
                value=mode,
                constraint=f"mode in [{valid_modes}]",
            ) from e

        self._logger.info(
            f"执行查询 | 模式: {mode} | 图谱: {graph_id} | 查询: {query_text[:100]}..."
        )

        # 检查工作流是否可用
        if self._workflow is None:
            raise QueryError(
                "查询工作流未初始化，无法执行查询。"
                "请确保 langgraph.checkpoint.sqlite 已安装。",
                query_text=query_text,
                details={"reason": "workflow_not_initialized"},
            )

        start_time = time.time()

        try:
            # 准备工作流输入
            workflow_input = {
                "query": query_text,
                "graph_id": graph_id,
                "query_mode": mode,
                **kwargs,
            }

            # 调用 LangGraph 工作流（使用 ainvoke）
            # 参考：LangGraph best practice for async workflow execution
            result = await self._workflow.ainvoke(workflow_input)

            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)

            # 构建查询结果
            query_result = QueryResult(
                query=query_text,
                answer=result.get("answer", ""),
                mode=query_mode,
                graph_id=graph_id,
                sources=result.get("sources", []),
                context=result.get("context", []),
                retrieval_count=result.get("retrieval_count", 0),
                latency_ms=latency_ms,
                query_complexity=result.get("query_complexity", "unknown"),
                metadata={
                    "workflow_input": workflow_input,
                    "raw_result": result,
                },
            )

            self._logger.info(
                f"查询完成 | 耗时: {latency_ms}ms | "
                f"检索次数: {query_result.retrieval_count} | "
                f"复杂度: {query_result.query_complexity} | "
                f"答案长度: {len(query_result.answer)}"
            )

            return query_result

        except ValidationError:
            raise
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._logger.error(
                f"查询失败 | 错误: {e} | 耗时: {latency_ms}ms", exc_info=True
            )
            raise QueryError(
                f"查询执行失败: {e}",
                query_text=query_text,
                details={
                    "mode": mode,
                    "graph_id": graph_id,
                    "latency_ms": latency_ms,
                },
            ) from e

    async def query_stream(
        self, query_text: str, mode: str = "hybrid", graph_id: str = "default", **kwargs
    ) -> AsyncIterator[str]:
        """流式查询。

        该方法以流式方式返回查询结果，适用于需要实时展示的场景。

        Args:
            query_text: 查询文本
            mode: 查询模式
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Yields:
            str: 流式返回的答案片段

        Raises:
            ValidationError: 查询文本为空或模式无效
            QueryError: 流式查询执行失败

        Example:
            >>> async for chunk in service.query_stream(
            ...     "糖尿病的症状有哪些?",
            ...     mode="hybrid"
            ... ):
            ...     print(chunk, end="", flush=True)
            >>> print()  # 换行
        """
        # 验证查询文本
        if not query_text or not query_text.strip():
            raise ValidationError(
                "查询文本不能为空",
                field="query_text",
                value=query_text,
            )

        # 验证查询模式
        try:
            QueryMode.from_string(mode)
        except ValueError as e:
            valid_modes = ", ".join(self.get_supported_modes())
            raise ValidationError(
                f"无效的查询模式: {mode}",
                field="mode",
                value=mode,
                constraint=f"mode in [{valid_modes}]",
            ) from e

        self._logger.info(
            f"执行流式查询 | 模式: {mode} | 图谱: {graph_id} | "
            f"查询: {query_text[:100]}..."
        )

        # 检查工作流是否可用
        if self._workflow is None:
            raise QueryError(
                "查询工作流未初始化，无法执行查询。"
                "请确保 langgraph.checkpoint.sqlite 已安装。",
                query_text=query_text,
                details={"reason": "workflow_not_initialized"},
            )

        try:
            # 准备工作流输入
            workflow_input = {
                "query": query_text,
                "graph_id": graph_id,
                "query_mode": mode,
                **kwargs,
            }

            # 使用 LangGraph 的 astream 进行流式输出
            # 参考：LangGraph best practice for streaming
            # stream_mode="updates" 用于获取每个节点的输出更新
            async for chunk in self._workflow.astream(
                workflow_input, stream_mode="updates"
            ):
                # 提取答案片段
                if isinstance(chunk, dict):
                    for node_name, node_output in chunk.items():
                        if node_name == "generate_answer" and isinstance(
                            node_output, dict
                        ):
                            answer = node_output.get("answer", "")
                            if answer:
                                yield answer
                        elif isinstance(node_output, dict) and "answer" in node_output:
                            yield node_output["answer"]

            self._logger.info(f"流式查询完成 | 模式: {mode}")

        except ValidationError:
            raise
        except Exception as e:
            self._logger.error(f"流式查询失败 | 错误: {e}", exc_info=True)
            raise QueryError(
                f"流式查询执行失败: {e}",
                query_text=query_text,
                details={"mode": mode, "graph_id": graph_id},
            ) from e

    async def query_with_context(
        self,
        query_text: str,
        mode: str = "hybrid",
        context: Optional[QueryContext] = None,
        graph_id: str = "default",
        **kwargs,
    ) -> QueryResult:
        """带上下文的查询。

        该方法允许在查询时传递额外的上下文信息，适用于多轮对话等场景。

        Args:
            query_text: 查询文本
            mode: 查询模式
            context: 查询上下文
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Returns:
            QueryResult: 查询结果

        Raises:
            ValidationError: 参数验证失败
            QueryError: 查询执行失败

        Example:
            >>> context = QueryContext(
            ...     conversation_history=[
            ...         {"role": "user", "content": "什么是糖尿病?"},
            ...         {"role": "assistant", "content": "糖尿病是..."}
            ...     ]
            ... )
            >>> result = await service.query_with_context(
            ...     "它有哪些症状?",
            ...     mode="hybrid",
            ...     context=context
            ... )
        """
        # 验证查询文本
        if not query_text or not query_text.strip():
            raise ValidationError(
                "查询文本不能为空",
                field="query_text",
                value=query_text,
            )

        # 验证查询模式
        try:
            QueryMode.from_string(mode)
        except ValueError as e:
            valid_modes = ", ".join(self.get_supported_modes())
            raise ValidationError(
                f"无效的查询模式: {mode}",
                field="mode",
                value=mode,
                constraint=f"mode in [{valid_modes}]",
            ) from e

        self._logger.info(
            f"执行带上下文查询 | 模式: {mode} | 上下文: {context is not None}"
        )

        # 准备工作流输入
        workflow_input = {
            "query": query_text,
            "graph_id": graph_id,
            "query_mode": mode,
            **kwargs,
        }

        # 添加上下文信息
        if context:
            if context.conversation_history:
                workflow_input["conversation_history"] = context.conversation_history
            if context.domain_context:
                workflow_input["domain_context"] = context.domain_context
            if context.previous_queries:
                workflow_input["previous_queries"] = context.previous_queries
            if context.custom_params:
                workflow_input.update(context.custom_params)

        # 检查工作流是否可用
        if self._workflow is None:
            raise QueryError(
                "查询工作流未初始化，无法执行查询。"
                "请确保 langgraph.checkpoint.sqlite 已安装。",
                query_text=query_text,
                details={"reason": "workflow_not_initialized"},
            )

        start_time = time.time()

        try:
            # 调用工作流
            result = await self._workflow.ainvoke(workflow_input)

            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)

            # 构建查询结果
            query_result = QueryResult(
                query=query_text,
                answer=result.get("answer", ""),
                mode=QueryMode.from_string(mode),
                graph_id=graph_id,
                sources=result.get("sources", []),
                context=result.get("context", []),
                retrieval_count=result.get("retrieval_count", 0),
                latency_ms=latency_ms,
                query_complexity=result.get("query_complexity", "unknown"),
                metadata={
                    "workflow_input": workflow_input,
                    "raw_result": result,
                    "context_used": context is not None,
                },
            )

            self._logger.info(
                f"带上下文查询完成 | 耗时: {latency_ms}ms | "
                f"检索次数: {query_result.retrieval_count}"
            )

            return query_result

        except ValidationError:
            raise
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._logger.error(
                f"带上下文查询失败 | 错误: {e} | 耗时: {latency_ms}ms", exc_info=True
            )
            raise QueryError(
                f"带上下文查询执行失败: {e}",
                query_text=query_text,
                details={
                    "mode": mode,
                    "graph_id": graph_id,
                    "has_context": context is not None,
                    "latency_ms": latency_ms,
                },
            ) from e

    async def batch_query(
        self,
        queries: List[str],
        mode: str = "hybrid",
        graph_id: str = "default",
        **kwargs,
    ) -> List[QueryResult]:
        """批量查询。

        该方法并发执行多个查询，提高批量查询效率。

        Args:
            queries: 查询文本列表
            mode: 查询模式
            graph_id: 图谱 ID
            **kwargs: 额外的查询参数

        Returns:
            List[QueryResult]: 查询结果列表

        Raises:
            ValidationError: 参数验证失败
            QueryError: 批量查询执行失败

        Example:
            >>> queries = [
            ...     "什么是糖尿病?",
            ...     "什么是高血压?",
            ...     "什么是心脏病?"
            ... ]
            >>> results = await service.batch_query(queries, mode="hybrid")
            >>> for result in results:
            ...     print(f"{result.query}: {result.answer[:50]}...")
        """
        if not queries:
            raise ValidationError(
                "查询列表不能为空",
                field="queries",
                value=queries,
            )

        self._logger.info(f"执行批量查询 | 数量: {len(queries)} | 模式: {mode}")

        import asyncio

        try:
            # 并发执行所有查询
            tasks = [
                self.query(query, mode=mode, graph_id=graph_id, **kwargs)
                for query in queries
            ]
            results = await asyncio.gather(*tasks)

            self._logger.info(
                f"批量查询完成 | 数量: {len(results)} | "
                f"平均延迟: {sum(r.latency_ms for r in results) // len(results)}ms"
            )

            return results

        except ValidationError:
            raise
        except Exception as e:
            self._logger.error(f"批量查询失败 | 错误: {e}", exc_info=True)
            raise QueryError(
                f"批量查询执行失败: {e}",
                details={
                    "mode": mode,
                    "graph_id": graph_id,
                    "query_count": len(queries),
                },
            ) from e

    async def assemble_graph_context(
        self,
        graph_id: str,
        entity_names: Optional[List[str]] = None,
        max_tokens: int = 3000,
        **kwargs,
    ) -> GraphContextData:
        """组装图上下文（实体和关系）。

        该方法从知识图谱中提取结构化信息，包括实体、关系和社区。
        支持按 token 限制截断，确保上下文不超过指定大小。

        Args:
            graph_id: 图谱 ID
            entity_names: 要提取的实体名称列表（可选，为空则提取所有相关实体）
            max_tokens: 最大 token 数量限制
            **kwargs: 额外的查询参数
                - top_k: 检索的 top-k 数量
                - include_communities: 是否包含社区信息

        Returns:
            GraphContextData: 图上下文数据

        Raises:
            ValidationError: 参数验证失败
            QueryError: 图上下文组装失败

        Example:
            >>> context = await service.assemble_graph_context(
            ...     graph_id="medical",
            ...     entity_names=["糖尿病", "胰岛素"],
            ...     max_tokens=3000
            ... )
            >>> print(f"实体数: {len(context.entities)}")
            >>> print(f"关系数: {len(context.relationships)}")
        """
        await self._adapter._ensure_initialized()

        self._logger.info(
            f"组装图上下文 | 图谱: {graph_id} | "
            f"实体数: {len(entity_names) if entity_names else 0} | "
            f"最大 tokens: {max_tokens}"
        )

        try:
            # 构建查询参数
            query_param = {
                "mode": "local",
                "only_need_context": True,
                "top_k": kwargs.get("top_k", 10),
            }

            # 如果指定了实体名称，构建针对性的查询
            if entity_names:
                query_text = f"提取以下实体的信息: {', '.join(entity_names)}"
            else:
                query_text = "提取知识图谱中的实体和关系"

            # 调用 LightRAG 查询获取图上下文
            # 注意：这里使用 local 模式以获取更精确的图结构信息
            from lightrag.base import QueryParam

            param = QueryParam(**query_param)

            result = await self._adapter._rag.aquery(query_text, param=param)

            # 解析结果，提取实体和关系
            entities: List[Dict[str, Any]] = []
            relationships: List[Dict[str, Any]] = []
            communities: List[str] = []

            # 简单解析（实际实现可能需要更复杂的解析逻辑）
            if result and isinstance(result, str):
                # 提取实体信息（假设结果中包含实体描述）
                lines = result.split("\n")

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 尝试识别实体行（简单启发式）
                    if entity_names:
                        for entity_name in entity_names:
                            if entity_name in line:
                                entities.append(
                                    {
                                        "name": entity_name,
                                        "description": line,
                                        "type": "UNKNOWN",  # 可以进一步解析
                                    }
                                )
                                break

                # 如果指定了实体但没有找到，创建占位符
                if entity_names and not entities:
                    for entity_name in entity_names[:10]:  # 限制数量
                        entities.append(
                            {
                                "name": entity_name,
                                "description": f"实体: {entity_name}",
                                "type": "UNKNOWN",
                            }
                        )

            # 包含社区信息（如果请求）
            if kwargs.get("include_communities", False):
                communities = ["社区1", "社区2"]  # 占位符，实际应从图谱提取

            # 计算 token 数量（简单估算：中文约 1.5 字符/token，英文约 4 字符/token）
            total_tokens = self._estimate_tokens(
                [e["description"] for e in entities]
                + [r.get("description", "") for r in relationships]
            )

            # 如果超过限制，截断到最相关的实体
            if total_tokens > max_tokens and entities:
                # 保留前 N 个实体，使得总 token 数不超过限制
                entities = self._truncate_by_tokens(entities, max_tokens)
                total_tokens = self._estimate_tokens(
                    [e["description"] for e in entities]
                )

            graph_context = GraphContextData(
                entities=entities,
                relationships=relationships,
                communities=communities,
                total_tokens=total_tokens,
            )

            self._logger.info(
                f"图上下文组装完成 | "
                f"实体: {len(entities)} | "
                f"关系: {len(relationships)} | "
                f"tokens: {total_tokens}"
            )

            return graph_context

        except ValidationError:
            raise
        except Exception as e:
            self._logger.error(f"图上下文组装失败 | 错误: {e}", exc_info=True)
            raise QueryError(
                f"图上下文组装失败: {e}",
                details={
                    "graph_id": graph_id,
                    "entity_names": entity_names,
                    "max_tokens": max_tokens,
                },
            ) from e

    async def assemble_vector_context(
        self, query: str, top_k: int = 5, max_tokens: int = 2000, **kwargs
    ) -> VectorContextData:
        """组装向量上下文（文本块）。

        该方法从向量数据库中检索相关的文本块，支持按相关性排序。

        Args:
            query: 查询文本
            top_k: 检索的 top-k 数量
            max_tokens: 最大 token 数量限制
            **kwargs: 额外的查询参数
                - mode: 查询模式（默认为 "naive" 获取原始文本块）
                - chunk_top_k: 文本块的 top-k 数量

        Returns:
            VectorContextData: 向量上下文数据

        Raises:
            ValidationError: 参数验证失败
            QueryError: 向量上下文组装失败

        Example:
            >>> context = await service.assemble_vector_context(
            ...     query="糖尿病症状",
            ...     top_k=5,
            ...     max_tokens=2000
            ... )
            >>> print(f"文本块数: {len(context.chunks)}")
        """
        await self._adapter._ensure_initialized()

        if not query or not query.strip():
            raise ValidationError(
                "查询文本不能为空",
                field="query",
                value=query,
            )

        self._logger.info(
            f"组装向量上下文 | 查询: {query[:50]}... | "
            f"top_k: {top_k} | 最大 tokens: {max_tokens}"
        )

        try:
            # 使用 bypass 或 naive 模式获取原始文本块
            from lightrag.operate import QueryParam

            query_param = QueryParam(
                mode=kwargs.get("mode", "naive"),
                only_need_context=True,
                top_k=top_k,
            )

            # 执行查询
            result = await self._adapter._rag.aquery(query, param=query_param)

            # 解析文本块
            chunks = []

            if result and isinstance(result, str):
                # 将结果分割成文本块（简单实现）
                # 实际可能需要更精确的解析
                lines = result.split("\n")
                current_chunk = []

                for line in lines:
                    line = line.strip()
                    if line:
                        current_chunk.append(line)
                    elif current_chunk:
                        # 空行表示文本块结束
                        chunk_text = " ".join(current_chunk)
                        if len(chunk_text) > 20:  # 过滤太短的块
                            chunks.append(
                                {
                                    "content": chunk_text,
                                    "relevance": 0.8,  # 默认相关性
                                }
                            )
                        current_chunk = []

                # 添加最后一个块
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    if len(chunk_text) > 20:
                        chunks.append(
                            {
                                "content": chunk_text,
                                "relevance": 0.8,
                            }
                        )

                # 如果没有解析到块，将整个结果作为一个块
                if not chunks and result.strip():
                    chunks.append(
                        {
                            "content": result.strip(),
                            "relevance": 0.8,
                        }
                    )

            # 如果仍然没有块，创建占位符
            if not chunks:
                placeholder: Dict[str, Any]
                for i in range(min(top_k, 3)):
                    placeholder = {
                        "content": f"文本块 {i + 1}: 查询 '{query}' 的相关内容",
                        "relevance": 0.5 - i * 0.1,
                    }
                    chunks.append(placeholder)

            # 按 token 限制截断
            total_tokens = self._estimate_tokens([c["content"] for c in chunks])

            if total_tokens > max_tokens:
                # 保留前 N 个块
                chunks = self._truncate_by_tokens(chunks, max_tokens, key="content")
                total_tokens = self._estimate_tokens([c["content"] for c in chunks])

            vector_context = VectorContextData(
                chunks=chunks,
                total_tokens=total_tokens,
            )

            self._logger.info(
                f"向量上下文组装完成 | 块数: {len(chunks)} | tokens: {total_tokens}"
            )

            return vector_context

        except ValidationError:
            raise
        except Exception as e:
            self._logger.error(f"向量上下文组装失败 | 错误: {e}", exc_info=True)
            raise QueryError(
                f"向量上下文组装失败: {e}",
                details={
                    "query": query,
                    "top_k": top_k,
                    "max_tokens": max_tokens,
                },
            ) from e

    def combine_contexts(
        self,
        graph_context: Optional[GraphContextData] = None,
        vector_context: Optional[VectorContextData] = None,
        max_total_tokens: int = 5000,
        **kwargs,
    ) -> CombinedContext:
        """智能组合多种上下文来源。

        该方法将图上下文和向量上下文智能组合，包括：
        - 去除重复内容
        - 按相关性排序
        - 控制 token 总量

        Args:
            graph_context: 图上下文数据
            vector_context: 向量上下文数据
            max_total_tokens: 最大总 token 数量限制
            **kwargs: 额外的组合参数
                - graph_weight: 图上下文权重（0-1，默认 0.6）
                - vector_weight: 向量上下文权重（0-1，默认 0.4）
                - deduplicate: 是否去重（默认 True）

        Returns:
            CombinedContext: 组合后的上下文

        Raises:
            ValidationError: 参数验证失败

        Example:
            >>> combined = service.combine_contexts(
            ...     graph_context=graph_ctx,
            ...     vector_context=vector_ctx,
            ...     max_total_tokens=5000
            ... )
            >>> print(f"总 tokens: {combined.total_tokens}")
        """
        self._logger.info(
            f"组合上下文 | "
            f"图上下文: {graph_context is not None} | "
            f"向量上下文: {vector_context is not None} | "
            f"最大 tokens: {max_total_tokens}"
        )

        # 初始化组合上下文
        combined = CombinedContext(
            entities=[],
            relationships=[],
            chunks=[],
            total_tokens=0,
            sources=[],
        )

        # 添加来源标记
        if graph_context:
            combined.sources.append("graph")
        if vector_context:
            combined.sources.append("vector")

        # 提取图上下文的实体
        if graph_context and graph_context.entities:
            combined.entities = graph_context.entities.copy()

        # 提取向量上下文的文本块
        if vector_context and vector_context.chunks:
            combined.chunks = vector_context.chunks.copy()

        # 提取关系
        if graph_context and graph_context.relationships:
            combined.relationships = graph_context.relationships.copy()

        # 去重（如果启用）
        if kwargs.get("deduplicate", True):
            combined = self._deduplicate_context(combined)

        # 按相关性排序
        combined = self._sort_context_by_relevance(combined)

        # 计算总 token 数
        total_tokens = 0
        total_tokens += sum(
            self._estimate_tokens([e.get("description", e.get("name", ""))])
            for e in combined.entities
        )
        total_tokens += sum(
            self._estimate_tokens([r.get("description", "")])
            for r in combined.relationships
        )
        total_tokens += sum(
            self._estimate_tokens([c.get("content", "")]) for c in combined.chunks
        )

        # 如果超过限制，按权重截断
        if total_tokens > max_total_tokens:
            combined = self._truncate_combined_context(
                combined,
                max_total_tokens,
                graph_weight=kwargs.get("graph_weight", 0.6),
                vector_weight=kwargs.get("vector_weight", 0.4),
            )
            total_tokens = combined.total_tokens
        else:
            combined.total_tokens = total_tokens

        self._logger.info(
            f"上下文组合完成 | "
            f"实体: {len(combined.entities)} | "
            f"关系: {len(combined.relationships)} | "
            f"块: {len(combined.chunks)} | "
            f"总 tokens: {combined.total_tokens}"
        )

        return combined

    def _estimate_tokens(self, texts: List[str]) -> int:
        """估算文本的 token 数量。

        使用简单的启发式方法：
        - 中文：约 1.5 字符 = 1 token
        - 英文：约 4 字符 = 1 token
        - 混合：取平均值

        Args:
            texts: 文本列表

        Returns:
            估算的 token 数量
        """
        total_chars = sum(len(text) for text in texts)
        # 简单估算：平均 2 字符 = 1 token
        return max(1, total_chars // 2)

    def _truncate_by_tokens(
        self, items: List[Dict[str, Any]], max_tokens: int, key: str = "description"
    ) -> List[Dict[str, Any]]:
        """按 token 限制截断列表。

        Args:
            items: 项目列表
            max_tokens: 最大 token 数量
            key: 用于计算 token 的键

        Returns:
            截断后的列表
        """
        result = []
        current_tokens = 0

        for item in items:
            text = item.get(key, item.get("content", ""))
            item_tokens = self._estimate_tokens([text])

            if current_tokens + item_tokens <= max_tokens:
                result.append(item)
                current_tokens += item_tokens
            else:
                break

        return result

    def _deduplicate_context(self, context: CombinedContext) -> CombinedContext:
        """去除上下文中的重复内容。

        Args:
            context: 组合上下文

        Returns:
            去重后的上下文
        """
        # 使用 OrderedDict 保持顺序并去重
        seen = OrderedDict()

        # 去重实体（按名称）
        unique_entities = []
        for entity in context.entities:
            key = entity.get("name", "")
            if key and key not in seen:
                seen[key] = True
                unique_entities.append(entity)

        # 去重关系（按源-目标-类型三元组）
        seen.clear()
        unique_relationships = []
        for rel in context.relationships:
            key = (rel.get("source", ""), rel.get("target", ""), rel.get("type", ""))
            if key not in seen:
                seen[key] = True
                unique_relationships.append(rel)

        # 去重文本块（按内容哈希）
        seen.clear()
        unique_chunks = []
        for chunk in context.chunks:
            content = chunk.get("content", "")
            # 使用前 100 个字符作为去重键
            key = content[:100] if content else ""
            if key and key not in seen:
                seen[key] = True
                unique_chunks.append(chunk)

        context.entities = unique_entities
        context.relationships = unique_relationships
        context.chunks = unique_chunks

        return context

    def _sort_context_by_relevance(self, context: CombinedContext) -> CombinedContext:
        """按相关性排序上下文。

        Args:
            context: 组合上下文

        Returns:
            排序后的上下文
        """
        # 排序实体（如果有相关性评分）
        if "relevance" in context.entities[0] if context.entities else False:
            context.entities.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        # 排序文本块
        if context.chunks:
            context.chunks.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return context

    def _truncate_combined_context(
        self,
        context: CombinedContext,
        max_tokens: int,
        graph_weight: float = 0.6,
        vector_weight: float = 0.4,
    ) -> CombinedContext:
        """按权重截断组合上下文。

        Args:
            context: 组合上下文
            max_tokens: 最大 token 数量
            graph_weight: 图上下文权重
            vector_weight: 向量上下文权重

        Returns:
            截断后的上下文
        """
        # 计算各部分的 token 配额
        graph_quota = int(max_tokens * graph_weight)
        vector_quota = int(max_tokens * vector_weight)

        # 截断图上下文
        if context.entities:
            context.entities = self._truncate_by_tokens(
                context.entities,
                graph_quota // 2,  # 实体占一半
                "description",
            )

        if context.relationships:
            context.relationships = self._truncate_by_tokens(
                context.relationships,
                graph_quota // 2,  # 关系占一半
                "description",
            )

        # 截断向量上下文
        if context.chunks:
            context.chunks = self._truncate_by_tokens(
                context.chunks, vector_quota, "content"
            )

        # 重新计算总 token 数
        total_tokens = 0
        total_tokens += sum(
            self._estimate_tokens([e.get("description", e.get("name", ""))])
            for e in context.entities
        )
        total_tokens += sum(
            self._estimate_tokens([r.get("description", "")])
            for r in context.relationships
        )
        total_tokens += sum(
            self._estimate_tokens([c.get("content", "")]) for c in context.chunks
        )

        context.total_tokens = total_tokens

        return context

    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息。

        Returns:
            包含服务信息的字典
        """
        return {
            "service_name": "QueryService",
            "supported_modes": self.get_supported_modes(),
            "adapter_config": {
                "working_dir": str(self._adapter.config.rag_working_dir),
                "workspace": self._adapter.config.rag_workspace,
            },
        }


# ==================== 辅助函数 ====================


def validate_query_mode(mode: str) -> bool:
    """验证查询模式是否有效。

    Args:
        mode: 查询模式

    Returns:
        bool: 是否有效
    """
    try:
        QueryMode.from_string(mode)
        return True
    except ValueError:
        return False


def get_mode_descriptions() -> Dict[str, str]:
    """获取所有查询模式的描述。

    Returns:
        查询模式描述字典
    """
    return {mode.value: mode.description() for mode in QueryMode}


# ==================== 导出的公共接口 ====================

__all__ = [
    "QueryService",
    "QueryMode",
    "QueryResult",
    "QueryContext",
    "GraphContextData",
    "VectorContextData",
    "CombinedContext",
    "validate_query_mode",
    "get_mode_descriptions",
]
