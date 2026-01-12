# 介入手术图谱 Schema 规范

**关联功能**：`workflow-extension`, `sdk-extension`

## 新增需求

### 需求：介入手术实体类型定义

系统**必须**支持介入手术专用的实体节点类型，用于表示解剖结构、病理改变、手术操作、医疗器械等临床概念。

#### 场景：创建解剖结构实体

**给定**：
- Neo4j 图数据库已连接
- 用户提供解剖结构信息

**当**：创建 `:Anatomy` 节点

**那么**：
- 节点应包含必需属性：`id`, `name`, `region`
- 节点应支持可选属性：`name_cn`, `code`, `parent_id`, `description`
- 应支持 `cardiac`, `cerebral`, `peripheral` 等 region 分类

**验证**：
```python
from src.graph.entities import AnatomyEntity

anatomy = AnatomyEntity(
    name="Left Anterior Descending Artery",
    name_cn="左前降支",
    region="cardiac",
    code="SNOMED:123456"
)
node_id = await graph_service.create_entity(anatomy)
assert node_id is not None

# 查询验证
result = await graph_service.get_entity(node_id)
assert result.name == "Left Anterior Descending Artery"
assert result.region == "cardiac"
```

#### 场景：创建病理改变实体

**给定**：
- Neo4j 图数据库已连接
- 用户提供病理信息

**当**：创建 `:Pathology` 节点

**那么**：
- 节点应包含必需属性：`id`, `name`, `severity`
- 节点应支持可选属性：`name_cn`, `code`, `classification`, `characteristics`
- `severity` 应限制为 `mild`, `moderate`, `severe`

**验证**：
```python
from src.graph.entities import PathologyEntity

pathology = PathologyEntity(
    name="Chronic Total Occlusion",
    name_cn="慢性完全闭塞病变",
    severity="severe",
    classification="J-CTO Score 3"
)
node_id = await graph_service.create_entity(pathology)
assert node_id is not None
```

#### 场景：创建手术操作实体

**给定**：
- Neo4j 图数据库已连接
- 用户提供手术信息

**当**：创建 `:Procedure` 节点

**那么**：
- 节点应包含必需属性：`id`, `name`, `type`
- 节点应支持可选属性：`name_cn`, `complexity`, `duration_minutes`, `success_rate`, `steps`, `indications`, `contraindications`
- `type` 应支持 `PCI`, `CAS`, `TAVI` 等分类

**验证**：
```python
from src.graph.entities import ProcedureEntity

procedure = ProcedureEntity(
    name="DK-Crush Technique",
    name_cn="DK挤压技术",
    type="PCI",
    complexity="complex",
    steps=["Main branch wiring", "Side branch stenting", "Crushing", "Re-wiring", "Final kissing"]
)
node_id = await graph_service.create_entity(procedure)
assert node_id is not None
```

#### 场景：创建医疗器械实体

**给定**：
- Neo4j 图数据库已连接
- 用户提供器械信息

**当**：创建 `:Device` 节点

**那么**：
- 节点应包含必需属性：`id`, `name`, `category`
- 节点应支持可选属性：`name_cn`, `manufacturer`, `specifications`, `indications`, `contraindications`
- `category` 应支持 `guidewire`, `stent`, `balloon`, `catheter`, `protection` 等分类

**验证**：
```python
from src.graph.entities import DeviceEntity

device = DeviceEntity(
    name="Runthrough NS Guide Wire",
    category="guidewire",
    manufacturer="Terumo",
    specifications={"diameter": "0.014in", "tip_load": "1.0g"}
)
node_id = await graph_service.create_entity(device)
assert node_id is not None
```

---

### 需求：介入手术关系类型定义

系统**必须**支持介入手术专用的关系类型，用于表示术前、术中、术后各阶段的临床关联。

#### 场景：创建禁忌关系

**给定**：
- 存在 `:RiskFactor` 节点（如 "高出血风险"）
- 存在 `:Procedure` 节点（如 "PCI"）

**当**：创建 `:CONTRAINDICATES` 关系

**那么**：
- 关系应从 `:RiskFactor` 指向 `:Procedure`
- 关系应包含 `strength` 属性（`absolute` 或 `relative`）
- 关系应支持可选属性：`evidence_level`, `source`, `notes`

**验证**：
```python
from src.graph.relationships import ContraindicatesRelation

relation = ContraindicatesRelation(
    from_id=risk_factor_id,
    to_id=procedure_id,
    strength="relative",
    evidence_level="B",
    source="ACC/AHA Guidelines 2021"
)
rel_id = await graph_service.create_relationship(relation)
assert rel_id is not None

# 查询禁忌症
contraindications = await graph_service.get_contraindications(procedure_id)
assert len(contraindications) > 0
```

#### 场景：创建器械使用关系

**给定**：
- 存在 `:IntraoperativeEvent` 节点（如 "支架植入"）
- 存在 `:Device` 节点（如 "Firehawk Stent"）

**当**：创建 `:USES_DEVICE` 关系

**那么**：
- 关系应从 `:IntraoperativeEvent` 指向 `:Device`
- 关系应包含 `required` 属性（布尔值）
- 关系应支持可选属性：`alternatives`, `parameters`, `notes`

**验证**：
```python
from src.graph.relationships import UsesDeviceRelation

relation = UsesDeviceRelation(
    from_id=event_id,
    to_id=device_id,
    required=True,
    parameters={"diameter": "3.0mm", "length": "24mm"}
)
rel_id = await graph_service.create_relationship(relation)
assert rel_id is not None
```

#### 场景：创建并发症关系

**给定**：
- 存在 `:IntraoperativeEvent` 节点（如 "导丝通过"）
- 存在 `:Complication` 节点（如 "冠脉夹层"）

**当**：创建 `:LEADS_TO_COMPLICATION` 关系

**那么**：
- 关系应从 `:IntraoperativeEvent` 指向 `:Complication`
- 关系应包含 `probability` 属性（0-1 之间的浮点数）
- 关系应支持可选属性：`risk_factors`, `prevention`, `source`

**验证**：
```python
from src.graph.relationships import LeadsToComplicationRelation

relation = LeadsToComplicationRelation(
    from_id=event_id,
    to_id=complication_id,
    probability=0.02,
    risk_factors=["CTO lesion", "Heavy calcification"],
    prevention=["Use polymer-jacketed wire", "Gentle manipulation"]
)
rel_id = await graph_service.create_relationship(relation)
assert rel_id is not None
```

---

### 需求：图谱 Schema 管理

系统**必须**提供介入手术图谱的 Schema 管理功能，包括约束、索引和版本管理。

#### 场景：初始化图谱 Schema

**给定**：
- Neo4j 数据库已连接
- 介入手术模块首次使用

**当**：调用 Schema 初始化

**那么**：
- 应创建所有实体类型的唯一约束（基于 `id` 属性）
- 应创建常用查询的索引（`name`, `type`, `category` 等）
- 应记录 Schema 版本信息

**验证**：
```python
from src.graph.schema import InterventionalSchemaManager

manager = InterventionalSchemaManager(neo4j_driver)
await manager.initialize()

# 验证约束
constraints = await manager.list_constraints()
assert "anatomy_id_unique" in constraints
assert "procedure_id_unique" in constraints

# 验证索引
indexes = await manager.list_indexes()
assert "anatomy_name_index" in indexes
```

#### 场景：Schema 版本迁移

**给定**：
- 现有 Schema 版本为 v1
- 需要升级到 v2

**当**：执行 Schema 迁移

**那么**：
- 应检测当前版本
- 应按顺序执行迁移脚本
- 应更新版本记录
- 应在失败时回滚

**验证**：
```python
from src.graph.schema import InterventionalSchemaManager

manager = InterventionalSchemaManager(neo4j_driver)
current_version = await manager.get_version()
await manager.migrate_to(target_version="v2")
new_version = await manager.get_version()
assert new_version == "v2"
```
