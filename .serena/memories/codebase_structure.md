# 代码库结构

## 顶层目录
```
Medical-Graph-RAG/
├── camel/                 # 主要代码目录（基于 CAMEL 框架）
│   ├── agents/           # Agent 实现
│   ├── types/            # 类型定义
│   ├── societies/        # Agent 社会编排
│   ├── storages/         # 存储抽象
│   └── ...
├── nano_graphrag/        # 图 RAG 实现
│   ├── graphrag.py       # GraphRAG 类
│   ├── _llm.py           # LLM 接口
│   ├── _storage.py       # 存储接口
│   └── ...
├── tests/                # 测试目录
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   ├── contract/         # 契约测试
│   ├── test_agents/      # Agent 测试
│   └── ...
├── docs/                 # 文档目录
├── openspec/             # OpenSpec 规范目录
│   └── changes/          # 变更提案
├── data/                 # 数据目录
├── examples/             # 示例代码
├── run.py                # 主入口脚本
├── requirements.txt      # 依赖列表
└── README.md             # 项目说明
```

## 关键文件
- `run.py` - 主入口脚本
- `requirements.txt` - Python 依赖
- `README.md` - 项目说明文档
- `CLAUDE.md` - 项目章程

## 主要模块说明
- `camel/agents/` - 各种 Agent 实现（base、chat_agent、task_agent 等）
- `nano_graphrag/` - 核心 Graph RAG 实现
- `tests/` - 完整的测试套件，包括单元测试、集成测试、性能测试等
