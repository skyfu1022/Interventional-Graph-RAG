# 常用命令

## 环境管理
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 导出环境
pip freeze > requirements.txt
```

## 测试命令
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_agents.py

# 运行带覆盖率的测试
pytest --cov=camel --cov=nano_graphrag --cov-report=html

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行异步测试
pytest -q tests/ -k "async"
```

## 代码质量检查
```bash
# 类型检查（严格模式）
mypy camel/ nano_graphrag/ --strict

# 代码格式化
ruff format camel/ nano_graphrag/ tests/

# Linting 检查
ruff check camel/ nano_graphrag/ tests/

# 自动修复 Linting 问题
ruff check --fix camel/ nano_graphrag/ tests/
```

## 运行应用
```bash
# 简单 RAG 推理
python run.py -simple True

# 图构建
python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -grained_chunk -ingraphmerge -construct_graph

# 模型推理
python run.py -dataset mimic_ex -data_path ./dataset/mimic_ex -inference
```

## Git 命令
```bash
# 查看状态
git status

# 添加更改
git add .

# 提交（遵循 Conventional Commits）
git commit -m "feat: 添加新功能"
git commit -m "fix: 修复 bug"
git commit -m "docs: 更新文档"

# 推送
git push origin feat/xxx
```

## Docker 命令
```bash
# 构建镜像
docker build -t medrag-post .

# 运行容器
docker run -it --rm --storage-opt size=10G -p 7860:7860 \
  -e OPENAI_API_KEY=your_key \
  -e NCBI_API_KEY=your_key \
  medrag-post
```
