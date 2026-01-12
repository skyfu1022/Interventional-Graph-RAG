# 规范：查询接口

## 功能 ID
`query-interface`

## 修改需求

### 需求：查询模式兼容

系统应支持与原 `nano_graphrag` 相同的三种查询模式。

#### 场景：本地模式查询

**给定** 图谱中已存在医学知识
**当** 调用 `await rag.aquery(query, mode="local")`
**那么** 应识别查询中的关键实体
**并且** 应检索实体相关的直接邻居
**并且** 应基于局部上下文生成答案
**并且** 答案应聚焦于与实体直接相关的信息

```python
# 示例
result = await rag.aquery(
    "远端栓塞保护装置有哪些类型?",
    mode="local"
)
# 预期行为：聚焦于 EPD 相关的直接实体和关系
```

#### 场景：全局模式查询

**给定** 图谱中已存在医学知识
**当** 调用 `await rag.aquery(query, mode="global")`
**那么** 应基于社区报告进行分析
**并且** 应综合多个相关社区的信息
**并且** 应生成涵盖广泛主题的答案
**并且** 答案应提供更高层次的概括

```python
# 示例
result = await rag.aquery(
    "介入治疗在脑血管疾病中的应用进展",
    mode="global"
)
# 预期行为：综合多个相关概念和社区
```

#### 场景：混合模式查询

**给定** 图谱中已存在医学知识
**当** 调用 `await rag.aquery(query, mode="hybrid")` 或不指定模式
**那么** 应结合本地和全局检索结果
**并且** 应根据查询内容动态平衡两种模式
**并且** 应生成既具体又全面的答案

---

### 需求：查询结果格式

系统应返回格式一致的查询结果。

#### 场景：标准结果格式

**给定** 执行任何查询模式
**当** 查询完成
**那么** 结果应包含 `answer` 字段（生成的答案）
**并且** 结果应包含 `context` 字段（使用的上下文）
**并且** 结果应包含 `entities` 字段（相关实体列表）
**并且** 结果应包含 `sources` 字段（来源信息）

```python
# 预期返回格式
{
    "answer": "远端栓塞保护装置（EPD）主要用于...",
    "context": [
        "EPD 装置通过捕获栓子来预防...",
        "常见的 EPD 类型包括远端滤器..."
    ],
    "entities": [
        "远端栓塞保护装置",
        "颈动脉支架置入术",
        "栓塞"
    ],
    "sources": [
        {
            "file": "carotid_intervention.pdf",
            "page": 15,
            "layer": "middle"
        }
    ],
    "mode_used": "hybrid"
}
```

#### 场景：空结果处理

**给定** 查询内容在图谱中无相关信息
**当** 执行查询
**那么** 应返回明确的无结果信息
**并且** `answer` 字段应说明未找到相关信息
**并且** 不应产生幻觉内容

---

### 需求：流式查询

系统应支持流式返回查询结果。

#### 场景：流式生成答案

**给定** 需要实时反馈的查询场景
**当** 调用 `rag.stream_query(query)`
**那么** 应逐块返回生成的答案
**并且** 每个块应可独立处理
**并且** 最终应返回完整的元数据

```python
# 示例
async for chunk in rag.stream_query("什么是 EPD 装置?"):
    print(chunk, end="")
# 输出: "远端..." "栓塞..." "保护..." ...
```

---

## 接口定义

```python
class QueryResult(TypedDict):
    """查询结果类型定义"""
    answer: str                  # 生成的答案
    context: list[str]           # 使用的上下文片段
    entities: list[str]          # 相关实体
    sources: list[SourceInfo]    # 来源信息
    mode_used: str               # 实际使用的查询模式

class SourceInfo(TypedDict):
    """来源信息"""
    file: str                    # 文件名
    page: int | None             # 页码
    layer: str                   # 所属层级
    chunk_id: str | None         # 文本块 ID
```

---

## 查询参数

### 支持的查询选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | str | 必填 | 查询文本 |
| mode | str | "hybrid" | 查询模式: local/global/hybrid |
| top_k | int | 10 | 返回的上下文数量 |
| temperature | float | 0.7 | 生成温度 |
| stream | bool | False | 是否流式返回 |
| include_sources | bool | True | 是否包含来源信息 |

### 查询模式选择逻辑

```python
def auto_select_mode(query: str) -> str:
    """根据查询内容自动选择模式"""
    if has_specific_entities(query):
        return "local"
    elif requires_broad_summary(query):
        return "global"
    else:
        return "hybrid"
```
