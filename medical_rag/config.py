"""
Medical RAG 配置类

提供统一的配置管理，支持：
1. RAG Anything (LightRAG-HKU) 配置参数
2. Neo4j 图数据库连接配置
3. Milvus 向量数据库连接配置
4. 配置验证逻辑
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, validator, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jConfig(BaseModel):
    """Neo4j 图数据库配置"""
    
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j 连接 URI"
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j 用户名"
    )
    password: str = Field(
        default="password",
        description="Neo4j 密码"
    )
    database: str = Field(
        default="neo4j",
        description="数据库名称"
    )
    
    @validator('uri')
    def validate_uri(cls, v):
        if not v.startswith(('bolt://', 'neo4j://', 'bolt+s://', 'neo4j+s://')):
            raise ValueError(f"无效的 Neo4j URI: {v}，必须以 bolt:// 或 neo4j:// 开头")
        return v


class MilvusConfig(BaseModel):
    """Milvus 向量数据库配置"""
    
    host: str = Field(
        default="localhost",
        description="Milvus 服务器地址"
    )
    port: int = Field(
        default=19530,
        description="Milvus 服务器端口"
    )
    collection_name: str = Field(
        default="medical_rag",
        description="集合名称"
    )
    index_type: str = Field(
        default="HNSW",
        description="索引类型 (HNSW, IVF_FLAT, etc.)"
    )
    metric_type: str = Field(
        default="COSINE",
        description="距离度量类型 (COSINE, L2, IP)"
    )
    embedding_dim: int = Field(
        default=3072,
        description="嵌入向量维度"
    )
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError(f"无效的端口号: {v}，必须在 1-65535 之间")
        return v
    
    @validator('embedding_dim')
    def validate_embedding_dim(cls, v):
        if v <= 0:
            raise ValueError(f"无效的嵌入维度: {v}，必须大于 0")
        return v


class LLMConfig(BaseModel):
    """LLM 模型配置"""
    
    provider: str = Field(
        default="openai",
        description="LLM 提供商 (openai, anthropic, etc.)"
    )
    model: str = Field(
        default="gpt-4o",
        description="模型名称"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL"
    )
    temperature: float = Field(
        default=0.7,
        description="温度参数"
    )
    max_tokens: int = Field(
        default=2000,
        description="最大生成 token 数"
    )
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError(f"无效的温度值: {v}，必须在 0-2 之间")
        return v


class EmbeddingConfig(BaseModel):
    """嵌入模型配置"""
    
    provider: str = Field(
        default="openai",
        description="嵌入提供商 (openai, sentence-transformers, etc.)"
    )
    model: str = Field(
        default="text-embedding-3-large",
        description="嵌入模型名称"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL"
    )
    embedding_dim: int = Field(
        default=3072,
        description="嵌入向量维度"
    )
    batch_size: int = Field(
        default=32,
        description="批量处理大小"
    )


class RAGConfig(BaseModel):
    """RAG Anything (LightRAG-HKU) 配置"""
    
    working_dir: str = Field(
        default="./rag_storage",
        description="RAG 工作目录"
    )
    chunk_token_size: int = Field(
        default=1200,
        description="文本块 token 大小"
    )
    chunk_overlap_token_size: int = Field(
        default=100,
        description="文本块重叠 token 大小"
    )
    tiktoken_model_name: str = Field(
        default="gpt-4o",
        description="Tiktoken 模型名称"
    )
    max_token_size: int = Field(
        default=8192,
        description="最大 token 大小"
    )
    embedding_dim: int = Field(
        default=3072,
        description="嵌入向量维度"
    )
    enable_llm_cache: bool = Field(
        default=True,
        description="是否启用 LLM 缓存"
    )
    # 实体提取配置
    entity_extract_max_gleaning: int = Field(
        default=1,
        description="实体提取最大轮数"
    )
    # 图存储配置
    graph_storage_cls: Optional[str] = Field(
        default=None,
        description="图存储类名称"
    )
    # 向量存储配置
    vector_storage_cls: Optional[str] = Field(
        default=None,
        description="向量存储类名称"
    )
    
    @validator('working_dir')
    def validate_working_dir(cls, v):
        # 将相对路径转换为绝对路径
        path = Path(v).expanduser().absolute()
        # 创建目录（如果不存在）
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @validator('chunk_token_size')
    def validate_chunk_size(cls, v):
        if v <= 0:
            raise ValueError(f"无效的块大小: {v}，必须大于 0")
        return v
    
    @validator('embedding_dim')
    def validate_embedding_dim(cls, v):
        if v <= 0:
            raise ValueError(f"无效的嵌入维度: {v}，必须大于 0")
        return v


class MedicalRAGConfig(BaseSettings):
    """
    Medical RAG 统一配置类
    
    支持从环境变量和 .env 文件加载配置。
    优先级：环境变量 > .env 文件 > 默认值
    """
    
    # 模型配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )
    
    # RAG 核心配置
    rag: RAGConfig = Field(
        default_factory=RAGConfig,
        description="RAG 引擎配置"
    )
    
    # LLM 配置
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM 模型配置"
    )
    
    # 嵌入配置
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="嵌入模型配置"
    )
    
    # Neo4j 配置
    neo4j: Neo4jConfig = Field(
        default_factory=Neo4jConfig,
        description="Neo4j 图数据库配置"
    )
    
    # Milvus 配置
    milvus: MilvusConfig = Field(
        default_factory=MilvusConfig,
        description="Milvus 向量数据库配置"
    )
    
    # 应用配置
    app_name: str = Field(
        default="Medical RAG",
        description="应用名称"
    )
    debug: bool = Field(
        default=False,
        description="调试模式"
    )
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    @root_validator(skip_on_failure=True)
    def validate_configs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置一致性"""
        rag: RAGConfig = values.get("rag")
        embedding: EmbeddingConfig = values.get("embedding")
        milvus: MilvusConfig = values.get("milvus")
        
        if rag and embedding:
            # 确保 RAG 和嵌入配置的维度一致
            if rag.embedding_dim != embedding.embedding_dim:
                raise ValueError(
                    f"RAG 嵌入维度 ({rag.embedding_dim}) 与嵌入模型维度 "
                    f"({embedding.embedding_dim}) 不一致"
                )
        
        if milvus and embedding:
            # 确保 Milvus 和嵌入配置的维度一致
            if milvus.embedding_dim != embedding.embedding_dim:
                raise ValueError(
                    f"Milvus 嵌入维度 ({milvus.embedding_dim}) 与嵌入模型维度 "
                    f"({embedding.embedding_dim}) 不一致"
                )
        
        return values
    
    def to_lightrag_kwargs(self) -> Dict[str, Any]:
        """
        转换为 LightRAG-HKU 初始化参数
        
        Returns:
            LightRAG 初始化参数字典
        """
        return {
            "working_dir": self.rag.working_dir,
            "chunk_token_size": self.rag.chunk_token_size,
            "chunk_overlap_token_size": self.rag.chunk_overlap_token_size,
            "tiktoken_model_name": self.rag.tiktoken_model_name,
            "max_token_size": self.rag.max_token_size,
            "embedding_dim": self.rag.embedding_dim,
            "enable_llm_cache": self.rag.enable_llm_cache,
        }
    
    def get_neo4j_kwargs(self) -> Dict[str, Any]:
        """
        获取 Neo4j 连接参数
        
        Returns:
            Neo4j 连接参数字典
        """
        return {
            "uri": self.neo4j.uri,
            "username": self.neo4j.username,
            "password": self.neo4j.password,
            "database": self.neo4j.database,
        }
    
    def get_milvus_kwargs(self) -> Dict[str, Any]:
        """
        获取 Milvus 连接参数
        
        Returns:
            Milvus 连接参数字典
        """
        return {
            "host": self.milvus.host,
            "port": self.milvus.port,
            "collection_name": self.milvus.collection_name,
        }
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "MedicalRAGConfig":
        """
        从环境变量和 .env 文件加载配置
        
        Args:
            env_file: .env 文件路径（可选）
        
        Returns:
            MedicalRAGConfig 实例
        """
        if env_file:
            return cls(_env_file=env_file)
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MedicalRAGConfig":
        """
        从字典创建配置
        
        Args:
            config_dict: 配置字典
        
        Returns:
            MedicalRAGConfig 实例
        """
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        return self.model_dump()


def load_config(
    config_path: Optional[str] = None,
    env_file: Optional[str] = None,
) -> MedicalRAGConfig:
    """
    加载配置的便捷函数
    
    Args:
        config_path: 配置文件路径（JSON/YAML）
        env_file: .env 文件路径
    
    Returns:
        MedicalRAGConfig 实例
    """
    if config_path:
        # TODO: 实现从 JSON/YAML 文件加载
        raise NotImplementedError("从配置文件加载尚未实现")
    
    return MedicalRAGConfig.from_env(env_file)
