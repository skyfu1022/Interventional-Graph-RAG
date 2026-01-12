# 介入手术 SDK 扩展规范

**关联功能**：`workflow-extension`, `state-extension`, `graph-schema`

## 新增需求

### 需求：介入手术规划接口

系统**必须**提供 SDK 接口用于规划介入手术方案，包括患者分析、风险评估和方案生成。

#### 场景：完整的介入手术规划

**给定**：
- Python SDK 客户端已初始化
- 用户提供完整的患者数据和手术类型

**当**：调用 `plan_intervention()` 方法

**那么**：
- 应执行完整的术前评估工作流
- 应返回首选方案和备选方案
- 应包含器械推荐和选择理由
- 应包含风险评估和缓解建议
- 应提供完整的推理链
- 应返回置信度分数

**验证**：
```python
from medgraph import MedGraphClient
from medgraph.types import ProcedureType

client = MedGraphClient(...)

result = await client.plan_intervention(
    patient_data={
        "age": 72,
        "gender": "female",
        "diagnosis": "左侧颈内动脉重度狭窄",
        "history": ["高血压", "高血脂", "TIA"]
    },
    procedure_type=ProcedureType.CAS
)

assert result.primary_plan is not None
assert result.backup_plans is not None
assert len(result.selected_devices) > 0
assert result.confidence_score > 0
assert len(result.reasoning_chain) > 0
assert result.recommendations is not None
```

#### 场景：仅术前风险评估

**给定**：
- 用户仅需风险评估
- SDK 客户端已初始化

**当**：调用 `assess_preop_risks()` 方法

**那么**：
- 应仅执行术前评估相关节点
- 应返回风险因素列表及严重程度
- 应返回禁忌症检查结果（绝对/相对禁忌）
- 应返回风险缓解建议

**验证**：
```python
from medgraph import MedGraphClient

client = MedGraphClient(...)

result = await client.assess_preop_risks(
    patient_data={
        "age": 80,
        "gender": "male",
        "diagnosis": "LAD-CTO",
        "history": ["肾功能不全", "糖尿病"]
    },
    procedure_type="PCI"
)

assert result.risk_factors is not None
assert result.contraindications is not None
assert result.mitigation_suggestions is not None
assert result.overall_risk_level in ["low", "moderate", "high", "very_high"]
```

---

### 需求：器械推荐接口

系统**必须**提供基于病理特征和手术类型的器械推荐接口。

#### 场景：获取器械推荐

**给定**：
- 手术类型和病理特征
- SDK 客户端已初始化

**当**：调用 `get_device_recommendations()` 方法

**那么**：
- 应查询图谱中的器械信息
- 应基于病理特征筛选合适的器械
- 应返回器械列表及推荐理由
- 应包含替代选项
- 应考虑器械的适应症和禁忌症

**验证**：
```python
from medgraph import MedGraphClient

client = MedGraphClient(...)

recommendations = await client.get_device_recommendations(
    procedure_type="CAS",
    pathology={
        "condition": "活动性斑块",
        "severity": "severe"
    }
)

assert len(recommendations.primary) > 0
assert len(recommendations.alternatives) > 0
assert all(d.rationale is not None for d in recommendations.primary)
assert any(d.category == "protection" for d in recommendations.primary)
```

---

### 需求：手术模拟接口

系统**必须**提供流式手术模拟接口，允许用户模拟术中事件并查看系统响应。

#### 场景：流式手术模拟

**给定**：
- 已生成的手术方案
- SDK 客户端已初始化
- 用户指定术中事件序列

**当**：调用 `simulate_procedure()` 方法

**那么**：
- 应返回异步迭代器
- 应按步骤输出模拟结果
- 应响应术中并发症事件
- 应动态调整方案建议
- 应支持中断和恢复

**验证**：
```python
from medgraph import MedGraphClient

client = MedGraphClient(...)

async for step in client.simulate_procedure(
    plan=primary_plan,
    scenario_events=["导丝无法通过", "支架贴壁不良"]
):
    assert step.step_number is not None
    assert step.description is not None
    assert step.status in ["pending", "in_progress", "completed", "failed", "rescued"]

    if step.status == "failed":
        assert step.rescue_action is not None
```

---

### 需求：指南查询接口

系统**必须**提供基于手术类型和临床场景的指南查询接口。

#### 场景：查询相关指南

**给定**：
- 手术类型
- 具体临床场景

**当**：调用 `get_guidelines()` 方法

**那么**：
- 应返回相关指南列表
- 应包含推荐等级和证据级别
- 应支持按推荐等级筛选
- 应包含指南摘要和适用条件

**验证**：
```python
from medgraph import MedGraphClient, RecommendationClass

client = MedGraphClient(...)

guidelines = await client.get_guidelines(
    procedure_type="CAS",
    filters={
        "recommendation_class": RecommendationClass.CLASS_I,
        "age_gt": 70
    }
)

assert len(guidelines) > 0
assert all(g.recommendation_class == "I" for g in guidelines)
assert all("evidence_level" in g for g in guidelines)
```

---

### 需求：术后管理规划接口

系统**必须**提供基于手术方案和患者特征的术后管理规划接口。

#### 场景：生成术后管理方案

**给定**：
- 手术方案已确定
- 患者风险因素已知

**当**：调用 `plan_postop_care()` 方法

**那么**：
- 应返回用药方案
- 应返回监测项目和时间表
- 应返回随访计划
- 应根据风险因素调整方案

**验证**：
```python
from medgraph import MedGraphClient

client = MedGraphClient(...)

postop = await client.plan_postop_care(
    procedure_type="PCI",
    devices_used=["药物洗脱支架"],
    risk_factors=["high_bleeding_risk"]
)

assert postop.medication is not None
assert postop.monitoring is not None
assert postop.followup is not None

# 验证高出血风险时 DAPT 时长调整
assert postop.medication.dapt_duration_months <= 6  # 可能缩短
```

---

### 需求：RESTful API 扩展

系统**必须**扩展 RESTful API 以支持介入手术相关功能。

#### 场景：通过 API 规划介入手术

**给定**：
- API 服务器已启动
- 用户发送 POST 请求

**当**：调用 `POST /api/v1/interventional/plan`

**那么**：
- 应返回 200 状态码
- 响应体应包含完整的手术规划结果
- 应支持同步和异步执行模式

**验证**：
```bash
curl -X POST http://localhost:8000/api/v1/interventional/plan \
  -H "Content-Type: application/json" \
  -d '{
    "patient_data": {
      "age": 72,
      "gender": "female",
      "diagnosis": "左侧颈内动脉重度狭窄",
      "history": ["高血压", "高血脂", "TIA"]
    },
    "procedure_type": "CAS"
  }'

# 响应
{
  "primary_plan": {...},
  "backup_plans": [...],
  "selected_devices": [...],
  "risk_assessment": {...},
  "recommendations": "...",
  "confidence_score": 0.92
}
```

#### 场景：通过 API 执行手术模拟

**给定**：
- API 服务器已启动
- 用户发送 POST 请求

**当**：调用 `POST /api/v1/interventional/simulate`

**那么**：
- 应返回 Server-Sent Events (SSE) 流
- 每个事件应包含步骤信息
- 应支持客户端取消请求

**验证**：
```bash
curl -X POST http://localhost:8000/api/v1/interventional/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan-123",
    "scenario_events": ["导丝无法通过"]
  }'

# SSE 响应流
data: {"step_number": 1, "status": "in_progress", "description": "导丝尝试通过"}
data: {"step_number": 1, "status": "failed", "description": "导丝无法通过"}
data: {"step_number": 2, "status": "in_progress", "description": "尝试平行导丝技术"}
```

---

### 需求：CLI 命令扩展

系统**必须**扩展 CLI 命令以支持介入手术相关功能。

#### 场景：通过 CLI 规划介入手术

**给定**：
- 用户通过命令行使用工具
- 配置文件已设置

**当**：执行 `medgraph interventional plan` 命令

**然后**：
- 应提示用户输入患者信息
- 应显示手术规划结果
- 应支持交互式确认和修改

**验证**：
```bash
medgraph interventional plan --procedure-type CAS <<EOF
72
female
左侧颈内动脉重度狭窄
高血压,高血脂,TIA
EOF

# 输出
╭─────────────────────────────────────────────────────────────────╮
│                    介入手术规划结果                              │
├─────────────────────────────────────────────────────────────────┤
│ 手术类型: CAS (颈动脉支架置入术)                                 │
│ 置信度: 92%                                                      │
│                                                                 │
│ 首选方案:                                                       │
│   • 经股动脉入路，6F导引导管                                     │
│   • 远端栓塞保护装置 (EPD) - 推荐: FilterWire EZ               │
│   • 自膨式支架 - 推荐: Precise PRO RX                          │
│                                                                 │
│ 备选方案:                                                       │
│   • 近端保护系统（Flow Reversal）                               │
│   • 颈动脉内膜剥脱术 (CEA)                                      │
│                                                                 │
│ 风险提示:                                                       │
│   ⚠ 高龄患者围手术期心脑血管事件风险高                          │
│                                                                 │
│ 推荐理由:                                                       │
│   症状性狭窄（TIA病史）+ 重度狭窄（85%）是明确的干预指征。       │
│   活动性斑块增加栓塞风险，强烈推荐使用 EPD。                      │
╰─────────────────────────────────────────────────────────────────╯
```

#### 场景：通过 CLI 查询器械推荐

**给定**：
- 用户需要查询特定器械

**当**：执行 `medgraph interventional devices` 命令

**然后**：
- 应显示器械分类列表
- 应支持筛选和搜索

**验证**：
```bash
medgraph interventional devices --category protection --procedure CAS

# 输出
╭─────────────────────────────────────────────────────────────────╮
│              脑保护装置推荐 (CAS 术式)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 远端滤网装置:                                                   │
│   ✓ FilterWire EZ (Boston Scientific) - Class I 推荐            │
│   ✓ Angioguard XP (Cordis)                                     │
│   ✓ Spider FX (Medtronic)                                      │
│                                                                 │
│ 近端保护系统:                                                   │
│   ✓ Mo.Ma (Medtronic)                                          │
│   ✓ GPI (KIST)                                                 │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```
