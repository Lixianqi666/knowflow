# KnowFlow 生产部署指南

## 环境要求

- Docker & Docker Compose v2+
- 4GB+ 可用内存（含 reranker 需 8GB+）
- Linux amd64 / arm64

## 快速部署

```bash
# 1. 克隆并配置
git clone <repo> && cd knowflow
cp .env.example .env
vim .env   # 填入 LLM_API_KEY 等关键配置

# 2. 启动
docker compose up -d --build

# 3. 验证
curl http://localhost/health
curl http://localhost/api/v1/auth/login
```

## 生产配置建议

### .env 关键项

```ini
# 必填 — 生产环境必须用强密钥
SECRET_KEY=<openssl rand -hex 32 生成的 64 位 hex>

# 必填 — LLM 配置
LLM_API_KEY=your_real_api_key
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Embedding
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_real_api_key

# 可选 — 精排（需手动安装 FlagEmbedding）
RERANKER_ENABLED=false

# 可选 — 可观测性
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

### 安全加固

1. **DB 密码**: `.env` 中修改 `DB_PASSWORD`，Docker Compose 会自动传递
2. **CORS**: 生产环境收紧 `CORS_ORIGINS=https://your-domain.com`
3. **JWT**: 设置 `SECRET_KEY`，否则重启后所有 token 失效
4. **反向代理**: nginx 已内置（端口 80/443），开发环境自动生成自签名证书

### 生产 SSL（Let's Encrypt）

```bash
# 1. 设置域名，先启动 HTTP 服务
docker compose up -d nginx backend frontend

# 2. 首次申请证书（替换 your-domain.com）
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d your-domain.com

# 3. 用生产 Compose 文件重启（启用 HTTPS）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 资源规划

| 服务      | CPU  | 内存   | 说明 |
|-----------|------|--------|------|
| postgres  | 2.0  | 2G     | pgvector 索引需要内存 |
| redis     | 0.5  | 256M   | |
| backend   | 1.0  | 512M   | |
| worker    | 2.0  | 1G     | 文档索引时 CPU 密集 |
| frontend  | 0.5  | 256M   | |
| nginx     | 0.25 | 128M   | |

资源限制已在 `docker-compose.yml` 中配置，`docker compose up` 直接生效。

### 可观测性

#### Prometheus 指标
后端暴露 `/metrics` 端点（Prometheus 文本格式），仅限 Docker 内部网络访问：

```yaml
# prometheus.yml 配置示例
scrape_configs:
  - job_name: knowflow
    metrics_path: /metrics
    static_configs:
      - targets:
          - backend:8000
```

#### 结构化日志
所有服务日志输出为 JSON 格式，每条日志包含 `request_id` 用于链路追踪：

```json
{"timestamp":"2026-05-08 12:00:00,000","level":"INFO","logger":"app.main","message":"startup","request_id":"-"}
```

#### Langfuse
LLM 调用追踪通过 Langfuse（可选），配置 `.env` 中的 `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY` 即可启用。

### 备份策略

```bash
# 数据库备份
docker exec knowflow-postgres-1 pg_dump -U knowflow knowflow > backup.sql

# 文件备份
tar czf uploads.tar.gz -C /path/to/uploads .
```

### 升级流程

```bash
git pull
docker compose build
docker compose up -d
# 迁移自动执行（alembic upgrade head）
```
