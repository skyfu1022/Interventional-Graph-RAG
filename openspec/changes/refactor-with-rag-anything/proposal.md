# 提案：基于 RAG Anything 重构项目

## 变更 ID
`refactor-with-rag-anything`

## 概述

将 Medical-Graph-RAG 项目的核心 RAG 引擎从自实现的 `nano_graphrag` 迁移到 [RAG-Anything](https://github.com/hkuds/rag-anything)，利用其成熟的多模态处理能力和完整的 RAG 流程，减少重复造轮子。

## 动机

### 当前问题
1. **重复实现**：`nano_graphrag` 模块实现了文本分块、实体提取、向量检索等功能，这些功能在 RAG Anything 中已有成熟实现
2. **多模态支持有限**：当前实现对图像、表格、公式等多模态内容的处理不够完善
3. **维护成本高**：自实现的 RAG 引擎需要持续维护和优化

### RAG Anything 的优势
- 基于 LightRAG 构建的成熟 RAG 框架
- 内置多模态文档处理（支持 MinerU 和 Docling 解析器）
- 支持图像、表格、公式的语义理解和索引
- 完整的知识图谱构建和查询能力
- 活跃的社区支持和持续更新

## 目标

1. 保持项目原有的三层层次化图谱结构
2. 保持 LangGraph Agent 工作流编排不变
3. 使用 RAG Anything 替代 `nano_graphrag` 的核心功能
4. 复用现有的 Neo4j 和 Milvus 存储层
5. 不新增复杂功能，仅进行等价重构

## 范围

### 包含
- 替换 `nano_graphrag` 核心模块为 RAG Anything
- 适配现有的存储抽象层（Neo4j、Milvus）
- 迁移实体提取和知识图谱构建逻辑
- 迁移查询和检索接口
- 更新测试用例

### 不包含
- 修改 Agent 工作流编排（`camel/agents/`）
- 修改 API 层
- 新增业务功能
- 性能优化（除非重构后性能下降）

## 设计原则

1. **最小变更**：只修改必要的代码，保持现有接口兼容
2. **渐进迁移**：分阶段进行，确保每个阶段都可验证
3. **测试先行**：在修改前确保测试覆盖完整

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| RAG Anything 不支持 Neo4j | 高 | 实现 LightRAG 到 Neo4j 的适配层 |
| 三层图谱结构难以实现 | 中 | 在 RAG Anything 之上构建层次化封装 |
| 查询结果差异 | 中 | 保留原有查询逻辑作为对比 |
| API 接口变化 | 低 | 创建适配层保持接口兼容 |

## 参考

- [RAG-Anything GitHub](https://github.com/hkuds/rag-anything)
- [LightRAG 文档](https://github.com/HKUDS/LightRAG)
- 项目论文：https://arxiv.org/abs/2408.04187
