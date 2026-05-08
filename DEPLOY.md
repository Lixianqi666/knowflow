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
curl http://localhost:8000/health
curl http://localhost:3000
```

## 生产配置建议

### .env 关键项

```ini
# 必填 — 生产环境必须用强密钥
SECRET_KEY=<openssl rand -hex 32 生成的 64 位 hex>

# 必填 — LLM 配置
LLM_API_KEY=your_real_api_key
LLM_MODEL=openai/gpt-4o-mini       # 或 deepseek-v4-flash 等
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
4. **反向代理**: 建议前置 nginx/Caddy，配置 HTTPS 和 WAF

```nginx
# nginx 配置示例
server {
    listen 443 ssl;
    server_name knowflow.example.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
    }
}
```

### 资源规划

| 服务      | 最低内存 | 建议内存 | 说明 |
|-----------|---------|---------|------|
| postgres  | 512MB   | 2GB     | pgvector 索引需要内存 |
| redis     | 128MB   | 256MB   | |
| backend   | 256MB   | 512MB   | |
| worker    | 256MB   | 512MB   | 文档索引时 CPU 密集 |
| frontend  | 128MB   | 256MB   | |
| reranker  | 2GB     | 4GB     | 可选，仅装 FlagEmbedding 时需要 |

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
