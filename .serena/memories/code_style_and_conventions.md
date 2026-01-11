# 代码风格和规范

## 命名约定
- 函数名使用 snake_case: `creat_metagraph`, `load_high`, `seq_ret`
- 变量名使用 snake_case: `graph_func`, `file_name`, `sum_query`
- 类名使用 PascalCase（来自 CAMEL 框架）

## 代码结构
- 代码组织为模块化脚本，每个文件负责特定功能
- 主要入口点: `run.py` - 命令行参数解析和流程编排
- 核心模块:
  - `creat_graph.py` - 图谱创建
  - `retrieve.py` - 检索逻辑
  - `data_chunk.py` - 数据分块
  - `summerize.py` - 文档摘要
  - `dataloader.py` - 数据加载
  - `utils.py` - 工具函数

## 类型提示
- 项目中较少使用类型提示
- 函数参数和返回值通常没有显式类型注解

## 文档字符串
- 代码中缺少详细的 docstring
- 复杂逻辑缺少注释说明

## 导入风格
```python
import os
from getpass import getpass
from camel.storages import Neo4jGraph
from camel.agents import KnowledgeGraphAgent
```
- 先导入标准库
- 再导入第三方库
- 使用明确的模块导入

## 代码特点
- 使用 argparse 进行命令行参数解析
- 使用环境变量管理敏感配置（API密钥、数据库凭证）
- 使用 Cypher 查询语言操作 Neo4j
