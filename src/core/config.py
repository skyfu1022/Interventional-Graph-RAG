"""
核心配置管理模块。

该模块负责管理项目的所有配置信息，包括：
- LLM 配置（OpenAI API）
- Neo4j 图数据库配置
- Milvus 向量数据库配置
- RAG-Anything 配置
- 医学领域实体类型配置

配置加载优先级：
1. 环境变量（最高优先级）
2. .env 文件
3. 代码中的默认值（最低优先级）

使用示例：
    >>> from src.core.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.llm_model)
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置类。

    使用 Pydantic Settings 从环境变量和 .env 文件加载配置。
    支持类型验证、自动转换和默认值设置。

    Attributes:
        openai_api_key: OpenAI API 密钥（必需）
        openai_api_base: OpenAI API 基础 URL（可选）
        llm_model: 使用的语言模型名称
        embedding_model: 使用的嵌入模型名称
        neo4j_uri: Neo4j 数据库连接 URI
        neo4j_username: Neo4j 数据库用户名
        neo4j_password: Neo4j 数据库密码
        milvus_uri: Milvus 向量数据库连接 URI
        milvus_token: Milvus 认证令牌（可选）
        milvus_api_key: Milvus API 密钥（可选）
        rag_working_dir: RAG-Anything 工作目录
        rag_workspace: RAG-Anything 工作空间名称
        medical_entity_types: 医学领域实体类型列表
    """

    # ========== LLM 配置 ==========
    openai_api_key: str = Field(
        ..., description="OpenAI API 密钥，用于访问 LLM 和嵌入模型"
    )
    openai_api_base: Optional[str] = Field(
        None, description="OpenAI API 基础 URL，用于使用代理或自定义端点"
    )
    llm_model: str = Field(
        default="gpt-4o-mini", description="用于文本生成和推理的语言模型"
    )
    embedding_model: str = Field(
        default="text-embedding-3-large", description="用于生成文本嵌入向量的模型"
    )

    # ========== Neo4j 配置（图存储）==========
    neo4j_uri: str = Field(
        default="neo4j://localhost:7687",
        description="Neo4j 数据库连接 URI，格式：neo4j://host:port",
    )
    neo4j_username: str = Field(default="neo4j", description="Neo4j 数据库用户名")
    neo4j_password: str = Field(default="password", description="Neo4j 数据库密码")

    # ========== Milvus 配置（向量存储）==========
    milvus_uri: str = Field(
        default="http://localhost:19530", description="Milvus 向量数据库连接 URI"
    )
    milvus_token: Optional[str] = Field(
        None, description="Milvus 认证令牌（如果使用 Milvus Cloud）"
    )
    milvus_api_key: Optional[str] = Field(
        None, description="Milvus API 密钥（可选认证方式）"
    )

    # ========== RAG-Anything 配置 ==========
    rag_working_dir: str = Field(
        default="./data/rag_storage", description="RAG-Anything 存储工作目录的路径"
    )
    rag_workspace: str = Field(
        default="medical", description="RAG-Anything 工作空间名称，用于隔离不同项目"
    )

    # ========== 医学领域定制 ==========
    medical_entity_types: List[str] = Field(
        default=[
            "DISEASE",  # 疾病/问题
            "MEDICINE",  # 药物
            "SYMPTOM",  # 症状
            "ANATOMICAL_STRUCTURE",  # 解剖结构
            "BODY_FUNCTION",  # 身体功能
            "LABORATORY_DATA",  # 实验室数据
            "PROCEDURE",  # 医疗程序
        ],
        description="医学领域支持的实体类型列表，用于知识图谱构建",
    )

    # Pydantic Settings 配置
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("neo4j_uri")
    @classmethod
    def validate_neo4j_uri(cls, v: str) -> str:
        """验证 Neo4j URI 格式。

        Args:
            v: Neo4j URI 字符串

        Returns:
            验证后的 URI

        Raises:
            ValueError: 如果 URI 格式无效
        """
        if not v.startswith(("neo4j://", "bolt://", "neo4j+s://", "bolt+s://")):
            raise ValueError(
                f"Neo4j URI 必须以 neo4j://, bolt://, neo4j+s:// 或 bolt+s:// 开头，当前值：{v}"
            )
        return v

    @field_validator("milvus_uri")
    @classmethod
    def validate_milvus_uri(cls, v: str) -> str:
        """验证 Milvus URI 格式。

        Args:
            v: Milvus URI 字符串

        Returns:
            验证后的 URI

        Raises:
            ValueError: 如果 URI 格式无效
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Milvus URI 必须以 http:// 或 https:// 开头，当前值：{v}")
        return v

    @field_validator("medical_entity_types")
    @classmethod
    def validate_medical_entity_types(cls, v: List[str]) -> List[str]:
        """验证医学实体类型列表。

        Args:
            v: 实体类型列表

        Returns:
            验证后的实体类型列表

        Raises:
            ValueError: 如果列表为空或包含无效值
        """
        if not v:
            raise ValueError("医学实体类型列表不能为空")

        # 确保所有实体类型都是大写
        return [entity_type.upper() for entity_type in v]


@lru_cache()
def get_settings() -> Settings:
    """获取全局唯一的配置实例（单例模式）。

    使用 lru_cache 装饰器确保整个应用程序生命周期中
    只创建一次 Settings 实例，避免重复加载配置。

    Returns:
        Settings: 全局配置实例

    Example:
        >>> settings = get_settings()
        >>> api_key = settings.openai_api_key
    """
    return Settings()


def reload_settings() -> Settings:
    """重新加载配置（清除缓存并创建新实例）。

    用于测试或需要动态更新配置的场景。
    注意：这不会更新已经获取的 settings 实例。

    Returns:
        Settings: 新的配置实例

    Example:
        >>> new_settings = reload_settings()
    """
    get_settings.cache_clear()
    return get_settings()
