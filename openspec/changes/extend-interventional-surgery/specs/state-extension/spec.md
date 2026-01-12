# 介入手术状态扩展规范

**关联功能**：`workflow-extension`, `graph-schema`

## 新增需求

### 需求：扩展状态类型定义

系统**必须**定义扩展的介入手术状态类型，包含更丰富的临床信息字段。

#### 场景：定义 ExtendedInterventionalState

**给定**：
- 需要管理介入手术工作流的完整状态
- 现有 `InterventionalState` 字段不足

**当**：定义 `ExtendedInterventionalState` 类型

**那么**：应包含以下字段组：

**患者信息组**：
- `patient_data`: 患者基础数据（必需，Required）
- `anatomy_findings`: 解剖结构发现列表（累加，Annotated[List, add]）
- `pathology_findings`: 病理改变发现列表（累加）
- `risk_factors`: 风险因素列表（累加）

**术式规划组**：
- `procedure_type`: 手术类型（必需）
- `primary_plan`: 首选方案（可选）
- `backup_plans`: 备选方案列表（累加）

**器械选择组**：
- `selected_devices`: 选择的器械列表（累加）
- `device_alternatives`: 替代器械列表（累加）

**指南匹配组**：
- `matched_guidelines`: 匹配的指南列表（累加）

**术中事件组**：
- `intraop_events`: 术中事件列表（累加）
- `complications`: 并发症列表（累加）

**术后管理组**：
- `postop_plan`: 术后管理方案（可选）

**推理过程组**：
- `reasoning_chain`: 推理步骤列表（累加）
- `context`: 检索上下文列表（累加）

**输出组**：
- `recommendations`: 推荐方案描述（字符串）
- `confidence_score`: 置信度分数（浮点数）

**控制组**：
- `current_phase`: 当前阶段（preop/intraop/postop）
- `step`: 当前步骤
- `error`: 错误信息（可选）

**验证**：
```python
from src.agents.states import ExtendedInterventionalState

# 类型检查
state: ExtendedInterventionalState = {
    "patient_data": {
        "age": 72,
        "gender": "female",
        "diagnosis": "颈动脉狭窄"
    },
    "procedure_type": "CAS",
    "anatomy_findings": [],
    "pathology_findings": [],
    "risk_factors": [],
    "primary_plan": None,
    "backup_plans": [],
    "selected_devices": [],
    "device_alternatives": [],
    "matched_guidelines": [],
    "intraop_events": [],
    "complications": [],
    "postop_plan": None,
    "reasoning_chain": [],
    "context": [],
    "recommendations": "",
    "confidence_score": 0.0,
    "current_phase": "preop",
    "step": "init",
    "error": None
}

# 验证必需字段
assert state["patient_data"] is not None
assert state["procedure_type"] is not None
```

---

### 需求：嵌套数据模型

系统**必须**定义状态中嵌套字段的 Pydantic 数据模型，确保类型安全和数据验证。

#### 场景：定义患者数据模型

**给定**：
- 状态中包含 `patient_data` 字段

**当**：定义 `PatientDataModel`

**那么**：应包含以下字段：
- `age`: 年龄（整数，必需）
- `gender`: 性别（字符串，必需）
- `weight`: 体重（浮点数，可选）
- `height`: 身高（浮点数，可选）
- `diagnosis`: 诊断（字符串，必需）
- `history`: 病史列表（字符串列表）
- `medications`: 用药列表（字符串列表）
- `lab_results`: 检验结果（字典）
- `imaging_results`: 影像结果（字符串列表）

**验证**：
```python
from src.agents.models import PatientDataModel

patient = PatientDataModel(
    age=72,
    gender="female",
    diagnosis="左侧颈内动脉重度狭窄",
    history=["高血压", "高血脂", "TIA"],
    medications=["阿司匹林", "阿托伐他汀"],
    lab_results={"eGFR": 65, "HbA1c": 6.5},
    imaging_results=["颈部超声：左ICA 85%狭窄，活动性斑块"]
)

assert patient.age == 72
assert len(patient.history) == 3
```

#### 场景：定义解剖发现模型

**给定**：
- 状态中包含 `anatomy_findings` 字段

**当**：定义 `AnatomyFindingModel`

**那么**：应包含以下字段：
- `structure`: 解剖结构名称（字符串，必需）
- `location`: 位置描述（字符串，必需）
- `characteristics`: 特征列表（字符串列表）
- `measurements`: 测量值字典（如血管直径）

**验证**：
```python
from src.agents.models import AnatomyFindingModel

finding = AnatomyFindingModel(
    structure="Left Internal Carotid Artery",
    location="起始部",
    characteristics=["重度狭窄", "活动性斑块"],
    measurements={"stenosis_rate": 0.85, "diameter": 4.5}
)

assert finding.structure == "Left Internal Carotid Artery"
assert finding.measurements["stenosis_rate"] == 0.85
```

#### 场景：定义手术方案模型

**给定**：
- 状态中包含 `primary_plan` 和 `backup_plans` 字段

**当**：定义 `ProcedurePlanModel`

**那么**：应包含以下字段：
- `procedure_name`: 术式名称（字符串，必需）
- `procedure_type`: 手术类型（枚举，必需）
- `steps`: 手术步骤列表（字符串列表，必需）
- `devices`: 器械选择列表（DeviceSelectionModel 列表）
- `estimated_duration`: 预计时长（分钟）
- `success_probability`: 成功概率（浮点数 0-1）
- `rationale`: 选择理由（字符串，必需）

**验证**：
```python
from src.agents.models import ProcedurePlanModel, ProcedureType

plan = ProcedurePlanModel(
    procedure_name="颈动脉支架置入术",
    procedure_type=ProcedureType.CAS,
    steps=[
        "股动脉穿刺",
        "导引导管就位",
        "部署远端保护装置",
        "预扩张",
        "支架释放",
        "后扩张",
        "撤除保护装置"
    ],
    devices=[...],
    estimated_duration=60,
    success_probability=0.95,
    rationale="症状性狭窄获益明确，EPD可降低术中栓塞风险"
)

assert plan.procedure_type == ProcedureType.CAS
assert len(plan.steps) == 7
```

#### 场景：定义推理步骤模型

**给定**：
- 状态中包含 `reasoning_chain` 字段

**当**：定义 `ReasoningStepModel`

**那么**：应包含以下字段：
- `step_number`: 步骤序号（整数，必需）
- `phase`: 所属阶段（字符串：preop/intraop/postop）
- `description`: 推理描述（字符串，必需）
- `evidence`: 证据来源列表（字符串列表）
- `conclusion`: 结论（字符串，必需）
- `confidence`: 置信度（浮点数 0-1）

**验证**：
```python
from src.agents.models import ReasoningStepModel

step = ReasoningStepModel(
    step_number=1,
    phase="preop",
    description="评估手术适应症",
    evidence=[
        "症状性颈动脉狭窄（TIA病史）",
        "狭窄程度 85% (>70%)",
        "NASCET指南 Class I推荐"
    ],
    conclusion="符合CAS手术适应症",
    confidence=0.95
)

assert step.phase == "preop"
assert step.confidence > 0.9
```

---

### 需求：状态累加器定义

系统**必须**使用 LangGraph 的 Annotated 类型实现状态字段的正确累加行为。

#### 场景：列表字段累加

**给定**：
- 多个节点向 `risk_factors` 字段添加风险因素

**当**：工作流顺序执行这些节点

**那么**：
- 各节点添加的风险因素应合并到同一列表
- 不应覆盖之前节点添加的内容
- 应支持去重（可选配置）

**验证**：
```python
from src.agents.states import ExtendedInterventionalState
from langgraph.graph import StateGraph

# 模拟两个节点分别添加风险因素
def node_a(state):
    return {"risk_factors": [{"name": "高龄", "severity": "moderate"}]}

def node_b(state):
    return {"risk_factors": [{"name": "高血压", "severity": "moderate"}]}

# 执行后应包含两个风险因素
final_state = await workflow.ainvoke(initial_state)
assert len(final_state["risk_factors"]) == 2
```

#### 场景：字典字段合并

**给定**：
- 多个节点更新 `patient_data` 字段的不同子键

**当**：工作流顺序执行这些节点

**那么**：
- 各节点更新的子键应合并
- 相同子键应以最后一个节点的值为准
- 不应丢失未更新的子键

**验证**：
```python
# 初始状态
initial = {"patient_data": {"age": 72, "gender": "female"}}

# node_a 添加诊断
def node_a(state):
    data = state["patient_data"].copy()
    data["diagnosis"] = "颈动脉狭窄"
    return {"patient_data": data}

# node_b 添加病史
def node_b(state):
    data = state["patient_data"].copy()
    data["history"] = ["高血压"]
    return {"patient_data": data}

# 最终应包含所有字段
final = await workflow.ainvoke(initial)
assert final["patient_data"]["age"] == 72
assert final["patient_data"]["diagnosis"] == "颈动脉狭窄"
assert final["patient_data"]["history"] == ["高血压"]
```

---

### 需求：向后兼容性

系统**必须**保持与现有 `InterventionalState` 的向后兼容性。

#### 场景：使用简化状态调用工作流

**给定**：
- 用户使用旧版 `InterventionalState` 格式
- 调用新版工作流

**当**：工作流接收简化状态

**那么**：
- 应自动补充缺失的可选字段
- 应使用默认值初始化新增字段
- 不应抛出类型错误

**验证**：
```python
from src.agents.workflows.interventional import create_interventional_workflow

workflow = create_interventional_workflow(rag_adapter, llm)

# 使用旧版简化状态
legacy_state = {
    "patient_data": {"age": 65, "diagnosis": "冠心病"},
    "procedure_type": "PCI",
    "devices": [],
    "risks": [],
    "recommendations": "",
    "context": [],
    "error": None
}

# 应能正常执行
result = await workflow.ainvoke(legacy_state)
assert result["recommendations"] is not None
```
