# 常用命令

## 环境设置
```bash
# 创建并激活 conda 环境
conda env create -f medgraphrag.yml
conda activate medgraphrag

# 或使用 GPU 版本环境
conda env create -f medgraphrag_gpu.yml
```

## 配置环境变量
```bash
# OpenAI API（必需）
export OPENAI_API_KEY=your_key

# Neo4j 数据库（必需，完整流程）
export NEO4J_URL=your_neo4j_url
export NEO4J_USERNAME=your_username
export NEO4J_PASSWORD=your_password

# NCBI API（可选，用于 PubMed 搜索）
export NCBI_API_KEY=your_key
```

## 快速开始（简单示例）
```bash
# 使用预置示例运行简单的 Graph RAG
python run.py -simple True
```

## 构建图谱
```bash
# 使用 mimic_ex 数据集构建图谱
python run.py \
  -dataset mimic_ex \
  -data_path ./dataset/mimic_ex \
  -grained_chunk \
  -ingraphmerge \
  -construct_graph

# 启用三层架构图谱链接
python run.py \
  -dataset mimic_ex \
  -data_path ./dataset/mimic_ex \
  -grained_chunk \
  -trinity \
  -trinity_gid1 <graph_id_1> \
  -trinity_gid2 <graph_id_2> \
  -construct_graph

# 启用跨图谱合并
python run.py \
  -dataset mimic_ex \
  -data_path ./dataset/mimic_ex \
  -grained_chunk \
  -ingraphmerge \
  -crossgraphmerge \
  -construct_graph
```

## 模型推理
```bash
# 1. 将问题写入 prompt.txt
echo "你的问题" > ./prompt.txt

# 2. 运行推理
python run.py \
  -dataset mimic_ex \
  -data_path ./dataset/mimic_ex \
  -inference
```

## Docker 演示
```bash
docker run -it --rm --storage-opt size=10G -p 7860:7860 \
  -e OPENAI_API_KEY=your_key \
  -e NCBI_API_KEY=your_key \
  medrag-post
```

## Git 命令
```bash
# 查看状态
git status

# 提交更改
git add .
git commit -m "描述更改"
git push

# 使用 git_push.sh 脚本
./git_push.sh
```

## 系统工具 (macOS)
```bash
# 列出文件
ls -la

# 查找文件
find . -name "*.py"

# 搜索代码内容
grep -r "keyword" .

# 查看进程
ps aux | grep python

# 终止进程
kill <pid>
```
