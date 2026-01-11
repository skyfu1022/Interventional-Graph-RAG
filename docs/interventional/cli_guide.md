# 介入手术智能体 CLI 使用指南

## 目录

- [简介](#简介)
- [安装](#安装)
- [配置](#配置)
- [命令参考](#命令参考)
- [使用示例](#使用示例)
- [高级功能](#高级功能)
- [技巧和窍门](#技巧和窍门)

## 简介

介入手术智能体命令行接口 (CLI) 提供了快速、便捷的命令行工具，支持术前评估、风险分析、器械推荐等功能。

### 主要特性

- ✅ **简单易用**：直观的命令结构
- ✅ **交互式模式**：支持交互式问答
- ✅ **批量处理**：支持批量评估多个患者
- ✅ **输出格式**：支持 JSON、表格、文本等多种格式
- ✅ **管道友好**：输出可与其他工具集成

## 安装

### 系统要求

- Python 3.10+
- 虚拟环境 (venv)

### 安装步骤

```bash
# 激活虚拟环境
source venv/bin/activate  # macOS/Linux

# 安装 CLI 依赖
pip install -r requirements.txt

# 验证安装
medgraph --version
# 输出: Medical Graph RAG v1.0.0
```

## 配置

### 配置文件

CLI 优先从以下位置读取配置：

1. 当前目录：`./config.yaml`
2. 用户目录：`~/.medgraph/config.yaml`
3. 系统目录：`/etc/medgraph/config.yaml`

### 环境变量

```bash
# 设置 API 密钥
export OPENAI_API_KEY="your-api-key"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_PASSWORD="your-password"
export MILVUS_URI="localhost:19530"

# CLI 特定配置
export MEDGRAPH_OUTPUT_FORMAT="json"  # json / table / text
export MEDGRAPH_LOG_LEVEL="INFO"      # DEBUG / INFO / WARNING / ERROR
```

### 配置示例

创建 `~/.medgraph/config.yaml`：

```yaml
# API 配置
api:
  base_url: "http://localhost:8000"
  api_key: "${MEDGRAPH_API_KEY}"

# 输出配置
output:
  format: "table"  # json / table / text
  pager: "less"    # less / more / none
  color: true

# 工作流配置
workflow:
  timeout: 300  # seconds
  retries: 3

# 日志配置
logging:
  level: "INFO"
  file: "~/.medgraph/cli.log"
```

## 命令参考

### 命令结构

```
medgraph interventional <command> [options] [arguments]
```

### 可用命令

| 命令 | 描述 |
|------|------|
| `plan` | 生成手术方案 |
| `risks` | 风险评估 |
| `devices` | 器械推荐 |
| `guidelines` | 查询指南 |
| `simulate` | 模拟手术 |
| `postop` | 术后管理计划 |
| `batch` | 批量评估 |
| `completion` | 生成 shell 自动补全脚本 |

### 全局选项

```bash
medgraph [global-options] interventional <command>

全局选项:
  -h, --help          显示帮助信息
  -v, --version       显示版本信息
  -c, --config FILE   指定配置文件
  -o, --output FILE   输出到文件
  -f, --format FORMAT 输出格式 (json/table/text)
  --log-level LEVEL   日志级别
  --no-color          禁用彩色输出
  --verbose           详细输出
  --quiet             静默模式
```

---

## 命令详解

### 1. plan - 生成手术方案

生成完整的介入手术方案。

```bash
medgraph interventional plan [OPTIONS]
```

#### 选项

| 选项 | 描述 | 必需 |
|------|------|------|
| `--patient-age INT` | 患者年龄 | 是 |
| `--patient-gender TEXT` | 患者性别 (Male/Female) | 是 |
| `--symptoms TEXT` | 症状描述 | 是 |
| `--stenosis INT` | 狭窄百分比 | 是 |
| `--vessel TEXT` | 目标血管 | 是 |
| `--procedure-type TEXT` | 手术类型 (CAS/PCI/TAVI) | 是 |
| `--comorbidities TEXT` | 合并症（逗号分隔） | 否 |
| `--medications TEXT` | 当前用药（逗号分隔） | 否 |
| `--include-reasoning` | 包含详细推理 | 否 |
| `--output FILE` | 输出到文件 | 否 |

#### 示例

```bash
# 基础用法
medgraph interventional plan \
  --patient-age 76 \
  --patient-gender Male \
  --symptoms "TIA with right-sided weakness" \
  --stenosis 85 \
  --vessel "Left ICA" \
  --procedure-type CAS

# 包含合并症
medgraph interventional plan \
  --patient-age 76 \
  --patient-gender Male \
  --symptoms "TIA x3" \
  --stenosis 85 \
  --vessel "Left ICA" \
  --procedure-type CAS \
  --comorbidities "Hypertension,Diabetes,Hyperlipidemia" \
  --medications "Aspirin,Lisinopril,Atorvastatin,Metformin"

# 包含详细推理
medgraph interventional plan \
  --patient-age 76 \
  --patient-gender Male \
  --symptoms "TIA" \
  --stenosis 85 \
  --vessel "Left ICA" \
  --procedure-type CAS \
  --include-reasoning \
  --format json

# 输出到文件
medgraph interventional plan \
  --patient-age 76 \
  --symptoms "TIA" \
  --stenosis 85 \
  --vessel "Left ICA" \
  --procedure-type CAS \
  --output assessment.json
```

#### 交互式模式

```bash
# 启动交互式模式
medgraph interventional plan --interactive

# 系统会逐步询问
? Patient age: 76
? Patient gender: Male
? Symptoms: TIA with right-sided weakness
? Stenosis percentage: 85
? Target vessel: Left ICA
? Procedure type: CAS
? Any comorbidities? (comma-separated): Hypertension, Diabetes

# 生成评估报告
```

---

### 2. risks - 风险评估

独立的术前风险评估。

```bash
medgraph interventional risks [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--patient-age INT` | 患者年龄 |
| `--comorbidities TEXT` | 合并症（逗号分隔） |
| `--procedure-type TEXT` | 手术类型 |
| `--lesion-stenosis INT` | 病变狭窄程度 |
| `--lesion-length TEXT` | 病变长度 |
| `--lesion-calcification TEXT` | 钙化程度 |

#### 示例

```bash
medgraph interventional risks \
  --patient-age 76 \
  --comorbidities "Hypertension,Diabetes,CKD Stage 3" \
  --procedure-type CAS \
  --lesion-stenosis 85 \
  --lesion-length "15mm" \
  --lesion-calcification "Moderate"
```

#### 输出示例

```
RISK ASSESSMENT
================================================================================
Overall Risk: High (7.5/10)

Risk Categories:
┌─────────────────────┬────────┬─────────────────────────────────┐
│ Category            │ Score  │ Factors                          │
├─────────────────────┼────────┼─────────────────────────────────┤
│ Patient Factors     │ 3.5/5  │ Age >70 (1.5), Diabetes (1.0),  │
│                     │        │ CKD Stage 3 (1.0)                │
├─────────────────────┼────────┼─────────────────────────────────┤
│ Anatomical Factors  │ 2.5/5  │ Severe stenosis 85% (1.5),      │
│                     │        │ Moderate calcification (1.0)     │
├─────────────────────┼────────┼─────────────────────────────────┤
│ Procedural Factors  │ 1.5/5  │ Symptomatic status (1.5)         │
└─────────────────────┴────────┴─────────────────────────────────┘

Modifiable Factors:
  • Diabetes: HbA1c 7.2% → Target <7%
  • Hypertension: 142/88 mmHg → Target <140/90 mmHg

Predicted Complications:
  • Peri-procedural stroke: 5% (High)
  • Hyperperfusion syndrome: 2% (Moderate)
  • Access site bleeding: 4% (Low)

Recommendations:
  ✓ Strict BP control pre-procedure
  ✓ Ensure adequate DAPT loading
  ✓ Consider hydration protocol for renal protection
```

---

### 3. devices - 器械推荐

获取器械推荐。

```bash
medgraph interventional devices [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--procedure TEXT` | 手术类型 |
| `--vessel TEXT` | 目标血管 |
| `--diameter FLOAT` | 血管直径 (mm) |
| `--length FLOAT` | 病变长度 (mm) |
| `--characteristics TEXT` | 解剖特征（逗号分隔） |

#### 示例

```bash
medgraph interventional devices \
  --procedure CAS \
  --vessel "Left ICA" \
  --diameter 4.8 \
  --length 15 \
  --characteristics "Tortuous,Ulcerated plaque"
```

#### 输出示例

```
DEVICE RECOMMENDATIONS
================================================================================
Procedure: Carotid Artery Stenting (CAS)

Embolic Protection:
  Primary: FilterWire EZ (Boston Scientific)
    • Size: 4.5mm filter
    • Rationale: First-line EPD, excellent trackability
    • Alternatives: Emboshield NAV6 (better visibility)

  Backup (if filter fails): MO.MA Proximal Protection
    • Requires: 8F sheath, proximal occlusion technique
    • Use case: Unable to cross with distal filter

Stent:
  Primary: PRECISE PRO RX (Cordis)
    • Size: 7x40mm
    • Design: Open-cell
    • Rationale: High flexibility for tortuous anatomy
    • Key features: Excellent conformability, Proven in CREST

  Alternative: Wallstent (Boston Scientific)
    • When to use: Better plaque coverage needed (closed-cell)
    • Note: Account for significant shortening during deployment

Balloon:
  Pre-dilatation: Avitar Plus 5x20mm (1mm smaller than vessel)
  Post-dilatation: Avitar Plus 7x20mm (same size as stent)
  Caution: Avoid high pressure (>12 atm)

Additional Equipment:
  • Sheath: 7F Flexor Shuttle Sheath (90cm)
  • Guidewire: 0.014-inch Whisper MS
  • Diagnostic: 5F Angled catheter for arch selection
```

---

### 4. guidelines - 查询指南

查询临床指南。

```bash
medgraph interventional guidelines [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--procedure-type TEXT` | 手术类型 |
| `--topic TEXT` | 主题 (indications/contraindications/complications) |
| `--patient-age INT` | 患者年龄（个性化） |
| `--symptomatic BOOL` | 是否有症状 |

#### 示例

```bash
# 查询适应症
medgraph interventional guidelines \
  --procedure-type CAS \
  --topic indications

# 个性化查询
medgraph interventional guidelines \
  --procedure-type CAS \
  --topic indications \
  --patient-age 76 \
  --symptomatic true

# 查询禁忌症
medgraph interventional guidelines \
  --procedure-type CAS \
  --topic contraindications

# 查询并发症处理
medgraph interventional guidelines \
  --procedure-type CAS \
  --topic complications
```

#### 输出示例

```
GUIDELINE: CAS Indications for Symptomatic Stenosis
================================================================================

Class I, Level A Recommendation:
  CAS is indicated for symptomatic patients with 50-99% stenosis of the
  internal carotid artery based on ACC/AHA 2021 Guidelines.

Supporting Evidence:
  • CREST Trial (2010)
    - Sample size: 2,502 patients
    - Key finding: CAS and CEA had similar long-term outcomes for
      symptomatic patients
    - Age interaction: CAS better for patients <70, CEA better for >70

  • NASCET Trial (1991)
    - Sample size: 659 patients
    - Key finding: CEA beneficial for symptomatic patients with >70%
      stenosis
    - Established the standard of care

Applicability to This Patient:
  ✓ Meets criteria: Symptomatic, 85% stenosis
  ✓ Age 76: Consider CEA may have lower stroke risk
  ✓ Individual decision based on anatomy and patient preference

Contraindications:
  • Absolute: Non-disabling stroke with mRS >2
  • Relative: Age >80, severe arch tortuosity

References:
  • ACC/AHA 2021 Guideline for Carotid Artery Stenting
    DOI: 10.1161/CIR.0000000000001025
```

---

### 5. simulate - 模拟手术

流式模拟手术过程。

```bash
medgraph interventional simulate [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--patient-file FILE` | 患者数据 JSON 文件 |
| `--procedure-type TEXT` | 手术类型 |
| `--speed TEXT` | 模拟速度 (slow/normal/fast) |

#### 示例

```bash
# 使用患者数据文件
medgraph interventional simulate \
  --patient-file patient.json \
  --procedure-type CAS \
  --speed normal

# 交互式模拟
medgraph interventional simulate --interactive

# 快速模拟（跳过详细说明）
medgraph interventional simulate \
  --patient-file patient.json \
  --speed fast
```

#### 模拟过程示例

```bash
$ medgraph interventional simulate --patient-file patient.json --procedure-type CAS

═══════════════════════════════════════════════════════════════════════════════
  SIMULATION: Carotid Artery Stenting (CAS)
  Patient: 76M, Symptomatic, 85% Left ICA stenosis
═══════════════════════════════════════════════════════════════════════════════

[PHASE 1: ACCESS]
─────────────────────────────────────────────────────────────────────────────
✓ Femoral access with 7F sheath
  Guidance: Use ultrasound guidance, micropuncture technique

[PHASE 2: EPD DEPLOYMENT]
─────────────────────────────────────────────────────────────────────────────
⚠ DECISION POINT: Unable to cross lesion with FilterWire

  Options:
    1) Continue attempts with different wire trajectory
    2) Convert to proximal protection (MO.MA)
    3) Abort and refer for CEA

  Recommendation: Convert to proximal protection
  Rationale: High embolic risk with multiple attempts, proximal protection
              provides safety before lesion crossing

  Your choice [2]: 2

✓ Deploying MO.MA proximal protection system
  Guidance: Inflate ECA balloon first, verify flow cessation

[PHASE 3: STENT DEPLOYMENT]
─────────────────────────────────────────────────────────────────────────────
✓ Pre-dilatation with 5x20mm balloon (low pressure)
✓ Deploying PRECISE 7x40mm stent
  Guidance: Deploy slowly to ensure accurate positioning

[PHASE 4: COMPLETION]
─────────────────────────────────────────────────────────────────────────────
✓ Post-dilatation (underexpanded)
✓ Final angiography - Good result, TIMI 3 flow
✓ Retrieve EPD

═══════════════════════════════════════════════════════════════════════════════
  SIMULATION COMPLETE
  Outcome: Successful
  Key Learning Points:
    • Proximal protection valuable when distal filter fails
    • Always have backup strategies prepared
    • Angiographic verification critical at each step
═══════════════════════════════════════════════════════════════════════════════
```

---

### 6. postop - 术后管理计划

生成术后护理计划。

```bash
medgraph interventional postop [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--procedure-type TEXT` | 手术类型 |
| `--patient-age INT` | 患者年龄 |
| `--comorbidities TEXT` | 合并症 |
| `--complications TEXT` | 术中并发症（如有） |

#### 示例

```bash
medgraph interventional postop \
  --procedure-type CAS \
  --patient-age 76 \
  --comorbidities "Hypertension,Diabetes"
```

---

### 7. batch - 批量评估

批量评估多个患者。

```bash
medgraph interventional batch [OPTIONS]
```

#### 选项

| 选项 | 描述 |
|------|------|
| `--input FILE` | 输入文件 (JSON/CSV) |
| `--output FILE` | 输出文件 |
| `--format FORMAT` | 输出格式 |

#### 输入文件格式 (JSON)

```json
{
  "patients": [
    {
      "patient_id": "P001",
      "age": 76,
      "symptoms": "TIA",
      "stenosis_percentage": 85,
      "procedure_type": "CAS"
    },
    {
      "patient_id": "P002",
      "age": 65,
      "symptoms": "Asymptomatic",
      "stenosis_percentage": 75,
      "procedure_type": "CAS"
    }
  ]
}
```

#### 示例

```bash
# 批量评估
medgraph interventional batch \
  --input patients.json \
  --output results.json \
  --format json

# 从 CSV 输入
medgraph interventional batch \
  --input patients.csv \
  --output results.csv
```

---

### 8. completion - 生成自动补全脚本

生成 shell 自动补全脚本。

```bash
# 生成 bash 补全
medgraph interventional completion --shell bash > ~/.medgraph-completion.bash
echo "source ~/.medgraph-completion.bash" >> ~/.bashrc

# 生成 zsh 补全
medgraph interventional completion --shell zsh > ~/.medgraph-completion.zsh
echo "source ~/.medgraph-completion.zsh" >> ~/.zshrc

# 生成 fish 补全
medgraph interventional completion --shell fish > ~/.config/fish/completions/medgraph.fish
```

---

## 高级功能

### 管道和过滤器

```bash
# 输出 JSON 并用 jq 处理
medgraph interventional plan \
  --patient-age 76 \
  --symptoms "TIA" \
  --stenosis 85 \
  --procedure-type CAS \
  --format json | jq '.data.primary_plan.devices'

# 只显示推荐结果
medgraph interventional plan ... | grep -A 5 "Recommendation"

# 导入到其他工具
medgraph interventional plan ... --format json | \
  python process_results.py
```

### 配置文件快速切换

```bash
# 使用不同配置文件
medgraph -c config-dev.yaml interventional plan ...
medgraph -c config-prod.yaml interventional plan ...

# 临时设置输出格式
medgraph -f json interventional plan ...
medgraph -f table interventional risks ...
```

### 环境变量覆盖

```bash
# 临时使用不同的 API
export MEDGRAPH_API_BASE="https://api.medgraph.com/v2"
medgraph interventional plan ...

# 临时更改日志级别
MEDGRAPH_LOG_LEVEL=DEBUG medgraph interventional plan ...
```

## 技巧和窍门

### 1. 创建别名

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias cas-assess='medgraph interventional plan --procedure-type CAS'
alias pci-assess='medgraph interventional plan --procedure-type PCI'
alias risks='medgraph interventional risks'

# 使用
cas-assess --patient-age 76 --symptoms "TIA" --stenosis 85 --vessel "Left ICA"
```

### 2. 保存常用配置

```bash
# 创建配置文件
cat > ~/.medgraph/cas-defaults.yaml <<EOF
procedure_type: CAS
include_reasoning: true
format: table
EOF

# 使用配置
medgraph interventional plan \
  --config ~/.medgraph/cas-defaults.yaml \
  --patient-age 76 \
  --symptoms "TIA" \
  --stenosis 85
```

### 3. 批处理脚本

```bash
#!/bin/bash
# batch_assess.sh

INPUT_FILE=$1
OUTPUT_DIR=$2

mkdir -p "$OUTPUT_DIR"

while IFS=',' read -r id age symptoms stenosis vessel; do
  echo "Assessing patient $id..."

  medgraph interventional plan \
    --patient-id "$id" \
    --patient-age "$age" \
    --symptoms "$symptoms" \
    --stenosis "$stenosis" \
    --vessel "$vessel" \
    --procedure-type CAS \
    --output "$OUTPUT_DIR/patient_${id}.json" \
    --format json
done < "$INPUT_FILE"

echo "Batch assessment complete. Results in $OUTPUT_DIR"
```

使用：

```bash
chmod +x batch_assess.sh
./batch_assess.sh patients.csv results/
```

### 4. 与其他工具集成

```bash
# 与 Excel 集成（使用 csvkit）
medgraph interventional plan ... --format json | \
  in2csv - > results.csv

# 与数据库集成
medgraph interventional plan ... --format json | \
  python import_to_db.py

# 发送邮件通知
medgraph interventional plan ... --format json | \
  mail -s "Assessment Results" physician@hospital.com
```

### 5. 调试模式

```bash
# 启用详细日志
medgraph --verbose --log-level DEBUG interventional plan ...

# 查看 API 调用
medgraph interventional plan ... --debug-api

# 保存日志
medgraph interventional plan ... 2> assessment.log
```

## 故障排除

### 常见问题

**Q: 命令找不到**

```bash
# 确保 venv 已激活
source venv/bin/activate

# 或使用完整路径
/path/to/venv/bin/medgraph interventional plan ...
```

**Q: 连接数据库失败**

```bash
# 检查服务状态
docker ps | grep neo4j
docker ps | grep milvus

# 检查配置
medgraph --show-config

# 测试连接
medgraph --test-connection
```

**Q: API 超时**

```bash
# 增加超时时间
medgraph interventional plan ... --timeout 600
```

**Q: 输出格式混乱**

```bash
# 禁用颜色
medgraph interventional plan ... --no-color

# 指定输出格式
medgraph interventional plan ... --format json
```

## 更多资源

- 📖 [SDK 使用指南](sdk_guide.md) - Python SDK 详细文档
- 🔌 [API 参考文档](api_reference.md) - RESTful API 参考
- 🏥 [临床场景示例](clinical_examples.md) - 真实临床案例
