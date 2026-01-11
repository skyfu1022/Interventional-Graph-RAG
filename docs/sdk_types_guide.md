# SDK 类型定义指南

## 概述

`src/sdk/types.py` 模块定义了 Medical Graph RAG SDK 的所有数据类型，基于 Pydantic v2 提供：

- **类型安全**：编译时类型检查和运行时验证
- **自动序列化**：支持字典和 JSON 格式转换
- **数据验证**：自动验证输入数据的有效性
- **中文文档**：所有类型和方法都有完整的中文文档

## 核心类型

### 1. QueryMode (枚举)

查询模式枚举，定义 6 种知识图谱查询模式：

```python
from src.sdk.types import QueryMode

mode = QueryMode.HYBRID  # 混合检索模式
print(mode.value)  # 输出: "hybrid"
```

**可用模式**：
- `NAIVE`: 简单检索，直接返回相关内容
- `LOCAL`: 局部社区检索，关注实体局部关系
- `GLOBAL`: 全局社区检索，关注图谱全局结构
- `HYBRID`: 混合检索，结合局部和全局优势
- `MIX`: 混合模式，动态调整检索策略
- `BYPASS`: 绕过图谱，直接检索原始文档

### 2. SourceInfo (来源信息)

表示查询结果的来源片段：

```python
from src.sdk.types import SourceInfo

source = SourceInfo(
    doc_id="doc_001",
    chunk_id="chunk_001",
    content="糖尿病是一种代谢疾病...",
    relevance=0.92,  # 相关性评分，范围 [0, 1]
)

# 转换为字典
data = source.to_dict()

# 转换为 JSON
json_str = source.to_json()
```

### 3. GraphContext (图谱上下文)

包含从知识图谱中提取的结构化信息：

```python
from src.sdk.types import GraphContext

context = GraphContext(
    entities=["糖尿病", "胰岛素", "血糖"],
    relationships=["糖尿病-需要-胰岛素治疗"],
    communities=["内分泌疾病"],
)

print(f"实体数量: {len(context.entities)}")
```

### 4. QueryResult (查询结果)

表示知识图谱查询的完整结果：

```python
from src.sdk.types import QueryResult, QueryMode, GraphContext

result = QueryResult(
    query="什么是糖尿病?",
    answer="糖尿病是一种慢性代谢疾病...",
    mode=QueryMode.HYBRID,
    graph_id="medical",
    latency_ms=150,
    retrieval_count=5,
    graph_context=GraphContext(
        entities=["糖尿病", "胰岛素"],
        relationships=["糖尿病-需要-胰岛素"],
    ),
)

# 序列化
json_data = result.to_json()
```

### 5. DocumentInfo (文档信息)

表示文档的元数据和状态信息：

```python
from src.sdk.types import DocumentInfo

doc = DocumentInfo(
    doc_id="doc_001",
    file_name="diabetes.txt",
    file_path="/data/medical/diabetes.txt",
    status="completed",  # pending | processing | completed | failed
    entity_count=156,
    relationship_count=243,
    created_at="2026-01-11T10:00:00Z",
)
```

### 6. GraphInfo (图谱信息)

表示知识图谱的统计信息和元数据：

```python
from src.sdk.types import GraphInfo

graph = GraphInfo(
    graph_id="medical",
    workspace="medical",
    entity_count=5420,
    relationship_count=12800,
    document_count=145,
    created_at="2026-01-11T10:00:00Z",
)
```

### 7. GraphConfig (图谱配置)

定义知识图谱的构建和配置参数：

```python
from src.sdk.types import GraphConfig

# 使用默认配置
config = GraphConfig()

# 自定义配置（小写会自动转大写）
custom_config = GraphConfig(
    workspace="cardiology",
    chunk_size=1024,
    overlap=100,
    entity_types=["disease", "medicine", "procedure"],  # 自动转为 ["DISEASE", "MEDICINE", "PROCEDURE"]
)
```

## Pydantic 特性

### 1. 数据验证

所有类型都包含自动验证逻辑：

```python
from src.sdk.types import SourceInfo
from pydantic import ValidationError

try:
    # 相关性评分超出 [0, 1] 范围会抛出 ValidationError
    invalid_source = SourceInfo(
        doc_id="doc_001",
        chunk_id="chunk_001",
        content="内容",
        relevance=1.5,
    )
except ValidationError as e:
    print(f"验证失败: {e}")
```

### 2. 字段验证器

自定义验证逻辑：

```python
from src.sdk.types import GraphConfig

# 实体类型自动转大写并去重
config = GraphConfig(entity_types=["disease", "MEDICINE", "Disease"])
print(config.entity_types)  # ['MEDICINE', 'DISEASE'] (去重后)

# 空列表会抛出 ValueError
try:
    GraphConfig(entity_types=[])
except ValueError as e:
    print(f"验证失败: {e}")
```

### 3. 配置选项

使用 `ConfigDict` 配置模型行为：

```python
from src.sdk.types import SourceInfo

# 字符串自动去空格
source = SourceInfo(
    doc_id="  doc_001  ",  # 自动转为 "doc_001"
    chunk_id="chunk_001",
    content="content",
)

# 赋值时验证
from pydantic import ValidationError

config = GraphConfig()
try:
    config.chunk_size = -100  # 抛出 ValidationError
except ValidationError as e:
    print(f"验证失败: {e}")
```

### 4. 序列化方法

每个类型都提供三个方法：

```python
from src.sdk.types import QueryResult, QueryMode

result = QueryResult(
    query="测试",
    answer="答案",
    mode=QueryMode.LOCAL,
    graph_id="test",
)

# 转换为字典
data_dict = result.to_dict()

# 转换为 JSON
json_str = result.to_json()

# 从字典恢复
restored = QueryResult.from_dict(data_dict)
```

## 嵌套对象处理

支持嵌套对象的序列化和反序列化：

```python
from src.sdk.types import QueryResult, SourceInfo, GraphContext, QueryMode

result = QueryResult(
    query="糖尿病的症状",
    answer="症状包括...",
    mode=QueryMode.HYBRID,
    graph_id="medical",
    graph_context=GraphContext(
        entities=["糖尿病", "症状"],
        relationships=["糖尿病-具有-症状"],
    ),
    sources=[
        SourceInfo(
            doc_id="doc_001",
            chunk_id="chunk_001",
            content="内容...",
            relevance=0.95,
        )
    ],
)

# 序列化时嵌套对象会自动转换
data = result.to_dict()
print(type(data['graph_context']))  # <class 'dict'>
print(type(data['sources']))  # <class 'list'>

# 反序列化时嵌套对象会自动恢复
restored = QueryResult.from_dict(data)
print(type(restored.graph_context))  # <class 'GraphContext'>
print(type(restored.sources[0]))  # <class 'SourceInfo'>
```

## 最佳实践

### 1. 使用类型注解

```python
from src.sdk.types import QueryResult, QueryMode

def process_query(result: QueryResult) -> dict:
    """处理查询结果。"""
    return result.to_dict()
```

### 2. 利用验证功能

```python
from src.sdk.types import GraphConfig
from pydantic import ValidationError

def create_config(entity_types: list[str]) -> GraphConfig:
    """创建配置，利用自动验证。"""
    try:
        return GraphConfig(entity_types=entity_types)
    except ValidationError as e:
        print(f"无效的实体类型: {e}")
        raise
```

### 3. 使用默认值

```python
from src.sdk.types import GraphConfig

# 使用合理的默认值
config = GraphConfig()  # 使用所有默认值

# 只覆盖需要的字段
custom_config = GraphConfig(chunk_size=1024)  # 其他字段使用默认值
```

### 4. 序列化数据传输

```python
from src.sdk.types import QueryResult

def send_result(result: QueryResult):
    """发送查询结果到远程服务。"""
    # 转换为 JSON 便于传输
    json_data = result.to_json()
    # 发送 json_data...
    return json_data

def receive_result(json_data: str) -> QueryResult:
    """接收并解析查询结果。"""
    # 从 JSON 恢复对象
    return QueryResult.model_validate_json(json_data)
```

## 验证测试

运行验证脚本确保类型定义正常工作：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行验证测试
python src/sdk/test_types.py

# 运行使用示例
python src/sdk/types_examples.py
```

## 扩展类型定义

如需添加新的类型，遵循以下模式：

```python
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

class NewType(BaseModel):
    """新类型描述。

    Attributes:
        field1: 字段 1 描述
        field2: 字段 2 描述
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    field1: str = Field(..., description="字段 1")
    field2: int = Field(default=0, ge=0, description="字段 2")

    @field_validator('field1')
    @classmethod
    def validate_field1(cls, v: str) -> str:
        """验证字段 1。"""
        if not v:
            raise ValueError("field1 不能为空")
        return v.strip()

    def to_dict(self) -> dict:
        """转换为字典。"""
        return self.model_dump()

    def to_json(self) -> str:
        """转换为 JSON。"""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict) -> "NewType":
        """从字典创建实例。"""
        return cls.model_validate(data)
```

## 总结

SDK 类型定义提供了：

1. **类型安全**：编译时和运行时双重保障
2. **自动验证**：确保数据有效性
3. **序列化支持**：轻松转换为字典或 JSON
4. **中文文档**：完整的类型和方法说明
5. **Pydantic v2**：使用最新的 Pydantic 特性

这些类型定义是 CLI 和 REST API 层的统一基础，确保整个 SDK 的类型一致性。
