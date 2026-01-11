# 配置管理使用指南

## 概述

`src/core/config.py` 模块提供了集中式的配置管理功能，使用 Pydantic Settings 从环境变量和 `.env` 文件加载配置。

## 快速开始

### 1. 创建配置文件

复制示例配置文件：

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

填写必需的配置项（至少需要 `OPENAI_API_KEY`）：

```bash
OPENAI_API_KEY=your-actual-api-key-here
```

### 3. 在代码中使用配置

```python
from src.core.config import get_settings

# 获取配置实例（单例）
settings = get_settings()

# 访问配置项
api_key = settings.openai_api_key
model = settings.llm_model
neo4j_uri = settings.neo4j_uri

print(f"使用模型: {model}")
print(f"Neo4j URI: {neo4j_uri}")
```

## 配置项说明

### LLM 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `openai_api_key` | `OPENAI_API_KEY` | *必需* | OpenAI API 密钥 |
| `openai_api_base` | `OPENAI_API_BASE` | `None` | OpenAI API 基础 URL（可选） |
| `llm_model` | `LLM_MODEL` | `gpt-4o-mini` | 语言模型名称 |
| `embedding_model` | `EMBEDDING_MODEL` | `text-embedding-3-large` | 嵌入模型名称 |

### Neo4j 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `neo4j_uri` | `NEO4J_URI` | `neo4j://localhost:7687` | Neo4j 连接 URI |
| `neo4j_username` | `NEO4J_USERNAME` | `neo4j` | Neo4j 用户名 |
| `neo4j_password` | `NEO4J_PASSWORD` | `password` | Neo4j 密码 |

### Milvus 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `milvus_uri` | `MILVUS_URI` | `http://localhost:19530` | Milvus 连接 URI |
| `milvus_token` | `MILVUS_TOKEN` | `None` | Milvus 认证令牌 |
| `milvus_api_key` | `MILVUS_API_KEY` | `None` | Milvus API 密钥 |

### RAG-Anything 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `rag_working_dir` | `RAG_WORKING_DIR` | `./data/rag_storage` | RAG 工作目录 |
| `rag_workspace` | `RAG_WORKSPACE` | `medical` | RAG 工作空间名称 |

### 医学实体类型

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `medical_entity_types` | `MEDICAL_ENTITY_TYPES` | 7 种类型 | 医学实体类型列表 |

默认实体类型：
- `DISEASE` - 疾病/问题
- `MEDICINE` - 药物
- `SYMPTOM` - 症状
- `ANATOMICAL_STRUCTURE` - 解剖结构
- `BODY_FUNCTION` - 身体功能
- `LABORATORY_DATA` - 实验室数据
- `PROCEDURE` - 医疗程序

## 高级用法

### 直接创建 Settings 实例

```python
from src.core.config import Settings

# 直接创建（不会使用缓存）
settings = Settings()
```

### 重新加载配置

```python
from src.core.config import reload_settings

# 清除缓存并重新加载
new_settings = reload_settings()
```

### 自定义实体类型

在 `.env` 文件中设置：

```bash
MEDICAL_ENTITY_TYPES=["DISEASE","MEDICINE","SYMPTOM","CUSTOM_TYPE"]
```

或在代码中：

```python
from src.core.config import Settings

settings = Settings(medical_entity_types=["DISEASE", "MEDICINE"])
```

## 配置验证

配置模块包含以下验证：

1. **URI 格式验证**
   - Neo4j URI 必须以 `neo4j://`、`bolt://`、`neo4j+s://` 或 `bolt+s://` 开头
   - Milvus URI 必须以 `http://` 或 `https://` 开头

2. **实体类型验证**
   - 实体类型列表不能为空
   - 实体类型会自动转换为大写

3. **必需字段验证**
   - `openai_api_key` 是必需的，缺少时会抛出 `ValidationError`

## 配置优先级

配置加载优先级（从高到低）：

1. 环境变量
2. `.env` 文件
3. 代码中的默认值

## 示例

### 示例 1：基本使用

```python
from src.core.config import get_settings

settings = get_settings()

print(f"LLM 模型: {settings.llm_model}")
print(f"嵌入模型: {settings.embedding_model}")
print(f"Neo4j URI: {settings.neo4j_uri}")
print(f"Milvus URI: {settings.milvus_uri}")
```

### 示例 2：访问医学实体类型

```python
from src.core.config import get_settings

settings = get_settings()

for entity_type in settings.medical_entity_types:
    print(f"支持的实体类型: {entity_type}")
```

### 示例 3：使用环境变量覆盖

```bash
# 在终端中设置
export OPENAI_API_KEY="your-key"
export LLM_MODEL="gpt-4o"
python your_script.py
```

或在 Python 中：

```python
import os
os.environ["OPENAI_API_KEY"] = "your-key"
os.environ["LLM_MODEL"] = "gpt-4o"

from src.core.config import get_settings
settings = get_settings()
```

## 错误处理

```python
from src.core.config import Settings
from pydantic import ValidationError

try:
    settings = Settings(openai_api_key="test-key")
except ValidationError as e:
    print(f"配置验证失败: {e}")
```

## 注意事项

1. **安全性**：不要将 `.env` 文件提交到版本控制系统
2. **密码**：生产环境中使用强密码
3. **API 密钥**：妥善保管 API 密钥，不要泄露
4. **URI 格式**：确保数据库 URI 格式正确
5. **缓存**：`get_settings()` 使用缓存，如需重新加载使用 `reload_settings()`
