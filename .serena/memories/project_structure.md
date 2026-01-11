# 项目结构

```
Medical-Graph-RAG/
├── run.py                    # 主入口，命令行参数解析
├── creat_graph.py            # 图谱创建逻辑
├── retrieve.py               # 检索逻辑
├── data_chunk.py             # 数据分块
├── summerize.py              # 文档摘要生成
├── dataloader.py             # 数据加载工具
├── utils.py                  # 工具函数集合
├── cleangraph.py             # 图谱清理
├── agentic_chunker.py        # 智能分块器
├── three_layer_import.py     # 三层架构导入
├── split_medr.py             # 数据分割
├── verify_installation.py    # 安装验证
│
├── camel/                    # CAMEL 框架集成
│   ├── agents/
│   ├── storages/
│   ├── loaders/
│   └── ...
│
├── nano_graphrag/           # Nano GraphRAG 实现
│   └── ...
│
├── src/                     # 源代码目录
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置
│   │   ├── database.py      # 数据库操作
│   │   └── audit.py         # 审计日志
│   ├── graph/               # 图谱相关
│   │   ├── nodes/           # 图谱节点
│   │   │   ├── check.py
│   │   │   ├── intent.py
│   │   │   ├── reasoner.py
│   │   │   └── retrieval.py
│   │   ├── workflow.py      # 工作流定义
│   │   └── state.py         # 状态管理
│   ├── ingestion/           # 数据摄取
│   ├── retrieval/           # 检索模块
│   ├── cli/                 # 命令行接口
│   └── api/                 # API 接口
│
├── tests/                   # 测试目录（已被 .gitignore 忽略）
│   ├── unit/
│   ├── integration/
│   └── contract/
│
├── docs/                    # 文档
├── data/                    # 数据目录
│
├── medgraphrag.yml          # Conda 环境配置
├── medgraphrag_gpu.yml      # GPU 版本环境配置
├── Dockerfile               # Docker 配置
├── requirements.txt         # Python 依赖（被忽略）
├── .gitignore               # Git 忽略规则
└── README.md                # 项目说明
```

## 关键目录说明

### camel/
CAMEL 框架的多智能体系统，提供：
- `KnowledgeGraphAgent` - 知识图谱构建智能体
- `Neo4jGraph` - Neo4j 图数据库存储接口
- `UnstructuredIO` - 非结构化数据处理

### nano_graphrag/
轻量级的 GraphRAG 实现，提供简单快速的 RAG 能力

### src/
结构化的源代码，包含：
- 工作流引擎
- 图谱节点定义
- 数据摄取和检索管道
- CLI 和 API 接口

### 数据集位置
- `./dataset/` - 主数据集目录
- `./dataset_ex/` - 示例数据集
- `./dataset_test/` - 测试数据集
- `./nanotest/` - Nano GraphRAG 测试目录
