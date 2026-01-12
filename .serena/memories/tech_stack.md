# 技术栈

## 核心语言
- Python 3.10+

## 主要依赖

### LangGraph 和 LangChain 生态
- `langgraph>=0.6.0` - Agent 工作流编排
- `langchain>=0.3.0` - LLM 框架
- `langchain-community>=0.3.0` - 社区集成
- `langchain-openai>=0.2.0` - OpenAI 集成
- `langchain-anthropic>=0.3.0` - Anthropic 集成

### 数据库
- `neo4j>=5.0.0` - 图数据库
- `pymilvus>=2.4.0` - 向量数据库

### Web 框架
- `fastapi[standard]>=0.115.0` - Web 框架
- `uvicorn[standard]>=0.32.0` - ASGI 服务器
- `pydantic>=2.0.0` - 数据验证
- `pydantic-settings>=2.0.0` - 配置管理

### 多模态和视觉
- `transformers>=4.40.0` - Hugging Face Transformers
- `torch>=2.3.0` - PyTorch
- `qwen-vl-utils>=0.0.1` - Qwen 视觉语言模型工具

### RAG
- `lightrag-hku>=1.3.0` - 多模态 RAG
- `lightrag>=0.1.0b6` - LightRAG 核心库

### 开发工具
- `pytest>=8.0.0` - 测试框架
- `pytest-asyncio>=0.23.0` - 异步测试支持
- `pytest-cov>=5.0.0` - 覆盖率
- `python-dotenv>=1.0.0` - 环境变量
- `loguru>=0.7.0` - 日志
- `rich>=13.0.0` - 终端美化
- `typer>=0.12.0` - CLI 框架

### 其他
- `sentence-transformers>=2.7.0` - 句子嵌入
- `httpx>=0.27.0` - HTTP 客户端
- `tiktoken>=0.7.0` - Token 计数
