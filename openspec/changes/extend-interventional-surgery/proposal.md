# 提案：扩展介入手术智能体支持

## 变更ID
`extend-interventional-surgery`

## 概述

在现有 Medical Graph RAG 项目基础上，扩展介入手术智能体的能力，包括：
1. 新增介入手术专用的知识图谱实体和关系类型
2. 扩展 LangGraph 工作流以支持完整的术前-术中-术后决策流程
3. 提供临床场景模拟能力（如冠脉介入 PCI、颈动脉支架置入 CAS 等）

## 动机

### 当前状态
现有的 `InterventionalState` 和 `create_interventional_agent` 仅提供了基础的扩展点框架，但存在以下问题：
- **未集成 GraphRAG 检索**：节点未调用 `RAGAnythingAdapter`，无法从知识图谱获取医学知识
- **基于硬编码规则**：患者分析、器械选择、风险评估使用 if/else 启发式规则，而非 LLM 驱动
- **缺少三层图谱协同**：未利用现有的患者数据/医学文献/医学词典三层图谱架构
- **缺少条件路由**：线性工作流，无法处理禁忌症分支和应急方案

### 扩展需求
介入手术场景需要更精细的知识表示和决策支持：

1. **GraphRAG 集成**：每个节点都应通过 `RAGAnythingAdapter` 检索三层图谱知识
2. **LLM 驱动决策**：移除所有硬编码规则，所有决策由 LLM 基于检索的上下文生成
3. **实体类型扩展**：新增解剖结构、病理改变、术中事件、并发症、术后管理等实体类型
4. **动态工作流**：支持条件分支（禁忌症路由）和应急方案处理
5. **临床指南集成**：从医学文献图谱检索权威临床指南作为决策依据

### 扩展收益

1. **三层图谱协同**：患者数据图谱（个体信息）+ 医学文献图谱（指南）+ 医学词典图谱（器械/术语）
2. **LLM-first 架构**：所有决策节点都是 LLM + GraphRAG 检索的组合
3. **可追溯推理**：每个决策都记录来源图谱、检索模式和置信度
4. **动态工作流**：基于禁忌症检查和风险评估的条件路由

## 技术选型

| 组件 | 当前实现 | 扩展方案 | 理由 |
|------|----------|----------|------|
| 图谱架构 | 单一图谱 | **三层图谱协同查询** | 患者数据(local) + 医学文献(global) + 医学词典(hybrid) |
| 检索引擎 | RAGAnythingAdapter（未使用） | **集成 RAGAnythingAdapter** | 支持6种检索模式，复用现有基础设施 |
| 实体类型 | 通用医学实体 | **11种介入手术专用实体** | 映射到 LightRAG 的 __Entity__ 模型 |
| 关系类型 | 通用关系 | **14种阶段性关系** | 术前/术中/术后各阶段专业关系 |
| 工作流 | 4节点线性流程（硬编码） | **多分支 LLM 驱动决策树** | 每个节点都是 LLM + GraphRAG |
| 状态管理 | 基础状态 | **扩展状态（含 GraphRAG 结果）** | retrieved_entities, matched_guidelines 等 |

## 新增实体类型

| 标签 | 英文名称 | 描述 | 示例 |
|------|----------|------|------|
| `:Anatomy` | 解剖结构 | 患者的解剖部位，血管信息 | "Left Anterior Descending Artery" (LAD) |
| `:Pathology` | 病理改变 | 疾病或病变特征 | "Chronic Total Occlusion" (CTO), "Medina 1,1,1" |
| `:Procedure` | 手术操作或术式 | 完整的术式或核心操作 | "DK-Crush", "Kissing Balloon Inflation" |
| `:Device` | 医疗器械 | 导管、导丝、支架等具体器械 | "Runthrough NS Guide Wire", "Firehawk Stent" |
| `:Guideline` | 指南条目 | 权威指南的推荐或决策树分支 | Class I/II/III Recommendation |
| `:Image` | 影像 | 存储影像的 Embedding 和元数据 | DSA 造影截图 |
| `:PatientData` | 患者基础数据 | 术前重要的生理参数和病史 | Age, eGFR, LVEF, History |
| `:RiskFactor` | 临床风险因素 | 可能影响决策的风险项 | "High Bleeding Risk" (HBR), "Contrast Allergy" |
| `:IntraoperativeEvent` | 术中关键事件/步骤 | 术中实际执行的特定动作 | "Stent Post-dilation", "Wire Passage Attempt" |
| `:Complication` | 并发症 | 术中或术后发生的负面事件 | "Dissection", "No Reflow", "Stent Thrombosis" |
| `:PostoperativeCare` | 术后管理 | 术后用药、随访等方案 | "DAPT Regimen", "6-Month Follow-up" |

## 新增关系类型

### 术前（Pre-operative）阶段

| 关系类型 | 描述 | 示例关系 |
|----------|------|----------|
| `:HAS_RISK` | 患者具有某种风险因素 | `(:PatientData) -[:HAS_RISK]-> (:RiskFactor)` |
| `:HAS_EXAM_RESULT` | 患者拥有某项检查结果 | `(:PatientData) -[:HAS_EXAM_RESULT]-> (:Image)` |
| `:SHOWS` | 检查或影像显示病理信息 | `(:Image) -[:SHOWS]-> (:Pathology)` |
| `:BASED_ON_GUIDELINE` | 初始方案是基于某个指南 | `(:Procedure) -[:BASED_ON_GUIDELINE]-> (:Guideline)` |
| `:CONTRAINDICATES` | 风险因素禁忌某种术式或器械 | `(:RiskFactor) -[:CONTRAINDICATES]-> (:Procedure)` |

### 术中（Intra-operative）阶段

| 关系类型 | 描述 | 示例关系 |
|----------|------|----------|
| `:HAS_STEP` | 术式包含的具体步骤 | `(:Procedure) -[:HAS_STEP]-> (:IntraoperativeEvent)` |
| `:USES_DEVICE` | 术中步骤使用特定器械 | `(:IntraoperativeEvent) -[:USES_DEVICE]-> (:Device)` |
| `:LEADS_TO_COMPLICATION` | 术中操作导致并发症 | `(:IntraoperativeEvent) -[:LEADS_TO_COMPLICATION]-> (:Complication)` |
| `:REQUIRES_RESCUE` | 并发症需要抢救/备选方案 | `(:Complication) -[:REQUIRES_RESCUE]-> (:Procedure)` |
| `:MEASURES` | 术中测量的解剖或病变数据 | `(:IntraoperativeEvent) -[:MEASURES]-> (:Anatomy)` |

### 术后（Post-operative）阶段

| 关系类型 | 描述 | 示例关系 |
|----------|------|----------|
| `:PRESCRIBES` | 手术方案对应的术后护理 | `(:Procedure) -[:PRESCRIBES]-> (:PostoperativeCare)` |
| `:RECEIVED_CARE` | 患者接受了某种术后管理 | `(:PatientData) -[:RECEIVED_CARE]-> (:PostoperativeCare)` |
| `:OBSERVED_OUTCOME` | 术后管理/随访观察到的结果 | `(:PostoperativeCare) -[:OBSERVED_OUTCOME]-> (:Complication)` |
| `:LINKED_TO` | 链接到最终临床结果 | `(:Procedure) -[:LINKED_TO]-> (:PatientData)` |

## 影响范围

### 代码组织变化
```
src/
├── agents/
│   ├── workflows/
│   │   └── interventional.py  # 扩展现有工作流
│   └── states.py              # 扩展状态定义
├── graph/                     # 新增：介入手术图谱模块
│   ├── __init__.py
│   ├── entities.py           # 实体类型定义
│   ├── relationships.py      # 关系类型定义
│   └── schema.py             # Neo4j Schema 管理
├── services/
│   └── interventional.py     # 新增：介入手术服务层
└── sdk/
    └── interventional.py     # 新增：SDK 扩展
```

### 依赖变更
- 无新依赖，复用现有 Neo4j 和 LangGraph

### 功能变更

#### 1. 扩展的介入手术工作流
现有 4 节点工作流扩展为多分支决策树：
- 术前评估分支：适应症评估 → 风险分层 → 方案选择
- 术中决策分支：器械选择 → 步骤执行 → 并发症处理
- 术后管理分支：用药方案 → 随访计划

#### 2. 临床场景模拟
支持的介入手术类型：
- **PCI**（经皮冠状动脉介入）：包括 CTO、分叉病变等复杂场景
- **CAS**（颈动脉支架置入术）：包括脑保护装置选择
- **TAVI**（经导管主动脉瓣置换术）：预留扩展接口

#### 3. 指南集成
集成权威临床指南作为决策依据：
- ACC/AHA 冠脉介入指南
- NASCET/CAS 颈动脉介入指南
- ESC 心血管疾病指南

## 向后兼容性

此扩展为**非破坏性变更**：
1. 现有 `InterventionalState` 保持兼容，通过继承扩展
2. 现有 `create_interventional_agent` 保留原有接口
3. 新增功能通过可选参数和新方法提供

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 实体/关系过于复杂 | 中 | 分阶段实现，先核心后扩展 |
| 临床知识准确性 | 高 | 基于权威指南，需临床专家审核 |
| 工作流分支过多 | 中 | 使用 LangGraph 条件路由，保持清晰 |
| Neo4j Schema 迁移 | 低 | 使用 Schema 版本管理 |

## 临床场景示例

### 颈动脉支架置入术（CAS）规划

**用户输入**：
> "患者72岁女性，高血压、高血脂史。颈部超声显示左侧颈内动脉起始部重度狭窄（85%），有活动性斑块。患者近期有短暂性脑缺血发作（TIA）病史。请制定颈动脉支架置入术（CAS）的手术策略。"

**系统执行流程**：

1. **意图识别**：识别为"症状性颈动脉狭窄（CAS）策略制定"
   - 提取实体：Age > 70, Hypertension, Hyperlipidemia, Left ICA stenosis 85%, Active plaque, TIA

2. **三层图谱检索（U-Retrieval）**：
   ```python
   # 跨三层图谱并行查询
   results = await cross_graph_query(
       rag_adapter=rag_adapter,
       query="症状性颈动脉狭窄 CAS 适应症 禁忌症 脑保护装置",
       procedure_type="CAS",
       patient_id="patient_123"  # 可选，用于检索患者历史
   )
   # 返回：
   # - patient_context: 从患者数据图谱检索（local 模式）
   # - guideline_context: 从医学文献图谱检索（global 模式）
   # - device_context: 从医学词典图谱检索（hybrid 模式）
   ```

3. **LLM 驱动的代理推理**：
   - **适应症评估节点**：LLM 基于检索到的指南，判断症状性+重度狭窄（85%）是否为干预指征
   - **风险评估节点**：LLM 基于患者特征和指南，评估高龄+活动性斑块的卒中风险
   - **器械推荐节点**：LLM 从检索到的器械中选择远端栓塞保护装置（EPD）

4. **条件路由**：
   ```python
   def check_contraindications(state) -> Literal["proceed", "modify", "abort"]:
       analysis = state["patient_analysis"]
       for c in analysis.get("contraindications", []):
           if c.get("class") == "III":  # 绝对禁忌
               return "abort"
           elif c.get("class") == "II":  # 相对禁忌
               return "modify"
       return "proceed"
   ```

5. **生成输出**：
   - **首选方案**：CAS + 远端栓塞保护装置（EPD）
   - **备选方案**：近端保护系统（Flow Reversal）或 CEA
   - **来源追溯**：每个推荐都标注来源图谱和指南条目

## 参考资料

- 现有 `src/agents/workflows/interventional.py` 实现
- 现有 `src/agents/states.py` 中的 `InterventionalState`
- 现有 `src/core/adapters.py` 中的 `RAGAnythingAdapter`
- `openspec/changes/refactor-langgraph-raganything/specs/agent-layer/spec.md` 规范
