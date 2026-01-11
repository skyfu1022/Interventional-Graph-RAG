# Build 命令使用指南

## 概述

`build` 命令用于从文件或目录构建医学知识图谱。支持单个文件处理、批量处理、节点合并等功能。

## 功能特性

- ✓ 支持从单个文件或目录批量构建知识图谱
- ✓ 支持指定图谱 ID 隔离不同的知识图谱
- ✓ 支持节点合并优化功能
- ✓ 使用 Rich 进度条显示构建进度
- ✓ 自动识别支持的文件格式
- ✓ 异步并发处理提高性能

## 基本用法

### 1. 从单个文件构建

```bash
# 处理单个文本文件
medgraph build document.txt

# 处理 PDF 文件
medgraph build medical_paper.pdf

# 处理 Markdown 文件
medgraph build README.md
```

### 2. 从目录批量构建

```bash
# 处理目录中的所有支持文件
medgraph build ./documents/

# 处理特定目录
medgraph build /path/to/medical/papers/
```

### 3. 指定图谱 ID

```bash
# 为不同的医学领域创建独立的图谱
medgraph build cardiology_papers.txt --graph-id cardiology
medgraph build neurology_papers.txt --graph-id neurology
medgraph build diabetes_guidelines.txt --graph-id endocrinology
```

### 4. 启用节点合并

```bash
# 自动合并相似实体
medgraph build documents/ --merge

# 指定合并阈值（0.0-1.0，默认 0.7）
medgraph build documents/ --merge --merge-threshold 0.8
```

### 5. 高级选项

```bash
# 设置并发数（默认 5）
medgraph build documents/ --max-concurrency 10

# 指定工作空间
medgraph build documents/ --workspace my_medical_db

# 显示详细输出
medgraph build documents/ --verbose
```

## 支持的文件格式

- **文本文件**: `.txt`, `.md`
- **文档文件**: `.pdf`, `.docx`, `.doc`
- **数据文件**: `.json`, `.csv`
- **网页文件**: `.html`, `.htm`

## 命令参数

### 位置参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | Path | 文件或目录路径（必需） |

### 可选参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--graph-id` | `-g` | str | `default` | 指定图谱 ID |
| `--merge` | `-m` | bool | `False` | 启用节点合并 |
| `--merge-threshold` | `-t` | float | `0.7` | 节点合并相似度阈值 (0.0-1.0) |
| `--max-concurrency` | `-c` | int | `5` | 最大并发文件处理数 (1-20) |
| `--workspace` | `-w` | str | `medical` | 工作空间名称 |
| `--verbose` | `-v` | bool | `False` | 显示详细输出 |

## 使用示例

### 示例 1: 构建糖尿病知识图谱

```bash
# 从单个指南文件构建
medgraph build diabetes_guideline.txt --graph-id diabetes

# 从整个目录构建
medgraph build ./diabetes_documents/ --graph-id diabetes --verbose
```

### 示例 2: 构建心脏病学知识图谱并启用合并

```bash
medgraph build \
  ./cardiology_papers/ \
  --graph-id cardiology \
  --merge \
  --merge-threshold 0.8 \
  --max-concurrency 10
```

### 示例 3: 快速原型测试

```bash
# 使用单个小文件快速测试
echo "糖尿病是一种慢性代谢性疾病，特征是高血糖。" > test.txt
medgraph build test.txt --graph-id test --verbose
```

## 输出说明

### 进度条

构建过程中会显示进度条：

```
→ 构建图谱 'medical' ━━━━━━━━━━━━━━━━━━━━ 3/10 00:02:30
```

进度条包含：
- 当前任务描述
- 可视化进度条
- 完成数量/总数量
- 剩余时间

### 构建摘要

构建完成后会显示摘要表格：

```
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ 指标           ┃ 数值        ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 图谱 ID        │ medical     │
│ 总文件数       │ 10          │
│ 成功           │ 9           │
│ 失败           │ 1           │
│ 节点合并       │ 未启用      │
└────────────────┴────────────┘
```

### 状态消息

- ✓ **绿色**: 操作成功
- ⚠ **黄色**: 警告或部分完成
- ✗ **红色**: 错误或失败

## 错误处理

### 路径不存在

```bash
$ medgraph build nonexistent.txt

错误: 路径不存在: nonexistent.txt
```

### 不支持的文件格式

```bash
$ medgraph build document.xyz

警告: 文件格式 '.xyz' 可能不支持，但将尝试处理。
```

### 目录为空

```bash
$ medgraph build empty_dir/

错误: 在目录 'empty_dir' 中未找到支持的文件。
支持的格式: .csv, .doc, .docx, .html, .htm, .json, .md, .pdf, .txt
```

## SDK 集成

`build` 命令使用以下 SDK 方法：

```python
from src.sdk import MedGraphClient

async def main():
    async with MedGraphClient(workspace="medical") as client:
        # 单个文件
        await client.ingest_document("document.txt")

        # 批量文件
        await client.ingest_batch(
            file_paths=["doc1.txt", "doc2.txt"],
            max_concurrency=5
        )

        # 获取图谱信息
        graph_info = await client.get_graph("graph_id")

        # 节点合并
        await client._graph_service.merge_graph_nodes(
            graph_id="graph_id",
            source_entities=["entity1", "entity2"],
            target_entity="merged_entity",
            threshold=0.7
        )
```

## 最佳实践

1. **目录结构**: 将相关文档放在同一目录中便于批量处理
2. **图谱隔离**: 为不同的医学领域使用不同的 `--graph-id`
3. **并发控制**: 根据系统资源调整 `--max-concurrency`
4. **节点合并**: 对于大型知识图谱，建议启用 `--merge` 减少冗余
5. **逐步构建**: 先用小文件测试，确认配置正确后再批量处理

## 故障排除

### 问题: 构建缓慢

**解决方案**: 增加 `--max-concurrency` 值

```bash
medgraph build documents/ --max-concurrency 10
```

### 问题: 内存不足

**解决方案**: 减少 `--max-concurrency` 值

```bash
medgraph build documents/ --max-concurrency 2
```

### 问题: 实体过多导致查询缓慢

**解决方案**: 启用节点合并

```bash
medgraph build documents/ --merge --merge-threshold 0.8
```

### 问题: 需要查看详细日志

**解决方案**: 使用 `--verbose` 参数

```bash
medgraph build documents/ --verbose
```

## 相关命令

- `medgraph query`: 查询知识图谱
- `medgraph ingest`: 摄入单个文档
- `medgraph export`: 导出知识图谱

## 技术细节

### 异步处理

`build` 命令使用 Python 的 `asyncio` 进行异步处理，支持并发文件摄入。

### 进度显示

使用 Rich 库的 `Progress` 组件实现实时进度显示。

### 错误处理

- 单个文件失败不会中断整个流程
- 所有错误都会在摘要中报告
- 使用 `--verbose` 查看详细错误信息

## 版本信息

- 实现版本: 0.2.0
- SDK 版本: 0.2.0
- Python 要求: 3.10+
