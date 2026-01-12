# 介入手术智能体扩展 - 架构设计

## 1. 架构概览

### 1.1 设计原则

1. **三层图谱协同**：患者数据图谱(local) + 医学文献图谱(global) + 医学词典图谱(hybrid)
2. **LLM-first 架构**：每个节点都是 LLM + GraphRAG 检索的组合，移除所有硬编码规则
3. **可追溯推理**：每个决策都记录来源图谱、检索模式和置信度
4. **动态工作流**：基于禁忌症检查和风险评估的条件路由

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         SDK / API 层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ CLI Commands │  │ REST API     │  │ Python SDK           │   │
│  │ medgraph     │  │ /api/v1/     │  │ MedGraphClient       │   │
│  │ interventional│ │ interventional│ │ .plan_intervention() │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph 智能体层                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              InterventionalWorkflow (扩展)                  │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │ │
│  │  │ multi_graph│  │ analyze  │  │ assess   │  │ select    │  │ │
│  │  │ _retrieve  │→│ _patient │→│ _risks   │→│ _devices  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │ │
│  │       ↓             ↓             ↓             ↓         │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │         State: ExtendedInterventionalState           │ │ │
│  │  │   - patient_graph_context                             │ │ │
│  │  │   - literature_graph_context                          │ │ │
│  │  │   - dictionary_graph_context                          │ │ │
│  │  │   - retrieved_entities, matched_guidelines            │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RAGAnything 适配层                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  cross_graph_query()                        │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │  patient_data   │  │   literature    │  │  dictionary  │ │ │
│  │  │  (local mode)   │  │  (global mode)  │  │ (hybrid mode)│ │ │
│  │  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │ │
│  │           │                    │                   │       │ │
│  └───────────┼────────────────────┼───────────────────┼───────┘ │
│              ▼                    ▼                   ▼       │
└──────────────┼────────────────────┼───────────────────┼───────┘
               │                    │                   │
               ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    三层图谱架构（Graph Layer）                    │
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────┐│
│  │   患者数据图谱       │  │   医学文献图谱       │  │ 医学词典图谱││
│  │  (Patient Data)     │  │   (Literature)      │  │(Dictionary)││
│  │                     │  │                     │  │           ││
│  │ graph_id:           │  │ graph_id:           │  │ graph_id: ││
│  │ interventional_patient│ │ interventional_literature│ │ interventional_dictionary││
│  │                     │  │                     │  │           ││
│  │ 主要实体:           │  │ 主要实体:           │  │ 主要实体: ││
│  │ - PatientData       │  │ - Guideline         │  │ - Device   ││
│  │ - Anatomy (个体)    │  │ - Procedure         │  │ - Anatomy  ││
│  │ - Pathology (个体)   │  │ - RiskFactor        │  │ - Complication││
│  │                     │  │ - Complication      │  │           ││
│  │ 查询模式: local     │  │ 查询模式: global    │  │ 查询模式: ││
│  │ (个体数据检索)       │  │ (社区摘要检索)       │  │ hybrid     ││
│  └─────────────────────┘  └─────────────────────┘  └───────────┘│
│                                                                   │
│  底层存储: Neo4j (图) + Milvus (向量)                              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 三层图谱架构说明

| 图谱名称 | graph_id | 主要实体类型 | 查询模式 | 用途 |
|---------|----------|-------------|----------|------|
| 患者数据图谱 | `interventional_patient` | PatientData, Anatomy(个体), Pathology(个体) | `local` | 检索特定患者的历史数据、检查结果 |
| 医学文献图谱 | `interventional_literature` | Guideline, Procedure, RiskFactor, Complication | `global` | 检索指南推荐、社区摘要 |
| 医学词典图谱 | `interventional_dictionary` | Device, Anatomy(通用), PostoperativeCare | `hybrid` | 检索器械规格、术语定义 |

## 2. 图谱 Schema 设计

### 2.1 实体节点属性

#### :Anatomy（解剖结构）
```cypher
(:Anatomy {
    id: String,           -- 唯一标识符
    name: String,         -- 名称，如 "Left Anterior Descending Artery"
    name_cn: String,      -- 中文名称，如 "左前降支"
    code: String,         -- 标准编码（如 SNOMED-CT）
    region: String,       -- 区域分类：cardiac, cerebral, peripheral
    parent_id: String,    -- 父级解剖结构（层级关系）
    description: String,  -- 详细描述
    created_at: DateTime,
    updated_at: DateTime
})
```

#### :Pathology（病理改变）
```cypher
(:Pathology {
    id: String,
    name: String,         -- 如 "Chronic Total Occlusion"
    name_cn: String,      -- 如 "慢性完全闭塞病变"
    code: String,         -- ICD-10 或 SNOMED-CT 编码
    severity: String,     -- mild, moderate, severe
    classification: String, -- 分类标准，如 "Medina 1,1,1"
    characteristics: List[String], -- 特征列表
    description: String,
    created_at: DateTime
})
```

#### :Procedure（手术操作）
```cypher
(:Procedure {
    id: String,
    name: String,         -- 如 "DK-Crush"
    name_cn: String,      -- 如 "DK挤压技术"
    type: String,         -- PCI, CAS, TAVI, etc.
    complexity: String,   -- simple, intermediate, complex
    duration_minutes: Integer, -- 预计时长
    success_rate: Float,  -- 成功率
    steps: List[String],  -- 标准步骤列表
    indications: List[String], -- 适应症
    contraindications: List[String], -- 禁忌症
    created_at: DateTime
})
```

#### :Device（医疗器械）
```cypher
(:Device {
    id: String,
    name: String,         -- 如 "Runthrough NS Guide Wire"
    name_cn: String,
    manufacturer: String, -- 制造商
    category: String,     -- guidewire, stent, balloon, catheter, protection
    specifications: Map,  -- 规格参数
    indications: List[String],
    contraindications: List[String],
    created_at: DateTime
})
```

#### :Guideline（指南条目）
```cypher
(:Guideline {
    id: String,
    name: String,         -- 如 "ACC/AHA PCI Guidelines 2021"
    organization: String, -- 发布组织
    year: Integer,        -- 发布年份
    recommendation_class: String, -- I, IIa, IIb, III
    evidence_level: String, -- A, B, C
    content: String,      -- 推荐内容
    conditions: List[String], -- 适用条件
    created_at: DateTime
})
```

#### :RiskFactor（风险因素）
```cypher
(:RiskFactor {
    id: String,
    name: String,         -- 如 "High Bleeding Risk"
    name_cn: String,      -- 如 "高出血风险"
    category: String,     -- patient, procedural, medication
    severity: String,     -- low, moderate, high
    criteria: List[String], -- 判定标准
    mitigation: List[String], -- 缓解措施
    created_at: DateTime
})
```

#### :Complication（并发症）
```cypher
(:Complication {
    id: String,
    name: String,         -- 如 "Coronary Dissection"
    name_cn: String,      -- 如 "冠脉夹层"
    severity: String,     -- minor, major, life-threatening
    timing: String,       -- intraoperative, immediate, delayed
    incidence_rate: Float,
    symptoms: List[String],
    management: List[String], -- 处理措施
    created_at: DateTime
})
```

#### :PostoperativeCare（术后管理）
```cypher
(:PostoperativeCare {
    id: String,
    name: String,         -- 如 "DAPT Regimen"
    name_cn: String,      -- 如 "双联抗血小板治疗方案"
    type: String,         -- medication, monitoring, followup
    duration: String,     -- 持续时间
    protocol: String,     -- 详细方案
    monitoring_items: List[String], -- 监测项目
    created_at: DateTime
})
```

### 2.2 关系属性设计

#### :CONTRAINDICATES（禁忌）
```cypher
(:RiskFactor)-[:CONTRAINDICATES {
    strength: String,     -- absolute, relative
    evidence_level: String,
    source: String,       -- 来源指南
    notes: String
}]->(:Procedure)
```

#### :USES_DEVICE（使用器械）
```cypher
(:IntraoperativeEvent)-[:USES_DEVICE {
    required: Boolean,    -- 是否必需
    alternatives: List[String], -- 替代选择
    parameters: Map,      -- 使用参数
    notes: String
}]->(:Device)
```

#### :LEADS_TO_COMPLICATION（导致并发症）
```cypher
(:IntraoperativeEvent)-[:LEADS_TO_COMPLICATION {
    probability: Float,   -- 发生概率
    risk_factors: List[String], -- 增加风险的因素
    prevention: List[String], -- 预防措施
    source: String
}]->(:Complication)
```

## 3. LangGraph 工作流设计

### 3.1 扩展状态定义（含 GraphRAG 结果）

```python
from typing import TypedDict, List, Optional, Dict, Any, Annotated, Literal
from typing_extensions import Required
from operator import add
from pydantic import BaseModel
from enum import Enum
import json

class GraphSource(str, Enum):
    """图谱来源枚举"""
    PATIENT_DATA = "patient_data"
    LITERATURE = "literature"
    DICTIONARY = "dictionary"

class RetrievedEntity(BaseModel):
    """从图谱检索到的实体"""
    name: str
    type: str
    description: str
    confidence: float
    source_graph: GraphSource
    properties: Dict[str, Any] = {}

class RetrievedRelationship(BaseModel):
    """从图谱检索到的关系"""
    source: str
    target: str
    relation_type: str
    description: str
    weight: float
    source_graph: GraphSource

class GuidelineMatch(BaseModel):
    """匹配的指南条目"""
    guideline_name: str
    recommendation_class: str  # I, IIa, IIb, III
    evidence_level: str         # A, B, C
    content: str
    relevance_score: float
    source: str

class ExtendedInterventionalState(TypedDict):
    """扩展的介入手术智能体状态 - 支持 GraphRAG"""

    # ===== 输入 =====
    patient_data: Required[Dict[str, Any]]
    procedure_type: Required[str]
    query: str  # 原始查询

    # ===== GraphRAG 检索结果 =====
    retrieved_entities: Annotated[List[RetrievedEntity], add]
    retrieved_relationships: Annotated[List[RetrievedRelationship], add]
    matched_guidelines: Annotated[List[GuidelineMatch], add]

    # 来自不同图谱的上下文
    patient_graph_context: Optional[str]    # 患者数据图谱检索上下文
    literature_graph_context: Optional[str]  # 文献指南图谱检索上下文
    dictionary_graph_context: Optional[str]  # 医学词典图谱检索上下文

    # ===== LLM 分析结果 =====
    patient_analysis: Optional[Dict[str, Any]]      # 患者分析结果
    device_recommendations: Optional[List[Dict]]   # 器械推荐
    risk_assessment: Optional[Dict[str, Any]]      # 风险评估
    procedure_plan: Optional[Dict[str, Any]]       # 手术方案

    # ===== 推理链 =====
    reasoning_chain: Annotated[List[str], add]
    context: Annotated[List[str], add]

    # ===== 输出 =====
    recommendations: str
    confidence_score: float

    # ===== 元数据 =====
    retrieval_mode: str  # 使用的检索模式
    sources: Annotated[List[Dict], add]  # 来源追踪
    error: Optional[str]

    # ===== 控制 =====
    current_phase: str  # preop, intraop, postop
    step: str
```

### 3.2 术前评估工作流设计（Pre-op Workflow）

基于 U-Retrieval（Top-down + Bottom-up）的术前评估流程：

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         术前评估工作流 (Pre-operative)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐                                                              │
│  │  START       │                                                              │
│  └──────┬───────┘                                                              │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  intent_recognition_node (意图识别节点)                                  │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  输入: 用户原始查询                                                       │   │
│  │  处理:                                                                   │   │
│  │    1. 识别手术类型 (PCI/CAS/TAVI)                                        │   │
│  │    2. 提取实体:                                                           │   │
│  │       - :RiskFactor (风险因素): Age > 70, Hypertension, Hyperlipidemia   │   │
│  │       - :Pathology (病理): 重度狭窄85%, 活动性斑块                        │   │
│  │       - :PatientData (病史): TIA history                                 │   │
│  │       - :Anatomy (解剖): Left ICA, 起始部                                │   │
│  │  输出: structured_query (结构化查询参数)                                   │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  u_retrieval_node (U-Retrieval 知识检索节点) ⭐ 核心                       │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  Top-down（精确索引检索）:                                               │   │
│  │    ┌──────────────────────────────────────────────────────────────────┐ │   │
│  │    │ 从医学文献图谱 (global 模式) 检索:                                  │ │   │
│  │    │   • 权威指南节点 (:Guideline) - 如 NASCET/CAS 指南                │ │   │
│  │    │   • 推荐等级 (Class I/IIa/IIb/III) 和证据级别 (A/B/C)            │ │   │
│  │    │   • 适应症和禁忌症定义                                             │ │   │
│  │    └──────────────────────────────────────────────────────────────────┘ │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  Bottom-up（全局聚合检索）:                                              │   │
│  │    ┌──────────────────────────────────────────────────────────────────┐ │   │
│  │    │ 结合患者上下文向上聚合:                                            │ │   │
│  │    │   • 高龄(>70岁) + 症状性 → CAS vs CEA 风险比较数据                │ │   │
│  │    │   • 活动性斑块 → 脑保护装置(EPD)选择依据                           │ │   │
│  │    │   从患者图谱(local)检索: 既往病史、检查结果                        │ │   │
│  │    │   从词典图谱(hybrid)检索: 器械规格、适应症                         │ │   │
│  │    └──────────────────────────────────────────────────────────────────┘ │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  输出: guideline_context, patient_context, device_context              │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  assess_indications_node (适应症评估节点)                                │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  LLM 驱动分析:                                                            │   │
│  │    • 判断是否符合手术适应症 (基于指南推荐)                                │   │
│  │    • 引用指南依据 (如 "症状性+重度狭窄>70% = Class I 推荐")              │   │
│  │  输出: indicated / not_indicated / uncertain                             │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                    ┌──────────┴──────────┐                                    │
│                    │                     │                                    │
│              not_indicated          indicated                                 │
│                    │                     │                                    │
│                    ▼                     ▼                                    │
│            ┌───────────────┐   ┌─────────────────────────────────────────┐   │
│            │  END          │   │  assess_contraindications_node (禁忌症)  │   │
│            │  (不推荐手术)  │   │  --------------------------------------   │   │
│            └───────────────┘   │  • Class III (绝对禁忌) → abort          │   │
│                                │  • Class II (相对禁忌) → modify          │   │
│                                │  • 无禁忌症 → proceed                    │   │
│                                └──────────────┬──────────────────────────┘   │
│                                               │                               │
│                            ┌──────────────────┼──────────────────┐            │
│                            │                  │                  │            │
│                         proceed            modify             abort        │
│                            │                  │                  │            │
│                            ▼                  ▼                  ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  assess_risks_node (风险评估节点)        │ modify → 调整方案  │            │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  LLM + 指南驱动:                                                          │   │
│  │    • 风险等级评估 (低/中/高/极高)                                         │   │
│  │    • 识别主要风险因素 (高龄、活动性斑块、凝血功能等)                       │   │
│  │    • 提出风险缓解措施 (术前优化、药物调整)                                 │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  match_procedure_node (术式匹配节点) ⭐ Graph Traversal                    │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  图谱遍历逻辑 (沿关系链推理):                                              │   │
│  │    (:Guideline) -[:BASED_ON_GUIDELINE]-> (:Procedure) 首选术式            │   │
│  │           (:Procedure) -[:HAS_STEP]-> (:IntraoperativeEvent) 所需步骤     │   │
│  │             (:Event) -[:USES_DEVICE]-> (:Device) 所需器械                │   │
│  │               (:Device) -[:CONTRAINDICATES]-> (:RiskFactor) 器械禁忌      │   │
│  │           (:Procedure) -[:REQUIRES_RESCUE]-> (:Procedure) 备选方案        │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  LLM + Graph Traversal 结合:                                             │   │
│  │    • 根据检索到的关系链推理首选方案                                        │   │
│  │    • 识别关键分支点 (如 EPD 部署失败时的备选)                             │   │
│  │    • 考虑器械禁忌关系                                                    │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  generate_plan_node (方案综合节点)                                        │   │
│  │  ---------------------------------------------------------------------   │   │
│  │  整合所有分析，生成结构化输出:                                             │   │
│  │    • 首选方案 (Plan A): 术式、步骤、器械、入路、理由                       │   │
│  │    • 备选方案 (Plan B): 应急处理、转换条件                                │   │
│  │    • 风险提示: 主要风险因素和预防措施                                      │   │
│  │    • 推荐理由: 引用指南来源和图谱关系                                      │   │
│  └────────────────────────────┬────────────────────────────────────────────┘   │
│                               │                                                │
│                               ▼                                                │
│                          ┌─────────┐                                          │
│                          │  END    │                                          │
│                          └─────────┘                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 节点-图谱映射表（更新）

| 节点 | 使用的图谱 | 检索模式 | 检索内容 | LLM 角色 |
|------|-----------|---------|----------|----------|
| `intent_recognition` | 无 | N/A | 解析用户输入，提取实体 | LLM 实体识别 |
| `u_retrieval` (Top-down) | literature | **global** | 权威指南、推荐等级 | N/A（纯检索） |
| `u_retrieval` (Bottom-up) | patient + literature + dictionary | **local + global + hybrid** | 患者历史 + 风险数据 + 器械规格 | N/A（纯检索） |
| `assess_indications` | literature (已检索) | - | 使用已检索的指南上下文 | 基于指南判断适应症 |
| `assess_contraindications` | literature (已检索) | - | 使用已检索的禁忌症信息 | 基于指南判断禁忌等级 |
| `assess_risks` | literature (已检索) | - | 使用已检索的风险因素数据 | 基于患者特征评估风险 |
| `match_procedure` | 全部 | **Graph Traversal** | 沿关系链遍历：术式→步骤→器械→备选 | LLM 推理关系链 |
| `generate_plan` | 全部 (已检索) | - | 整合所有检索和分析结果 | LLM 综合生成方案 |

### 3.4 完整三阶段工作流（术中、术后扩展）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    完整介入手术工作流 (Pre-op → Intra-op → Post-op)             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  【术前评估阶段】                                                                │
│  START → intent_recognition → u_retrieval → assess_indications                 │
│         → assess_contraindications → assess_risks → match_procedure            │
│         → generate_preop_plan ──┐                                               │
│                                │                                                │
│  【术中执行阶段】(扩展)          │                                                │
│                         ◄──────┘                                                │
│  execute_procedure_node ──→ monitor_complications_node ──→ handle_events_node  │
│         (执行术式)               (监测并发症)                 (处理术中事件)     │
│                                                                                 │
│  【术后管理阶段】(扩展)                                                          │
│  plan_postop_care_node ──→ generate_discharge_plan ──→ END                     │
│    (规划术后管理)            (生成出院计划)                                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4. 数据模型设计

### 4.1 Pydantic 模型

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ProcedureType(str, Enum):
    PCI = "PCI"
    CAS = "CAS"
    TAVI = "TAVI"

class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"

class PatientDataModel(BaseModel):
    """患者数据模型"""
    age: int
    gender: str
    weight: Optional[float] = None
    height: Optional[float] = None
    diagnosis: str
    history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    lab_results: dict = Field(default_factory=dict)
    imaging_results: List[str] = Field(default_factory=list)

class AnatomyFinding(BaseModel):
    """解剖发现"""
    structure: str
    location: str
    characteristics: List[str] = Field(default_factory=list)

class PathologyFinding(BaseModel):
    """病理发现"""
    condition: str
    severity: Severity
    classification: Optional[str] = None
    measurements: dict = Field(default_factory=dict)

class RiskFactorModel(BaseModel):
    """风险因素"""
    name: str
    category: str
    severity: Severity
    mitigation: List[str] = Field(default_factory=list)

class DeviceSelection(BaseModel):
    """器械选择"""
    device_name: str
    category: str
    specifications: dict = Field(default_factory=dict)
    rationale: str

class ProcedurePlan(BaseModel):
    """手术方案"""
    procedure_name: str
    procedure_type: ProcedureType
    steps: List[str]
    devices: List[DeviceSelection]
    estimated_duration: int
    success_probability: float
    rationale: str

class GuidelineMatch(BaseModel):
    """指南匹配"""
    guideline_name: str
    recommendation_class: str
    evidence_level: str
    content: str
    relevance_score: float

class ReasoningStep(BaseModel):
    """推理步骤"""
    step_number: int
    description: str
    evidence: List[str]
    conclusion: str
```

## 5. API 设计

### 5.1 RESTful API 端点

```
POST /api/v1/interventional/plan
  - 请求体: InterventionalPlanRequest
  - 响应: InterventionalPlanResponse

POST /api/v1/interventional/simulate
  - 请求体: SimulationRequest
  - 响应: SimulationResponse (流式)

GET /api/v1/interventional/guidelines/{procedure_type}
  - 响应: List[Guideline]

GET /api/v1/interventional/devices/{category}
  - 响应: List[Device]

POST /api/v1/interventional/risk-assessment
  - 请求体: RiskAssessmentRequest
  - 响应: RiskAssessmentResponse
```

### 5.2 SDK 接口

```python
class InterventionalClient:
    """介入手术智能体客户端"""

    async def plan_intervention(
        self,
        patient_data: PatientDataModel,
        procedure_type: ProcedureType,
        preferences: Optional[dict] = None
    ) -> InterventionalPlanResult:
        """规划介入手术方案"""
        pass

    async def simulate_procedure(
        self,
        plan: ProcedurePlan,
        scenario_events: Optional[List[str]] = None
    ) -> AsyncIterator[SimulationStep]:
        """模拟手术过程（流式输出）"""
        pass

    async def assess_risks(
        self,
        patient_data: PatientDataModel,
        procedure_type: ProcedureType
    ) -> RiskAssessmentResult:
        """评估手术风险"""
        pass

    async def get_device_recommendations(
        self,
        procedure_type: ProcedureType,
        pathology: PathologyFinding
    ) -> List[DeviceRecommendation]:
        """获取器械推荐"""
        pass
```

## 6. 权衡与决策

### 6.1 状态管理策略

**选项 A**：继承现有 `InterventionalState`
- 优点：向后兼容，渐进式升级
- 缺点：可能导致状态类过于臃肿

**选项 B**：创建新的 `ExtendedInterventionalState`（选择）
- 优点：清晰分离，专注于介入手术场景
- 缺点：需要适配现有接口

**决策**：选择 B，通过工厂函数支持两种状态类型的兼容。

### 6.2 图谱 Schema 演进策略

**选项 A**：扩展现有 RAG-Anything 图谱
- 优点：复用现有基础设施
- 缺点：可能与通用医学实体混淆

**选项 B**：创建独立的介入手术图谱命名空间（选择）
- 优点：清晰分离，便于管理
- 缺点：需要跨图谱查询

**决策**：选择 B，使用 Neo4j 标签前缀（如 `:Interventional_Anatomy`）区分。

### 6.3 指南集成方式

**选项 A**：静态导入指南到图谱
- 优点：查询快速，离线可用
- 缺点：需要定期更新

**选项 B**：运行时检索指南（选择）
- 优点：始终使用最新版本
- 缺点：依赖 RAG 检索质量

**决策**：选择混合方案 - 核心指南静态导入，详细内容运行时检索。

## 7. GraphRAG 集成方案

### 7.1 跨图谱查询函数

```python
from src.core.adapters import RAGAnythingAdapter

async def cross_graph_query(
    adapter: RAGAnythingAdapter,
    query: str,
    procedure_type: str,
    patient_id: Optional[str] = None
) -> Dict[str, Any]:
    """执行跨三层图谱的联合查询"""

    results = {
        "patient_context": None,
        "guideline_context": None,
        "device_context": None,
        "retrieved_entities": [],
        "matched_guidelines": []
    }

    # 1. 从患者图谱检索该患者的历史数据
    if patient_id:
        results["patient_context"] = await adapter.query(
            query=f"患者 {patient_id} 的病史、检查结果、既往手术",
            mode="local",
            graph_id="interventional_patient"
        )

    # 2. 从指南图谱检索适应症/禁忌症
    results["guideline_context"] = await adapter.query(
        query=f"{procedure_type} 的适应症、禁忌症、操作规范",
        mode="global",
        graph_id="interventional_literature"
    )

    # 3. 从词典图谱检索器械/解剖术语
    results["device_context"] = await adapter.query(
        query=f"{procedure_type} 相关的器械名称、规格、适应症",
        mode="hybrid",
        graph_id="interventional_dictionary"
    )

    return results
```

### 7.2 LLM 驱动的节点实现示例

```python
async def analyze_patient_node_llm(
    state: InterventionalState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """使用 LLM + GraphRAG 分析患者数据"""

    rag_adapter = config["configurable"]["rag_adapter"]
    llm = config["configurable"]["llm"]

    patient_data = state["patient_data"]
    procedure_type = state["procedure_type"]

    # 1. 使用 GraphRAG 检索该患者相关的历史数据
    patient_context = await rag_adapter.query(
        query=f"""
        患者 {patient_data.get('patient_id', '')} 的相关信息：
        - 既往病史
        - 既往手术记录
        - 过敏史
        - 检查结果异常
        """,
        mode="local",
        graph_id="interventional_patient"
    )

    # 2. 使用 GraphRAG 检索该手术类型的患者筛选标准
    guideline_context = await rag_adapter.query(
        query=f"{procedure_type} 的患者适应症和禁忌症",
        mode="global",
        graph_id="interventional_literature"
    )

    # 3. 使用 LLM 进行综合分析
    analysis_prompt = f"""你是一位介入手术专家。请分析以下患者是否适合进行 {procedure_type}。

【患者信息】
{json.dumps(patient_data, ensure_ascii=False)}

【患者历史数据】（从知识图谱检索）
{patient_context.answer}

【临床指南】（从知识图谱检索）
{guideline_context.answer}

请按以下格式输出分析结果：

1. **适应症评估**：列出符合的适应症（引用指南依据）
2. **禁忌症检查**：列出存在的禁忌症（引用指南依据）
3. **风险分层**：评估手术风险等级（低/中/高）
4. **术前准备建议**：列出需要完成的术前检查或准备

输出为 JSON 格式。
"""

    response = await llm.ainvoke(analysis_prompt)

    # 4. 解析 LLM 返回的结构化结果
    try:
        analysis_result = json.loads(response.content)
    except:
        analysis_result = parse_analysis_fallback(response.content)

    return {
        "patient_analysis": analysis_result,
        "patient_graph_context": patient_context.answer,
        "literature_graph_context": guideline_context.answer,
        "sources": {
            "patient_graph": patient_context.sources,
            "guideline_graph": guideline_context.sources
        }
    }
```

### 7.3 条件路由实现

```python
def check_contraindications(state: InterventionalState) -> Literal["proceed", "modify", "abort"]:
    """检查是否存在绝对禁忌症"""
    analysis = state.get("patient_analysis", {})
    contraindications = analysis.get("contraindications", [])

    for c in contraindications:
        if c.get("class") == "III":  # Class III = 绝对禁忌
            return "abort"
        elif c.get("class") == "II":  # Class II = 相对禁忌
            return "modify"
    return "proceed"

def should_plan_rescue(state: InterventionalState) -> Literal["high_risk", "normal"]:
    """判断是否需要规划并发症处理方案"""
    risk_assessment = state.get("risk_assessment", {})
    risk_level = risk_assessment.get("risk_level", "low")
    return "high_risk" if risk_level in ["high", "very_high"] else "normal"
```

## 8. 实体类型映射到 LightRAG 模型

LightRAG 使用固定的 `__Entity__` 标签，介入手术专用实体需要映射：

```python
# 实体类型映射策略
ENTITY_TYPE_MAPPING = {
    # 介入手术专用类型 -> LightRAG 存储类型
    "Anatomy": "ANATOMY",
    "Pathology": "PATHOLOGY",
    "Procedure": "PROCEDURE",
    "Device": "DEVICE",
    "Guideline": "GUIDELINE",
    "RiskFactor": "RISK_FACTOR",
    "Complication": "COMPLICATION",
    "PostoperativeCare": "CARE_PLAN",
    "IntraoperativeEvent": "EVENT",
    "Image": "IMAGE",
    "PatientData": "PATIENT",
}

# 实体提取时指定类型
ENTITY_EXTRACTION_PROMPT = """
从以下医学文本中提取实体，包括以下类型：
{entity_types}

对于每个实体，返回：
- entity_name: 实体名称
- entity_type: 实体类型（必须从以下选择：{valid_types}）
- description: 实体描述

文本：{text}
"""
```
