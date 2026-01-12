# Medical-Graph-RAG

医疗领域的图检索增强生成（Graph RAG）系统。

## 论文

查看我们的论文：https://arxiv.org/abs/2408.04187

## 架构概述

本项目实现了一个基于 LightRAG-HKU 的医疗知识图谱系统，采用三层架构设计：

- **顶层（Top Layer）**：私有数据层 - 用户个人数据、病历笔记等
- **中层（Middle Layer）**：书籍和论文层 - 公开的医学书籍、研究论文等
- **底层（Bottom Layer）**：字典数据层 - 医学字典、术语表等基础数据

### 核心组件

1. **medical_rag/** - 核心 RAG 模块
   - `adapter.py`: LightRAG 适配器，支持文档插入和查询
   - `three_layer.py`: 三层图谱架构实现
   - `storage/`: 存储适配层（Neo4j、Milvus）
   - `config.py`: 配置管理

2. **camel/** - CAMEL 多智能体框架集成
3. **tests/** - 完整的单元测试和集成测试

---

## 快速开始

### 1. 环境准备

使用虚拟环境（推荐）：

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

或使用 conda：

```bash
conda env create -f medgraphrag.yml
conda activate medgraphrag
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，添加以下配置：

```bash
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE_URL=https://api.openai.com/v1  # 可选

# Neo4j 配置
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Milvus 配置（可选）
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. 基础使用

```python
from medical_rag import MedicalRAG, ThreeLayerGraph

# 创建 RAG 实例
rag = MedicalRAG()
rag.initialize()

# 插入文档
rag.insert("这是一段医疗文本...")

# 查询
result = rag.query("什么是糖尿病？", mode="hybrid")
print(result)
```

---

## Docker Demo

Docker 演示镜像：https://hub.docker.com/repository/docker/jundewu/medrag-post/general

使用方式：

```bash
docker run -it --rm --storage-opt size=10G -p 7860:7860 \
  -e OPENAI_API_KEY=your_key \
  -e NCBI_API_KEY=your_key \
  medrag-post
```

该演示使用基于 PubMed 的网络搜索来替代本地存储的医学论文和教科书，以规避许可限制。

---

## 完整构建流程

### 数据集说明

#### 论文数据集

**顶层私有数据（用户提供）**：我们使用 [MIMIC IV 数据集](https://physionet.org/content/mimiciv/3.0/) 作为私有数据。

**中层书籍和论文**：我们使用 MedC-K 作为中层数据。数据集来源于 [S2ORC](https://github.com/allenai/s2orc)。只有具有 PubMed ID 的论文被认为与医学相关，并在预训练中使用。书籍列在本仓库的 [MedicalBook.xlsx](https://github.com/MedicineToken/Medical-Graph-RAG/blob/main/MedicalBook.xlsx) 中，由于许可限制，我们无法发布原始内容。如需复现，请购买并处理这些书籍。

**底层字典数据**：我们使用 [统一医学语言系统（UMLS）](https://www.nlm.nih.gov/research/umls/index.html) 作为底层的数据。要访问它，您需要创建账户并申请使用。这是免费的，批准通常很快。

在代码中，我们使用 `trinity` 参数来启用层次图链接功能。如果设置为 True，还必须提供一个 `gid`（图 ID）来指定顶层应该链接到哪些图。UMLS 大部分结构是图，因此构建它的工作量很小。但是，MedC-K 必须构建为图数据。您可以使用几种方法，例如我们在这个仓库中处理顶层的方法（推荐使用开源 LLM 以降低成本），或者您可以选择基于非学习的图构建算法（更快、更便宜，但通常更嘈杂）。

#### 示例数据集

认识到访问和处理上述所有数据可能具有挑战性，我们正在努力提供更简单的示例数据集来演示功能。目前，我们使用这里的 [mimic_ex](https://huggingface.co/datasets/Morson/mimic_ex) 作为顶层的数据，这是从 MIMIC 派生的处理后的小数据集。对于中层和底层数据，我们正在确定合适的替代方案以简化实现，欢迎任何推荐。

### 1. 准备环境、Neo4j 和 LLM

```bash
conda env create -f medgraphrag.yml
```

准备 neo4j 和 LLM（这里以 ChatGPT 为例），您需要导出：

```bash
export OPENAI_API_KEY=your_openai_api_key
export NEO4J_URL=your_neo4j_url
export NEO4J_USERNAME=your_neo4j_username
export NEO4J_PASSWORD=your_neo4j_password
```

### 2. 构建图谱（以 "mimic_ex" 数据集为例）

1. 从[这里](https://huggingface.co/datasets/Morson/mimic_ex)下载 mimic_ex，放在您的数据路径下，如 `./dataset/mimic_ex`

2. ```bash
   python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -grained_chunk -ingraphmerge -construct_graph
   ```

### 3. 模型推理

1. 将您的提示放入 `./prompt.txt`

2. ```bash
   python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -inference
   ```

---

## 开发

### 运行测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块的测试
pytest tests/unit/medical_rag/ -v

# 查看测试覆盖率
pytest tests/unit/ --cov=medical_rag --cov-report=html
```

### 项目结构

```
Medical-Graph-RAG/
├── medical_rag/          # 核心 RAG 模块
│   ├── adapter.py        # LightRAG 适配器
│   ├── three_layer.py    # 三层图谱架构
│   ├── config.py         # 配置管理
│   ├── graphrag.py       # 兼容层
│   └── storage/          # 存储适配器
│       ├── neo4j_adapter.py
│       ├── milvus_adapter.py
│       └── factory.py
├── camel/                # CAMEL 框架集成
├── tests/                # 测试套件
│   ├── unit/
│   └── integration/
├── docs/                 # 文档
├── requirements.txt      # Python 依赖
├── README.md            # 本文件
└── run.py               # 主入口脚本
```

---

## 致谢

我们建立在 [CAMEL](https://github.com/camel-ai/camel) 之上，这是一个用于构建多智能体流程的优秀框架。

核心 RAG 引擎基于 [LightRAG-HKU](https://github.com/HKUDS/LightRAG) 实现。

---

## 引用

```bibtex
@article{wu2024medical,
  title={Medical Graph RAG: Towards Safe Medical Large Language Model via Graph Retrieval-Augmented Generation},
  author={Wu, Junde and Zhu, Jiayuan and Qi, Yunli},
  journal={arXiv preprint arXiv:2408.04187},
  year={2024}
}
```

---

## 许可证

本项目遵循相应的开源许可证。详见 LICENSE 文件。
