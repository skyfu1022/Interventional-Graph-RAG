# Medical-Graph-RAG 项目概览

## 项目目的
Medical-Graph-RAG 是一个专为医学领域构建的图谱检索增强生成（Graph RAG）系统。

该项目基于论文：https://arxiv.org/abs/2408.04187

## 核心功能
1. **医学知识图谱构建** - 从医学文档中提取实体和关系构建知识图谱
2. **三层架构图谱系统**：
   - 顶层（Top-level）：用户私有数据（如 MIMIC IV 数据集）
   - 中层（Medium-level）：医学书籍和论文（MedC-K 数据集）
   - 底层（Bottom-level）：医学词典数据（UMLS）
3. **智能检索** - 基于图谱的检索增强生成
4. **图谱合并** - 支持图内和跨图谱节点合并

## 技术栈
- **语言**: Python 3.10
- **主要框架**: 
  - CAMEL - 多智能体管道框架
  - Nano-GraphRAG - 轻量级图谱 RAG 实现
- **数据库**: Neo4j（图数据库）
- **LLM**: OpenAI API（支持通过环境变量配置）
- **向量检索**: FAISS, ChromaDB
- **其他**: PyTorch, Transformers, LangChain

## 依赖管理
- 使用 conda 环境管理
- 环境配置文件: `medgraphrag.yml`
