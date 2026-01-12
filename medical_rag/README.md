# Medical RAG 配置模块

本模块提供了 Medical RAG 系统的统一配置管理。

## 功能特性

### 1. 多层次配置结构

- **RAGConfig**: RAG Anything (LightRAG-HKU) 核心配置
  - 工作目录、文本分块、token 限制等
  
- **LLMConfig**: 大语言模型配置
  - 支持 OpenAI、Anthropic 等多种提供商
  
- **EmbeddingConfig**: 嵌入模型配置
  - 支持 OpenAI Embeddings、Sentence Transformers 等
  
- **Neo4jConfig**: Neo4j 图数据库连接配置
  
- **MilvusConfig**: Milvus 向量数据库连接配置

### 2. 配置来源

支持多种配置来源，优先级如下：

1. 环境变量（最高优先级）
2. `.env` 文件
3. 默认值（最低优先级）

### 3. 配置验证

- 自动验证配置参数的合法性
- 确保相关配置的一致性（如嵌入维度）
- 提供清晰的错误提示

## 使用示例

### 基本使用

```python
from medical_rag.config import MedicalRAGConfig

# 从默认配置和环境变量加载
config = MedicalRAGConfig()

# 访问配置
print(config.rag.working_dir)
print(config.neo4j.uri)
print(config.milvus.host)
```

### 从 .env 文件加载

```python
from medical_rag.config import MedicalRAGConfig

# 指定 .env 文件路径
config = MedicalRAGConfig.from_env(env_file=".env.local")
```

### 从字典创建配置

```python
from medical_rag.config import MedicalRAGConfig

config_dict = {
    "rag": {
        "working_dir": "/path/to/rag_storage",
        "chunk_token_size": 1500,
    },
    "neo4j": {
        "uri": "bolt://localhost:7687",
        "password": "your-password",
    }
}

config = MedicalRAGConfig.from_dict(config_dict)
```

### 获取组件初始化参数

```python
from medical_rag.config import MedicalRAGConfig

config = MedicalRAGConfig()

# 获取 LightRAG 初始化参数
lightrag_kwargs = config.to_lightrag_kwargs()

# 获取 Neo4j 连接参数
neo4j_kwargs = config.get_neo4j_kwargs()

# 获取 Milvus 连接参数
milvus_kwargs = config.get_milvus_kwargs()
```

## 环境变量配置

环境变量使用 `__` 作为嵌套分隔符。例如：

```bash
# RAG 配置
RAG__WORKING_DIR=./rag_storage
RAG__CHUNK_TOKEN_SIZE=1200

# Neo4j 配置
NEO4J__URI=bolt://localhost:7687
NEO4J__PASSWORD=your-password

# Milvus 配置
MILVUS__HOST=localhost
MILVUS__PORT=19530
```

详细配置示例请参考项目根目录的 `.env.example` 文件。

## 配置验证规则

1. **端口号验证**: 必须在 1-65535 之间
2. **URI 验证**: Neo4j URI 必须以 `bolt://` 或 `neo4j://` 开头
3. **维度一致性**: RAG、Embedding、Milvus 的嵌入维度必须一致
4. **数值范围**: 温度、token 大小等参数必须在合理范围内

## 依赖关系

- `pydantic>=2.0.0`: 配置模型和验证
- `pydantic-settings>=2.0.0`: 从环境变量加载配置
- `python-dotenv>=1.0.0`: 加载 .env 文件
