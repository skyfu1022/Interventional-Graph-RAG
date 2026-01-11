# 介入手术智能体使用指南

## 概述

介入手术智能体是 Medical-Graph-RAG 项目中的一个扩展点，为未来的介入手术智能体提供基础架构。该智能体工作流整合患者数据分析、器械推荐、风险评估和方案推荐等功能。

## 文件位置

```
/Users/skyfu/Projects/AntigravityProjects/Medical-Graph-RAG/src/agents/workflows/interventional.py
```

## 工作流结构

```
患者数据 + 手术类型
    │
    ▼
analyze_patient (分析患者情况)
    │
    ▼
select_devices (选择器械)
    │
    ▼
assess_risks (评估风险)
    │
    ▼
generate_plan (生成手术方案)
    │
    ▼
END
```

## 快速开始

### 1. 导入模块

```python
from src.agents.workflows.interventional import create_interventional_agent
```

### 2. 创建工作流

```python
# 创建工作流（使用模拟的 RAG 适配器）
class MockRAGAdapter:
    pass

rag_adapter = MockRAGAdapter()
workflow = create_interventional_agent(rag_adapter)
```

### 3. 执行工作流

```python
# 准备输入数据
input_data = {
    "patient_data": {
        "age": 65,
        "gender": "male",
        "diagnosis": "冠心病",
        "history": ["高血压", "糖尿病"]
    },
    "procedure_type": "PCI",
    "devices": [],
    "risks": [],
    "recommendations": "",
    "context": [],
    "error": None
}

# 执行工作流
result = workflow.invoke(input_data)

# 查看结果
print(result["recommendations"])
```

## 状态定义

工作流使用 `InterventionalState` 作为状态类型，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `patient_data` | `Required[Dict]` | 患者数据字典 |
| `procedure_type` | `Required[str]` | 手术类型（如 PCI、起搏器植入等） |
| `devices` | `Annotated[List[str], add]` | 推荐的器械列表 |
| `risks` | `Annotated[List[str], add]` | 识别的风险列表 |
| `recommendations` | `str` | 推荐方案描述 |
| `context` | `Annotated[List[str], add]` | 检索到的相关上下文 |
| `error` | `Optional[str]` | 错误信息 |

## 节点功能

### 1. analyze_patient_node
分析患者数据和病史，提取关键信息并识别潜在风险因素。

**输入：** 患者数据、手术类型
**输出：** 检索到的上下文信息

### 2. select_devices_node
根据患者特征和手术类型选择合适的介入器械。

**输入：** 患者数据、手术类型
**输出：** 推荐的器械列表

### 3. assess_risks_node
评估患者特定的风险因素和手术并发症风险。

**输入：** 患者数据、手术类型
**输出：** 识别的风险列表

### 4. generate_plan_node
综合所有信息，生成结构化的手术方案。

**输入：** 患者数据、手术类型、器械、风险、上下文
**输出：** 完整的推荐方案

## 支持的手术类型

目前支持以下手术类型：

| 手术类型 | 说明 |
|---------|------|
| `PCI` | 经皮冠状动脉介入治疗 |
| `起搏器植入` | 心脏起搏器植入手术 |
| `消融术` | 心律失常消融手术 |
| 其他 | 通用介入手术 |

## 输出示例

```markdown
## PCI 手术方案

### 患者信息
- 年龄：65岁
- 性别：male
- 诊断：冠心病

### 推荐器械
1. 导引导管
2. 指引导丝
3. 球囊导管
4. 药物洗脱支架

### 风险评估
1. 糖尿病患者：感染风险增加、伤口愈合延迟
2. 高血压患者：术中血压波动风险
3. PCI手术风险：冠脉穿孔、支架血栓、边支闭塞
4. 介入手术通用风险：出血、感染、麻醉并发症

### 手术步骤建议
1. 术前评估：冠状动脉造影明确病变位置
2. 器械准备：准备导引导管、指引导丝、球囊和支架
3. 病变预处理：根据病变特点选择适当的预扩张策略
4. 支架植入：植入药物洗脱支架，确保充分贴壁
5. 术后优化：必要时进行后扩张，确保支架展开良好

### 注意事项
- 术中持续监测生命体征
- 准备好急救设备和药物
- 严格执行无菌操作
- 术后密切观察并发症
```

## 扩展说明

当前实现为**占位符实现**，提供了完整的工作流架构和数据流。未来的扩展可以包括：

1. **集成真实的 RAG 适配器**：使用 `rag_adapter` 从知识图谱中检索医学知识
2. **集成 LLM**：使用 `llm` 参数生成更智能和个性化的推荐
3. **增强风险评估**：基于医学指南和临床试验数据
4. **器械选择优化**：考虑器械可用性、成本和患者偏好
5. **多模态输入**：支持医学影像、实验室检查结果等

## 验证测试

运行验证脚本：

```bash
python tests/test_interventional_workflow.py
```

验证内容包括：
- 工作流创建
- 基本功能测试
- 不同手术类型测试
- 结果完整性验证

## 注意事项

1. 这是扩展点实现，节点函数目前为占位符
2. 实际应用时需要集成真实的医学知识库和 LLM
3. 推荐结果仅供参考，不能替代专业医疗建议
4. 需要符合当地医疗法规和伦理要求

## 许可证

本代码遵循 Medical-Graph-RAG 项目的许可证。
