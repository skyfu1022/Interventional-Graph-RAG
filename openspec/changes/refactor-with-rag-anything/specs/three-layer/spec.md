# 规范：三层图谱封装

## 功能 ID
`three-layer`

## 修改需求

### 需求：层次化图谱结构

系统应保持原有的三层层次化图谱结构，每层独立存储和管理。

#### 场景：初始化三层图谱

**给定** 已配置存储参数
**当** 调用 `ThreeLayerGraph(config)`
**那么** 应创建三个独立的 RAG 实例
**并且** 顶层实例应使用 `./data/top` 作为工作目录
**并且** 中层实例应使用 `./data/middle` 作为工作目录
**并且** 底层实例应使用 `./data/bottom` 作为工作目录

```python
# 示例
three_layer = ThreeLayerGraph(
    top_config=LayerConfig(
        name="私有数据",
        working_dir="./data/top"
    ),
    middle_config=LayerConfig(
        name="书籍论文",
        working_dir="./data/middle"
    ),
    bottom_config=LayerConfig(
        name="字典数据",
        working_dir="./data/bottom"
    )
)
```

#### 场景：向指定层插入数据

**给定** 已初始化的三层图谱实例
**当** 调用 `await three_layer.insert_to_layer("top", [documents])`
**那么** 应仅将文档插入到顶层图谱
**并且** 其他层不应受到影响

#### 场景：获取层级统计信息

**给定** 已初始化的三层图谱实例
**当** 调用 `stats = await three_layer.get_layer_stats()`
**那么** 应返回每一层的统计信息
**并且** 统计信息应包含文档数量、实体数量、关系数量

```python
# 预期返回格式
{
    "top": {
        "documents": 150,
        "entities": 2340,
        "relationships": 5670
    },
    "middle": {
        "documents": 50,
        "entities": 8500,
        "relationships": 21000
    },
    "bottom": {
        "documents": 20,
        "entities": 15000,
        "relationships": 45000
    }
}
```

---

### 需求：跨层查询

系统应支持跨三个层级的联合查询。

#### 场景：查询所有层级

**给定** 已有数据的三层图谱
**当** 调用 `await three_layer.query_all_layers("什么是远端栓塞保护装置?")`
**那么** 应依次查询顶层、中层、底层
**并且** 结果应按层级优先级合并
**并且** 顶层结果应具有最高权重

```python
# 示例
result = await three_layer.query_all_layers(
    "什么是远端栓塞保护装置?"
)
# 返回格式
{
    "answer": "远端栓塞保护装置（EPD）是一种介入治疗器械...",
    "sources": {
        "top": [/* 来自私有数据的结果 */],
        "middle": [/* 来自书籍论文的结果 */],
        "bottom": [/* 来自字典数据的结果 */]
    }
}
```

#### 场景：指定层级查询

**给定** 已有数据的三层图谱
**当** 调用 `await three_layer.query_layer("middle", query)`
**那么** 应仅在中层执行查询
**并且** 结果应仅包含中层数据

#### 场景：层级优先级

**给定** 多层都有相关信息的查询
**当** 执行跨层查询
**那么** 顶层（私有数据）的结果应优先展示
**并且** 中层（书籍论文）的结果作为补充
**并且** 底层（字典数据）的结果作为背景参考

---

### 需求：层级数据隔离

系统应确保不同层级之间的数据相互隔离。

#### 场景：数据隔离验证

**给定** 向顶层插入了敏感文档
**当** 从底层查询相同内容
**那么** 底层查询结果不应包含顶层敏感数据
**并且** 各层实体 ID 空间应相互独立

#### 场景：独立存储管理

**给定** 三个层级的实例
**当** 清空某一层的数据
**那么** 其他层的数据应保持不变
**并且** 每层可独立备份和恢复

---

## 接口定义

```python
class ThreeLayerGraph:
    """三层层次化图谱结构"""

    def __init__(
        self,
        top_config: LayerConfig,
        middle_config: LayerConfig,
        bottom_config: LayerConfig
    ):
        """初始化三层图谱"""

    async def insert_to_layer(
        self,
        layer: Literal["top", "middle", "bottom"],
        documents: list[str]
    ) -> None:
        """向指定层插入文档"""

    async def query_layer(
        self,
        layer: Literal["top", "middle", "bottom"],
        query: str,
        mode: Literal["local", "global", "hybrid"] = "hybrid"
    ) -> dict:
        """查询指定层级"""

    async def query_all_layers(
        self,
        query: str,
        mode: Literal["local", "global", "hybrid"] = "hybrid"
    ) -> dict:
        """跨所有层级查询"""

    async def get_layer_stats(
        self,
        layer: Literal["top", "middle", "bottom"] | None = None
    ) -> dict:
        """获取层级统计信息"""

    async def clear_layer(
        self,
        layer: Literal["top", "middle", "bottom"]
    ) -> None:
        """清空指定层级数据"""
```

---

## 数据结构

### 层级配置

```python
class LayerConfig:
    name: str              # 层级名称
    working_dir: str       # 工作目录
    description: str = ""  # 层级描述
    priority: int = 0      # 查询优先级
```

### 跨层查询结果

```python
class CrossLayerResult:
    answer: str           # 合并后的答案
    sources: dict         # 按层级分组的来源
    top_results: list     # 顶层结果
    middle_results: list  # 中层结果
    bottom_results: list  # 底层结果
```
