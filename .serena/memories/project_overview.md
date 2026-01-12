# 项目概述

## 项目名称
Medical Graph RAG

## 项目目的
专门为医疗领域构建的图检索增强生成（Graph RAG）系统。该系统通过三层图谱结构（顶层私有数据、中层书籍和论文、底层字典数据）提供安全的医学大语言模型服务。

## 论文链接
https://arxiv.org/abs/2408.04187

## 核心特性
- 三层层次化图谱结构
- 基于 LangGraph 的 Agent 工作流编排
- 多模态文档处理与检索（支持 Qwen3-VL）
- 远程栓塞保护装置（EPD）选择等介入手术支持

## 系统架构
- **Orchestration**: LangGraph - 用于构建 Agent 工作流
- **RAG Pipeline**: LightRAG - 多模态文档处理与检索
- **图数据库**: Neo4j - 存储知识图谱
- **向量数据库**: Milvus - 向量检索
- **Web 框架**: FastAPI - 提供 REST API
