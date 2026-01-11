# TASK-050: 实现上下文组装逻辑 - 完成总结

## 任务概述

完成 **TASK-050: 实现上下文组装逻辑**，增强 `QueryService` 的上下文处理能力，支持智能组装图上下文、向量上下文以及多源上下文组合。

## 实现内容

### 1. 新增数据类

在 `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/query.py` 中添加了三个新的数据类：

#### `GraphContextData`
- **用途**: 封装从知识图谱中提取的结构化信息
- **字段**:
  - `entities`: 实体列表（包含名称、类型、描述）
  - `relationships`: 关系列表（包含源、目标、类型、描述）
  - `communities`: 社区列表
  - `total_tokens`: 上下文的总 token 数量

#### `VectorContextData`
- **用途**: 封装从向量数据库中检索的文本块信息
- **字段**:
  - `chunks`: 文本块列表（包含内容和相关性评分）
  - `total_tokens`: 上下文的总 token 数量

#### `CombinedContext`
- **用途**: 智能组合多种上下文来源
- **字段**:
  - `entities`: 去重后的实体列表
  - `relationships`: 去重后的关系列表
  - `chunks`: 去重后的文本块列表
  - `total_tokens`: 总 token 数量
  - `sources`: 上下文来源标记（graph, vector, hybrid）

### 2. 核心方法实现

#### `assemble_graph_context()`
```python
async def assemble_graph_context(
    self,
    graph_id: str,
    entity_names: Optional[List[str]] = None,
    max_tokens: int = 3000,
    **kwargs
) -> GraphContextData
```

**功能**:
- 从知识图谱中提取结构化信息（实体、关系、社区）
- 支持按指定实体名称提取
- 支持按 token 限制自动截断
- 使用 LightRAG 的 `only_need_context=True` 参数获取原始上下文

**参数**:
- `graph_id`: 图谱 ID
- `entity_names`: 要提取的实体名称列表（可选）
- `max_tokens`: 最大 token 数量限制
- `top_k`: 检索的 top-k 数量
- `include_communities`: 是否包含社区信息

#### `assemble_vector_context()`
```python
async def assemble_vector_context(
    self,
    query: str,
    top_k: int = 5,
    max_tokens: int = 2000,
    **kwargs
) -> VectorContextData
```

**功能**:
- 从向量数据库中检索相关的文本块
- 支持按相关性排序
- 支持按 token 限制自动截断
- 使用 LightRAG 的 naive 模式获取原始文本块

**参数**:
- `query`: 查询文本
- `top_k`: 检索的 top-k 数量
- `max_tokens`: 最大 token 数量限制
- `mode`: 查询模式（默认为 "naive"）

#### `combine_contexts()`
```python
def combine_contexts(
    self,
    graph_context: Optional[GraphContextData] = None,
    vector_context: Optional[VectorContextData] = None,
    max_total_tokens: int = 5000,
    **kwargs
) -> CombinedContext
```

**功能**:
- 智能组合图上下文和向量上下文
- 自动去重（实体按名称，关系按三元组，文本块按内容）
- 按相关性排序
- 按权重截断（支持自定义图上下文和向量上下文的权重）

**参数**:
- `graph_context`: 图上下文数据
- `vector_context`: 向量上下文数据
- `max_total_tokens`: 最大总 token 数量限制
- `graph_weight`: 图上下文权重（0-1，默认 0.6）
- `vector_weight`: 向量上下文权重（0-1，默认 0.4）
- `deduplicate`: 是否去重（默认 True）

### 3. 辅助方法

#### `_estimate_tokens()`
- 估算文本的 token 数量
- 使用启发式方法：平均 2 字符 = 1 token

#### `_truncate_by_tokens()`
- 按 token 限制截断列表
- 保留最前面的项目，直到达到 token 限制

#### `_deduplicate_context()`
- 去除上下文中的重复内容
- 实体按名称去重
- 关系按源-目标-类型三元组去重
- 文本块按内容前 100 字符去重

#### `_sort_context_by_relevance()`
- 按相关性评分排序
- 降序排列（相关性高的在前）

#### `_truncate_combined_context()`
- 按权重截断组合上下文
- 分别计算图上下文和向量上下文的 token 配额

## 技术特性

### 1. 异步优先
- 所有上下文组装方法都是异步的
- 使用 `async/await` 处理 I/O 操作

### 2. 类型安全
- 完整的类型提示（支持 mypy 严格模式）
- 使用 `Optional`、`List`、`Dict` 等类型注解

### 3. 错误处理
- 验证输入参数（空查询、无效模式等）
- 抛出语义化的异常（`ValidationError`、`QueryError`）
- 详细的错误信息和上下文

### 4. 日志记录
- 使用 `loguru` 记录关键操作
- 记录参数、执行过程和结果统计

### 5. 代码质量
- 遵循 PEP 8 标准（通过 ruff 检查）
- Google 风格的文档字符串
- 完整的单元测试覆盖

## 测试覆盖

### 测试文件
`/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_context_assembly.py`

### 测试统计
- **总测试数**: 17 个
- **通过率**: 100%
- **测试分类**:
  - 图上下文组装测试：4 个
    - 指定实体名称
    - 不指定实体名称
    - 包含社区信息
    - Token 限制截断
  - 向量上下文组装测试：4 个
    - 基本查询
    - 空查询验证
    - 大 top_k 值
    - Token 限制
  - 上下文组合测试：5 个
    - 基本组合
    - 去重功能
    - 只有图上下文
    - 只有向量上下文
    - 权重截断
  - 辅助方法测试：4 个
    - Token 估算
    - Token 截断
    - 去重逻辑
    - 排序逻辑

### 测试结果
```
============================== 17 passed in 6.16s ===============================
```

### 兼容性测试
所有现有测试继续通过（35 个查询服务测试），确保向后兼容：
```
============================== 35 passed in 5.89s ===============================
```

## 使用示例

### 示例 1：组装图上下文
```python
from src.services.query import QueryService

service = QueryService(adapter)

# 指定实体名称
graph_context = await service.assemble_graph_context(
    graph_id="medical",
    entity_names=["糖尿病", "胰岛素"],
    max_tokens=3000
)

print(f"实体数量: {len(graph_context.entities)}")
print(f"关系数量: {len(graph_context.relationships)}")
print(f"总 tokens: {graph_context.total_tokens}")
```

### 示例 2：组装向量上下文
```python
# 查询相关文本块
vector_context = await service.assemble_vector_context(
    query="糖尿病症状",
    top_k=5,
    max_tokens=2000
)

print(f"文本块数量: {len(vector_context.chunks)}")
for i, chunk in enumerate(vector_context.chunks):
    print(f"块 {i+1}: {chunk['content'][:50]}... (相关性: {chunk['relevance']})")
```

### 示例 3：组合上下文
```python
# 组合图上下文和向量上下文
combined = service.combine_contexts(
    graph_context=graph_context,
    vector_context=vector_context,
    max_total_tokens=5000,
    graph_weight=0.6,
    vector_weight=0.4,
    deduplicate=True
)

print(f"总实体: {len(combined.entities)}")
print(f"总关系: {len(combined.relationships)}")
print(f"总文本块: {len(combined.chunks)}")
print(f"总 tokens: {combined.total_tokens}")
print(f"来源: {combined.sources}")
```

### 示例 4：完整工作流
```python
# 1. 组装图上下文
graph_context = await service.assemble_graph_context(
    graph_id="medical",
    entity_names=["糖尿病"],
    max_tokens=2000
)

# 2. 组装向量上下文
vector_context = await service.assemble_vector_context(
    query="糖尿病的治疗方法",
    top_k=5,
    max_tokens=1500
)

# 3. 组合上下文
combined = service.combine_contexts(
    graph_context=graph_context,
    vector_context=vector_context,
    max_total_tokens=3000
)

# 4. 使用组合后的上下文进行查询
result = await service.query(
    "如何治疗糖尿病？",
    mode="hybrid",
    custom_context=combined.to_dict()
)
```

## 代码规范

### PEP 8 合规
- 使用 `ruff` 进行代码格式检查
- 所有检查通过：`All checks passed!`

### 类型检查
- 使用 `mypy --strict` 进行类型检查
- 完整的类型提示（包括返回类型和参数类型）

### 文档字符串
- 所有公共方法都包含 Google 风格的文档字符串
- 包含参数说明、返回值说明、异常说明和使用示例

## 文件清单

### 修改的文件
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/services/query.py`
  - 添加了 3 个新的数据类
  - 添加了 3 个核心方法（assemble_graph_context, assemble_vector_context, combine_contexts）
  - 添加了 5 个辅助方法
  - 更新了导出列表

### 新增的文件
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/tests/unit/test_context_assembly.py`
  - 17 个单元测试用例
  - 完整的测试覆盖

### 更新的文件
- `/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/openspec/changes/refactor-langgraph-raganything/tasks.md`
  - 标记 TASK-050 为已完成
  - 更新总进度为 42/53 (79%)

## 性能考虑

### Token 估算
- 使用轻量级的启发式方法（2 字符 = 1 token）
- 避免调用昂贵的 tokenizer
- 对于大多数场景足够准确

### 去重效率
- 使用 `OrderedDict` 进行 O(n) 去重
- 保持原始顺序的同时去除重复

### 内存优化
- 使用生成器和迭代器处理大量数据
- 按需截断，避免加载全部数据

## 未来改进

### 短期改进
1. 集成真实的 tokenizer 进行精确的 token 计算
2. 支持更复杂的实体和关系解析逻辑
3. 添加缓存机制避免重复查询

### 长期改进
1. 支持动态调整上下文权重
2. 实现上下文质量评分
3. 支持多模态上下文组装（图像、表格等）

## 验证清单

- [x] 实现 `assemble_graph_context()` 方法
- [x] 实现 `assemble_vector_context()` 方法
- [x] 实现智能组合上下文的 `combine_contexts()` 方法
- [x] 实现去重功能
- [x] 实现按相关性排序
- [x] 实现 token 限制和截断
- [x] 添加完整的类型提示
- [x] 添加 Google 风格文档字符串
- [x] 通过 ruff 代码格式检查
- [x] 通过 17 个单元测试
- [x] 通过现有查询服务测试（35 个）
- [x] 更新 tasks.md 标记完成

## 总结

TASK-050 已成功完成，实现了完整的上下文组装逻辑，包括：

1. ✅ 图上下文组装（实体、关系、社区）
2. ✅ 向量上下文组装（文本块）
3. ✅ 智能上下文组合（去重、排序、截断）
4. ✅ 完整的单元测试覆盖
5. ✅ 代码质量和文档规范

该实现为后续的检索增强功能（TASK-048, TASK-049）提供了坚实的基础。
