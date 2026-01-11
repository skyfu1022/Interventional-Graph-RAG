# Medical Graph RAG - Docker 部署指南

本指南介绍如何使用 Docker 部署 Medical Graph RAG 系统。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [数据持久化](#数据持久化)
- [故障排查](#故障排查)
- [生产环境部署](#生产环境部署)

---

## 系统要求

### 硬件要求

- **CPU**: 4 核心及以上
- **内存**: 8GB 及以上（推荐 16GB）
- **磁盘**: 20GB 及以上可用空间
- **网络**: 稳定的网络连接（用于下载 Docker 镜像和依赖）

### 软件要求

- **Docker**: 20.10.0 及以上
- **Docker Compose**: 2.0.0 及以上

### 验证安装

```bash
# 验证 Docker 版本
docker --version

# 验证 Docker Compose 版本
docker-compose --version

# 验证 Docker 服务运行状态
docker ps
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/Medical-Graph-RAG.git
cd Medical-Graph-RAG
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填写必要的配置
# 至少需要配置以下变量：
# - OPENAI_API_KEY (必需)
# - NEO4J_PASSWORD (推荐修改默认值)
# - MINIO_ROOT_PASSWORD (推荐修改默认值)
nano .env
```

### 3. 构建并启动服务

```bash
# 构建镜像并启动所有服务（后台运行）
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

### 4. 验证服务

```bash
# 检查所有服务健康状态
docker-compose ps

# 访问 API 文档
open http://localhost:8000/docs

# 访问健康检查端点
curl http://localhost:8000/health
```

### 5. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止服务并删除数据卷（谨慎使用！）
docker-compose down -v
```

---

## 配置说明

### 环境变量

在 `.env` 文件中配置以下环境变量：

#### 必需配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |

#### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_BASE` | OpenAI API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 使用的语言模型 | `gpt-4o-mini` |
| `EMBEDDING_MODEL` | 使用的嵌入模型 | `text-embedding-3-large` |
| `NEO4J_PASSWORD` | Neo4j 数据库密码 | `password` |
| `NEO4J_URI` | Neo4j 连接 URI | `neo4j://localhost:7687` |
| `NEO4J_USERNAME` | Neo4j 用户名 | `neo4j` |
| `MILVUS_URI` | Milvus 连接 URI | `http://localhost:19530` |
| `MILVUS_TOKEN` | Milvus 认证令牌 | - |
| `RAG_WORKSPACE` | RAG 工作空间名称 | `medical` |
| `API_KEYS` | API 认证密钥（逗号分隔） | - |
| `RATE_LIMIT_ENABLED` | 是否启用速率限制 | `true` |
| `RATE_LIMIT_REQUESTS` | 时间窗口内最大请求数 | `100` |
| `RATE_LIMIT_WINDOW` | 时间窗口长度（秒） | `60` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| **应用** | 8000 | FastAPI 应用 |
| **Neo4j** | 7687 | Bolt 协议（应用连接） |
| | 7474 | HTTP 协议（Web UI） |
| | 7473 | HTTPS 协议（Web UI） |
| **Milvus** | 19530 | gRPC 端口 |
| | 9091 | 管理 REST API |
| **MinIO** | 9000 | API 端口 |
| | 9001 | Web 控制台 |
| **Nginx** | 80 | HTTP（可选） |
| | 443 | HTTPS（可选） |

### 数据卷

| 数据卷 | 说明 |
|--------|------|
| `medgraphrag_neo4j_data` | Neo4j 数据 |
| `medgraphrag_neo4j_logs` | Neo4j 日志 |
| `medgraphrag_etcd_data` | etcd 数据 |
| `medgraphrag_minio_data` | MinIO 数据 |
| `medgraphrag_milvus_data` | Milvus 数据 |
| `medgraphrag_rag_storage` | RAG 存储数据 |
| `medgraphrag_logs` | 应用日志 |
| `medgraphrag_output` | 输出文件 |

---

## 服务管理

### 查看服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看资源使用情况
docker stats

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f neo4j
docker-compose logs -f milvus
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app
docker-compose restart neo4j
docker-compose restart milvus
```

### 扩容服务

```bash
# 扩容应用服务（运行 3 个实例）
docker-compose up -d --scale app=3

# 注意：需要配置负载均衡器（如 Nginx）
```

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -a
```

---

## 数据持久化

### 备份数据

```bash
# 备份所有数据卷
docker run --rm -v medgraphrag_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_backup.tar.gz -C /data .
docker run --rm -v medgraphrag_milvus_data:/data -v $(pwd):/backup alpine tar czf /backup/milvus_backup.tar.gz -C /data .
docker run --rm -v medgraphrag_rag_storage:/data -v $(pwd):/backup alpine tar czf /backup/rag_backup.tar.gz -C /data .
```

### 恢复数据

```bash
# 恢复数据卷
docker run --rm -v medgraphrag_neo4j_data:/data -v $(pwd):/backup alpine tar xzf /backup/neo4j_backup.tar.gz -C /data
docker run --rm -v medgraphrag_milvus_data:/data -v $(pwd):/backup alpine tar xzf /backup/milvus_backup.tar.gz -C /data
docker run --rm -v medgraphrag_rag_storage:/data -v $(pwd):/backup alpine tar xzf /backup/rag_backup.tar.gz -C /data
```

### 清理数据

```bash
# 停止服务并删除数据卷（谨慎使用！）
docker-compose down -v

# 删除未使用的数据卷
docker volume prune
```

---

## 故障排查

### 服务无法启动

1. **检查日志**
   ```bash
   docker-compose logs app
   docker-compose logs neo4j
   docker-compose logs milvus
   ```

2. **检查端口占用**
   ```bash
   # 检查端口 8000 是否被占用
   lsof -i :8000

   # 检查端口 7687 是否被占用
   lsof -i :7687
   ```

3. **检查磁盘空间**
   ```bash
   df -h
   ```

### 内存不足

1. **增加 Docker 内存限制**
   - Docker Desktop: Settings > Resources > Memory
   - 设置为至少 8GB（推荐 16GB）

2. **减少并发 worker 数量**
   ```yaml
   # 在 docker-compose.yml 中修改
   command: ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
   ```

### Neo4j 连接失败

1. **检查 Neo4j 健康状态**
   ```bash
   docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"
   ```

2. **重置 Neo4j 密码**
   ```bash
   docker-compose exec neo4j cypher-shell -u neo4j -p old_password "CALL dbms.security.changePassword('new_password')"
   ```

### Milvus 连接失败

1. **检查 Milvus 日志**
   ```bash
   docker-compose logs milvus
   docker-compose logs etcd
   docker-compose logs minio
   ```

2. **重启 Milvus 服务**
   ```bash
   docker-compose restart etcd minio milvus
   ```

### API 响应缓慢

1. **检查资源使用情况**
   ```bash
   docker stats
   ```

2. **查看应用日志**
   ```bash
   docker-compose logs -f app
   ```

3. **增加 worker 数量**
   ```yaml
   # 在 docker-compose.yml 中修改
   command: ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
   ```

---

## 生产环境部署

### 启用 Nginx 反向代理

```bash
# 复制 Nginx 配置文件
cp nginx.conf.example nginx.conf

# 根据需要修改配置
nano nginx.conf

# 使用 nginx profile 启动
docker-compose --profile nginx up -d
```

### 配置 HTTPS

1. **获取 SSL 证书**
   ```bash
   # 使用 Let's Encrypt
   certbot certonly --standalone -d your-domain.com
   ```

2. **配置 Nginx**
   ```nginx
   server {
       listen 443 ssl http2;
       server_name your-domain.com;

       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       # ... 其他配置
   }
   ```

3. **重启 Nginx**
   ```bash
   docker-compose restart nginx
   ```

### 监控和日志

1. **查看实时日志**
   ```bash
   docker-compose logs -f
   ```

2. **导出日志**
   ```bash
   docker-compose logs > app.log
   ```

3. **集成监控系统**
   - Prometheus + Grafana
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - 云服务商监控 (AWS CloudWatch, Azure Monitor, Google Cloud Monitoring)

### 安全加固

1. **修改默认密码**
   ```bash
   # 在 .env 文件中修改
   NEO4J_PASSWORD=your_strong_password
   MINIO_ROOT_PASSWORD=your_strong_password
   ```

2. **启用 API 认证**
   ```bash
   # 在 .env 文件中配置
   API_KEYS=sk-key1,sk-key2,sk-key3
   ```

3. **配置防火墙**
   ```bash
   # 只允许必要的端口
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

4. **定期更新镜像**
   ```bash
   # 拉取最新镜像
   docker-compose pull

   # 重新构建
   docker-compose up -d --build
   ```

---

## 附录

### 相关链接

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [Neo4j Docker 文档](https://neo4j.com/docs/operations-manual/current/docker/)
- [Milvus Docker 文档](https://milvus.io/docs/install_standalone-docker.md)

### 常见问题

**Q: Docker 镜像构建失败怎么办？**

A: 检查网络连接，确保可以访问 Docker Hub 和 PyPI。如果在中国，可以配置镜像加速器。

**Q: 如何清理 Docker 资源？**

A: 使用 `docker system prune -a --volumes` 清理所有未使用的资源。

**Q: 数据存储在哪里？**

A: 数据存储在 Docker 数据卷中，可以使用 `docker volume ls` 查看。

**Q: 如何升级到新版本？**

A: 拉取最新代码，然后运行 `docker-compose up -d --build`。

---

**版本**: 1.0.0
**最后更新**: 2026-01-11
**维护者**: Medical Graph RAG Team
