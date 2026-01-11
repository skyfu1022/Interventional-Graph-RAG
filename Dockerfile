# Medical Graph RAG - Docker 镜像
#
# 多阶段构建，优化镜像大小和构建效率
# 基于 Python 3.10 官方镜像
#
# 作者: Medical Graph RAG Team
# 版本: 1.0.0
# 更新时间: 2026-01-11

# ============================================
# 阶段 1: 基础镜像 - 构建依赖
# ============================================
FROM python:3.10-slim as builder

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制依赖文件
COPY requirements.txt .

# 升级 pip 并安装 Python 依赖
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================
# 阶段 2: 运行时镜像 - 最小化镜像
# ============================================
FROM python:3.10-slim

# 设置标签
LABEL maintainer="Medical Graph RAG Team <team@medgraphrag.com>" \
      version="1.0.0" \
      description="Medical Graph RAG - 医学知识图谱 RAG 系统"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    curl \
    ca-certificates \
    # 图像处理依赖（用于多模态查询）
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # 文档处理依赖
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 创建应用目录
WORKDIR /app

# 创建非 root 用户（安全最佳实践）
RUN useradd -m -u 1000 -s /bin/bash medgraphrag && \
    chown -R medgraphrag:medgraphrag /app

# 复制应用代码
COPY --chown=medgraphrag:medgraphrag . .

# 创建必要的目录
RUN mkdir -p /app/data/rag_storage /app/logs /app/output && \
    chown -R medgraphrag:medgraphrag /app/data /app/logs /app/output

# 切换到非 root 用户
USER medgraphrag

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
# 8000: FastAPI 应用
EXPOSE 8000

# 设置默认命令
# 使用 uvicorn 启动 FastAPI 应用
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
