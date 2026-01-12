# 提案：基于 RAG-Anything 重构 Medical-Graph-RAG

## 概述

本提案旨在使用 [RAG-Anything](https://github.com/hkuds/rag-anything) 框架重构现有的 Medical-Graph-RAG 项目，以简化代码库并利用成熟的开源库提供的功能，避免重复造轮子。重构将保持原有的核心逻辑和功能，不引入新的复杂特性。

## 背景

### 当前实现

Medical-Graph-RAG 项目目前使用以下技术栈：

1. **自定义 GraphRAG 实现** (`nano_graphrag/`):
   - 自行实现了实体提取、图构建、社区检测等功能
   - 使用 NetworkX 作为图存储
   - 使用 MilvusLite 作为向量数据库
   - 实现了 local 和 global 两种查询模式

2. **Neo4j 图数据库**:
   - 用于三层架构的知识图谱存储
   - 支持 Top-level（患者数据）、Medium-level（医学书籍/论文）、Bottom-level（UMLS 医学词典）
   - 使用 CAMEL 框架的 Neo4jGraph 接口

3. **数据处理流程**:
   - 使用 `agentic_chunker.py` 进行智能分块
   - 使用 `creat_graph_with_description.py` 提取实体和关系
   - 支持图内合并 (ingraphmerge) 和跨图合并 (crossgraphmerge)
   - 支持三层架构链接 (trinity)

### 存在的问题

1. **代码重复**: 自定义的 `nano_graphrag` 实现与现有成熟的开源库（如 LightRAG）功能重叠
2. **维护成本高**: 需要维护自己的 GraphRAG 实现和相关的提示词
3. **功能局限**: 当前实现主要处理文本，缺乏对多模态内容（图像、表格、公式）的原生支持
4. **技术债务**: 混合使用 Neo4j 和自定义图存储，架构不够统一

## 解决方案

### RAG-Anything 的优势

[RAG-Anything](https://github.com/hkuds/rag-anything) 是基于 [LightRAG](https://github.com/HKUDS/LightRAG) 构建的一体化多模态 RAG 系统，具有以下特点：

1. **成熟的 GraphRAG 实现**:
   - 完整的实体提取和关系构建
   - 自动化的社区检测和报告生成
   - 支持 local、global、hybrid 三种查询模式

2. **灵活的存储支持**:
   - 支持多种图数据库后端（Neo4j、NetworkX 等）
   - 支持多种向量数据库（Milvus、ChromaDB 等）
   - 可扩展的存储接口

3. **多模态能力**:
   - 原生支持文本、图像、表格、公式的处理
   - 跨模态关系映射
   - 多模态查询支持

4. **可定制性强**:
   - 可以使用自定义的 LLM 函数
   - 可以使用自定义的嵌入函数
   - 支持直接插入预处理的内容

### 重构策略

#### 1. 核心功能映射

| 现有功能 | RAG-Anything 对应实现 |
|---------|---------------------|
| `nano_graphrag.GraphRAG` | `raganything.RAGAnything` (基于 LightRAG) |
| 实体提取 (`extract_entities_with_description`) | LightRAG 内置的实体提取 |
| 图存储 (NetworkX) | LightRAG 的可配置图存储后端 |
| 向量存储 (MilvusLite) | LightRAG 的可配置向量存储后端 |
| 社区检测和报告 | LightRAG 内置功能 |
| local/global 查询 | LightRAG 内置的 local/global/hybrid 查询 |

#### 2. 保留的功能

以下功能需要在重构中保留，因为它们是 Medical-Graph-RAG 特有的：

1. **三层架构支持**:
   - 继续使用 Neo4j 存储三层知识图谱
   - 保留 `gid` (graph ID) 机制用于区分不同层级
   - 保留 `link_context` 函数用于跨层链接

2. **医学领域特定功能**:
   - 保留医学实体类型定义（Disease、Symptom、Treatment 等）
   - 保留 UMLS 集成逻辑
   - 保留 MedC-K 数据处理逻辑

3. **数据处理流程**:
   - 保留 `agentic_chunker` 的智能分块（可选，可与 LightRAG 的分块结合使用）
   - 保留图内合并 (`merge_similar_nodes`) 功能
   - 保留摘要节点 (`add_sum`) 功能

#### 3. 重构范围

**需要重构的部分**:

1. 移除 `nano_graphrag/` 目录及其内容
2. 使用 `raganything` 替代核心 GraphRAG 功能
3. 重写 `run.py` 以使用新的 API
4. 重写 `creat_graph_with_description.py` 以使用 RAG-Anything 的实体提取
5. 更新 `requirements.txt` 添加 `rag-anything` 相关依赖

**保持不变的部分**:

1. Neo4j 三层架构的核心逻辑
2. CAMEL 框架的集成（用于 Agent 相关功能）
3. 数据加载器 (`dataloader.py`)
4. 工具函数 (`utils.py` 中的 Neo4j 相关函数)
5. 检索逻辑 (`retrieve.py`)

## 实施计划

详细的实施步骤请参考 [tasks.md](./tasks.md)。

## 技术细节

详细的架构设计和技术决策请参考 [design.md](./design.md)。

## 预期收益

1. **代码简化**: 移除约 1500+ 行自定义 GraphRAG 代码
2. **维护性提升**: 利用社区维护的成熟库，减少维护负担
3. **功能增强**: 获得多模态处理能力（图像、表格、公式）
4. **未来扩展**: 更容易集成 RAG-Anything 的未来功能更新
5. **稳定性提升**: 使用经过充分测试的开源库

## 风险和缓解措施

### 风险 1: API 不兼容

**风险**: RAG-Anything 的 API 可能无法完全满足现有需求

**缓解**:
- RAG-Anything 基于 LightRAG，支持自定义存储后端
- 可以实现自定义的 Neo4j 存储后端以保持三层架构
- 可以使用 `insert_content_list` API 直接插入预处理的内容

### 风险 2: 性能差异

**风险**: 新实现可能在性能上与现有实现有差异

**缓解**:
- 分阶段迁移，先在小数据集上验证
- 保留现有的性能测试用例
- 必要时可以调整 RAG-Anything 的配置参数

### 风险 3: 三层架构兼容性

**风险**: RAG-Anything 可能不原生支持三层架构

**缓解**:
- 使用多个 RAGAnything 实例分别处理不同层级
- 通过 Neo4j 实现层级间的链接
- 保留现有的 `gid` 机制和跨层查询逻辑

## 兼容性声明

本重构将保持以下接口的向后兼容：

1. **命令行接口**: `run.py` 的参数保持不变
2. **数据格式**: 输入数据格式保持不变
3. **Neo4j 模式**: 图数据库的节点和关系结构保持不变
4. **查询接口**: 检索和查询的输入输出格式保持不变

## 后续步骤

1. 审查并批准本提案
2. 根据 `tasks.md` 开始实施
3. 在测试环境中验证重构结果
4. 更新文档和示例
5. 部署到生产环境

## 参考资料

- [RAG-Anything GitHub](https://github.com/hkuds/rag-anything)
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [Medical-Graph-RAG 论文](https://arxiv.org/abs/2408.04187)
