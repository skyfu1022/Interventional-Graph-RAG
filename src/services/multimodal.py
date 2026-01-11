"""
多模态查询服务模块。

该模块提供多模态查询支持，包括：
- 图像查询：支持分析医学影像（如X光片、CT扫描图）
- 表格查询：支持解析和处理表格数据
- 多模态模型集成：使用 LangChain 和 OpenAI 视觉模型

核心功能：
- 图像编码为 Base64 格式
- 表格数据解析和文本化
- 异步查询执行
- 统一的查询结果格式
- 性能监控（延迟、Token 使用量）

使用示例：
    >>> from src.services.multimodal import MultimodalQueryService
    >>> from langchain_openai import ChatOpenAI
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     llm = ChatOpenAI(model="gpt-4o", max_tokens=1024)
    >>>     service = MultimodalQueryService(llm)
    >>>
    >>>     # 图像查询
    >>>     result = await service.query_with_image(
    >>>         query="分析这张X光片显示的异常",
    >>>         image_path="xray.jpg"
    >>>     )
    >>>     print(f"分析结果: {result.answer}")
    >>>
    >>>     # 表格查询
    >>>     table_data = [
    >>>         ["患者", "年龄", "诊断"],
    >>>         ["张三", "45", "高血压"],
    >>>         ["李四", "32", "糖尿病"]
    >>>     ]
    >>>     result = await service.query_with_table(
    >>>         query="从表格中提取所有诊断结果",
    >>>         table_data=table_data
    >>>     )
    >>>     print(f"提取结果: {result.answer}")
    >>>
    >>> asyncio.run(main())
"""

import base64
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field

# LangChain 导入
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage

# 内部模块导入
from src.core.exceptions import QueryError, ValidationError
from src.core.logging import get_logger

# 模块日志
logger = get_logger("src.services.multimodal")


# ==================== 数据类 ====================


@dataclass
class MultimodalQueryResult:
    """多模态查询结果。

    Attributes:
        answer: 模型生成的答案
        latency_ms: 查询耗时（毫秒）
        tokens_used: 使用的 Token 数量（如果有）
        metadata: 额外的元数据信息
    """

    answer: str
    latency_ms: float
    tokens_used: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典格式。

        Returns:
            包含结果信息的字典
        """
        return {
            "answer": self.answer,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
        }


# ==================== 主服务类 ====================


class MultimodalQueryService:
    """多模态查询服务类。

    提供图像和表格数据的查询分析功能，集成 OpenAI 视觉模型。

    Attributes:
        llm: LangChain ChatOpenAI 实例，用于调用 OpenAI API

    Example:
        >>> llm = ChatOpenAI(model="gpt-4o", max_tokens=1024)
        >>> service = MultimodalQueryService(llm)
        >>> result = await service.query_with_image("描述这张图", "xray.jpg")
    """

    # 支持的图像格式
    SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    def __init__(self, llm: ChatOpenAI) -> None:
        """初始化多模态查询服务。

        Args:
            llm: LangChain ChatOpenAI 实例

        Raises:
            ValidationError: 如果 LLM 实例无效
        """
        # 更宽松的类型检查：检查是否有必要的属性和方法
        if not (hasattr(llm, "ainvoke") and callable(llm.ainvoke)):
            raise ValidationError(
                f"LLM 必须有 ainvoke 方法，当前类型: {type(llm).__name__}",
                field="llm",
                value=type(llm).__name__,
            )

        if not hasattr(llm, "model_name"):
            raise ValidationError(
                f"LLM 必须有 model_name 属性，当前类型: {type(llm).__name__}",
                field="llm",
                value=type(llm).__name__,
            )

        self.llm = llm
        logger.info(
            f"初始化 MultimodalQueryService，模型: {llm.model_name}, "
            f"最大 Token: {getattr(llm, 'max_tokens', 'N/A')}"
        )

    # ==================== 图像查询方法 ====================

    async def query_with_image(
        self,
        query: str,
        image_path: Union[str, Path],
        detail: str = "auto",
    ) -> MultimodalQueryResult:
        """使用图像执行查询。

        该方法将图像编码为 Base64 格式，并使用多模态模型分析图像内容。

        Args:
            query: 查询文本，描述需要分析的内容
            image_path: 图像文件路径
            detail: 图像细节级别，可选值: "low", "auto", "high"

        Returns:
            MultimodalQueryResult: 包含答案、耗时等信息的查询结果

        Raises:
            ValidationError: 如果参数验证失败
            QueryError: 如果查询执行失败
            FileNotFoundError: 如果图像文件不存在

        Example:
            >>> result = await service.query_with_image(
            ...     query="这张X光片显示什么异常？",
            ...     image_path="xray.jpg"
            ... )
            >>> print(result.answer)
        """
        # 验证参数
        self._validate_query(query)

        logger.info(f"开始图像查询: {query}, 图像: {image_path}")

        # 记录开始时间
        start_time = time.time()

        try:
            # 验证图像路径
            image_path = self._validate_image_path(image_path)

            # 读取并编码图像
            image_base64 = self._encode_image_to_base64(image_path)
            image_format = Path(image_path).suffix.lstrip(".").lower()

            # 构造多模态消息
            message = HumanMessage(
                content=[
                    {"type": "text", "text": query},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image_base64}",
                            "detail": detail,
                        },
                    },
                ]
            )

            # 调用模型
            logger.debug(f"发送多模态查询请求到模型 {self.llm.model_name}")
            response: BaseMessage = await self.llm.ainvoke([message])

            # 计算耗时
            latency_ms = (time.time() - start_time) * 1000

            # 提取 Token 使用量（如果有）
            tokens_used = None
            usage_metadata = getattr(response, "usage_metadata", None)  # type: ignore[arg-type]
            if usage_metadata:
                tokens_used = usage_metadata.get("total_tokens")  # type: ignore[arg-type]

            # 提取答案
            answer = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )

            logger.info(
                f"图像查询完成，耗时: {latency_ms:.2f}ms, "
                f"Token: {tokens_used}, 答案长度: {len(answer)}"
            )

            return MultimodalQueryResult(
                answer=answer,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={"image_path": str(image_path), "detail": detail},
            )

        except FileNotFoundError as e:
            logger.error(f"图像文件不存在: {image_path}")
            raise QueryError(
                f"图像文件不存在: {image_path}",
                details={"image_path": str(image_path), "original_error": str(e)},
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"图像查询失败: {e}", exc_info=True)
            raise QueryError(
                f"图像查询失败: {str(e)}",
                details={
                    "query": query,
                    "image_path": str(image_path),
                    "latency_ms": latency_ms,
                },
            ) from e

    async def query_with_images(
        self,
        query: str,
        image_paths: List[Union[str, Path]],
        detail: str = "auto",
    ) -> MultimodalQueryResult:
        """使用多张图像执行查询。

        该方法支持同时分析多张图像，适用于需要对比或多角度分析的场景。

        Args:
            query: 查询文本，描述需要分析的内容
            image_paths: 图像文件路径列表
            detail: 图像细节级别，可选值: "low", "auto", "high"

        Returns:
            MultimodalQueryResult: 包含答案、耗时等信息的查询结果

        Raises:
            ValidationError: 如果参数验证失败
            QueryError: 如果查询执行失败

        Example:
            >>> result = await service.query_with_images(
            ...     query="对比这两张X光片的差异",
            ...     image_paths=["xray1.jpg", "xray2.jpg"]
            ... )
            >>> print(result.answer)
        """
        # 验证参数
        self._validate_query(query)
        if not image_paths:
            raise ValidationError(
                "图像路径列表不能为空", field="image_paths", value=image_paths
            )

        if len(image_paths) > 5:
            logger.warning(f"图像数量过多 ({len(image_paths)})，可能导致超时或费用增加")

        logger.info(f"开始多图像查询: {query}, 图像数量: {len(image_paths)}")

        # 记录开始时间
        start_time = time.time()

        try:
            # 构造消息内容
            content = [{"type": "text", "text": query}]

            # 添加所有图像
            for img_path in image_paths:
                img_path = self._validate_image_path(img_path)
                image_base64 = self._encode_image_to_base64(img_path)
                image_format = Path(img_path).suffix.lstrip(".").lower()

                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image_base64}",
                            "detail": detail,
                        },
                    }  # type: ignore[dict-item]
                )

            # 构造多模态消息
            message = HumanMessage(content=content)  # type: ignore[arg-type]

            # 调用模型
            logger.debug(f"发送多模态查询请求到模型 {self.llm.model_name}")
            response: BaseMessage = await self.llm.ainvoke([message])

            # 计算耗时
            latency_ms = (time.time() - start_time) * 1000

            # 提取 Token 使用量（如果有）
            tokens_used = None
            usage_metadata = getattr(response, "usage_metadata", None)  # type: ignore[arg-type]
            if usage_metadata:
                tokens_used = usage_metadata.get("total_tokens")  # type: ignore[arg-type]

            # 提取答案
            answer = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )

            logger.info(
                f"多图像查询完成，耗时: {latency_ms:.2f}ms, "
                f"Token: {tokens_used}, 答案长度: {len(answer)}"
            )

            return MultimodalQueryResult(
                answer=answer,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={
                    "image_count": len(image_paths),
                    "image_paths": [str(p) for p in image_paths],
                    "detail": detail,
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"多图像查询失败: {e}", exc_info=True)
            raise QueryError(
                f"多图像查询失败: {str(e)}",
                details={
                    "query": query,
                    "image_count": len(image_paths),
                    "latency_ms": latency_ms,
                },
            ) from e

    # ==================== 表格查询方法 ====================

    async def query_with_table(
        self,
        query: str,
        table_data: List[List[Any]],
        headers: Optional[List[str]] = None,
        table_format: str = "markdown",
    ) -> MultimodalQueryResult:
        """使用表格数据执行查询。

        该方法将表格数据转换为文本格式，并使用模型分析表格内容。

        Args:
            query: 查询文本，描述需要从表格中提取或分析的内容
            table_data: 表格数据，二维列表格式
            headers: 表格头部（可选），如果不提供则使用第一行作为头部
            table_format: 表格格式化方式，可选值: "markdown", "json", "text"

        Returns:
            MultimodalQueryResult: 包含答案、耗时等信息的查询结果

        Raises:
            ValidationError: 如果参数验证失败
            QueryError: 如果查询执行失败

        Example:
            >>> table = [
            ...     ["患者", "年龄", "诊断"],
            ...     ["张三", "45", "高血压"],
            ...     ["李四", "32", "糖尿病"]
            ... ]
            >>> result = await service.query_with_table(
            ...     query="从表格中提取所有诊断结果",
            ...     table_data=table
            ... )
            >>> print(result.answer)
        """
        # 验证参数
        self._validate_query(query)
        self._validate_table_data(table_data)

        logger.info(
            f"开始表格查询: {query}, 表格行数: {len(table_data)}, 格式: {table_format}"
        )

        # 记录开始时间
        start_time = time.time()

        try:
            # 格式化表格
            formatted_table = self._format_table(table_data, headers, table_format)

            # 构造完整的提示词
            full_query = f"{query}\n\n表格数据：\n{formatted_table}"

            # 构造消息
            message = HumanMessage(content=full_query)

            # 调用模型
            logger.debug(f"发送表格查询请求到模型 {self.llm.model_name}")
            response: BaseMessage = await self.llm.ainvoke([message])

            # 计算耗时
            latency_ms = (time.time() - start_time) * 1000

            # 提取 Token 使用量（如果有）
            tokens_used = None
            usage_metadata = getattr(response, "usage_metadata", None)  # type: ignore[arg-type]
            if usage_metadata:
                tokens_used = usage_metadata.get("total_tokens")  # type: ignore[arg-type]

            # 提取答案
            answer = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )

            logger.info(
                f"表格查询完成，耗时: {latency_ms:.2f}ms, "
                f"Token: {tokens_used}, 答案长度: {len(answer)}"
            )

            return MultimodalQueryResult(
                answer=answer,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={
                    "table_rows": len(table_data),
                    "table_format": table_format,
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"表格查询失败: {e}", exc_info=True)
            raise QueryError(
                f"表格查询失败: {str(e)}",
                details={
                    "query": query,
                    "table_rows": len(table_data),
                    "latency_ms": latency_ms,
                },
            ) from e

    # ==================== 辅助方法 ====================

    def _validate_query(self, query: str) -> None:
        """验证查询参数。

        Args:
            query: 查询文本

        Raises:
            ValidationError: 如果查询无效
        """
        if not query or not isinstance(query, str):
            raise ValidationError(
                "查询必须是非空字符串",
                field="query",
                value=query,
                constraint="must be non-empty string",
            )

        if len(query.strip()) == 0:
            raise ValidationError(
                "查询不能为空或仅包含空格",
                field="query",
                value=query,
                constraint="must not be empty or whitespace only",
            )

        if len(query) > 10000:
            logger.warning(f"查询文本过长 ({len(query)} 字符)，可能导致性能问题")

    def _validate_image_path(self, image_path: Union[str, Path]) -> Path:
        """验证图像文件路径。

        Args:
            image_path: 图像文件路径

        Returns:
            Path: 验证后的 Path 对象

        Raises:
            ValidationError: 如果路径无效
            FileNotFoundError: 如果文件不存在
        """
        path = Path(image_path)

        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        # 检查是否为文件
        if not path.is_file():
            raise ValidationError(
                f"路径不是文件: {image_path}",
                field="image_path",
                value=str(image_path),
                constraint="must be a valid file path",
            )

        # 检查文件格式
        if path.suffix.lower() not in self.SUPPORTED_IMAGE_FORMATS:
            raise ValidationError(
                f"不支持的图像格式: {path.suffix}, "
                f"支持的格式: {', '.join(self.SUPPORTED_IMAGE_FORMATS)}",
                field="image_path",
                value=str(image_path),
                constraint=f"must be one of {self.SUPPORTED_IMAGE_FORMATS}",
            )

        return path

    def _encode_image_to_base64(self, image_path: Path) -> str:
        """将图像文件编码为 Base64 格式。

        Args:
            image_path: 图像文件路径

        Returns:
            str: Base64 编码的图像字符串

        Raises:
            IOError: 如果读取文件失败
        """
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")
                logger.debug(
                    f"图像编码完成: {image_path.name}, 大小: {len(image_data)} 字节"
                )
                return image_base64
        except IOError as e:
            logger.error(f"读取图像文件失败: {image_path}, 错误: {e}")
            raise IOError(f"无法读取图像文件: {image_path}") from e

    def _validate_table_data(self, table_data: List[List[Any]]) -> None:
        """验证表格数据。

        Args:
            table_data: 表格数据

        Raises:
            ValidationError: 如果数据无效
        """
        if not table_data or not isinstance(table_data, list):
            raise ValidationError(
                "表格数据必须是非空列表",
                field="table_data",
                value=table_data,
                constraint="must be non-empty list",
            )

        if not all(isinstance(row, list) for row in table_data):
            raise ValidationError(
                "表格数据的每一行必须是列表",
                field="table_data",
                value=table_data,
                constraint="all rows must be lists",
            )

        # 检查所有行的列数是否一致
        if len(table_data) > 1:
            first_row_len = len(table_data[0])
            if not all(len(row) == first_row_len for row in table_data):
                logger.warning("表格数据的行长度不一致，可能导致解析问题")

    def _format_table(
        self,
        table_data: List[List[Any]],
        headers: Optional[List[str]],
        table_format: str,
    ) -> str:
        """将表格数据格式化为指定格式的字符串。

        Args:
            table_data: 表格数据
            headers: 表格头部（可选）
            table_format: 格式化方式

        Returns:
            str: 格式化后的表格字符串

        Raises:
            ValidationError: 如果格式不支持
        """
        if table_format == "markdown":
            return self._format_table_markdown(table_data, headers)
        elif table_format == "json":
            return self._format_table_json(table_data, headers)
        elif table_format == "text":
            return self._format_table_text(table_data, headers)
        else:
            raise ValidationError(
                f"不支持的表格格式: {table_format}",
                field="table_format",
                value=table_format,
                constraint="must be one of: markdown, json, text",
            )

    def _format_table_markdown(
        self,
        table_data: List[List[Any]],
        headers: Optional[List[str]],
    ) -> str:
        """将表格格式化为 Markdown 表格。

        Args:
            table_data: 表格数据
            headers: 表格头部（可选）

        Returns:
            str: Markdown 格式的表格字符串
        """
        # 如果没有提供 headers，使用第一行作为头部
        if headers is None:
            headers = [str(cell) for cell in table_data[0]]
            data_rows = table_data[1:]
        else:
            data_rows = table_data

        # 构造 Markdown 表格
        lines = []

        # 头部行
        lines.append("| " + " | ".join(headers) + " |")

        # 分隔行
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # 数据行
        for row in data_rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        return "\n".join(lines)

    def _format_table_json(
        self,
        table_data: List[List[Any]],
        headers: Optional[List[str]],
    ) -> str:
        """将表格格式化为 JSON。

        Args:
            table_data: 表格数据
            headers: 表格头部（可选）

        Returns:
            str: JSON 格式的表格字符串
        """
        import json

        # 如果没有提供 headers，使用第一行作为头部
        if headers is None:
            headers = [str(cell) for cell in table_data[0]]
            data_rows = table_data[1:]
        else:
            data_rows = table_data

        # 构造 JSON
        json_data = []
        for row in data_rows:
            row_dict = {}
            for i, cell in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = cell
            json_data.append(row_dict)

        return json.dumps(json_data, ensure_ascii=False, indent=2)

    def _format_table_text(
        self,
        table_data: List[List[Any]],
        headers: Optional[List[str]],
    ) -> str:
        """将表格格式化为纯文本。

        Args:
            table_data: 表格数据
            headers: 表格头部（可选）

        Returns:
            str: 纯文本格式的表格字符串
        """
        lines = []

        # 如果有 headers，先输出
        if headers is not None:
            lines.append(" | ".join(str(h) for h in headers))
            lines.append("-" * len(lines[0]))

        # 输出数据行
        for row in table_data:
            lines.append(" | ".join(str(cell) for cell in row))

        return "\n".join(lines)
