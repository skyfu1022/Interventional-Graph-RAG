# 介入手术智能体 SDK 使用指南

## 目录

- [简介](#简介)
- [安装与配置](#安装与配置)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [高级用法](#高级用法)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [完整示例](#完整示例)

## 简介

InterventionalClient 是介入手术智能体的 Python SDK，提供了简洁的接口用于术前评估、风险分析、器械推荐和方案生成。

### 主要特性

- ✅ **类型安全**：完整的类型提示，支持 mypy 静态检查
- ✅ **异步支持**：所有 I/O 操作都是异步的，提高性能
- ✅ **可配置**：支持自定义 LLM、数据库和工作流参数
- ✅ **可扩展**：易于添加新的手术类型和决策节点
- ✅ **可观测**：内置日志记录和性能监控

## 安装与配置

### 安装

```bash
# 确保已激活虚拟环境
source venv/bin/activate  # macOS/Linux

# 安装项目依赖
pip install -r requirements.txt
```

### 配置

创建配置文件 `config.yaml`：

```yaml
# LLM 配置
llm:
  provider: "openai"  # 或 "anthropic", "azure"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4"
  temperature: 0.0
  max_tokens: 2000

# Graph RAG 配置
graph_rag:
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: "${NEO4J_PASSWORD}"
  milvus_uri: "localhost:19530"
  embedding_model: "text-embedding-3-small"

# 工作流配置
workflow:
  timeout_seconds: 300
  max_retries: 3
  enable_streaming: false
```

或使用环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
export NEO4J_PASSWORD="your-password"
export MILVUS_URI="localhost:19530"
```

## 快速开始

### 基础示例

```python
import asyncio
from src.sdk.interventional import InterventionalClient

async def main():
    # 创建客户端
    client = InterventionalClient()

    # 术前评估
    result = await client.plan_intervention(
        patient_age=76,
        gender="Male",
        symptoms="TIA x3, last 2 weeks ago",
        stenosis_percentage=85,
        vessel="Left ICA",
        procedure_type="CAS"
    )

    # 打印结果
    print(f"推荐方案: {result['recommendation']}")
    print(f"首选术式: {result['primary_plan']['procedure']}")
    print(f"推荐器械: {result['primary_plan']['devices']}")
    print(f"风险等级: {result['risk_assessment']['level']}")
    print(f"置信度: {result['confidence_score']}")

if __name__ == "__main__":
    asyncio.run(main())
```

输出：

```
推荐方案: recommended
首选术式: Carotid Artery Stenting (CAS)
推荐器械: ['FilterWire EZ EPD (4.5mm)', 'PRECISE PRO RX 7x40mm Stent']
风险等级: High
置信度: 0.85
```

## 核心功能

### 1. 术前规划 (plan_intervention)

生成完整的手术方案，包括首选方案、备选方案和风险评估。

```python
result = await client.plan_intervention(
    # 患者基本信息
    patient_age=76,
    patient_gender="Male",

    # 临床信息
    symptoms="TIA with right-sided weakness",
    comorbidities=["Hypertension", "Hyperlipidemia", "Diabetes"],

    # 影像学发现
    stenosis_percentage=85,
    stenosis_method="NASCET",
    vessel="Left ICA",
    plaque_features="Ulcerated, hypoechoic on ultrasound",

    # 手术类型
    procedure_type="CAS",

    # 可选参数
    include_detailed_reasoning=True,
    enable_confidence_scoring=True
)
```

**返回结构**：

```python
{
    "recommendation": "recommended",  # recommended / not_recommended / uncertain

    "primary_plan": {
        "procedure": "Carotid Artery Stenting (CAS)",
        "approach": "Femoral access",
        "devices": [
            {
                "name": "FilterWire EZ",
                "type": "Embolic Protection Device",
                "size": "4.5mm",
                "quantity": 1,
                "rationale": "Standard EPD for CAS"
            },
            {
                "name": "PRECISE PRO RX",
                "type": "Carotid Stent",
                "size": "7x40mm",
                "quantity": 1,
                "rationale": "Open-cell design for tortuous anatomy"
            }
        ],
        "steps": [
            "Femoral access with 7F sheath",
            "Guidewire navigation to left ICA",
            "Deploy FilterWire EZ 2-3cm beyond lesion",
            "Pre-dilatation with 5x20mm balloon (if needed)",
            "Deploy PRECISE stent covering lesion",
            "Post-dilatation (if underexpanded)",
            "Final angiography",
            "Retrieve EPD"
        ],
        "rationale": "Based on ACC/AHA Class I recommendation for symptomatic >70% stenosis"
    },

    "backup_plan": {
        "condition": "If EPD deployment fails",
        "alternative": "Convert to proximal protection (MO.MA)",
        "fallback": "Abort and refer for CEA"
    },

    "risk_assessment": {
        "level": "High",
        "factors": [
            {"factor": "Age >70", "severity": "High", "modifiable": False},
            {"factor": "Symptomatic status", "severity": "High", "modifiable": False},
            {"factor": "Active plaque", "severity": "High", "modifiable": False},
            {"factor": "Hypertension", "severity": "Medium", "modifiable": True}
        ],
        "mitigation": [
            "Universal EPD use",
            "Careful technique",
            "Strict BP control (<140/90 mmHg)",
            "Pre-procedure DAPT optimization"
        ],
        "expected_complication_rate": "5-7% (stroke/death/MI)"
    },

    "sources": [
        {
            "graph": "literature",
            "source": "ACC/AHA 2021 Guidelines",
            "recommendation": "Class I, Level A",
            "relevant_quote": "CAS is indicated for symptomatic patients with 50-99% stenosis"
        },
        {
            "graph": "patient",
            "source": "Clinical data",
            "key_findings": ["Age 76", "Symptomatic", "85% stenosis", "Active plaque"]
        }
    ],

    "confidence_score": 0.85,
    "reasoning_chain": ["..."]  # 详细的推理链
}
```

### 2. 风险评估 (assess_preop_risks)

独立的风险评估模块，专注于风险因素识别和缓解。

```python
risk_assessment = await client.assess_preop_risks(
    patient_age=76,
    comorbidities=["Hypertension", "Diabetes", "CKD Stage 3"],
    procedure_type="CAS",
    lesion_characteristics={
        "stenosis": 85,
        "length": "15mm",
        "calcification": "Moderate"
    }
)
```

**返回结构**：

```python
{
    "overall_risk": "High",
    "risk_score": 7.5,  # 0-10 scale

    "risk_categories": {
        "patient_factors": {
            "score": 3.5,
            "factors": [
                {"name": "Age >70", "weight": 1.5, "mitigable": False},
                {"name": "Diabetes", "weight": 1.0, "mitigable": True},
                {"name": "CKD Stage 3", "weight": 1.0, "mitigable": False}
            ]
        },
        "anatomical_factors": {
            "score": 2.5,
            "factors": [
                {"name": "Severe stenosis (85%)", "weight": 1.5},
                {"name": "Moderate calcification", "weight": 1.0}
            ]
        },
        "procedural_factors": {
            "score": 1.5,
            "factors": [
                {"name": "Symptomatic status", "weight": 1.5}
            ]
        }
    },

    "modifiable_factors": [
        {
            "factor": "Diabetes",
            "current_status": "HbA1c 7.2%",
            "target": "HbA1c <7%",
            "intervention": "Optimize diabetes regimen pre-procedure"
        },
        {
            "factor": "Hypertension",
            "current_status": "142/88 mmHg",
            "target": "<140/90 mmHg",
            "intervention": "Adjust antihypertensive regimen"
        }
    ],

    "predicted_complications": [
        {"complication": "Peri-procedural stroke", "probability": "5%", "severity": "High"},
        {"complication": "Hyperperfusion syndrome", "probability": "2%", "severity": "Moderate"},
        {"complication": "Access site bleeding", "probability": "4%", "severity": "Low"}
    ],

    "recommendations": [
        "Strict BP control pre-procedure",
        "Ensure adequate DAPT loading",
        "Consider hydration protocol for renal protection",
        "Discuss risks/benefits with patient",
        "Ensure experienced operator available"
    ]
}
```

### 3. 器械推荐 (get_device_recommendations)

基于解剖特征和手术类型推荐器械。

```python
devices = await client.get_device_recommendations(
    procedure="CAS",
    anatomy={
        "vessel": "Left ICA",
        "diameter_mm": 4.8,
        "lesion_length_mm": 15,
        "characteristics": ["Tortuous", "Ulcerated plaque"],
        "access_anatomy": "Type I aortic arch"
    },
    preferences={
        "prioritize_flexibility": True,
        "avoid_large_sheaths": False
    }
)
```

**返回结构**：

```python
{
    "embolic_protection": {
        "primary_recommendation": {
            "device": "FilterWire EZ",
            "manufacturer": "Boston Scientific",
            "size": "4.5mm filter",
            "rationale": "First-line EPD, excellent trackability",
            "alternatives": [
                {
                    "device": "Emboshield NAV6",
                    "when_to_use": "If better fluoroscopic visibility needed"
                }
            ]
        },
        "backup_for_filter_failure": {
            "device": "MO.MA Proximal Protection",
            "when_to_use": "If unable to cross with distal filter",
            "note": "Requires 8F sheath, proximal occlusion technique"
        }
    },

    "stent": {
        "primary_recommendation": {
            "device": "PRECISE PRO RX",
            "manufacturer": "Cordis",
            "size": "7x40mm",
            "rationale": "Open-cell design provides flexibility for tortuous anatomy",
            "key_features": ["High flexibility", "Excellent conformability", "Proven in CREST"]
        },
        "alternatives": [
            {
                "device": "Wallstent",
                "when_to_use": "If better plaque coverage needed (closed-cell)",
                "note": "Account for significant shortening during deployment"
            }
        ]
    },

    "balloon": {
        "pre_dilatation": {
            "device": "Avitar Plus",
            "size": "5x20mm",
            "rationale": "1mm smaller than vessel for safe pre-dilatation"
        },
        "post_dilatation": {
            "device": "Avitar Plus",
            "size": "7x20mm",
            "rationale": "Same size as stent for optimal expansion",
            "caution": "Avoid high pressure (>12 atm)"
        }
    },

    "additional_equipment": {
        "sheath": "7F Flexor Shuttle Sheath (90cm)",
        "guidewire": "0.014-inch Whisper MS guidewire",
        "diagnostic": "5F Angled catheter for arch selection"
    }
}
```

### 4. 指南查询 (get_guidelines)

查询临床指南和循证医学证据。

```python
guidelines = await client.get_guidelines(
    procedure_type="CAS",
    topic="indications",
    patient_profile={
        "symptomatic": True,
        "stenosis_percentage": 85,
        "age": 76
    }
)
```

**返回结构**：

```python
{
    "topic": "CAS Indications for Symptomatic Stenosis",

    "recommendations": [
        {
            "class": "Class I",
            "level": "Level A",
            "statement": "CAS is indicated for symptomatic patients with 50-99% stenosis of the internal carotid artery",
            "patient_applicability": "This patient meets criteria (symptomatic, 85% stenosis)",

            "evidence": {
                "supporting_studies": [
                    {
                        "name": "CREST Trial",
                        "year": 2010,
                        "sample_size": 2502,
                        "key_finding": "CAS and CEA had similar long-term outcomes for symptomatic patients",
                        "note": "Age interaction: CAS better for patients <70, CEA better for >70"
                    },
                    {
                        "name": "NASCET Trial",
                        "year": 1991,
                        "sample_size": 659,
                        "key_finding": "CEA beneficial for symptomatic patients with >70% stenosis",
                        "note": "Established the standard of care"
                    }
                ]
            }
        }
    ],

    "contraindications": [
        {
            "type": "Absolute",
            "contraindication": "Non-disabling stroke with mRS >2",
            "rationale": "Limited functional benefit, high peri-procedural risk"
        },
        {
            "type": "Relative",
            "contraindication": "Age >80",
            "rationale": "Higher peri-procedural stroke risk in elderly",
            "consideration": "CEA may be preferred"
        }
    ],

    "references": [
        {
            "organization": "ACC/AHA",
            "title": "2021 Guideline for Carotid Artery Stenting",
            "url": "https://www.acc.org/guidelines",
            "doi": "10.1161/CIR.0000000000001025"
        }
    ]
}
```

### 5. 模拟手术 (simulate_procedure)

流式模拟手术过程，提供逐步决策支持。

```python
async for event in client.simulate_procedure(
    patient_data=patient_info,
    procedure_type="CAS",
    stream=True
):
    print(f"[{event['phase']}] {event['description']}")

    if event['type'] == 'decision_point':
        print(f"  Decision: {event['options']}")
        # 用户可以选择或让 AI 决定
```

**流式事件示例**：

```python
# 事件 1
{
    "type": "phase_start",
    "phase": "access",
    "description": "Femoral access with 7F sheath",
    "guidance": "Use ultrasound guidance, micropuncture technique"
}

# 事件 2
{
    "type": "decision_point",
    "phase": "access",
    "description": "Sheath successfully placed",
    "options": [
        "Proceed with standard approach",
        "Consider radial access (if femoral contraindicated)"
    ],
    "recommendation": "Proceed with femoral access"
}

# 事件 3
{
    "type": "guidance",
    "phase": "epd_deployment",
    "description": "Preparing to deploy EPD",
    "guidance": "Deploy FilterWire 2-3cm beyond lesion in straight segment",
    "warnings": [
        "Avoid deployment in tortuous segments",
        "Ensure proper flushing before deployment"
    ]
}

# 事件 4
{
    "type": "complication_scenario",
    "phase": "epd_deployment",
    "description": "Simulated: Unable to cross lesion with EPD",
    "actions": [
        "Consider proximal protection (MO.MA)",
        "Attempt different wire trajectory",
        "Abort and refer for CEA"
    ],
    "recommendation": "Convert to proximal protection"
}
```

### 6. 术后管理计划 (plan_postop_care)

生成术后护理和随访计划。

```python
postop_plan = await client.plan_postop_care(
    procedure_type="CAS",
    patient_age=76,
    comorbidities=["Hypertension", "Diabetes"],
    procedure_details={
        "devices_used": ["FilterWire EZ", "PRECISE 7x40mm"],
        "complications": None,
        "length_of_stay": "1 day planned"
    }
)
```

**返回结构**：

```python
{
    "medications": {
        "dual_antiplatelet_therapy": {
            "aspirin": {
                "dose": "81 mg daily",
                "duration": "Lifelong",
                "timing": "Continue existing dose"
            },
            "clopidogrel": {
                "loading_dose": "Already given pre-op",
                "maintenance": "75 mg daily",
                "duration": "Minimum 30 days, consider 4-6 weeks",
                "class": "Class I, Level A"
            }
        },
        "statin": {
            "drug": "Atorvastatin",
            "dose": "40-80 mg daily",
            "intensity": "High-intensity",
            "target_ldl": "<70 mg/dL (preferably <55 mg/dL)",
            "rationale": "Secondary prevention, plaque stabilization"
        },
        "blood_pressure": {
            "target": "SBP <140 mmHg, DBP <90 mmHg",
            "urgency": "CRITICAL for first 72 hours",
            "medications": ["Continue existing regimen", "Consider adding if BP elevated"]
        }
    },

    "monitoring": {
        "immediate_postop": {
            "duration": "18-24 hours observation",
            "neurological_checks": "Every hour for first 6 hours, then every 4 hours",
            "vital_signs": "Continuous cardiac monitoring, hourly BP",
            "laboratory": "CBC, BMP in morning"
        },
        "discharge_criteria": [
            "Neurologically stable",
            "BP adequately controlled",
            "No access site complications",
            "Patient education complete"
        ]
    },

    "follow_up_schedule": [
        {
            "timeframe": "30 days",
            "assessments": [
                "Clinical evaluation",
                "Duplex ultrasound",
                "Medication adherence",
                "BP control"
            ]
        },
        {
            "timeframe": "6 months",
            "assessments": [
                "Clinical evaluation",
                "Duplex ultrasound",
                "Restenosis screening"
            ]
        },
        {
            "timeframe": "12 months and annually",
            "assessments": [
                "Clinical evaluation",
                "Duplex ultrasound"
            ]
        }
    ],

    "patient_education": {
        "warning_signs": [
            "Sudden weakness or numbness",
            "Speech difficulty",
            "Vision changes",
            "Severe headache",
            "Facial swelling (access site)"
        ],
        "medication_adherence": "Critical to take DAPT as prescribed",
        "lifestyle": [
            "Smoking cessation",
            "Heart-healthy diet",
            "Regular exercise (walking)",
            "BP monitoring at home"
        ],
        "activity_restrictions": "No heavy lifting >10 lbs for 1 week"
    },

    "warning_signs": {
        "call_911": [
            "Sudden neurological deficit (stroke symptoms)",
            "Severe headache with neurological changes (hyperperfusion)",
            "Chest pain or shortness of breath"
        ],
        "call_office": [
            "Access site pain or swelling",
            "New neurological symptoms (mild)",
            "Medication side effects"
        ]
    }
}
```

## 高级用法

### 自定义 LLM 配置

```python
from langchain_openai import ChatOpenAI
from src.sdk.interventional import InterventionalClient

# 使用自定义 LLM
custom_llm = ChatOpenAI(
    model="gpt-4-turbo",
    temperature=0.1,
    max_tokens=3000,
    api_key="your-api-key"
)

client = InterventionalClient(llm=custom_llm)
```

### 流式响应

```python
# 启用流式输出
async for chunk in client.plan_intervention_stream(
    patient_age=76,
    procedure_type="CAS",
    enable_streaming=True
):
    print(chunk, end="", flush=True)
```

### 批量处理

```python
# 批量评估多个患者
patients = [
    {"age": 76, "symptoms": "TIA", "stenosis": 85},
    {"age": 65, "symptoms": "Asymptomatic", "stenosis": 75},
    {"age": 82, "symptoms": "Stroke", "stenosis": 90}
]

results = await client.batch_assess(patients, procedure_type="CAS")
```

### 自定义检索策略

```python
from src.graph.entities import GraphSource

# 只检索特定图谱
result = await client.plan_intervention(
    patient_age=76,
    procedure_type="CAS",
    retrieval_strategy={
        "include_graphs": [GraphSource.LITERATURE, GraphSource.PATIENT],
        "exclude_graphs": [GraphSource.DICTIONARY],
        "max_results_per_graph": 10
    }
)
```

## 错误处理

### 标准错误处理

```python
from src.sdk.interventional import InterventionalClient
from src.core.exceptions import (
    RetrievalError,
    LLMError,
    ValidationError,
    WorkflowTimeoutError
)

try:
    result = await client.plan_intervention(
        patient_age=76,
        procedure_type="CAS"
    )
except ValidationError as e:
    print(f"输入验证失败: {e}")
    # 处理验证错误

except RetrievalError as e:
    print(f"图谱检索失败: {e}")
    # 检查数据库连接

except LLMError as e:
    print(f"LLM 调用失败: {e}")
    # 检查 API 密钥和网络

except WorkflowTimeoutError as e:
    print(f"工作流超时: {e}")
    # 增加超时时间或简化查询

except Exception as e:
    print(f"未知错误: {e}")
    # 记录日志并报告
```

### 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def robust_assessment(client, patient_data):
    return await client.plan_intervention(**patient_data)
```

## 最佳实践

### 1. 输入数据验证

```python
from pydantic import BaseModel, validator

class PatientInput(BaseModel):
    age: int
    gender: str
    stenosis_percentage: float
    procedure_type: str

    @validator('age')
    def validate_age(cls, v):
        if not 18 <= v <= 120:
            raise ValueError('Age must be between 18 and 120')
        return v

    @validator('stenosis_percentage')
    def validate_stenosis(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Stenosis must be between 0 and 100')
        return v

    @validator('procedure_type')
    def validate_procedure(cls, v):
        allowed = ['CAS', 'PCI', 'TAVI']
        if v not in allowed:
            raise ValueError(f'Procedure must be one of {allowed}')
        return v

# 使用验证后的输入
validated_input = PatientInput(**user_input)
result = await client.plan_intervention(**validated_input.dict())
```

### 2. 性能优化

```python
import asyncio
from functools import lru_cache

# 缓存指南查询（不变的数据）
@lru_cache(maxsize=100)
async def get_cached_guidelines(procedure_type: str):
    return await client.get_guidelines(procedure_type)

# 并行处理多个独立查询
async def comprehensive_assessment(patient_data):
    # 并行执行多个独立查询
    results = await asyncio.gather(
        client.plan_intervention(**patient_data),
        client.assess_preop_risks(**patient_data),
        client.get_device_recommendations(**patient_data),
        return_exceptions=True  # 处理部分失败
    )

    return {
        "plan": results[0],
        "risks": results[1],
        "devices": results[2]
    }
```

### 3. 日志记录

```python
import logging
from src.sdk.interventional import InterventionalClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 使用日志记录
client = InterventionalClient()

try:
    result = await client.plan_intervention(
        patient_age=76,
        procedure_type="CAS"
    )
    logger.info(f"Assessment completed for patient age 76, CAS")
    logger.info(f"Recommendation: {result['recommendation']}")
    logger.info(f"Confidence: {result['confidence_score']}")

except Exception as e:
    logger.error(f"Assessment failed: {e}", exc_info=True)
```

### 4. 测试

```python
import pytest
from src.sdk.interventional import InterventionalClient

@pytest.mark.asyncio
async def test_cas_recommendation():
    client = InterventionalClient()

    result = await client.plan_intervention(
        patient_age=76,
        symptoms="TIA",
        stenosis_percentage=85,
        procedure_type="CAS"
    )

    assert result["recommendation"] == "recommended"
    assert result["primary_plan"]["procedure"] == "Carotid Artery Stenting (CAS)"
    assert result["confidence_score"] > 0.7
    assert "FilterWire" in str(result["primary_plan"]["devices"])

@pytest.mark.asyncio
async def test_contraindications():
    client = InterventionalClient()

    result = await client.plan_intervention(
        patient_age=76,
        symptoms="Asymptomatic",
        stenosis_percentage=40,
        procedure_type="CAS"
    )

    # 不应该推荐 CAS
    assert result["recommendation"] in ["not_recommended", "uncertain"]
```

## 完整示例

### 门诊术前评估应用

```python
"""
门诊术前评估应用示例
完整的工作流程：患者信息采集 → 风险评估 → 方案生成 → 报告输出
"""

import asyncio
import json
from datetime import datetime
from src.sdk.interventional import InterventionalClient
from pydantic import BaseModel, validator

class PatientData(BaseModel):
    """患者数据模型"""
    patient_id: str
    age: int
    gender: str
    symptoms: str
    stenosis_percentage: float
    vessel: str
    comorbidities: list[str] = []
    medications: list[str] = []

    @validator('age')
    def check_age(cls, v):
        if v < 18 or v > 120:
            raise ValueError('Invalid age')
        return v

async def generate_assessment_report(patient_data: dict) -> dict:
    """生成完整的术前评估报告"""

    # 验证输入
    validated_data = PatientData(**patient_data)

    # 创建客户端
    client = InterventionalClient()

    # 并行执行所有评估
    plan, risks, devices, guidelines = await asyncio.gather(
        client.plan_intervention(**validated_data.dict(), include_detailed_reasoning=True),
        client.assess_preop_risks(**validated_data.dict()),
        client.get_device_recommendations(
            procedure="CAS",
            anatomy={"vessel": validated_data.vessel}
        ),
        client.get_guidelines(procedure_type="CAS")
    )

    # 生成报告
    report = {
        "report_id": f"RPT-{validated_data.patient_id}-{datetime.now().strftime('%Y%m%d')}",
        "generated_at": datetime.now().isoformat(),
        "patient_data": validated_data.dict(),

        "summary": {
            "recommendation": plan["recommendation"],
            "procedure": plan["primary_plan"]["procedure"],
            "risk_level": risks["overall_risk"],
            "confidence": plan["confidence_score"]
        },

        "detailed_plan": plan["primary_plan"],
        "backup_plan": plan.get("backup_plan"),

        "risk_analysis": {
            "overall_risk": risks["overall_risk"],
            "risk_score": risks["risk_score"],
            "key_factors": risks["risk_categories"],
            "modifiable_factors": risks.get("modifiable_factors", []),
            "predicted_complications": risks.get("predicted_complications", [])
        },

        "device_recommendations": devices,

        "guideline_basis": {
            "recommendation_class": guidelines["recommendations"][0]["class"],
            "evidence_level": guidelines["recommendations"][0]["level"],
            "supporting_studies": [
                s["name"] for s in guidelines["recommendations"][0]["evidence"]["supporting_studies"]
            ]
        },

        "postoperative_plan": await client.plan_postop_care(
            procedure_type="CAS",
            patient_age=validated_data.age,
            comorbidities=validated_data.comorbidities
        )
    }

    return report

async def main():
    """主函数"""

    # 患者信息
    patient_info = {
        "patient_id": "P001",
        "age": 76,
        "gender": "Male",
        "symptoms": "TIA x3, last episode 2 weeks ago with right-sided weakness",
        "stenosis_percentage": 85,
        "vessel": "Left ICA",
        "comorbidities": ["Hypertension", "Hyperlipidemia", "Type 2 Diabetes"],
        "medications": ["Aspirin", "Lisinopril", "Atorvastatin", "Metformin"]
    }

    # 生成报告
    report = await generate_assessment_report(patient_info)

    # 输出报告
    print("=" * 80)
    print("PRE-PROCEDURAL ASSESSMENT REPORT")
    print("=" * 80)
    print(f"Report ID: {report['report_id']}")
    print(f"Generated: {report['generated_at']}")
    print(f"Patient: {report['patient_data']['patient_id']}, Age {report['patient_data']['age']}")
    print()

    print("SUMMARY")
    print("-" * 80)
    print(f"Recommendation: {report['summary']['recommendation'].upper()}")
    print(f"Procedure: {report['summary']['procedure']}")
    print(f"Risk Level: {report['summary']['risk_level']}")
    print(f"Confidence: {report['summary']['confidence']:.2%}")
    print()

    print("DETAILED PLAN")
    print("-" * 80)
    print(f"Approach: {report['detailed_plan']['approach']}")
    print(f"Devices:")
    for device in report['detailed_plan']['devices']:
        print(f"  - {device['name']} ({device['type']}) - {device['rationale']}")
    print(f"Steps:")
    for i, step in enumerate(report['detailed_plan']['steps'], 1):
        print(f"  {i}. {step}")
    print()

    print("RISK ANALYSIS")
    print("-" * 80)
    print(f"Overall Risk: {report['risk_analysis']['overall_risk']}")
    print(f"Risk Score: {report['risk_analysis']['risk_score']}/10")
    print(f"Predicted Complications:")
    for comp in report['risk_analysis']['predicted_complications']:
        print(f"  - {comp['complication']}: {comp['probability']} ({comp['severity']})")
    print()

    print("GUIDELINE BASIS")
    print("-" * 80)
    print(f"Recommendation: {report['guideline_basis']['recommendation_class']}")
    print(f"Evidence Level: {report['guideline_basis']['evidence_level']}")
    print(f"Supporting Studies: {', '.join(report['guideline_basis']['supporting_studies'])}")
    print()

    # 保存到文件
    with open(f"{report['report_id']}.json", 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report['report_id']}.json")

if __name__ == "__main__":
    asyncio.run(main())
```

## 更多资源

- 📖 [API 参考文档](api_reference.md) - 完整的 API 参考
- 💻 [CLI 使用指南](cli_guide.md) - 命令行工具使用
- 🏥 [临床场景示例](clinical_examples.md) - 真实临床案例
- 🔧 [开发者指南](../developer-guide.md) - 开发和贡献指南

## 问题反馈

如有问题或建议，请通过以下方式联系：

- GitHub Issues: [Medical-Graph-RAG Issues](https://github.com/your-org/Medical-Graph-RAG/issues)
- 邮件: support@medicalgraphrag.org
