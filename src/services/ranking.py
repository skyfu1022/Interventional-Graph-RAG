"""
结果排序和重排服务模块。

该模块提供查询结果的排序、重排和去重功能。

核心功能：
- 基于相关性分数的结果排序
- 支持可选的机器学习重排序模型
- 结果去重功能
- 多样性排序

使用示例：
    >>> from src.services.ranking import ResultRanker
    >>>
    >>> # 创建排序器
    >>> ranker = ResultRanker()
    >>>
    >>> # 重排序结果
    >>> results = [
    ...     {"content": "糖尿病是一种代谢性疾病", "score": 0.7},
    ...     {"content": "高血压是心血管疾病", "score": 0.9},
    ...     {"content": "糖尿病的症状包括多饮", "score": 0.85}
    ... ]
    >>> reranked = ranker.rerank(
    ...     results=results,
    ...     query="糖尿病症状",
    ...     top_n=2
    ... )
    >>> print(reranked[0]["score"])  # 最相关的结果
"""

import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

from src.core.exceptions import QueryError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.ranking")


# ==================== 枚举和常量 ====================


class RankingMethod(str, Enum):
    """排序方法枚举。

    定义支持的排序方法：
    - SCORE (score): 基于相关性分数排序
    - RERANK (rerank): 使用重排序模型
    - DIVERSITY (diversity): 多样性排序
    """

    SCORE = "score"
    RERANK = "rerank"
    DIVERSITY = "diversity"


class DedupMethod(str, Enum):
    """去重方法枚举。

    定义支持的去重方法：
    - CONTENT (content): 基于内容去重
    - FINGERPRINT (fingerprint): 基于指纹去重
    - NONE (none): 不去重
    """

    CONTENT = "content"
    FINGERPRINT = "fingerprint"
    NONE = "none"


# ==================== 数据类 ====================


@dataclass
class RankedResult:
    """排序后的结果。

    表示经过排序和重排的查询结果。

    Attributes:
        content: 结果内容
        score: 相关性分数
        original_index: 原始索引
        rank: 排序后的排名
        metadata: 额外的元数据
    """

    content: str
    score: float
    original_index: int
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含排序结果的字典
        """
        return {
            "content": self.content,
            "score": self.score,
            "original_index": self.original_index,
            "rank": self.rank,
            "metadata": self.metadata,
        }


@dataclass
class RankingConfig:
    """排序配置。

    定义排序行为的配置参数。

    Attributes:
        method: 排序方法
        dedup_method: 去重方法
        dedup_threshold: 去重相似度阈值
        top_n: 返回前 N 个结果
        diversity_lambda: 多样性排序的 lambda 参数（0-1）
        enable_rerank: 是否启用重排序
    """

    method: RankingMethod = RankingMethod.SCORE
    dedup_method: DedupMethod = DedupMethod.CONTENT
    dedup_threshold: float = 0.85
    top_n: int = 5
    diversity_lambda: float = 0.5
    enable_rerank: bool = False

    def __post_init__(self) -> None:
        """初始化后验证。"""
        if not 0 <= self.diversity_lambda <= 1:
            raise ValueError("diversity_lambda 必须在 [0, 1] 范围内")
        if not 0 <= self.dedup_threshold <= 1:
            raise ValueError("dedup_threshold 必须在 [0, 1] 范围内")
        if self.top_n <= 0:
            raise ValueError("top_n 必须大于 0")


# ==================== 核心服务类 ====================


class ResultRanker:
    """结果排序器类。

    提供查询结果的排序、重排和去重功能。

    核心功能：
    - 基于相关性分数排序
    - 支持可选的机器学习重排序
    - 结果去重（基于内容或指纹）
    - 多样性排序（MMR 算法）
    - 性能监控

    Attributes:
        _config: 排序配置
        _rerank_func: 可选的重排序函数
        _logger: 日志记录器

    Example:
        >>> ranker = ResultRanker()
        >>> results = [{"content": "...", "score": 0.7}]
        >>> ranked = ranker.rerank(results, query="糖尿病", top_n=5)
    """

    def __init__(
        self,
        config: Optional[RankingConfig] = None,
        rerank_func: Optional[
            Callable[[List[Dict[str, Any]], str], List[float]]
        ] = None,
    ):
        """初始化结果排序器。

        Args:
            config: 排序配置，如果为 None 则使用默认配置
            rerank_func: 可选的重排序函数，签名为:
                (results: List[Dict], query: str) -> List[float]
                返回每个结果的新分数

        Raises:
            ValidationError: 配置参数无效
        """
        if config is None:
            config = RankingConfig()
        else:
            # 验证配置
            try:
                RankingConfig.__post_init__(config)
            except ValueError as e:
                raise ValidationError(
                    f"排序配置无效: {e}",
                    field="config",
                    value=config,
                ) from e

        self._config = config
        self._rerank_func = rerank_func
        self._logger = logger

        self._logger.info(
            f"结果排序器初始化完成 | "
            f"方法: {config.method.value} | "
            f"去重: {config.dedup_method.value} | "
            f"重排序: {rerank_func is not None}"
        )

    def rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_n: Optional[int] = None,
        method: Optional[RankingMethod] = None,
    ) -> List[RankedResult]:
        """重排序查询结果。

        该方法根据指定的排序方法对查询结果进行重排序，
        并可选地进行去重。

        Args:
            results: 查询结果列表，每个结果应包含 'content' 和 'score' 字段
            query: 查询文本
            top_n: 返回前 N 个结果，如果为 None 则使用配置中的值
            method: 排序方法，如果为 None 则使用配置中的值

        Returns:
            List[RankedResult]: 排序后的结果列表

        Raises:
            ValidationError: 参数验证失败
            QueryError: 排序执行失败

        Example:
            >>> results = [
            ...     {"content": "糖尿病症状", "score": 0.7},
            ...     {"content": "高血压治疗", "score": 0.9}
            ... ]
            >>> ranked = ranker.rerank(results, query="糖尿病", top_n=1)
            >>> assert ranked[0].content == "糖尿病症状"
        """
        # 验证输入
        if not results:
            self._logger.warning("结果列表为空，返回空列表")
            return []

        if not query or not query.strip():
            raise ValidationError(
                "查询文本不能为空",
                field="query",
                value=query,
            )

        # 验证结果格式
        for i, result in enumerate(results):
            if "content" not in result:
                raise ValidationError(
                    "结果缺少 'content' 字段",
                    field=f"results[{i}].content",
                    value=result,
                )
            if "score" not in result:
                raise ValidationError(
                    "结果缺少 'score' 字段",
                    field=f"results[{i}].score",
                    value=result,
                )

        # 确定参数
        if top_n is None:
            top_n = self._config.top_n
        if method is None:
            method = self._config.method

        self._logger.info(
            f"开始重排序 | 结果数量: {len(results)} | "
            f"方法: {method.value} | top_n: {top_n}"
        )

        try:
            # 1. 去重
            deduplicated = self._deduplicate(results)

            # 2. 根据方法排序
            ranked: List[RankedResult]
            if method == RankingMethod.RERANK and self._rerank_func is not None:
                ranked = self._rerank_results(deduplicated, query)
            elif method == RankingMethod.DIVERSITY:
                ranked = self._diversity_rank(deduplicated, query)
            else:  # SCORE
                ranked = self._score_rank(deduplicated)

            # 3. 截取 top_n
            final_results: List[RankedResult] = ranked[:top_n]

            # 4. 更新排名
            for i, result in enumerate(final_results):  # type: ignore[assignment]
                result.rank = i + 1  # type: ignore[attr-defined]

            self._logger.info(
                f"重排序完成 | 原始: {len(results)} | "
                f"去重后: {len(deduplicated)} | "
                f"最终: {len(final_results)}"
            )

            return final_results

        except Exception as e:
            self._logger.error(f"重排序失败 | 错误: {e}", exc_info=True)
            raise QueryError(
                f"重排序执行失败: {e}",
                details={
                    "method": method.value,
                    "result_count": len(results),
                    "query": query,
                },
            ) from e

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复的结果。

        Args:
            results: 原始结果列表

        Returns:
            去重后的结果列表
        """
        if self._config.dedup_method == DedupMethod.NONE:
            return results[:]

        deduplicated: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for result in results:
            content = result.get("content", "")

            if self._config.dedup_method == DedupMethod.FINGERPRINT:
                # 使用指纹去重
                fingerprint = self._compute_fingerprint(content)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                deduplicated.append(result)

            else:  # CONTENT
                # 基于内容相似度去重
                is_duplicate = False
                for existing in deduplicated:
                    similarity = self._compute_similarity(
                        content,
                        existing.get("content", ""),
                    )
                    if similarity >= self._config.dedup_threshold:
                        is_duplicate = True
                        # 保留分数更高的结果
                        if result.get("score", 0) > existing.get("score", 0):
                            deduplicated.remove(existing)
                            deduplicated.append(result)
                        break

                if not is_duplicate:
                    deduplicated.append(result)

        if len(deduplicated) < len(results):
            self._logger.info(
                f"去重完成 | 原始: {len(results)} | 去重后: {len(deduplicated)}"
            )

        return deduplicated

    def _score_rank(self, results: List[Dict[str, Any]]) -> List[RankedResult]:
        """基于分数排序。

        Args:
            results: 结果列表

        Returns:
            排序后的 RankedResult 列表
        """
        # 按分数降序排序
        sorted_results = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        # 转换为 RankedResult
        ranked = [
            RankedResult(
                content=result.get("content", ""),
                score=result.get("score", 0),
                original_index=i,
                metadata=result.get("metadata", {}),
            )
            for i, result in enumerate(sorted_results)
        ]

        return ranked

    def _rerank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[RankedResult]:
        """使用重排序模型重排序。

        Args:
            results: 结果列表
            query: 查询文本

        Returns:
            重排序后的 RankedResult 列表
        """
        if self._rerank_func is None:
            self._logger.warning("重排序函数未设置，回退到分数排序")
            return self._score_rank(results)

        try:
            # 调用重排序函数
            new_scores = self._rerank_func(results, query)

            if len(new_scores) != len(results):
                raise ValueError(
                    f"重排序函数返回的分数数量 ({len(new_scores)}) "
                    f"与结果数量 ({len(results)}) 不匹配"
                )

            # 更新分数并排序
            for i, result in enumerate(results):
                result["rerank_score"] = new_scores[i]

            sorted_results = sorted(
                results,
                key=lambda x: x.get("rerank_score", x.get("score", 0)),
                reverse=True,
            )

            # 转换为 RankedResult
            ranked = [
                RankedResult(
                    content=result.get("content", ""),
                    score=result.get("rerank_score", result.get("score", 0)),
                    original_index=i,
                    metadata={
                        **result.get("metadata", {}),
                        "original_score": result.get("score", 0),
                    },
                )
                for i, result in enumerate(sorted_results)
            ]

            self._logger.info("重排序模型排序完成")
            return ranked

        except Exception as e:
            self._logger.error(f"重排序模型失败: {e}，回退到分数排序")
            return self._score_rank(results)

    def _diversity_rank(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[RankedResult]:
        """多样性排序（MMR 算法）。

        使用 Maximal Marginal Relevance (MMR) 算法进行多样性排序，
        平衡相关性和多样性。

        Args:
            results: 结果列表
            query: 查询文本

        Returns:
            多样性排序后的 RankedResult 列表
        """
        if not results:
            return []

        lambda_param = self._config.diversity_lambda
        selected: List[Dict[str, Any]] = []
        remaining = results[:]

        # 选择第一个（相关性最高的）
        remaining.sort(key=lambda x: x.get("score", 0), reverse=True)
        selected.append(remaining.pop(0))

        # 迭代选择后续结果
        best_score: float = 0.0  # 初始化 MMR 分数
        while remaining and len(selected) < len(results):
            best_score = -float("inf")
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # 计算相关性分数
                relevance = candidate.get("score", 0)

                # 计算与已选结果的最大相似度
                max_similarity = 0.0
                for sel in selected:
                    sim = self._compute_similarity(
                        candidate.get("content", ""),
                        sel.get("content", ""),
                    )
                    max_similarity = max(max_similarity, sim)

                # MMR 分数
                mmr_score = (
                    lambda_param * relevance - (1 - lambda_param) * max_similarity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            # 选择最佳候选
            selected.append(remaining.pop(best_idx))

        # 转换为 RankedResult
        ranked = [
            RankedResult(
                content=result.get("content", ""),
                score=result.get("score", 0),
                original_index=i,
                metadata={
                    **result.get("metadata", {}),
                    "mmr_score": best_score if i > 0 else result.get("score", 0),
                },
            )
            for i, result in enumerate(selected)
        ]

        self._logger.info(
            f"多样性排序完成 | lambda: {lambda_param} | 结果数量: {len(ranked)}"
        )

        return ranked

    @staticmethod
    def _compute_fingerprint(text: str) -> str:
        """计算文本指纹。

        使用 MD5 哈希计算文本的指纹。

        Args:
            text: 文本内容

        Returns:
            文本指纹（MD5 哈希）
        """
        # 标准化文本
        normalized = " ".join(text.lower().split())
        # 计算 MD5 哈希
        return hashlib.md5(normalized.encode()).hexdigest()

    @staticmethod
    def _compute_similarity(text1: str, text2: str) -> float:
        """计算两个文本的相似度。

        使用简单的 Jaccard 相似度。

        Args:
            text1: 文本 1
            text2: 文本 2

        Returns:
            相似度分数（0-1）
        """
        if not text1 or not text2:
            return 0.0

        # 分词
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Jaccard 相似度
        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    async def arerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_n: Optional[int] = None,
        method: Optional[RankingMethod] = None,
    ) -> List[RankedResult]:
        """异步重排序查询结果。

        Args:
            results: 查询结果列表
            query: 查询文本
            top_n: 返回前 N 个结果
            method: 排序方法

        Returns:
            List[RankedResult]: 排序后的结果列表

        Example:
            >>> ranked = await ranker.arerank(results, query="糖尿病")
        """
        # 如果重排序函数是异步的，需要特殊处理
        # 这里使用 asyncio.to_thread 在线程池中运行同步函数
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.rerank(results, query, top_n, method)
        )

    def get_config(self) -> RankingConfig:
        """获取当前配置。

        Returns:
            排序配置
        """
        return self._config

    def update_config(self, **kwargs: Any) -> None:
        """更新配置。

        Args:
            **kwargs: 要更新的配置参数

        Example:
            >>> ranker.update_config(top_n=10, method=RankingMethod.DIVERSITY)
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                self._logger.warning(f"未知配置参数: {key}")

        # 验证更新后的配置
        try:
            RankingConfig.__post_init__(self._config)
            self._logger.info(f"配置已更新: {kwargs}")
        except ValueError as e:
            raise ValidationError(
                f"更新后的配置无效: {e}",
                field="config",
                value=kwargs,
            ) from e


# ==================== 辅助函数 ====================


def create_ranker(
    method: str = "score",
    dedup: bool = True,
    top_n: int = 5,
    rerank_func: Optional[
        Callable[[List[Dict[str, Any]], str], List[float]]
    ] = None,
) -> ResultRanker:
    """创建结果排序器的便捷函数。

    Args:
        method: 排序方法 (score, rerank, diversity)
        dedup: 是否启用去重
        top_n: 返回前 N 个结果
        rerank_func: 可选的重排序函数

    Returns:
        ResultRanker: 配置好的结果排序器

    Example:
        >>> ranker = create_ranker(method="diversity", top_n=10)
    """
    config = RankingConfig(
        method=RankingMethod(method),
        dedup_method=DedupMethod.CONTENT if dedup else DedupMethod.NONE,
        top_n=top_n,
        enable_rerank=(rerank_func is not None),
    )

    return ResultRanker(config=config, rerank_func=rerank_func)


# ==================== 导出的公共接口 ====================

__all__ = [
    "ResultRanker",
    "RankedResult",
    "RankingConfig",
    "RankingMethod",
    "DedupMethod",
    "create_ranker",
]
