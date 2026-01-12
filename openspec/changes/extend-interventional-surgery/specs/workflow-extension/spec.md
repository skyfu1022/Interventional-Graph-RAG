# 介入手术工作流扩展规范

**关联功能**：`state-extension`, `graph-schema`, `sdk-extension`

## 新增需求

### 需求：多阶段工作流架构

系统**必须**将介入手术工作流扩展为三个独立阶段：术前评估、术中决策、术后管理。每个阶段应可独立执行或组合执行。

#### 场景：执行完整工作流

**给定**：
- 用户提供患者数据和手术类型
- 介入手术工作流已配置

**当**：执行完整工作流（preop → intraop → postop）

**那么**：
- 应按顺序执行三个阶段
- 前一阶段的输出应作为后一阶段的输入
- 任一阶段失败应停止后续阶段并记录错误
- 最终输出应包含所有阶段的综合结果

**验证**：
```python
from src.agents.workflows.interventional import create_interventional_workflow

workflow = create_interventional_workflow(rag_adapter, llm)

result = await workflow.ainvoke({
    "patient_data": {
        "age": 72,
        "gender": "female",
        "diagnosis": "左侧颈内动脉重度狭窄",
        "history": ["高血压", "高血脂", "TIA"]
    },
    "procedure_type": "CAS",
    "current_phase": "preop"
})

assert result["primary_plan"] is not None
assert result["selected_devices"] is not None
assert result["postop_plan"] is not None
assert result["reasoning_chain"] is not None
```

#### 场景：独立执行术前评估阶段

**给定**：
- 用户仅需术前风险评估
- 介入手术工作流已配置

**当**：仅执行术前评估阶段

**那么**：
- 应仅运行术前相关节点
- 应输出适应症评估、风险分层、禁忌症检查结果
- 不应执行术中或术后相关节点

**验证**：
```python
from src.agents.workflows.interventional import create_preop_phase_workflow

workflow = create_preop_phase_workflow(rag_adapter, llm)

result = await workflow.ainvoke({
    "patient_data": {...},
    "procedure_type": "PCI"
})

assert "indications_met" in result
assert "risk_factors" in result
assert "contraindications" in result
assert "selected_devices" not in result  # 术中内容不应存在
```

---

### 需求：条件分支与决策路由

系统**必须**支持基于检查结果的动态分支决策，包括禁忌症路由、并发症应急路由等。

#### 场景：禁忌症检查路由

**给定**：
- 患者存在某项禁忌症
- 禁忌症检查节点已完成

**当**：工作流到达禁忌症路由节点

**那么**：
- 应根据禁忌症严重程度（绝对/相对）决定路由
- 绝对禁忌 → 转向 `contraindication_absolute` 节点，终止手术规划
- 相对禁忌 → 转向 `contraindication_relative` 节点，尝试优化方案
- 无禁忌 → 继续正常流程

**验证**：
```python
from src.agents.nodes.interventional import check_contraindications_node
from src.agents.states import ContraindicationResult

# 绝对禁忌场景
state_absolute = await check_contraindications_node({
    "patient_data": {"risk_factors": ["contrast_allergy_severe"]},
    "procedure_type": "PCI"
})
assert state_absolute["route"] == "contraindication_absolute"

# 相对禁忌场景
state_relative = await check_contraindications_node({
    "patient_data": {"risk_factors": ["high_bleeding_risk"]},
    "procedure_type": "PCI"
})
assert state_relative["route"] == "contraindication_relative"

# 无禁忌场景
state_none = await check_contraindications_node({
    "patient_data": {"risk_factors": []},
    "procedure_type": "PCI"
})
assert state_none["route"] == "continue"
```

#### 场景：并发症应急方案路由

**给定**：
- 术中发生并发症（如冠脉夹层）
- 并发症处理节点已触发

**当**：工作流到达应急方案路由

**那么**：
- 应识别并发症类型和严重程度
- 应查询图谱中该并发症的 `:REQUIRES_RESCUE` 关系
- 应返回匹配的应急方案（备选手术或处理措施）
- 应更新状态中的 `complications` 和 `backup_plans`

**验证**：
```python
from src.agents.nodes.interventional import handle_complication_node

# 模拟冠脉夹层并发症
state = await handle_complication_node({
    "intraop_events": ["guidewire_passage"],
    "complications": [
        {"name": "Coronary Dissection", "severity": "major"}
    ],
    "primary_plan": {...}
})

assert "backup_plans" in state
assert len(state["backup_plans"]) > 0
assert any("stent" in p.lower() for p in state["backup_plans"])
```

---

### 需求：节点实现

系统**必须**实现介入手术工作流的所有关键节点。

#### 场景：解剖结构提取节点

**给定**：
- 用户输入包含解剖位置描述（如 "左前降支近段"）
- 工作流状态包含原始患者数据

**当**：执行 `extract_anatomy_node`

**那么**：
- 应从用户输入中识别解剖结构实体
- 应在图谱中查询匹配的 `:Anatomy` 节点
- 应提取相关属性（如血管直径、位置）
- 应将结果添加到状态的 `anatomy_findings` 字段

**验证**：
```python
from src.agents.nodes.interventional import extract_anatomy_node

state = await extract_anatomy_node({
    "patient_data": {
        "diagnosis": "LAD近段80%狭窄"
    },
    "anatomy_findings": []
})

assert len(state["anatomy_findings"]) > 0
assert any(f.structure == "LAD" for f in state["anatomy_findings"])
```

#### 场景：病理改变识别节点

**给定**：
- 用户输入包含病理描述（如 "慢性完全闭塞"、"Medina 1,1,1"）
- 工作流状态已包含解剖发现

**当**：执行 `identify_pathology_node`

**那么**：
- 应从用户输入中识别病理类型
- 应在图谱中查询匹配的 `:Pathology` 节点
- 应提取严重程度、分类标准等信息
- 应将结果添加到状态的 `pathology_findings` 字段

**验证**：
```python
from src.agents.nodes.interventional import identify_pathology_node

state = await identify_pathology_node({
    "patient_data": {
        "diagnosis": "LAD近段CTO病变，Medina 1,1,1"
    },
    "pathology_findings": []
})

assert len(state["pathology_findings"]) > 0
assert any(p.condition == "Chronic Total Occlusion" for p in state["pathology_findings"])
assert any(p.classification == "Medina 1,1,1" for p in state["pathology_findings"])
```

#### 场景：指南匹配节点

**给定**：
- 患者数据和病理发现已提取
- 图谱中存在相关指南条目

**当**：执行 `match_guidelines_node`

**那么**：
- 应基于患者特征和病理类型构建检索查询
- 应调用 RAG-Anything 检索相关指南
- 应匹配推荐等级（Class I/IIa/IIb/III）和证据级别
- 应按相关性排序并返回前 N 条指南
- 应将结果添加到状态的 `matched_guidelines` 字段

**验证**：
```python
from src.agents.nodes.interventional import match_guidelines_node

state = await match_guidelines_node({
    "patient_data": {"age": 65, "diagnosis": "LAD stenosis"},
    "pathology_findings": [{"condition": "Severe Stenosis", "severity": "severe"}],
    "procedure_type": "PCI",
    "matched_guidelines": []
}, rag_adapter)

assert len(state["matched_guidelines"]) > 0
assert all("recommendation_class" in g for g in state["matched_guidelines"])
assert all("evidence_level" in g for g in state["matched_guidelines"])
```

#### 场景：器械选择节点

**给定**：
- 手术类型已确定
- 病理特征已识别
- 图谱中存在器械信息

**当**：执行 `select_devices_node`

**那么**：
- 应查询图谱中与手术类型和病理匹配的器械
- 应考虑器械的适应症和禁忌症
- 应返回推荐的器械列表及选择理由
- 应包含替代选项
- 应将结果添加到状态的 `selected_devices` 字段

**验证**：
```python
from src.agents.nodes.interventional import select_devices_node

state = await select_devices_node({
    "procedure_type": "CAS",
    "pathology_findings": [{"condition": "Active Plaque"}],
    "selected_devices": []
}, rag_adapter)

assert len(state["selected_devices"]) > 0
assert any(d.category == "protection" for d in state["selected_devices"])  # EPD
assert any("rationale" in d for d in state["selected_devices"])
```

#### 场景：手术方案生成节点

**给定**：
- 所有术前评估已完成
- 器械已选择
- 指南已匹配

**当**：执行 `generate_plan_node`

**那么**：
- 应综合所有可用信息生成首选方案
- 应基于风险因素生成备选方案
- 应构建完整的推理链
- 应使用 LLM 生成自然语言描述
- 应计算置信度分数
- 应将结果添加到状态的 `primary_plan`, `backup_plans`, `recommendations` 字段

**验证**：
```python
from src.agents.nodes.interventional import generate_plan_node

state = await generate_plan_node({
    "patient_data": {...},
    "anatomy_findings": [...],
    "pathology_findings": [...],
    "selected_devices": [...],
    "matched_guidelines": [...],
    "risk_factors": [...]
}, rag_adapter, llm)

assert state["primary_plan"] is not None
assert state["backup_plans"] is not None
assert state["recommendations"] is not None
assert state["confidence_score"] > 0
assert len(state["reasoning_chain"]) > 0
```

#### 场景：术后管理规划节点

**给定**：
- 手术方案已生成
- 手术类型和器械已确定

**当**：执行 `plan_postop_node`

**那么**：
- 应查询 `:Procedure` 节点的 `:PRESCRIBES` 关系
- 应基于患者风险因素调整用药方案
- 应生成随访计划（监测项目、时间点）
- 应将结果添加到状态的 `postop_plan` 字段

**验证**：
```python
from src.agents.nodes.interventional import plan_postop_node

state = await plan_postop_node({
    "primary_plan": {"procedure_type": "PCI", "devices": ["stent"]},
    "patient_data": {"risk_factors": ["high_bleeding_risk"]},
    "postop_plan": None
}, rag_adapter)

assert state["postop_plan"] is not None
assert state["postop_plan"]["medication"] is not None
assert state["postop_plan"]["followup"] is not None
```

---

### 需求：工作流可视化

系统**必须**支持介入手术工作流的可视化，便于调试和临床审核。

#### 场景：生成工作流图

**给定**：
- 介入手术工作流已配置

**当**：调用 `get_graph()` 方法

**那么**：
- 应返回包含所有节点和边的 Mermaid 图表
- 应标注条件分支（如禁忌症路由）
- 应区分不同阶段的节点（术前/术中/术后）

**验证**：
```python
from src.agents.workflows.interventional import create_interventional_workflow

workflow = create_interventional_workflow(rag_adapter, llm)
graph = workflow.get_graph()
mermaid_code = graph.print_mermaid()

assert "extract_anatomy" in mermaid_code
assert "identify_pathology" in mermaid_code
assert "check_contraindications" in mermaid_code
assert "contraindication_absolute" in mermaid_code or "contraindication_relative" in mermaid_code
```

#### 场景：工作流执行追踪

**给定**：
- 工作流正在执行

**当**：启用追踪模式

**那么**：
- 应记录每个节点的输入输出
- 应记录节点的执行时间
- 应记录分支决策的理由
- 应生成可读的执行日志

**验证**：
```python
from src.agents.workflows.interventional import create_interventional_workflow

workflow = create_interventional_workflow(rag_adapter, llm)
config = {"configurable": {"trace_enabled": True}}

result = await workflow.ainvoke(initial_state, config)

trace = result.get("__trace__")
assert trace is not None
assert all("node" in step for step in trace)
assert all("timestamp" in step for step in trace)
```
