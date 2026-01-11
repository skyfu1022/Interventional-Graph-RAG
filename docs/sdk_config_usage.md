# SDK 配置管理功能使用指南

本文档介绍如何使用 Medical Graph RAG SDK 的配置管理功能。

## 功能概述

SDK 提供了两种便捷的客户端创建方式：
- **`from_env()`**: 从环境变量加载配置
- **`from_config()`**: 从配置文件（YAML/JSON）加载配置

## 方式一：从环境变量创建客户端

### 1. 设置环境变量

```bash
# OpenAI 配置
export OPENAI_API_KEY="sk-your-api-key-here"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-4o-mini"  # 可选
export EMBEDDING_MODEL="text-embedding-3-large"  # 可选

# Neo4j 配置
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"

# Milvus 配置
export MILVUS_URI="http://localhost:19530"
export MILVUS_TOKEN=""  # 可选
export MILVUS_API_KEY=""  # 可选

# RAG 配置
export RAG_WORKING_DIR="./data/rag_storage"  # 可选
```

### 2. 创建客户端

```python
from src.sdk import MedGraphClient

# 从环境变量创建客户端
client = MedGraphClient.from_env(
    workspace="medical",
    log_level="INFO"
)

# 使用客户端
config = client.get_config()
print(f"工作空间: {config['workspace']}")
print(f"LLM 模型: {config['llm_model']}")
```

## 方式二：从配置文件创建客户端

### 1. 创建配置文件

**YAML 格式** (`config.yaml`):
```yaml
workspace: "medical"

# OpenAI 配置
openai_api_key: "sk-your-api-key-here"
openai_api_base: null  # 可选
llm_model: "gpt-4o-mini"
embedding_model: "text-embedding-3-large"

# Neo4j 配置
neo4j_uri: "neo4j://localhost:7687"
neo4j_username: "neo4j"
neo4j_password: "password"

# Milvus 配置
milvus_uri: "http://localhost:19530"
milvus_token: null
milvus_api_key: null

# RAG 配置
rag_working_dir: "./data/rag_storage"
rag_workspace: "medical"

# 医学实体类型
medical_entity_types:
  - "DISEASE"
  - "MEDICINE"
  - "SYMPTOM"
  - "ANATOMICAL_STRUCTURE"
  - "BODY_FUNCTION"
  - "LABORATORY_DATA"
  - "PROCEDURE"
```

**JSON 格式** (`config.json`):
```json
{
  "workspace": "medical",
  "openai_api_key": "sk-your-api-key-here",
  "neo4j_uri": "neo4j://localhost:7687",
  "neo4j_username": "neo4j",
  "neo4j_password": "password",
  "milvus_uri": "http://localhost:19530",
  "llm_model": "gpt-4o-mini",
  "embedding_model": "text-embedding-3-large",
  "rag_working_dir": "./data/rag_storage",
  "medical_entity_types": [
    "DISEASE",
    "MEDICINE",
    "SYMPTOM"
  ]
}
```

### 2. 创建客户端

```python
from src.sdk import MedGraphClient

# 从 YAML 文件创建客户端
client = MedGraphClient.from_config("config.yaml", log_level="INFO")

# 或从 JSON 文件创建
client = MedGraphClient.from_config("config.json", log_level="INFO")

# 使用客户端
config = client.get_config()
print(f"配置信息: {config}")
```

## 配置管理方法

### 获取当前配置

```python
client = MedGraphClient.from_env()
config = client.get_config()

# config 包含以下信息（敏感信息已脱敏）:
# - workspace: 工作空间名称
# - llm_model: LLM 模型名称
# - embedding_model: 嵌入模型名称
# - neo4j_uri: Neo4j 连接 URI
# - neo4j_username: Neo4j 用户名
# - milvus_uri: Milvus 连接 URI
# - rag_working_dir: RAG 工作目录
# - medical_entity_types: 医学实体类型列表
```

### 重新加载配置

```python
# 重新加载配置（清除 Pydantic Settings 缓存）
client.reload_config()
```

## 错误处理

```python
from src.sdk import MedGraphClient, ConfigError

try:
    client = MedGraphClient.from_config("config.yaml")
except ConfigError as e:
    print(f"配置错误: {e.message}")
    print(f"配置键: {e.config_key}")
    print(f"配置文件: {e.config_file}")
```

## 完整示例

```python
import asyncio
from src.sdk import MedGraphClient

async def main():
    # 从配置文件创建客户端
    client = MedGraphClient.from_config("config.yaml", log_level="INFO")

    # 初始化客户端
    await client.initialize()

    try:
        # 获取配置信息
        config = client.get_config()
        print(f"工作空间: {config['workspace']}")
        print(f"LLM 模型: {config['llm_model']}")

        # 执行查询
        result = await client.query("什么是糖尿病?")
        print(f"答案: {result.answer}")

    finally:
        # 关闭客户端
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 验证代码

运行项目根目录下的测试脚本验证配置管理功能：

```bash
source venv/bin/activate
python test_sdk_config.py
```

测试脚本会验证以下功能：
- ✓ 从环境变量创建客户端
- ✓ 从 YAML 配置文件创建客户端
- ✓ 从 JSON 配置文件创建客户端
- ✓ 配置验证（缺失必需配置项）
- ✓ 文件不存在错误处理
- ✓ 不支持的格式错误处理
- ✓ 配置重新加载

## 参考文件

- 示例配置文件：
  - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/config.example.yaml`
  - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/config.example.json`
- 验证测试脚本：
  - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/test_sdk_config.py`
- SDK 客户端实现：
  - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/client.py`
- SDK 异常定义：
  - `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/sdk/exceptions.py`
