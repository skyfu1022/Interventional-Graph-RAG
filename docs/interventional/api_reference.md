# 介入手术智能体 API 参考文档

## 目录

- [概述](#概述)
- [认证](#认证)
- [API 端点](#api-端点)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [速率限制](#速率限制)
- [示例](#示例)

## 概述

介入手术智能体 RESTful API 提供了完整的 HTTP 接口，支持术前评估、风险分析、器械推荐等功能。

### 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **内容类型**: `application/json`
- **认证方式**: Bearer Token / API Key
- **响应格式**: JSON

### API 版本

- **当前版本**: v1.0.0
- **版本策略**: URL 路径版本 (`/api/v1/...`)

## 认证

### API Key 认证

```bash
# 设置 API Key
export INTERVENTIONAL_API_KEY="your-api-key-here"

# 使用 API Key
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/api/v1/interventional/plan
```

### Bearer Token 认证

```bash
# 获取 Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 使用 Token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/interventional/plan
```

## API 端点

### 1. 术前规划

生成完整的介入手术方案。

**端点**: `POST /api/v1/interventional/plan`

**描述**: 基于患者信息生成手术方案，包括首选方案、备选方案、风险评估和推荐理由。

#### 请求

```http
POST /api/v1/interventional/plan HTTP/1.1
Content-Type: application/json
X-API-Key: your-api-key

{
  "patient_age": 76,
  "patient_gender": "Male",
  "symptoms": "TIA with right-sided weakness",
  "stenosis_percentage": 85,
  "vessel": "Left ICA",
  "procedure_type": "CAS",
  "comorbidities": ["Hypertension", "Diabetes"],
  "include_detailed_reasoning": true
}
```

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `patient_age` | integer | 是 | 患者年龄 (18-120) |
| `patient_gender` | string | 是 | 患者性别 ("Male" / "Female") |
| `symptoms` | string | 是 | 症状描述 |
| `stenosis_percentage` | number | 是 | 狭窄百分比 (0-100) |
| `vessel` | string | 是 | 目标血管 |
| `procedure_type` | string | 是 | 手术类型 ("CAS" / "PCI" / "TAVI") |
| `comorbidities` | array[string] | 否 | 合并症列表 |
| `medications` | array[string] | 否 | 当前用药列表 |
| `allergies` | array[string] | 否 | 过敏史列表 |
| `include_detailed_reasoning` | boolean | 否 | 是否包含详细推理 (默认: false) |
| `enable_confidence_scoring` | boolean | 否 | 是否计算置信度 (默认: true) |

#### 响应

```json
{
  "success": true,
  "data": {
    "recommendation": "recommended",
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
        {"factor": "Age >70", "severity": "High", "modifiable": false},
        {"factor": "Symptomatic status", "severity": "High", "modifiable": false},
        {"factor": "Active plaque", "severity": "High", "modifiable": false}
      ],
      "mitigation": [
        "Universal EPD use",
        "Careful technique",
        "Strict BP control"
      ],
      "expected_complication_rate": "5-7%"
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
        "key_findings": ["Age 76", "Symptomatic", "85% stenosis"]
      }
    ],
    "confidence_score": 0.85,
    "reasoning_chain": ["Step 1: Intent recognition...", "Step 2: Knowledge retrieval..."]
  },
  "meta": {
    "request_id": "req-abc123",
    "timestamp": "2026-01-11T10:30:00Z",
    "processing_time_ms": 1250,
    "model_version": "v1.0.0"
  }
}
```

#### 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 422 | 输入验证失败 |
| 500 | 服务器错误 |

---

### 2. 风险评估

独立的术前风险评估。

**端点**: `POST /api/v1/interventional/risk-assessment`

#### 请求

```http
POST /api/v1/interventional/risk-assessment HTTP/1.1
Content-Type: application/json

{
  "patient_age": 76,
  "comorbidities": ["Hypertension", "Diabetes", "CKD Stage 3"],
  "procedure_type": "CAS",
  "lesion_characteristics": {
    "stenosis": 85,
    "length": "15mm",
    "calcification": "Moderate"
  }
}
```

#### 响应

```json
{
  "success": true,
  "data": {
    "overall_risk": "High",
    "risk_score": 7.5,
    "risk_categories": {
      "patient_factors": {
        "score": 3.5,
        "factors": [
          {"name": "Age >70", "weight": 1.5, "mitigable": false},
          {"name": "Diabetes", "weight": 1.0, "mitigable": true}
        ]
      },
      "anatomical_factors": {
        "score": 2.5,
        "factors": [
          {"name": "Severe stenosis (85%)", "weight": 1.5}
        ]
      }
    },
    "modifiable_factors": [
      {
        "factor": "Diabetes",
        "current_status": "HbA1c 7.2%",
        "target": "HbA1c <7%",
        "intervention": "Optimize diabetes regimen"
      }
    ],
    "predicted_complications": [
      {"complication": "Peri-procedural stroke", "probability": "5%", "severity": "High"},
      {"complication": "Hyperperfusion syndrome", "probability": "2%", "severity": "Moderate"}
    ],
    "recommendations": [
      "Strict BP control pre-procedure",
      "Ensure adequate DAPT loading"
    ]
  }
}
```

---

### 3. 器械推荐

获取器械推荐。

**端点**: `POST /api/v1/interventional/devices`

#### 请求

```http
POST /api/v1/interventional/devices HTTP/1.1
Content-Type: application/json

{
  "procedure": "CAS",
  "anatomy": {
    "vessel": "Left ICA",
    "diameter_mm": 4.8,
    "lesion_length_mm": 15,
    "characteristics": ["Tortuous", "Ulcerated plaque"]
  }
}
```

#### 响应

```json
{
  "success": true,
  "data": {
    "embolic_protection": {
      "primary_recommendation": {
        "device": "FilterWire EZ",
        "manufacturer": "Boston Scientific",
        "size": "4.5mm filter",
        "rationale": "First-line EPD, excellent trackability"
      },
      "backup_for_filter_failure": {
        "device": "MO.MA Proximal Protection",
        "when_to_use": "If unable to cross with distal filter"
      }
    },
    "stent": {
      "primary_recommendation": {
        "device": "PRECISE PRO RX",
        "manufacturer": "Cordis",
        "size": "7x40mm",
        "rationale": "Open-cell design for tortuous anatomy"
      }
    },
    "balloon": {
      "pre_dilatation": {
        "device": "Avitar Plus",
        "size": "5x20mm"
      },
      "post_dilatation": {
        "device": "Avitar Plus",
        "size": "7x20mm"
      }
    }
  }
}
```

---

### 4. 指南查询

查询临床指南。

**端点**: `GET /api/v1/interventional/guidelines/{procedure_type}`

#### 请求

```http
GET /api/v1/interventional/guidelines/CAS?topic=indications HTTP/1.1
```

#### 查询参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `procedure_type` | string | 是 | 路径参数，手术类型 |
| `topic` | string | 否 | 主题 (indications, contraindications, complications) |
| `patient_age` | integer | 否 | 患者年龄（用于个性化） |
| `symptomatic` | boolean | 否 | 是否有症状 |

#### 响应

```json
{
  "success": true,
  "data": {
    "topic": "CAS Indications for Symptomatic Stenosis",
    "recommendations": [
      {
        "class": "Class I",
        "level": "Level A",
        "statement": "CAS is indicated for symptomatic patients with 50-99% stenosis",
        "evidence": {
          "supporting_studies": [
            {
              "name": "CREST Trial",
              "year": 2010,
              "sample_size": 2502,
              "key_finding": "CAS and CEA had similar long-term outcomes"
            }
          ]
        }
      }
    ]
  }
}
```

---

### 5. 手术模拟

流式模拟手术过程。

**端点**: `POST /api/v1/interventional/simulate`

**注意**: 此端点使用 Server-Sent Events (SSE) 流式返回。

#### 请求

```http
POST /api/v1/interventional/simulate HTTP/1.1
Content-Type: application/json

{
  "patient_data": {
    "age": 76,
    "symptoms": "TIA",
    "stenosis_percentage": 85
  },
  "procedure_type": "CAS"
}
```

#### 响应 (SSE Stream)

```
data: {"type": "phase_start", "phase": "access", "description": "Femoral access with 7F sheath"}

data: {"type": "guidance", "phase": "access", "guidance": "Use ultrasound guidance"}

data: {"type": "decision_point", "phase": "epd_deployment", "options": ["Continue", "Switch to proximal"]}

data: {"type": "complete", "summary": "Simulation completed successfully"}
```

---

### 6. 术后管理计划

生成术后护理计划。

**端点**: `POST /api/v1/interventional/postop-plan`

#### 请求

```http
POST /api/v1/interventional/postop-plan HTTP/1.1
Content-Type: application/json

{
  "procedure_type": "CAS",
  "patient_age": 76,
  "comorbidities": ["Hypertension", "Diabetes"],
  "procedure_details": {
    "devices_used": ["FilterWire EZ", "PRECISE 7x40mm"],
    "complications": null
  }
}
```

#### 响应

```json
{
  "success": true,
  "data": {
    "medications": {
      "dual_antiplatelet_therapy": {
        "aspirin": {"dose": "81 mg daily", "duration": "Lifelong"},
        "clopidogrel": {"dose": "75 mg daily", "duration": "Minimum 30 days"}
      },
      "statin": {"drug": "Atorvastatin", "dose": "40-80 mg daily"},
      "blood_pressure": {"target": "SBP <140 mmHg"}
    },
    "monitoring": {
      "immediate_postop": {
        "duration": "18-24 hours observation",
        "neurological_checks": "Every hour for first 6 hours"
      }
    },
    "follow_up_schedule": [
      {"timeframe": "30 days", "assessments": ["Clinical evaluation", "Duplex ultrasound"]},
      {"timeframe": "6 months", "assessments": ["Clinical evaluation", "Duplex ultrasound"]}
    ]
  }
}
```

---

### 7. 批量评估

批量评估多个患者。

**端点**: `POST /api/v1/interventional/batch-assess`

#### 请求

```http
POST /api/v1/interventional/batch-assess HTTP/1.1
Content-Type: application/json

{
  "patients": [
    {"age": 76, "symptoms": "TIA", "stenosis_percentage": 85, "procedure_type": "CAS"},
    {"age": 65, "symptoms": "Asymptomatic", "stenosis_percentage": 75, "procedure_type": "CAS"},
    {"age": 82, "symptoms": "Stroke", "stenosis_percentage": 90, "procedure_type": "CAS"}
  ]
}
```

#### 响应

```json
{
  "success": true,
  "data": {
    "results": [
      {"index": 0, "recommendation": "recommended", "confidence": 0.85},
      {"index": 1, "recommendation": "consider", "confidence": 0.72},
      {"index": 2, "recommendation": "recommended", "confidence": 0.78}
    ],
    "summary": {
      "total": 3,
      "recommended": 2,
      "consider": 1,
      "not_recommended": 0
    }
  }
}
```

---

### 8. 健康检查

检查 API 服务状态。

**端点**: `GET /api/v1/health`

#### 响应

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "neo4j": "connected",
    "milvus": "connected",
    "llm": "available"
  },
  "timestamp": "2026-01-11T10:30:00Z"
}
```

## 数据模型

### ErrorResponse

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {"field": "patient_age", "message": "Age must be between 18 and 120"}
    ]
  },
  "request_id": "req-abc123"
}
```

### 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|----------|------|
| `VALIDATION_ERROR` | 422 | 输入验证失败 |
| `AUTHENTICATION_ERROR` | 401 | 认证失败 |
| `AUTHORIZATION_ERROR` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过速率限制 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 错误处理

### 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "request_id": "req-abc123",
    "timestamp": "2026-01-11T10:30:00Z"
  }
}
```

### 错误处理示例 (Python)

```python
import requests
from requests.exceptions import HTTPError, RequestException

def assess_patient(patient_data):
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/interventional/plan",
            json=patient_data,
            headers={"X-API-Key": "your-api-key"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except HTTPError as e:
        error_data = e.response.json()
        print(f"Error {error_data['error']['code']}: {error_data['error']['message']}")
        if error_data['error'].get('details'):
            print("Details:", error_data['error']['details'])

    except RequestException as e:
        print(f"Request failed: {e}")
```

## 速率限制

### 默认限制

- **免费用户**: 100 请求/小时
- **付费用户**: 1000 请求/小时
- **企业用户**: 无限制

### 速率限制头

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641888000
```

### 处理速率限制

```python
import time
import requests

def make_request_with_retry(url, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=data)

        if response.status_code == 429:
            # 获取重置时间
            reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
            wait_time = max(reset_time - time.time(), 0)
            print(f"Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        return response.json()

    raise Exception("Max retries exceeded")
```

## 示例

### cURL 示例

```bash
# 术前评估
curl -X POST http://localhost:8000/api/v1/interventional/plan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "patient_age": 76,
    "patient_gender": "Male",
    "symptoms": "TIA with right-sided weakness",
    "stenosis_percentage": 85,
    "vessel": "Left ICA",
    "procedure_type": "CAS",
    "comorbidities": ["Hypertension", "Diabetes"]
  }'

# 风险评估
curl -X POST http://localhost:8000/api/v1/interventional/risk-assessment \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "patient_age": 76,
    "comorbidities": ["Hypertension", "Diabetes"],
    "procedure_type": "CAS",
    "lesion_characteristics": {
      "stenosis": 85,
      "length": "15mm",
      "calcification": "Moderate"
    }
  }'

# 器械推荐
curl -X POST http://localhost:8000/api/v1/interventional/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "procedure": "CAS",
    "anatomy": {
      "vessel": "Left ICA",
      "diameter_mm": 4.8,
      "lesion_length_mm": 15,
      "characteristics": ["Tortuous", "Ulcerated plaque"]
    }
  }'

# 查询指南
curl -X GET "http://localhost:8000/api/v1/interventional/guidelines/CAS?topic=indications" \
  -H "X-API-Key: your-api-key"
```

### Python 示例

```python
import requests
import json

API_BASE = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# 术前评估
def plan_intervention(patient_data):
    response = requests.post(
        f"{API_BASE}/interventional/plan",
        json=patient_data,
        headers=headers
    )
    response.raise_for_status()
    return response.json()

# 使用示例
patient = {
    "patient_age": 76,
    "patient_gender": "Male",
    "symptoms": "TIA with right-sided weakness",
    "stenosis_percentage": 85,
    "vessel": "Left ICA",
    "procedure_type": "CAS",
    "comorbidities": ["Hypertension", "Diabetes"]
}

result = plan_intervention(patient)
print(f"Recommendation: {result['data']['recommendation']}")
print(f"Procedure: {result['data']['primary_plan']['procedure']}")
```

### JavaScript 示例

```javascript
const API_BASE = 'http://localhost:8000/api/v1';
const API_KEY = 'your-api-key';

async function planIntervention(patientData) {
  const response = await fetch(`${API_BASE}/interventional/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify(patientData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  return response.json();
}

// 使用示例
const patient = {
  patient_age: 76,
  patient_gender: 'Male',
  symptoms: 'TIA with right-sided weakness',
  stenosis_percentage: 85,
  vessel: 'Left ICA',
  procedure_type: 'CAS',
  comorbidities: ['Hypertension', 'Diabetes']
};

planIntervention(patient)
  .then(result => {
    console.log('Recommendation:', result.data.recommendation);
    console.log('Procedure:', result.data.primary_plan.procedure);
  })
  .catch(error => {
    console.error('Error:', error.message);
  });
```

## WebSocket 支持

对于实时手术模拟，支持 WebSocket 连接：

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/interventional/simulate/ws');

ws.onopen = () => {
  // 发送患者数据
  ws.send(JSON.stringify({
    patient_data: { age: 76, symptoms: 'TIA' },
    procedure_type: 'CAS'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.description);

  if (data.type === 'decision_point') {
    // 发送决策
    ws.send(JSON.stringify({
      decision: data.options[0]
    }));
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Simulation completed');
};
```

## 更多资源

- 📖 [SDK 使用指南](sdk_guide.md) - Python SDK 详细文档
- 💻 [CLI 使用指南](cli_guide.md) - 命令行工具使用
- 🏥 [临床场景示例](clinical_examples.md) - 真实临床案例
