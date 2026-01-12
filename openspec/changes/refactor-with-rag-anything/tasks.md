# 任务清单：基于 RAG-Anything 重构

本文档列出了重构项目所需的所有任务，按执行顺序排列。每个任务都是小型可验证的工作项，提供用户可见的进展。

## 阶段 1: 准备和依赖管理

### 任务 1.1: 更新依赖配置

**描述**: 更新 `requirements.txt`，添加 RAG-Anything 相关依赖，移除不再需要的依赖。

**详细步骤**:
1. 添加 `rag-anything` 包
2. 确认 `lightrag-hku` 版本兼容性
3. 保留现有的 Neo4j、CAMEL 等依赖
4. 移除仅用于 `nano_graphrag` 的特定依赖（如果有）

**验证方法**:
```bash
pip install -r requirements.txt --dry-run
```

**依赖**: 无

**预计产出**:
- 更新后的 `requirements.txt`

---

### 任务 1.2: 创建测试环境

**描述**: 建立一个测试环境，用于验证重构后的功能。

**详细步骤**:
1. 准备小规模测试数据集（来自 `dataset_ex/`）
2. 设置 Neo4j 测试实例
3. 配置环境变量

**验证方法**:
- 测试数据集能够加载
- Neo4j 连接正常

**依赖**: 任务 1.1

**预计产出**:
- 测试数据集配置
- 测试环境配置文档

---

## 阶段 2: 核心功能重构

### 任务 2.1: 创建 RAG-Anything 适配器模块

**描述**: 创建一个新模块 `medgraphrag/rag_adapter.py`，封装 RAG-Anything 的功能并提供与现有系统兼容的接口。

**详细步骤**:
1. 创建 `medgraphrag/` 目录
2. 实现 `RAGAdapter` 类，包装 `RAGAnything`
3. 配置医学领域特定的实体类型
4. 实现与现有 `gid` 机制的集成
5. 提供与 Neo4j 的集成接口

**关键接口**:
```python
class RAGAdapter:
    def __init__(self, working_dir: str, gid: str, neo4j_graph):
        """初始化 RAG 适配器"""

    async def process_content(self, content: str) -> Dict:
        """处理内容并提取实体关系"""

    async def insert_to_neo4j(self, entities, relationships):
        """将提取的实体和关系插入 Neo4j"""

    async def query(self, question: str, mode: str = "hybrid") -> str:
        """执行查询"""
```

**验证方法**:
- 单元测试验证适配器的各个方法
- 集成测试验证与 Neo4j 的交互

**依赖**: 任务 1.2

**预计产出**:
- `medgraphrag/rag_adapter.py`
- 单元测试文件 `tests/unit/test_rag_adapter.py`

---

### 任务 2.2: 重构实体提取逻辑

**描述**: 使用 RAG-Anything 的实体提取功能替换 `creat_graph_with_description.py` 中的自定义实现。

**详细步骤**:
1. 保留 `creat_graph_with_description.py` 作为新的高层接口
2. 使用 `RAGAdapter` 进行实体提取
3. 保留医学实体类型的定义
4. 保留实体合并逻辑
5. 保留与 Neo4j 的写入逻辑

**需要修改的函数**:
- `extract_entities_with_description` → 使用 `RAGAdapter.process_content`
- `creat_metagraph_with_description` → 集成新的提取逻辑

**验证方法**:
- 对比新旧实现提取的实体数量和质量
- 验证实体描述的完整性
- 验证 Neo4j 中的数据结构

**依赖**: 任务 2.1

**预计产出**:
- 重构后的 `creat_graph_with_description.py`
- 集成测试 `tests/integration/test_entity_extraction.py`

---

### 任务 2.3: 重构主程序 run.py

**描述**: 更新 `run.py` 使用新的 RAG-Anything 适配器。

**详细步骤**:
1. 保持命令行参数不变
2. 对于 `-simple` 模式：使用 RAG-Anything 的简单查询
3. 对于 `-construct_graph` 模式：使用新的实体提取逻辑
4. 对于 `-inference` 模式：集成 RAG-Anything 的查询功能
5. 保留三层架构支持 (`-trinity`)
6. 保留图合并功能 (`-ingraphmerge`, `-crossgraphmerge`)

**需要修改的部分**:
```python
# 移除
from nano_graphrag import GraphRAG, QueryParam

# 添加
from medgraphrag.rag_adapter import RAGAdapter

# simple 模式
if args.simple:
    # 使用 RAGAdapter 替代 GraphRAG
    ...
```

**验证方法**:
- 运行所有命令行参数组合
- 验证输出与原实现一致
- 性能基准测试

**依赖**: 任务 2.2

**预计产出**:
- 重构后的 `run.py`
- 端到端测试 `tests/integration/test_run.py`

---

### 任务 2.4: 处理分块逻辑

**描述**: 决定如何整合现有的 `agentic_chunker` 与 RAG-Anything 的分块功能。

**详细步骤**:
1. 评估两种分块方法的优劣
2. 选择其中一种作为主要方法：
   - 选项 A: 使用 RAG-Anything 的内置分块
   - 选项 B: 保留 `agentic_chunker` 并将结果传递给 RAG-Anything
   - 选项 C: 提供两种模式供用户选择
3. 实现选定的方案
4. 更新相关的参数和配置

**推荐**: 选项 C - 提供配置选项，默认使用 RAG-Anything 分块

**验证方法**:
- 比较不同分块方法的结果
- 验证分块对最终查询质量的影响

**依赖**: 任务 2.3

**预计产出**:
- 更新后的分块逻辑
- 配置文档

---

## 阶段 3: Neo4j 集成和三层架构

### 任务 3.1: 实现自定义 Neo4j 存储后端

**描述**: 为 LightRAG 创建自定义的 Neo4j 存储后端，支持三层架构的 `gid` 机制。

**详细步骤**:
1. 创建 `medgraphrag/neo4j_storage.py`
2. 继承 LightRAG 的 `BaseGraphStorage` 接口
3. 实现节点和关系的 CRUD 操作
4. 支持 `gid` 字段用于层级区分
5. 保持与现有 Neo4j 模式的兼容性

**关键方法**:
```python
class Neo4jGraphStorage(BaseGraphStorage):
    def __init__(self, neo4j_graph, gid: str):
        """初始化 Neo4j 存储"""

    async def upsert_node(self, node_id: str, node_data: dict):
        """插入或更新节点，自动添加 gid"""

    async def upsert_edge(self, source_id: str, target_id: str, edge_data: dict):
        """插入或更新关系"""

    async def get_node(self, node_id: str):
        """获取节点"""
```

**验证方法**:
- 单元测试各个存储操作
- 验证 `gid` 正确应用
- 验证与现有 Neo4j 数据的兼容性

**依赖**: 任务 2.3

**预计产出**:
- `medgraphrag/neo4j_storage.py`
- 单元测试 `tests/unit/test_neo4j_storage.py`

---

### 任务 3.2: 实现三层架构链接

**描述**: 实现跨层级的知识图谱链接功能。

**详细步骤**:
1. 保留 `utils.py` 中的 `link_context` 函数
2. 更新以支持新的 RAG-Anything 数据结构
3. 实现跨层级的实体匹配和链接
4. 支持 UMLS 词典的集成

**验证方法**:
- 验证不同层级间的链接正确建立
- 验证跨层级查询功能

**依赖**: 任务 3.1

**预计产出**:
- 更新后的 `utils.py`
- 集成测试 `tests/integration/test_trinity.py`

---

### 任务 3.3: 实现图合并功能

**描述**: 保留并更新图内合并和跨图合并功能。

**详细步骤**:
1. 保留 `utils.py` 中的 `merge_similar_nodes` 函数
2. 更新以兼容新的存储结构
3. 保留相似度计算逻辑
4. 支持跨 `gid` 的合并（`-crossgraphmerge`）

**验证方法**:
- 验证合并逻辑正确执行
- 验证合并后的图结构完整性

**依赖**: 任务 3.2

**预计产出**:
- 更新后的合并功能
- 测试用例

---

## 阶段 4: 查询和检索优化

### 任务 4.1: 集成 RAG-Anything 查询功能

**描述**: 使用 RAG-Anything 的查询功能替换现有的检索逻辑。

**详细步骤**:
1. 评估 `retrieve.py` 和 `summerize.py` 的功能
2. 确定哪些功能可以由 RAG-Anything 直接提供
3. 保留领域特定的检索逻辑（如 UMLS 查询）
4. 实现混合查询策略（结合 RAG-Anything 和自定义逻辑）

**查询模式映射**:
- `local` → RAG-Anything 的 local 查询
- `global` → RAG-Anything 的 global 查询
- `hybrid` → RAG-Anything 的 hybrid 查询

**验证方法**:
- 查询质量评估
- 响应时间对比
- 准确性测试

**依赖**: 任务 3.3

**预计产出**:
- 更新后的查询逻辑
- 性能基准测试结果

---

### 任务 4.2: 优化医学领域查询

**描述**: 针对医学领域优化查询提示词和参数。

**详细步骤**:
1. 自定义医学领域的查询提示词
2. 调整实体提取的置信度阈值
3. 优化社区检测参数
4. 实现医学术语的同义词处理

**验证方法**:
- 使用医学问答数据集评估
- 对比原系统的查询质量

**依赖**: 任务 4.1

**预计产出**:
- 医学领域配置文件
- 查询质量评估报告

---

## 阶段 5: 清理和文档

### 任务 5.1: 移除旧代码

**描述**: 移除不再需要的 `nano_graphrag` 目录和相关代码。

**详细步骤**:
1. 确认所有功能已迁移
2. 删除 `nano_graphrag/` 目录
3. 删除相关的导入和引用
4. 清理未使用的依赖

**验证方法**:
- 所有测试仍然通过
- 代码中无死链接或导入错误

**依赖**: 任务 4.2

**预计产出**:
- 清理后的代码库

---

### 任务 5.2: 更新文档

**描述**: 更新 README 和相关文档以反映新的实现。

**详细步骤**:
1. 更新 `README.md` 的架构说明
2. 更新安装和使用指南
3. 添加 RAG-Anything 的相关说明
4. 更新 Docker 配置（如果需要）
5. 添加迁移指南（从旧版本升级）

**验证方法**:
- 按照文档能够成功安装和运行
- 文档完整覆盖所有功能

**依赖**: 任务 5.1

**预计产出**:
- 更新后的 `README.md`
- `MIGRATION_GUIDE.md`（迁移指南）

---

### 任务 5.3: 更新测试套件

**描述**: 完善测试套件以覆盖所有重构的功能。

**详细步骤**:
1. 审查现有测试用例
2. 添加缺失的测试覆盖
3. 更新测试文档
4. 配置 CI/CD 流程

**测试覆盖目标**:
- 单元测试覆盖率 > 80%
- 集成测试覆盖核心流程
- 端到端测试覆盖主要用例

**验证方法**:
- 运行完整的测试套件
- 检查测试覆盖率报告

**依赖**: 任务 5.2

**预计产出**:
- 完整的测试套件
- 测试覆盖率报告

---

## 阶段 6: 验证和部署

### 任务 6.1: 集成测试和性能验证

**描述**: 在完整的数据集上验证重构后的系统。

**详细步骤**:
1. 使用 mimic_ex 数据集测试
2. 比较新旧实现的性能指标
3. 验证查询质量
4. 压力测试

**性能指标**:
- 实体提取速度
- 图构建时间
- 查询响应时间
- 内存使用

**验证方法**:
- 性能指标在可接受范围内
- 查询质量不下降

**依赖**: 任务 5.3

**预计产出**:
- 性能测试报告
- 问题修复（如果发现）

---

### 任务 6.2: 发布和部署

**描述**: 准备发布重构后的版本。

**详细步骤**:
1. 创建版本标签（如 v2.0.0）
2. 更新 CHANGELOG
3. 打包 Docker 镜像
4. 更新在线演示（如果有）
5. 发布到 GitHub

**验证方法**:
- Docker 镜像可以正常运行
- 所有文档链接有效

**依赖**: 任务 6.1

**预计产出**:
- 发布版本 v2.0.0
- 更新的 Docker 镜像

---

## 任务依赖关系图

```
1.1 (更新依赖) → 1.2 (测试环境)
                    ↓
2.1 (RAG 适配器) → 2.2 (实体提取) → 2.3 (主程序) → 2.4 (分块逻辑)
                                                        ↓
                                    3.1 (Neo4j 存储) → 3.2 (三层链接) → 3.3 (图合并)
                                                                            ↓
                                                        4.1 (查询功能) → 4.2 (领域优化)
                                                                            ↓
                                                        5.1 (清理) → 5.2 (文档) → 5.3 (测试)
                                                                                    ↓
                                                                    6.1 (验证) → 6.2 (发布)
```

## 可并行执行的任务

以下任务可以并行执行以加快进度：

- **阶段 3**: 任务 3.1 和任务 2.4 可以并行
- **阶段 5**: 任务 5.2 (文档) 可以在任务 5.1 完成后与 5.3 并行

## 总结

- **总任务数**: 18 个
- **预计阶段数**: 6 个
- **关键里程碑**:
  1. RAG 适配器完成（任务 2.1）
  2. 核心功能重构完成（任务 2.3）
  3. Neo4j 集成完成（任务 3.1）
  4. 查询功能完成（任务 4.2）
  5. 发布准备完成（任务 6.2）
