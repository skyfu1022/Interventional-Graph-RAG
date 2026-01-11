# 介入手术智能体临床场景示例

## 目录

- [简介](#简介)
- [场景一：CAS 术前评估](#场景一cas-术前评估)
- [场景二：PCI 复杂病变处理](#场景二-pci-复杂病变处理)
- [场景三：并发症应急处理](#场景三-并发症应急处理)
- [场景四：多学科会诊支持](#场景四多学科会诊支持)
- [场景五：器械选择优化](#场景五器械选择优化)
- [场景六：术后管理计划](#场景六术后管理计划)
- [场景七：批量患者评估](#场景七批量患者评估)
- [场景八：临床研究支持](#场景八临床研究支持)

## 简介

本文档提供了介入手术智能体在真实临床场景中的应用示例。每个场景都包含完整的患者信息、系统输出和临床解读。

### 临床场景覆盖

- ✅ **CAS (颈动脉支架植入术)**：症状性和无症状性颈动脉狭窄
- ✅ **PCI (经皮冠状动脉介入)**：复杂冠状动脉病变
- ✅ **并发症处理**：术中意外情况应对
- ✅ **器械选择**：基于解剖特征的个性化推荐
- ✅ **术后管理**：完整的护理计划生成
- ✅ **批量处理**：高效的多患者评估

---

## 场景一：CAS 术前评估

### 临床背景

**患者信息**：
- 76 岁男性
- 主诉：近期 3 次 TIA，最近一次 2 周前
- 症状：右侧肢体无力、言语不清，持续 30 分钟后完全缓解
- 既往史：高血压 15 年、2 型糖尿病、高脂血症
- 用药：阿司匹林 81mg、赖诺普利 20mg、阿托伐他汀 40mg、二甲双胍 1000mg BID

**影像学发现**：
- CTA：左侧颈内动脉起始部 85% 狭窄（NASCET 法）
- 斑块特征：溃疡状、低回声（超声提示易损斑块）
- 远端血流：保留良好
- 对侧颈内动脉：轻度狭窄（<30%）

**临床问题**：
该患者是否适合 CAS？如果适合，应该使用什么器械？主要风险是什么？

### 使用系统评估

#### SDK 调用

```python
from src.sdk.interventional import InterventionalClient

client = InterventionalClient()

result = await client.plan_intervention(
    patient_age=76,
    patient_gender="Male",
    symptoms="TIA x3, last episode 2 weeks ago with right-sided weakness and speech difficulty, lasting 30 minutes",
    stenosis_percentage=85,
    stenosis_method="NASCET",
    vessel="Left ICA",
    plaque_features="Ulcerated, hypoechoic on ultrasound indicating vulnerable plaque",
    comorbidities=["Hypertension (15 years)", "Type 2 Diabetes", "Hyperlipidemia"],
    medications=["Aspirin 81mg", "Lisinopril 20mg", "Atorvastatin 40mg", "Metformin 1000mg BID"],
    procedure_type="CAS",
    include_detailed_reasoning=True
)
```

#### CLI 调用

```bash
medgraph interventional plan \
  --patient-age 76 \
  --patient-gender Male \
  --symptoms "TIA x3, last episode 2 weeks ago with right-sided weakness" \
  --stenosis 85 \
  --vessel "Left ICA" \
  --procedure-type CAS \
  --comorbidities "Hypertension,Diabetes,Hyperlipidemia" \
  --include-reasoning
```

### 系统输出

```json
{
  "recommendation": "recommended",
  "confidence_score": 0.85,

  "primary_plan": {
    "procedure": "Carotid Artery Stenting (CAS)",
    "approach": "Femoral access with 7F sheath",
    "devices": [
      {
        "name": "FilterWire EZ",
        "type": "Embolic Protection Device",
        "manufacturer": "Boston Scientific",
        "size": "4.5mm filter",
        "quantity": 1,
        "rationale": "First-line EPD with excellent trackability. Essential given active plaque and symptomatic status."
      },
      {
        "name": "PRECISE PRO RX",
        "type": "Carotid Stent",
        "manufacturer": "Cordis",
        "size": "7x40mm",
        "quantity": 1,
        "rationale": "Open-cell design provides flexibility for potential tortuosity. 1-2mm larger than normal ICA diameter (4.8mm)."
      },
      {
        "name": "Avitar Plus",
        "type": "Balloon Catheter",
        "size": "5x20mm (pre-dilatation)",
        "quantity": 1,
        "rationale": "1mm smaller than vessel for safe pre-dilatation if needed"
      }
    ],
    "steps": [
      "1. Femoral access with ultrasound guidance using 7F sheath",
      "2. Administer heparin (target ACT >250 seconds)",
      "3. Navigate 0.014-inch guidewire to left ICA",
      "4. Deploy FilterWire EZ 2-3cm beyond lesion in straight segment",
      "5. Optional pre-dilatation with 5x20mm balloon at low pressure (4-6 atm)",
      "6. Deploy PRECISE stent covering lesion with 5-10mm margins",
      "7. Optional post-dilatation if underexpanded (use caution, <12 atm)",
      "8. Final angiography to confirm optimal expansion",
      "9. Retrieve FilterWire EZ using capture sheath"
    ],
    "rationale": "Based on ACC/AHA 2021 Class I, Level A recommendation for symptomatic patients with 50-99% ICA stenosis. Patient meets criteria with TIA symptoms and 85% stenosis."
  },

  "backup_plan": {
    "condition": "If unable to cross lesion with distal filter (3-5% of cases)",
    "alternative": "Convert to proximal protection (MO.MA system)",
    "technique": "8F sheath required, inflate ECA and CCA balloons for flow reversal",
    "fallback": "If proximal protection also fails, abort procedure and refer for CEA"
  },

  "risk_assessment": {
    "level": "High",
    "risk_score": 7.5,
    "factors": [
      {"factor": "Age >70 years", "severity": "High", "modifiable": false, "impact": "Increases peri-procedural stroke risk (CREST age interaction)"},
      {"factor": "Symptomatic status (recent TIA)", "severity": "High", "modifiable": false, "impact": "High recurrent stroke risk without intervention"},
      {"factor": "Active plaque (ulcerated, hypoechoic)", "severity": "High", "modifiable": false, "impact": "High embolization risk"},
      {"factor": "Hypertension", "severity": "Medium", "modifiable": true, "impact": "Requires careful BP management"},
      {"factor": "Diabetes", "severity": "Medium", "modifiable": true, "impact": "Increased cardiovascular risk"}
    ],
    "mitigation": [
      "Universal EPD use (FilterWire EZ or alternative)",
      "Careful technique - minimal wire manipulation",
      "Strict BP control (<140/90 mmHg pre-procedure)",
      "Ensure DAPT optimization (verify platelet inhibition if prior stent thrombosis)",
      "Consider heparin dosing to maintain ACT >300 seconds",
      "Post-procedure BP monitoring (hyperperfusion prevention)",
      "Operator with >30 CAS cases experience recommended"
    ],
    "expected_complication_rate": "5-7% (stroke/death/MI at 30 days)"
  },

  "sources": [
    {
      "graph": "literature",
      "source": "ACC/AHA 2021 Guideline for Carotid Artery Stenting",
      "recommendation": "Class I, Level A",
      "relevant_quote": "CAS is indicated for patients with recent TIA or ischemic stroke attributed to 50-99% stenosis of the internal carotid artery",
      "url": "https://www.acc.org/guidelines"
    },
    {
      "graph": "literature",
      "source": "CREST Trial (2010)",
      "recommendation": "Level A Evidence",
      "relevant_quote": "CAS and CEA had similar long-term outcomes for symptomatic patients. Age interaction: CAS safer in patients <70, CEA safer in patients >70",
      "note": "Patient age 76 favors CEA, but other factors (symptomatic, active plaque) still support CAS"
    },
    {
      "graph": "patient",
      "source": "Clinical data",
      "key_findings": ["Age 76", "Symptomatic (3 TIA episodes)", "85% stenosis", "Active plaque", "Good distal flow"]
    },
    {
      "graph": "dictionary",
      "source": "Device specifications",
      "relevant_info": "FilterWire EZ: 110 micron pores, 95% capture efficiency. PRECISE: Open-cell design, high flexibility"
    }
  ],

  "reasoning_chain": [
    "Step 1 (Intent Recognition): Identified CAS procedure from 'Left ICA stenosis' context",
    "Step 2 (Entity Extraction): Extracted age=76, symptomatic, stenosis=85%, active plaque, HTN, DM",
    "Step 3 (U-Retrieval - Global): Retrieved ACC/AHA Class I indication for symptomatic >50% stenosis",
    "Step 4 (U-Retrieval - Local): Identified patient-specific risks (age>70, active plaque)",
    "Step 5 (U-Retrieval - Hybrid): Retrieved device specifications (FilterWire, PRECISE)",
    "Step 6 (Indications Assessment): Meets Class I criteria - symptomatic + 85% stenosis",
    "Step 7 (Contraindications Assessment): No absolute contraindications. Age>70 is relative consideration",
    "Step 8 (Risk Assessment): Overall high risk due to age, symptoms, active plaque",
    "Step 9 (Procedure Matching): Guideline-based CAS with EPD mandatory",
    "Step 10 (Plan Synthesis): Primary plan (FilterWire + PRECISE), Backup (MO.MA), Risk mitigation strategies"
  ]
}
```

### 临床解读

**推荐等级：Class I（强烈推荐）**

该患者符合 CAS 的所有主要适应症：

1. **症状性颈动脉狭窄**：患者有明确的 TIA 病史（3次）
2. **狭窄程度**：85% 重度狭窄（NASCET 法）
3. **手术可及性**：解剖结构适合介入治疗

**主要考虑因素**：

| 因素 | 权重 | 考虑 |
|------|------|------|
| 症状状态 | ⭐⭐⭐ | 强烈支持干预（高卒中风险） |
| 狭窄程度 | ⭐⭐⭐ | 85% > 70% 阈值 |
| 活动性斑块 | ⭐⭐⭐ | 必须使用 EPD |
| 年龄 >70 | ⭐⭐ | 相对禁忌，CREST 提示 CEA 可能更安全 |
| 血管解剖 | ⭐ | 需要评估主动脉弓形态 |

**器械选择理由**：

1. **FilterWire EZ**：
   - 标准远端滤网 EPD
   - 110 微米孔径，95% 捕获效率
   - 活动性斑块必须使用 EPD

2. **PRECISE PRO RX (7x40mm)**：
   - 开环设计，适合潜在血管迂曲
   - 直径比正常 ICA (4.8mm) 大 1-2mm
   - CREST 试验中使用的支架，证据充分

**风险管理**：

- **总风险：高（7.5/10）**
- **预期并发症率：5-7%**
- **关键缓解措施**：
  - 严格 BP 控制（预防过度灌注综合征）
  - 确保 DAPT 充分
  - 经验丰富的术者（>30 例 CAS）
  - 备用方案：近端保护装置

**备选方案讨论**：

考虑到患者年龄（76岁），CEA 可能也有合理性。CREST 试验显示年龄>70岁时 CEA 卒中风险更低。应与患者讨论：
- CAS 优势：微创、避免颈部切口、较低的 MI 风险
- CEA 优势：年龄>70时卒中风险可能更低、一次性处理病变

**最终建议**：

**推荐 CAS**，但需：
1. 经验丰富的术者
2. 使用 EPD（FilterWire 或 MO.MA 备用）
3. 严格围手术期 BP 控制
4. 充分的 DAPT
5. 患者充分知情同意，了解 CEA 替代方案

---

## 场景二：PCI 复杂病变处理

### 临床背景

**患者信息**：
- 68 岁女性
- 主诉：劳力性胸痛 3 个月，加拿大心功能分级 III 级
- 既往史：2 型糖尿病、高血压、肥胖（BMI 32）
- 既往 PCI：RCA 支架植入（5年前）

**冠脉造影发现**：
- LAD：近中段 90% 弥漫性病变，长度 30mm，重度钙化
- LCX：OM 支架 70% 狭窄
- RCA：原支架通畅，无再狭窄
- LVEF：55%

**临床问题**：
如何处理 LAD 复杂病变？需要什么特殊器械和技术？

### 使用系统评估

```python
result = await client.plan_intervention(
    patient_age=68,
    patient_gender="Female",
    symptoms="Exertional chest pain, CCS Class III",
    stenosis_percentage=90,
    vessel="LAD",
    lesion_characteristics="Diffuse, 30mm length, severe calcification",
    comorbidities=["Diabetes", "Hypertension", "Obesity BMI 32"],
    procedure_type="PCI",
    include_detailed_reasoning=True
)
```

### 系统输出

```json
{
  "recommendation": "recommended with modifications",
  "confidence_score": 0.78,

  "primary_plan": {
    "procedure": "Complex PCI of LAD with rotational atherectomy",
    "approach": "Radial access with 7F EBU 3.5 guide catheter",
    "devices": [
      {
        "name": "Rotablator",
        "type": "Rotational Atherectomy Device",
        "size": "1.5mm burr",
        "rationale": "Severe calcification requires plaque modification before stenting"
      },
      {
        "name": "IVUS catheter",
        "type": "Intravascular Ultrasound",
        "rationale": "Assess calcium extent, optimize stent expansion, check edge dissection"
      },
      {
        "name": "Drug-eluting stent (Xience Sierra)",
        "type": "Coronary Stent",
        "size": "2.5x38mm and 2.75x38mm",
        "rationale": "Long lesion may require overlapping stents, ultrathin struts for deliverability"
      }
    ],
    "steps": [
      "1. Radial access with 7F sheath (consider femoral if need large burr)",
      "2. Administer heparin and bivalirudin (consider based on bleeding risk)",
      "3. Advance 7F EBU guide to LAD ostium",
      "4. Wire lesion with workhorse guidewire (Grand Slam)",
      "5. Perform IVUS pullback to assess calcium distribution",
      "6. Exchange to RotaWire, perform rotational atherectomy with 1.5mm burr",
      "7. Consider larger burr (1.75mm) if calcium remains significant",
      "8. Pre-dilatation with non-compliant balloon if needed",
      "9. Deploy first DES (2.5x38mm)",
      "10. IVUS check for optimal expansion and edge dissection",
      "11. Deploy second DES (2.75x38mm) with 3-4mm overlap",
      "12. Post-dilatation of overlap zone with non-compliant balloon",
      "13. Final IVUS to confirm optimal expansion (MSI >90%)",
      "14. Final angiography"
    ],
    "rationale": "ACC/AHA 2021 guidelines support PCI for symptomatic CAD. Complex calcified lesion requires plaque modification with rotational atherectomy."
  },

  "risk_assessment": {
    "level": "Intermediate-High",
    "key_factors": [
      {"factor": "Diabetes", "severity": "Medium", "impact": "Increased restenosis risk, consider longer DAPT"},
      {"factor": "Severe calcification", "severity": "High", "impact": "Requires rotational atherectomy, increases complexity"},
      {"factor": "Long lesion (30mm)", "severity": "Medium", "impact": "May require overlapping stents, higher restenosis risk"},
      {"factor": "Obesity", "severity": "Low", "impact": "May affect radiation dose and contrast volume"}
    ],
    "mitigation": [
      "IVUS guidance for optimal stent expansion",
      "Aggressive lipid management (target LDL <55 mg/dL)",
      "Consider DCB or bioresorbable scaffold if available (investigational)",
      "Meticulous overlapping technique to minimize restenosis",
      "Extended DAPT (12 months) given diabetes and long lesion"
    ]
  },

  "sources": [
    {
      "graph": "literature",
      "source": "ACC/AHA 2021 PCI Guideline",
      "recommendation": "Class I, Level A",
      "relevant_quote": "PCI is indicated for patients with symptomatic CAD suitable for revascularization"
    },
    {
      "graph": "literature",
      "source": "PREPARE-CALC and ROTAXUS trials",
      "recommendation": "Class IIa, Level B",
      "relevant_quote": "Rotational atherectomy is reasonable for heavily calcified lesions not modifiable by balloon dilatation alone"
    }
  ]
}
```

### 临床解读

**推荐等级：Class IIa（可以推荐）**

**技术要点**：

1. **旋磨治疗**：
   - 1.5mm 磨头首选，避免过大磨头
   - 160,000-180,000 rpm
   - 慢进快退（"pecking" motion）
   - 每次 15-20 秒，间歇 10 秒

2. **IVUS 引导**：
   - 评估钙化角度（>180°需要旋磨）
   - 评估支架扩张（MSI 目标 >90%）
   - 检查边缘夹层

3. **重叠支架**：
   - 3-4mm 重叠
   - 先远端后近端
   - 重叠区域后扩张

---

## 场景三：并发症应急处理

### 临床背景

**场景**：CAS 术中，FilterWire EPD 无法通过 85% 狭窄病变

**问题**：
- 已尝试 3 次不同导丝轨迹
- 患者症状性，85% 狭窄
- 斑块溃疡状，高栓塞风险

### 使用系统

```python
result = await client.handle_complication(
    complication_type="epd_deployment_failure",
    context={
        "procedure": "CAS",
        "patient_age": 76,
        "symptomatic": True,
        "stenosis": 85,
        "active_plaque": True,
        "attempts": 3,
        "available_devices": ["FilterWire", "MO.MA system", "GuardWire"]
    }
)
```

### 系统输出

```json
{
  "complication": "EPD Deployment Failure",
  "incidence": "2-5% of CAS procedures",
  "urgency": "High",

  "assessment": {
    "risk": "High embolic risk without EPD",
    "causes": ["Severe stenosis", "Tortuous proximal vessel", "Unfavorable lesion angle"],
    "continue_attempts": "NOT recommended - risk increases with multiple attempts"
  },

  "recommended_actions": {
    "step_1": {
      "action": "Convert to proximal protection (MO.MA system)",
      "rationale": "Protection starts before lesion crossing, no need to navigate past stenosis",
      "requirements": ["8F sheath", "Adequate common carotid length (>2cm)", "Patient tolerance of flow interruption"]
    },
    "step_2": {
      "action": "If MO.MA not available or contraindicated",
      "alternatives": [
        "Consider distal occlusion (GuardWire) - but still requires crossing",
        "Abort procedure and refer for CEA - safest option given symptomatic status"
      ]
    }
  },

  "decision_matrix": {
    "mo_ma_available": "Use MO.MA (success rate ~85%)",
    "mo_ma_unavailable_anatomy_favorable": "Consider one more careful attempt with different wire",
    "mo_ma_unavailable_anatomy_unfavorable": "ABORT and refer for CEA"
  },

  "technique_guidance": {
    "mo_ma_deployment": [
      "Exchange to 8F sheath (may need Perclose ProGlide for hemostasis)",
      "Advance MO.MA to common carotid artery",
      "Inflate external carotid artery balloon first (test occlusion)",
      "Inflate common carotid artery balloon",
      "Verify flow cessation (angiography or Doppler)",
      "Proceed with intervention under flow reversal",
      "Aspirate aggressively from sheath before balloon deflation"
    ]
  },

  "warning": "DO NOT proceed without EPD in symptomatic patient with active plaque - unacceptable stroke risk"
}
```

### 临床决策流程

```
EPD 无法通过 (3次尝试后)
       │
       ↓
  MO.MA 可用？
       │
   ┌───┴───┐
   │       │
  YES      NO
   │       │
   ↓       ↓
解剖适合？  尝试其他导丝？
   │       │
 ┌─┴─┐   ┌─┴─┐
 │   │   │   │
YES  NO  1次  否
 │   │   │   │
 ↓   ↓   ↓   ↓
使用 中止 降级 中止
MO.MA 并转CEA 后失败 CEA
```

---

## 场景四：多学科会诊支持

### 临床背景

**场景**：多学科会诊（MDT）讨论 76 岁症状性颈动脉狭窄患者的最佳治疗方案

**参与者**：
- 神经内科医师
- 介入放射科医师
- 血管外科医师
- 神经科医师

**问题**：CAS vs CEA？

### 使用系统

```python
# 准备比较报告
comparison = await client.compare_treatment_options(
    patient_profile={
        "age": 76,
        "symptoms": "TIA",
        "stenosis": 85,
        "comorbidities": ["HTN", "DM", "HL"]
    },
    options=["CAS", "CEA"],
    outcome_measures=["stroke", "mi", "death", "cranial_nerve_injury"]
)
```

### 系统输出

```json
{
  "patient_summary": "76M, symptomatic, 85% Left ICA stenosis, HTN/DM/HL",

  "comparison_table": {
    "cas": {
      "stroke_risk": "4.1% (CREST)",
      "mi_risk": "1.1% (CREST)",
      "death_risk": "<1%",
      "cranial_nerve_injury": "<1%",
      "advantages": [
        "No neck incision",
        "Lower cranial nerve injury",
        "Lower MI risk",
        "Shorter hospital stay",
        "Preferred for prior neck surgery or radiation"
      ],
      "disadvantages": [
        "Higher stroke risk in age >70",
        "Requires dual antiplatelet therapy",
        "Higher restenosis rate",
        "Learning curve for operator"
      ],
      "crest_age_interaction": "CAS safer for patients <70, CEA safer for >70"
    },
    "cea": {
      "stroke_risk": "2.3% (CREST)",
      "mi_risk": "2.3% (CREST)",
      "death_risk": "<1%",
      "cranial_nerve_injury": "5-10%",
      "advantages": [
        "Lower stroke risk in age >70",
        "Durable result (lower restenosis)",
        "No need for DAPT",
        "Proven long-term data",
        "Single procedure (no retreatment needed)"
      ],
      "disadvantages": [
        "Neck incision",
        "Higher cranial nerve injury",
        "Higher MI risk",
        "Longer hospital stay",
        "Not suitable for high cervical lesions"
      ]
    }
  },

  "guideline_recommendations": {
    "cas": "Class I for symptomatic 50-99% stenosis, Class IIa for asymptomatic >70%",
    "cea": "Class I for symptomatic 50-99% stenosis, Class IIa for asymptomatic >70%"
  },

  "patient_specific_considerations": {
    "age_76": "Favors CEA based on CREST age interaction (lower stroke risk)",
    "symptomatic": "Strong indication for revascularization (either CAS or CEA)",
    "comorbidities": {
      "diabetes": "No clear preference, both options acceptable",
      "hypertension": "No clear preference, BP control important for both",
      "hyperlipidemia": "No clear preference, statin therapy indicated"
    }
  },

  "shared_decision_making": {
    "discuss_with_patient": [
      "CAS: Less invasive, lower neck complications, higher stroke risk at age 76",
      "CEA: Lower stroke risk at age 76, neck incision, higher nerve injury risk",
      "Both: Require lifelong aspirin, risk reduction compared to medical therapy alone"
    ],
    "patient_preferences": [
      "Does patient prefer to avoid neck incision?",
      "Is patient willing to take dual antiplatelet therapy for 1-6 months?",
      "Is patient comfortable with cranial nerve injury risk (5-10%) vs stroke risk difference?"
    ]
  },

  "final_recommendation": {
    "summary": "Either CAS or CEA is acceptable based on guidelines. CREST data suggests lower stroke risk with CEA in patients >70. Decision should be based on anatomy, patient preference, and operator experience.",
    "if_anatomy_favorable_for_cas": "CAS is reasonable if patient prefers to avoid neck incision",
    "if_anatomy_unfavorable_for_cas": "CEA may be preferred given age >70",
    "key_criterion": "Anatomical assessment (arch type, lesion location, vessel tortuosity) should guide final decision"
    }
}
```

### MDT 讨论要点

**神经内科观点**：
- 支持积极干预（症状性、85% 狭窄）
- 担心 CAS 卒中风险（年龄>70）

**介入放射科观点**：
- CAS 可行，但需要注意：
  - III 型主动脉弓会增加难度
  - 需要经验丰富的术者
  - 必须使用 EPD

**血管外科观点**：
- CEA 是该年龄组的"金标准"
- 更低的卒中风险
- 可以在局麻下完成

**最终共识**：

1. 评估解剖结构（CTA 重建主动脉弓）
2. 如果解剖适合 CAS → 与患者讨论两种选择
3. 如果解剖不适合 CAS → CEA
4. 如果患者强烈倾向避免颈部切口 → CAS（知情同意）

---

## 场景五：器械选择优化

### 临床背景

**场景**：不同解剖特征下的器械个性化选择

### 系统使用

```python
scenarios = [
    {
        "name": "Tortuous ICA",
        "anatomy": {"diameter": 4.8, "length": 15, "tortuosity": "Severe"},
        "devices": await client.get_device_recommendations(...)
    },
    {
        "name": "Ulcerated Plaque",
        "anatomy": {"diameter": 5.2, "length": 12, "plaque": "Ulcerated"},
        "devices": await client.get_device_recommendations(...)
    },
    {
        "name": "Large Diameter ICA",
        "anatomy": {"diameter": 6.5, "length": 10, "tortuosity": "Minimal"},
        "devices": await client.get_device_recommendations(...)
    }
]
```

### 系统输出对比

| 解剖特征 | 支架推荐 | 理由 | EPD 推荐 |
|---------|---------|------|----------|
| **迂曲 ICA** | PRECISE (开环) | 高柔顺性，易于通过 | FilterWire EZ |
| **溃疡斑块** | Wallstent (闭环) | 更好的斑块覆盖 | FilterWire EZ |
| **大直径 ICA** | Cristallo Ideale | 锥形设计匹配解剖 | FilterWire EZ (大号) |

---

## 场景六：术后管理计划

### 临床背景

**场景**：CAS 术后，需要制定完整的护理计划

### 系统使用

```python
postop = await client.plan_postop_care(
    procedure_type="CAS",
    patient_age=76,
    comorbidities=["Hypertension", "Diabetes"],
    procedure_details={
        "devices_used": ["FilterWire EZ", "PRECISE 7x40mm"],
        "complications": null,
        "length_of_stay": "1 day planned"
    }
)
```

### 系统输出

```json
{
  "medications": {
    "dual_antiplatelet_therapy": {
      "aspirin": {"dose": "81-325 mg daily", "duration": "Lifelong"},
      "clopidogrel": {"dose": "75 mg daily", "duration": "Minimum 30 days (consider 6 weeks)"}
    },
    "statin": {
      "drug": "Atorvastatin 40-80 mg daily",
      "intensity": "High-intensity",
      "target_ldl": "<70 mg/dL (preferably <55 mg/dL)"
    },
    "blood_pressure": {
      "target": "SBP <140 mmHg for 72 hours, then <130/80 mmHg long-term",
      "urgency": "CRITICAL for first 72 hours (prevent hyperperfusion)"
    }
  },

  "monitoring": {
    "immediate": {
      "observation": "18-24 hours",
      "neuro_checks": "Every hour x 6, then every 4 hours",
      "bp_monitoring": "Continuous or hourly"
    },
    "discharge_criteria": [
      "Neurologically stable",
      "BP adequately controlled",
      "No access site complications",
      "Patient education complete"
    ]
  },

  "follow_up": [
    {"time": "30 days", "assessments": ["Clinical eval", "Duplex US", "DAPT adherence"]},
    {"time": "6 months", "assessments": ["Clinical eval", "Duplex US", "Restenosis screen"]},
    {"time": "12 months + annually", "assessments": ["Clinical eval", "Duplex US"]}
  ],

  "patient_education": {
    "warning_signs_call_911": [
      "Sudden weakness or numbness",
      "Speech difficulty",
      "Vision changes",
      "Severe headache with neurological changes"
    ],
    "warning_signs_call_office": [
      "Access site pain or swelling",
      "New mild neurological symptoms",
      "Medication side effects"
    ],
    "lifestyle": [
      "Smoking cessation",
      "Heart-healthy diet (Mediterranean)",
      "Exercise: walking 30 min daily",
      "BP monitoring at home"
    ]
  }
}
```

---

## 场景七：批量患者评估

### 临床背景

**场景**：评估 10 位等待 CAS 评估的患者

### 系统使用

```python
patients_df = pd.read_csv("patients_waiting_list.csv")

results = await client.batch_assess(
    patients=patients_df.to_dict('records'),
    procedure_type="CAS",
    priority_column="wait_time_weeks"
)

# 按优先级排序
results_sorted = sorted(results, key=lambda x: x['risk_score'], reverse=True)
```

### 输出示例

```csv
Patient_ID,Age,Symptoms,Stenosis,Risk_Score,Recommendation,Priority,Wait_Time
P001,76,TIA,85,7.5,Recommended,High,2
P002,65,None,78,4.2,Consider,Medium,8
P003,82,Stroke,90,8.8,Recommended,High,1
P004,71,None,72,5.1,Consider,Medium,5
P010,68,TIA,65,6.2,Recommended,Medium,3
```

### 临床决策

| 优先级 | 患者 | 行动 |
|--------|------|------|
| **高** | P003 (82岁, 卒中, 90%) | 立即评估，考虑 CEA（年龄因素） |
| **高** | P001 (76岁, TIA, 85%) | 2周内安排 CAS |
| **中** | P010 (68岁, TIA, 65%) | 4周内评估 |
| **中** | P004 (71岁, 无症状, 72%) | 讨论风险获益 |
| **低** | P002 (65岁, 无症状, 78%) | 6-8周内评估或考虑药物治疗 |

---

## 场景八：临床研究支持

### 临床背景

**场景**：研究者想了解 CAS 在不同年龄组的结局数据

### 系统使用

```python
# 查询临床试验数据
evidence = await client.query_clinical_trials(
    procedure="CAS",
    subgroups=["age <70", "age 70-80", "age >80"],
    outcomes=["stroke", "death", "mi", "restenosis"]
)
```

### 系统输出

```json
{
  "crest_trial_subgroup_analysis": {
    "age_lt_70": {
      "n": 1200,
      "stroke_rate_cas": "3.2%",
      "stroke_rate_cea": "5.8%",
      "hr": "0.55 (95% CI 0.38-0.80)",
      "interpretation": "CAS significantly better than CEA in patients <70"
    },
    "age_70_80": {
      "n": 950,
      "stroke_rate_cas": "5.5%",
      "stroke_rate_cea": "3.8%",
      "hr": "1.45 (95% CI 0.98-2.14)",
      "interpretation": "Trend favoring CEA, not statistically significant"
    },
    "age_gt_80": {
      "n": 352,
      "stroke_rate_cas": "7.2%",
      "stroke_rate_cea": "4.1%",
      "hr": "1.76 (95% CI 1.05-2.94)",
      "interpretation": "CEA significantly better than CAS in patients >80"
    }
  },

  "other_trials": {
    "sapphire": "High surgical risk patients, CAS non-inferior to CEA",
    "epace": "Did not complete, stopped early",
    "space": "Non-inferiority not demonstrated"
  },

  "meta_analysis": {
    "overall_conclusion": "Age is important effect modifier - CAS better for younger patients, CEA better for older patients",
    "optimal_cutoff": "Age 70-75 years based on trial data",
    "clinical_implication": "Patient age should be key consideration in treatment selection"
  }
}
```

---

## 总结

这些临床场景展示了介入手术智能体在实际临床工作中的应用价值：

1. **术前评估**：快速、标准化的评估流程
2. **器械推荐**：基于解剖特征的个性化选择
3. **风险管理**：系统性的风险识别和缓解策略
4. **并发症处理**：应急决策支持
5. **多学科讨论**：循证医学证据准备
6. **术后管理**：完整的护理计划
7. **批量处理**：高效的患者管理
8. **临床研究**：快速证据查询

---

## 更多资源

- 📖 [概述文档](overview.md) - 系统架构和核心概念
- 📖 [SDK 使用指南](sdk_guide.md) - Python SDK 详细文档
- 📖 [API 参考文档](api_reference.md) - RESTful API 参考
- 📖 [CLI 使用指南](cli_guide.md) - 命令行工具使用
