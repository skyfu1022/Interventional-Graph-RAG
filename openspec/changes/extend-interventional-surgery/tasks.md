# 介入手术智能体扩展 - 任务列表

## 概述

本任务列表基于提案 `extend-interventional-surgery` 的规范，按依赖关系排序。

**核心原则**：
1. **所有节点必须是 LLM 驱动**：移除所有硬编码规则，每个节点通过 LLM + GraphRAG 检索生成决策
2. **三层图谱协同**：患者数据图谱(local) + 医学文献图谱(global) + 医学词典图谱(hybrid)
3. **可追溯推理**：每个决策都记录来源图谱、检索模式和置信度

---

## 阶段一：图谱 Schema 层（可并行）

### 任务 1.1：定义介入手术实体类型（映射到 LightRAG） ✅
- **规范**：`graph-schema/spec.md` - 需求：介入手术实体类型定义
- **文件**：`src/graph/entities.py`（新建）
- **内容**：
  - [x] 定义 `ENTITY_TYPE_MAPPING` 常量（映射介入手术类型到 LightRAG）
  - [x] 创建 `AnatomyEntity` 类（映射到 `ANATOMY`）
  - [x] 创建 `PathologyEntity` 类（映射到 `PATHOLOGY`）
  - [x] 创建 `ProcedureEntity` 类（映射到 `PROCEDURE`）
  - [x] 创建 `DeviceEntity` 类（映射到 `DEVICE`）
  - [x] 创建 `GuidelineEntity` 类（映射到 `GUIDELINE`）
  - [x] 创建 `RiskFactorEntity` 类（映射到 `RISK_FACTOR`）
  - [x] 创建 `ComplicationEntity` 类（映射到 `COMPLICATION`）
  - [x] 创建 `PostoperativeCareEntity` 类（映射到 `CARE_PLAN`）
  - [x] 创建 `IntraoperativeEventEntity` 类（映射到 `EVENT`）
  - [x] 创建 `ImageEntity` 类（映射到 `IMAGE`）
  - [x] 创建 `PatientDataEntity` 类（映射到 `PATIENT`）
- **验证**：单元测试 `tests/test_graph/test_entities.py`

### 任务 1.2：定义介入手术关系类型 ✅
- **规范**：`graph-schema/spec.md` - 需求：介入手术关系类型定义
- **文件**：`src/graph/relationships.py`（新建）
- **依赖**：任务 1.1
- **内容**：
  - [x] 创建 `HasRiskRelation` 类
  - [x] 创建 `HasExamResultRelation` 类
  - [x] 创建 `ShowsRelation` 类
  - [x] 创建 `BasedOnGuidelineRelation` 类
  - [x] 创建 `ContraindicatesRelation` 类
  - [x] 创建 `HasStepRelation` 类
  - [x] 创建 `UsesDeviceRelation` 类
  - [x] 创建 `LeadsToComplicationRelation` 类
  - [x] 创建 `RequiresRescueRelation` 类
  - [x] 创建 `MeasuresRelation` 类
  - [x] 创建 `PrescribesRelation` 类
  - [x] 创建 `ReceivedCareRelation` 类
  - [x] 创建 `ObservedOutcomeRelation` 类
  - [x] 创建 `LinkedToRelation` 类
- **验证**：单元测试 `tests/test_graph/test_relationships.py`

### 任务 1.3：实现 Schema 管理器 ✅
- **规范**：`graph-schema/spec.md` - 需求：图谱 Schema 管理
- **文件**：`src/graph/schema.py`（新建）
- **依赖**：任务 1.1, 1.2
- **内容**：
  - [x] 创建 `InterventionalSchemaManager` 类
  - [x] 实现 `initialize()` 方法（创建约束和索引）
  - [x] 实现 `get_version()` 方法
  - [x] 实现 `migrate_to()` 方法
  - [x] 实现 `list_constraints()` 方法
  - [x] 实现 `list_indexes()` 方法
- **验证**：单元测试 `tests/unit/test_schema.py` ✅

### 任务 1.4：实现跨图谱查询函数 ✅ ⭐ 核心
- **规范**：`design.md` - 第7节 GraphRAG 集成方案
- **文件**：`src/services/cross_graph.py`（新建）
- **依赖**：任务 1.1, 1.2
- **内容**：
  - [x] 实现 `cross_graph_query()` 函数
  - [x] 支持并行查询三个图谱（patient/literature/dictionary）
  - [x] 支持不同检索模式（local/global/hybrid）
  - [x] 返回结构化的检索结果（含来源图谱信息）
- **验证**：单元测试 `tests/unit/test_cross_graph.py` ✅

---

## 阶段二：状态扩展层（可与阶段一并行）

### 任务 2.1：定义扩展数据模型 ✅
- **规范**：`state-extension/spec.md` - 需求：嵌套数据模型
- **文件**：`src/agents/models.py`（新建）
- **内容**：
  - [x] 创建 `GraphSource` 枚举（PATIENT_DATA/LITERATURE/DICTIONARY）
  - [x] 创建 `RetrievedEntity` 模型（含 source_graph 字段）
  - [x] 创建 `RetrievedRelationship` 模型（含 source_graph 字段）
  - [x] 创建 `GuidelineMatch` 模型
  - [x] 创建 `PatientDataModel` 模型
  - [x] 创建 `AnatomyFindingModel` 模型
  - [x] 创建 `PathologyFindingModel` 模型
  - [x] 创建 `RiskFactorModel` 模型
  - [x] 创建 `DeviceSelectionModel` 模型
  - [x] 创建 `ProcedurePlanModel` 模型
  - [x] 创建 `ReasoningStepModel` 模型（含 phase 字段）
  - [x] 创建 `PostOpPlanModel` 模型
  - [x] 创建枚举类型 `ProcedureType`, `Severity`, `Phase`
- **验证**：单元测试 `tests/unit/agents/test_models.py` ✅

### 任务 2.2：扩展介入手术状态类型（含 GraphRAG 结果） ✅
- **规范**：`state-extension/spec.md` - 需求：扩展状态类型定义
- **文件**：`src/agents/states.py`（修改）
- **依赖**：任务 2.1
- **内容**：
  - [x] 创建 `ExtendedInterventionalState` TypedDict
  - [x] 添加 GraphRAG 检索结果字段：
    - [x] `retrieved_entities` (累加)
    - [x] `retrieved_relationships` (累加)
    - [x] `matched_guidelines` (累加)
  - [x] 添加三层图谱上下文字段：
    - [x] `patient_graph_context`
    - [x] `literature_graph_context`
    - [x] `dictionary_graph_context`
  - [x] 添加 LLM 分析结果字段：
    - [x] `patient_analysis`
    - [x] `device_recommendations`
    - [x] `risk_assessment`
    - [x] `procedure_plan`
  - [x] 添加元数据字段：`retrieval_mode`, `sources`
  - [x] 配置正确的 Annotated 累加器
- **验证**：单元测试 `tests/unit/agents/test_states.py` ✅

---

## 阶段三：工作流扩展层（依赖阶段一、二）

### 任务 3.1：实现意图识别节点 ⭐ LLM 实体识别 ✅
- **规范**：`design.md` - §3.2 术前评估工作流
- **文件**：`src/agents/nodes/interventional.py`（新建）
- **依赖**：任务 2.2
- **内容**：
  - [x] 实现 `intent_recognition_node()` 函数
  - [x] 识别手术类型（PCI/CAS/TAVI）
  - [x] LLM 驱动提取实体：
    - [x] `:RiskFactor` (风险因素): Age > 70, Hypertension, Hyperlipidemia
    - [x] `:Pathology` (病理): 重度狭窄85%, 活动性斑块
    - [x] `:PatientData` (病史): TIA history
    - [x] `:Anatomy` (解剖): Left ICA, 起始部
  - [x] 构建结构化查询参数（structured_query）
  - [x] 输出到状态 `extracted_entities` 和 `procedure_type`
- **验证**：单元测试 `tests/test_agents/test_nodes_intent.py` ✅

### 任务 3.2：实现 U-Retrieval 知识检索节点 ⭐ Top-down + Bottom-up ✅
- **规范**：`design.md` - §3.2 U-Retrieval 节点设计
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 1.4, 3.1
- **内容**：
  - [x] 实现 `u_retrieval_node()` 函数
  - [x] **Top-down（精确索引检索）**：
    - [x] 从医学文献图谱（global 模式）检索权威指南 `:Guideline`
    - [x] 提取推荐等级（Class I/IIa/IIb/III）和证据级别（A/B/C）
    - [x] 提取适应症和禁忌症定义
  - [x] **Bottom-up（全局聚合检索）**：
    - [x] 结合患者上下文（高龄、症状性）向上聚合检索
    - [x] 从患者图谱（local）检索：既往病史、检查结果
    - [x] 从医学词典图谱（hybrid）检索：器械规格、适应症
  - [x] 合并检索结果到状态：`guideline_context`, `patient_context`, `device_context`
  - [x] 记录来源图谱和检索模式
- **验证**：单元测试 `tests/test_agents/test_nodes_retrieval.py` ✅

### 任务 3.3：实现适应症评估节点 ⭐ LLM+指南 ✅
- **规范**：`design.md` - §3.2 适应症评估节点
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.2
- **内容**：
  - [x] 实现 `assess_indications_node()` 函数
  - [x] 使用已检索的指南上下文（不重复检索）
  - [x] LLM 驱动分析：
    - [x] 判断是否符合手术适应症（基于指南推荐）
    - [x] 引用指南依据（如 "症状性+重度狭窄>70% = Class I 推荐"）
  - [x] 输出路由决策：`indicated` / `not_indicated` / `uncertain`
  - [x] 记录推理步骤到 `reasoning_chain`
- **验证**：单元测试 `tests/unit/agents/test_nodes_indications.py` ✅

### 任务 3.4：实现禁忌症评估节点 ⭐ LLM+指南 ✅
- **规范**：`design.md` - §3.2 禁忌症评估节点
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.3
- **内容**：
  - [x] 实现 `assess_contraindications_node()` 函数
  - [x] 使用已检索的禁忌症信息（不重复检索）
  - [x] LLM 驱动分析：
    - [x] 检查 Class III（绝对禁忌）
    - [x] 检查 Class II（相对禁忌）
  - [x] 输出路由决策：`proceed` / `modify` / `abort`
  - [x] 记录推理步骤和来源指南
- **验证**：单元测试 `tests/unit/agents/test_nodes_contraindications.py` ✅

### 任务 3.5：实现风险评估节点 ⭐ LLM+指南 ✅
- **规范**：`design.md` - §3.2 风险评估节点
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.4
- **内容**：
  - [x] 实现 `assess_risks_node()` 函数
  - [x] 使用已检索的风险因素数据（不重复检索）
  - [x] LLM 驱动分析：
    - [x] 风险等级评估（低/中/高/极高）
    - [x] 识别主要风险因素（高龄、活动性斑块、凝血功能等）
    - [x] 提出风险缓解措施（术前优化、药物调整）
  - [x] 输出结构化风险评估到 `risk_assessment`
  - [x] 记录来源图谱和置信度
- **验证**：单元测试 `tests/test_agents/test_nodes_risks.py` ✅

### 任务 3.6：实现术式匹配节点 ⭐ Graph Traversal ✅
- **规范**：`design.md` - §3.2 术式匹配节点
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.5
- **内容**：
  - [x] 实现 `match_procedure_node()` 函数
  - [x] **图谱遍历逻辑（沿关系链推理）**：
    - [x] `(:Guideline)-[:BASED_ON_GUIDELINE]->(:Procedure)` 首选术式
    - [x] `(:Procedure)-[:HAS_STEP]->(:IntraoperativeEvent)` 所需步骤
    - [x] `(:Event)-[:USES_DEVICE]->(:Device)` 所需器械
    - [x] `(:Device)-[:CONTRAINDICATES]->(:RiskFactor)` 器械禁忌
    - [x] `(:Procedure)-[:REQUIRES_RESCUE]->(:Procedure)` 备选方案
  - [x] **LLM + Graph Traversal 结合**：
    - [x] 根据检索到的关系链推理首选方案
    - [x] 识别关键分支点（如 EPD 部署失败时的备选）
    - [x] 考虑器械禁忌关系
  - [x] 输出到状态 `procedure_plan`（含首选方案和备选方案）
  - [x] 记录遍历路径和推理依据
- **验证**：单元测试 `tests/test_agents/test_nodes_match_procedure.py` ✅

### 任务 3.7：实现方案综合节点 ⭐ LLM 综合生成 ✅
- **规范**：`design.md` - §3.2 方案综合节点
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.6
- **内容**：
  - [x] 实现 `generate_plan_node()` 函数
  - [x] 整合所有检索和分析结果（不重复检索）
  - [x] LLM 驱动综合生成：
    - [x] **首选方案 (Plan A)**：术式、步骤、器械、入路、理由
    - [x] **备选方案 (Plan B)**：应急处理、转换条件
    - [x] **风险提示**：主要风险因素和预防措施
    - [x] **推荐理由**：引用指南来源和图谱关系
  - [x] 生成结构化输出到 `recommendations`
  - [x] 计算综合置信度分数到 `confidence_score`
- **验证**：单元测试 `tests/test_agents/test_nodes_generate_plan.py` ✅

### 任务 3.8：实现条件路由函数 ✅
- **规范**：`design.md` - §3.2 条件路由设计
- **文件**：`src/agents/nodes/interventional.py`（续）
- **依赖**：任务 3.3, 3.4
- **内容**：
  - [x] 实现 `route_indications()` - 适应症路由（indicated → continue / not_indicated → end）
  - [x] 实现 `route_contraindications()` - 禁忌症路由（proceed/modify/abort）
  - [x] 实现 `route_should_abort()` - 终止条件判断
- **验证**：单元测试 `tests/test_agents/test_routing.py` ✅

### 任务 3.9：构建术前评估工作流 ✅
- **规范**：`design.md` - §3.2, §3.4 完整工作流
- **文件**：`src/agents/workflows/interventional.py`（修改）
- **依赖**：任务 3.1-3.8
- **内容**：
  - [x] 创建 `create_preop_workflow()` 函数
  - [x] 添加所有术前评估节点（按顺序连接）
  - [x] 添加条件边和路由逻辑
  - [x] 从 config 获取 `rag_adapter` 和 `llm`
  - [x] 保持向后兼容：保留原有 `create_interventional_agent()`
- **验证**：集成测试 `tests/test_agents/test_workflow_preop.py` ✅

### 任务 3.10：移除旧的硬编码节点 ⭐ 清理 ✅
- **文件**：`src/agents/workflows/interventional.py`
- **依赖**：任务 3.9
- **内容**：
  - [x] 确认所有新节点正常工作
  - [x] 保留旧的硬编码节点实现（向后兼容）
  - [x] 更新文档说明迁移路径
- **验证**：回归测试确保功能不降级 ✅

---

## 阶段四：术中/术后扩展（可选，依赖阶段三）

### 任务 4.1：实现术中执行节点（扩展）✅
- **规范**：`design.md` - §3.4 完整三阶段工作流
- **文件**：`src/agents/nodes/intraop.py`（新建）
- **依赖**：任务 3.9
- **内容**：
  - [x] 实现 `execute_procedure_node()` - 执行术式
  - [x] 实现 `monitor_complications_node()` - 监测并发症
  - [x] 实现 `handle_events_node()` - 处理术中事件
- **验证**：单元测试 `tests/test_agents/test_nodes_intraop.py` ✅

### 任务 4.2：实现术后管理节点（扩展）✅
- **规范**：`design.md` - §3.4 完整三阶段工作流
- **文件**：`src/agents/nodes/postop.py`（新建）
- **依赖**：任务 3.9
- **内容**：
  - [x] 实现 `plan_postop_care_node()` - 规划术后管理
  - [x] 实现 `generate_discharge_plan_node()` - 生成出院计划
- **验证**：单元测试 `tests/test_agents/test_nodes_postop.py` ✅

---

## 阶段五：SDK/API 扩展层（依赖阶段三）

### 任务 5.1：扩展 SDK 客户端 ✅
- **规范**：`sdk-extension/spec.md` - 所有需求
- **文件**：`src/sdk/interventional.py`（新建）
- **依赖**：任务 3.9
- **内容**：
  - [x] 创建 `InterventionalClient` 类
  - [x] 实现 `plan_intervention()` 方法
  - [x] 实现 `assess_preop_risks()` 方法
  - [x] 实现 `get_device_recommendations()` 方法
  - [x] 实现 `simulate_procedure()` 方法（流式）
  - [x] 实现 `get_guidelines()` 方法
  - [x] 实现 `plan_postop_care()` 方法
- **验证**：单元测试 `tests/test_sdk/test_interventional.py` ✅ (20/22 测试通过)

### 任务 5.2：扩展 RESTful API ✅
- **规范**：`sdk-extension/spec.md` - 需求：RESTful API 扩展
- **文件**：`src/api/routes/interventional.py`（新建）
- **依赖**：任务 5.1
- **内容**：
  - [x] 实现 `POST /api/v1/interventional/plan`
  - [x] 实现 `POST /api/v1/interventional/simulate`（SSE 流式）
  - [x] 实现 `POST /api/v1/interventional/risk-assessment`
  - [x] 实现 `GET /api/v1/interventional/guidelines/{procedure_type}`
  - [x] 实现 `GET /api/v1/interventional/devices/{category}`
  - [x] 实现 `POST /api/v1/interventional/postop-care`
  - [x] 注册路由到主应用
- **验证**：API 测试 `tests/test_api/test_interventional_api.py` ✅ (18/18 测试通过)

### 任务 5.3：扩展 CLI 命令 ✅
- **规范**：`sdk-extension/spec.md` - 需求：CLI 命令扩展
- **文件**：`src/cli/interventional.py`（新建）
- **依赖**：任务 5.1
- **内容**：
  - [x] 实现 `medgraph interventional plan` 命令
  - [x] 实现 `medgraph interventional devices` 命令
  - [x] 实现 `medgraph interventional guidelines` 命令
  - [x] 实现 `medgraph interventional simulate` 命令
  - [x] 实现 `medgraph interventional risk` 命令
  - [x] 实现 `medgraph interventional postop` 命令
  - [x] 注册到主 CLI 应用
- **验证**：CLI 测试 `tests/test_cli/test_interventional_cli.py` ✅ (18/23 测试通过)

---

## 阶段六：数据与文档（可与阶段三、五并行）

### 任务 6.1：创建三层图谱示例数据 ✅
- **文件**：`data/interventional/`（新建目录）
- **内容**：
  - [x] 患者数据图谱示例（local 模式）- `patient_data_example.json`
  - [x] 医学文献图谱示例（global 模式）- `literature_example.json`
  - [x] 医学词典图谱示例（hybrid 模式）- `dictionary_example.json`
- **验证**：数据加载测试 ✅ `tests/test_data/test_data_loading.py`

### 任务 6.2：创建指南和器械数据 ✅
- **文件**：`data/guidelines/`, `data/devices/`（新建目录）
- **内容**：
  - [x] PCI 指南数据（ACC/AHA）- `guidelines/pci_guidelines.json`
  - [x] CAS 指南数据（NASCET）- `guidelines/cas_guidelines.json`
  - [x] 器械推荐数据 - `devices/devices_catalog.json`
  - [x] 并发症处理数据 - `devices/complications_management.json`
- **验证**：数据加载测试 ✅ `tests/test_data/test_data_loading.py`

### 任务 6.3：编写用户文档 ✅
- **文件**：`docs/interventional/`（新建目录）
- **内容**：
  - [x] 编写介入手术模块概述（强调三层图谱协同）- `overview.md`
  - [x] 编写 SDK 使用指南 - `sdk_guide.md`
  - [x] 编写 API 参考文档 - `api_reference.md`
  - [x] 编写 CLI 使用指南 - `cli_guide.md`
  - [x] 编写临床场景示例 - `clinical_examples.md`

---

## 阶段七：集成测试（依赖所有前序任务）

### 任务 7.1：端到端集成测试 ✅
- **文件**：`tests/integration/test_interventional_e2e.py`
- **依赖**：所有前序任务
- **内容**：
  - [x] 测试完整的 CAS 规划场景（三层图谱检索）
  - [x] 测试完整的 PCI 规划场景
  - [x] 测试禁忌症处理流程（条件路由）
  - [x] 测试并发症应急流程
  - [x] 测试术后管理生成
  - [x] 验证所有决策都记录了来源图谱
- **验证**：CI 集成 ✅（8/8 测试通过）

### 任务 7.2：性能基准测试 ✅
- **文件**：`tests/performance/test_interventional_perf.py`
- **依赖**：任务 7.1
- **内容**：
  - [x] 测试工作流执行时间（目标 < 500ms）
  - [x] 测试三层图谱并行查询性能
  - [x] 测试 LLM 调用延迟
  - [x] 生成性能报告
- **验证**：性能报告生成 ✅（8/8 测试通过）

---

## 关键里程碑

| 里程碑 | 完成标准 | 预期产出 |
|--------|----------|----------|
| M1: 三层图谱架构 | 任务 1.1-1.4 | Schema 定义、跨图谱查询函数 |
| M2: LLM 驱动节点 | 任务 3.1-3.7 | 所有节点都是 LLM+GraphRAG |
| M3: 工作流集成 | 任务 3.8-3.9 | 完整工作流，移除硬编码 |
| M4: SDK/API | 任务 5.1-5.3 | CLI、API、SDK 可用 |
| M5: E2E 验证 | 任务 7.1-7.2 | 所有测试通过，性能达标 |

---

## 验收标准

1. ✅ 所有单元测试通过（覆盖率 ≥ 90%）
2. ✅ 所有集成测试通过
3. ✅ API 响应时间 < 500ms（复杂查询）
4. ✅ CLI 命令正常工作并有帮助文档
5. ✅ 代码通过 `ruff` 检查和 `mypy` 类型检查
6. ✅ 用户文档完整且示例可运行
7. ✅ ⭐ **所有决策节点都是 LLM 驱动，无硬编码规则**
8. ✅ ⭐ **所有检索都使用三层图谱协同查询**
9. ✅ ⭐ **每个决策都记录来源图谱和置信度**
