# 规范：医学领域实体提取

**所有者**: Medical-Graph-RAG 团队
**创建日期**: 2026-01-12
**状态**: 提案中

---

## 新增需求

### 需求：医学实体类型定义

**编号**: ENTITY-001

**描述**:
系统必须定义并使用标准的医学实体类型列表,用于实体提取时的类型分类。

**验收标准**:
1. 默认实体类型包括：Disease, Symptom, Treatment, Medication, Test, Anatomy, Procedure, Condition, Measurement, Hormone, Diagnostic_Criteria, Clinical_Guideline, Patient, Doctor
2. 实体类型可配置
3. 实体类型在提取时被正确应用

#### 场景：使用默认医学实体类型

**前提条件**:
- RAGAdapter 已初始化

**步骤**:
1. 检查 `entity_types` 属性
2. 验证包含所有默认类型

**预期结果**:
- `entity_types` 包含所有 14 种默认类型

**示例代码**:
```python
from medgraphrag.rag_adapter import RAGAdapter

adapter = RAGAdapter(
    working_dir="./test",
    gid="test_001",
    neo4j_graph=neo4j,
    llm_model_func=llm_func,
    embedding_func=embedding_func
)

expected_types = [
    "Disease", "Symptom", "Treatment", "Medication", "Test",
    "Anatomy", "Procedure", "Condition", "Measurement", "Hormone",
    "Diagnostic_Criteria", "Clinical_Guideline", "Patient", "Doctor"
}

assert adapter.entity_types == expected_types
```

#### 场景：使用自定义实体类型

**步骤**:
1. 定义自定义实体类型
2. 初始化 RAGAdapter 时传入
3. 验证类型被正确使用

**预期结果**:
- 提取的实体类型符合自定义列表

---

### 需求：实体描述提取

**编号**: ENTITY-002

**描述**:
系统必须为每个提取的实体生成描述信息,提供实体的详细上下文和定义。

**验收标准**:
1. 每个实体包含 `description` 字段
2. 描述包含实体的关键属性和上下文
3. 描述长度合理（10-200 字符）
4. 描述基于原始文本内容,不产生幻觉

#### 场景：提取带描述的疾病实体

**前提条件**:
- 输入文本包含疾病及其描述

**步骤**:
1. 准备医学文本
2. 调用实体提取
3. 验证实体和描述

**预期结果**:
- 疾病实体被正确提取
- 描述包含疾病的关键特征
- 描述准确反映源文本

**示例代码**:
```python
content = """
2型糖尿病（Type 2 Diabetes Mellitus）是一种代谢性疾病,
主要特征是胰岛素抵抗和高血糖。患者常表现为多饮、多尿、多食和体重下降。
"""

result = await adapter.process_content(content)

entities = result["entities"]
disease_entities = [e for e in entities if e["entity_type"] == "Disease"]

assert len(disease_entities) > 0
entity = disease_entities[0]

assert "entity_name" in entity
assert "entity_type" in entity
assert "description" in entity
assert len(entity["description"]) > 10
# 描述应该包含关键信息
assert any(keyword in entity["description"].lower() for keyword in
           ["糖尿病", "diabetes", "胰岛素", "insulin", "血糖", "blood sugar"])
```

---

### 需求：关系强度标注

**编号**: ENTITY-003

**描述**:
系统必须为提取的关系分配强度等级,表示关系的置信度和重要性。

**验收标准**:
1. 每个关系包含 `strength` 字段
2. 强度值可以是：high, medium, low
3. 强度基于关系描述的明确性和确定性
4. 强度信息可用于查询时的排序和过滤

#### 场景：提取不同强度的关系

**前提条件**:
- 输入文本包含不同确定性的关系

**步骤**:
1. 准备包含明确和模糊关系的文本
2. 调用实体提取
3. 验证关系强度

**预期结果**:
- 明确的关系（如"导致"）获得 high 强度
- 模糊的关系（如"可能与...有关"）获得 medium 或 low 强度

**示例代码**:
```python
content = """
高血压会导致心脏病。这是明确的因果关系。
研究表明,吸烟可能与肺癌有关,但需要更多证据确认。
"""

result = await adapter.process_content(content)
relationships = result["relationships"]

# 验证强度标注
assert any(rel.get("strength") in ["high", "medium", "low"] for rel in relationships)

# 明确的因果关系应该是 high
causal_rels = [r for r in relationships if "cause" in r.get("description", "").lower()]
if len(causal_rels) > 0:
    assert causal_rels[0].get("strength") == "high"
```

---

### 需求：医学关系类型推断

**编号**: ENTITY-004

**描述**:
系统必须根据关系描述自动推断医学领域特定的关系类型,如 TREATS, CAUSES, HAS_SYMPTOM 等。

**验收标准**:
1. 治疗相关描述 → TREATS
2. 因果相关描述 → CAUSES
3. 症状相关描述 → HAS_SYMPTOM
4. 诊断相关描述 → INDICATES
5. 其他 → RELATED_TO

#### 场景：推断治疗关系

**前提条件**:
- 输入文本包含药物治疗信息

**步骤**:
1. 准备包含治疗关系的文本
2. 调用实体提取
3. 验证关系类型

**预期结果**:
- 治疗关系被正确识别为 TREATS 类型

**示例代码**:
```python
content = """
阿司匹林可以治疗头痛和发热。
医生建议患者服用奥司他韦来治疗流感。
"""

result = await adapter.process_content(content)
relationships = result["relationships"]

# 验证治疗关系
treat_rels = [r for r in relationships if "src" in r and "tgt" in r]
# 应该有药物到疾病/症状的 TREATS 关系
assert len(treat_rels) > 0
```

---

### 需求：实体合并和去重

**编号**: ENTITY-005

**描述**:
系统必须能够识别和合并相同实体的多次出现,避免冗余。

**验收标准**:
1. 相同名称的实体被识别为同一实体
2. 合并时保留所有描述信息
3. 合并时聚合所有关系
4. 合并后的实体包含完整的上下文

#### 场景：合并同一实体的多次提及

**前提条件**:
- 文本在不同位置提及同一实体

**步骤**:
1. 准备包含同一实体多次提及的文本
2. 调用实体提取（带分块）
3. 验证实体合并结果

**预期结果**:
- 同一实体只出现一次
- 描述包含所有提及的信息

**示例代码**:
```python
content = """
患者主诉头痛。头痛已持续三天,疼痛程度为中度。
查体显示患者神志清楚,头痛时伴有恶心症状。
"""

result = await adapter.process_content(content, use_grained_chunking=True)
entities = result["entities"]

# 检查头痛实体
headache_entities = [e for e in entities if "头痛" in e.get("entity_name", "") or
                                              "HEADACHE" in e.get("entity_name", "")]
# 应该只有一个头痛实体（合并后）
assert len(headache_entities) == 1
# 描述应该包含多个来源的信息
assert len(headache_entities[0]["description"]) > 20
```

---

## 修改需求

### 需求：支持细粒度分块

**编号**: ENTITY-006

**修改内容**:
系统**必须**支持可选的细粒度分块模式,使用语义相关的文本块进行实体提取。

**验收标准**:
1. `use_grained_chunking` 参数启用细粒度分块
2. 细粒度分块产生更聚焦的实体提取
3. 跨块的相同实体被合并
4. 用户可以选择使用哪种分块方式

#### 场景：比较分块模式

**前提条件**:
- 较长的医学文本（> 2000 字符）

**步骤**:
1. 使用默认分块提取实体
2. 使用细粒度分块提取实体
3. 比较结果

**预期结果**:
- 细粒度分块提取更多细粒度实体
- 两种模式的实体质量都符合要求

---

### 需求：医学缩写词扩展

**编号**: ENTITY-007

**修改内容**:
系统**必须**能够识别和扩展医学缩写词,提取完整形式。

**验收标准**:
1. 识别常见的医学缩写（如 BP, HR, BMI）
2. 提取时保留完整形式
3. 在描述中注明缩写和全称

#### 场景：提取带缩写的医学术语

**步骤**:
1. 准备包含医学缩写的文本
2. 调用实体提取
3. 验证缩写被正确处理

**预期结果**:
- 实体名称使用完整形式
- 描述包含缩写信息

**示例代码**:
```python
content = """
患者BP（血压）为140/90 mmHg，HR（心率）为85次/分，
BMI（体重指数）计算为26.5，属于超重范围。
"""

result = await adapter.process_content(content)
entities = result["entities"]

# 验证实体包含完整形式
entity_names = [e["entity_name"] for e in entities]
# 应该包含完整形式而非仅缩写
assert any("BLOOD" in name or "血压" in name for name in entity_names) or \
       any("HEART" in name or "心率" in name for name in entity_names)
```

---

## 技术约束

1. **实体数量**:
   - 单次提取建议不超过 100 个实体
   - 超过时自动分批处理

2. **描述长度**:
   - 最小 10 字符
   - 最大 500 字符

3. **并发**:
   - 支持多个文档并发提取

---

## 非功能需求

1. **准确性**:
   - 实体类型准确率 > 85%
   - 关系提取准确率 > 80%

2. **性能**:
   - 1000 字符文本提取 < 10 秒
   - 支持批量处理

3. **可配置性**:
   - 所有阈值可配置
   - 支持添加自定义实体类型

---

## 参考资料

- [UMLS Semantic Types](https://www.nlm.nih.gov/research/umls/sourcereleasedocs/current/semantic_types.html)
- [SNOMED CT Entity Types](https://confluence.ihtsdotools.org/)
