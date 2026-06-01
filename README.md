# KnowFlow

> 当前版本：v0.1.0 · [CHANGELOG](./CHANGELOG.md) · [版本策略](./docs/versioning.md)

企业知识库 RAG 问答系统。上传文档，基于检索增强生成（RAG）进行流式问答，支持多知识库、多角色权限、Agent 对话、管理后台。

## 功能特性

- **RAG 问答** — 向量检索 + BM25 全文检索 + RRF 融合 + 可选精排（FlagEmbedding），LLM 流式生成
- **多知识库** — 按业务场景隔离文档和对话
- **文档管理** — 支持 TXT / Markdown / PDF / DOCX / XLSX，拖拽上传，批量操作
- **Agent 对话** — 可配置系统提示词、关联知识库的独立对话 Agent
- **管理后台** — 用户管理、文档权限、数据统计、审计日志、Prompt 模板
- **可观测性** — Prometheus 指标（`/metrics`）、结构化 JSON 日志（含 request_id）、Langfuse LLM 追踪
- **生产就绪** — nginx 反向代理 + SSL、Docker 资源限制、CI 测试流水线

## 系统架构

```
                        ┌─────────────────────────┐
                        │          nginx          │
                        │        :80 / :443       │
                        └────────────┬────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
           ┌──────────┐       ┌──────────────┐     ┌──────────┐
           │  /api/*  │       │     /*       │     │ /health  │
           └────┬─────┘       └──────┬───────┘     └────┬─────┘
                │                    │                   │
                ▼                    ▼                   ▼
         ┌─────────────┐      ┌─────────────┐     ┌───────────┐
         │   backend   │      │  frontend   │     │  backend  │
         │    :8000    │      │    :3000    │     │   :8000   │
         └──────┬──────┘      └─────────────┘     └───────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌───────┐  ┌───────┐  ┌──────────┐
│Postgre│  │ Redis │  │  Worker  │
│SQL    │  │       │  │ Celery   │
│+pgvec │  │ :6379 │  │          │
│ :5432 │  └───────┘  └──────────┘
└───────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 15 + Tailwind CSS + Zustand |
| 后端 | Python FastAPI + SQLAlchemy async + Alembic |
| 向量库 | PostgreSQL + pgvector |
| 缓存 / 队列 | Redis（缓存 + Celery broker） |
| 任务队列 | Celery（文档索引异步处理） |
| LLM | litellm 统一接口（SiliconFlow / OpenAI / DeepSeek） |
| 反向代理 | nginx（SSL 终止、负载均衡） |
| 可观测性 | Prometheus + 结构化 JSON 日志 + Langfuse（可选） |

## 快速开始

### Docker 一键部署

```bash
git clone https://github.com/Lixianqi666/knowflow.git
cd knowflow

# 配置环境变量
cp .env.example .env
vim .env   # 填入 LLM_API_KEY 等

# 启动
docker compose up -d --build

# 访问
# https://localhost（自签名证书，浏览器需确认安全例外）
```

### Docker 本地开发

本项目本地开发、测试、构建统一通过 Docker 执行，不要在宿主机安装依赖。

```bash
# 首次启动（构建并启动所有服务）
docker compose up -d --build

# 查看日志
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# 重建后端（代码变更后）
docker compose build backend worker && docker compose up -d backend worker

# 重建前端
docker compose build frontend && docker compose up -d frontend

# 停止
docker compose down
```

## 核心流程

### 文档索引

```
上传 → 文本提取（pdfplumber / python-docx / openpyxl）
     → 分块（Markdown 标题感知，512 token / 64 overlap）
     → Embedding（litellm → pgvector）
     → 写入 document_chunks 表（向量 + tsvector）
```

### RAG 检索

```
提问 → Embedding
     → pgvector cosine 向量检索
     → BM25 全文检索
     → RRF 融合排序
     → LIKE 子串补充
     → 可选 FlagEmbedding 精排
     → Prompt 组装 → LLM 流式生成 → SSE 推送
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_MODEL` | 是 | 模型名，如 `openai/deepseek-ai/DeepSeek-V3` |
| `LLM_BASE_URL` | 否 | API 地址，如 `https://api.siliconflow.cn/v1` |
| `EMBEDDING_MODEL` | 是 | Embedding 模型，如 `BAAI/bge-m3` |
| `EMBEDDING_API_KEY` | 否 | 默认同 `LLM_API_KEY` |
| `EMBEDDING_BASE_URL` | 否 | 默认同 `LLM_BASE_URL` |
| `SECRET_KEY` | 是 | JWT 签名密钥（`openssl rand -hex 32`） |
| `DB_PASSWORD` | 否 | 数据库密码，默认 `knowflow` |
| `RERANKER_ENABLED` | 否 | 启用精排，需安装 FlagEmbedding |
| `LANGFUSE_PUBLIC_KEY` | 否 | Langfuse 可观测性 |

完整变量见 [.env.example](./.env.example)。

## 运维能力

### nginx 反向代理

所有服务通过 nginx 统一入口（80/443），后端和前端不再直接暴露端口：

- `/api/*` → backend:8000
- `/*` → frontend:3000
- `/health` → backend 健康检查
- `/metrics` → 仅限 Docker 内部网络访问

开发环境自动生成自签名证书，生产环境使用 Let's Encrypt（详见 [DEPLOY.md](./DEPLOY.md)）。

### Prometheus 指标

后端暴露 `/metrics` 端点，采集以下指标：

- `http_requests_total` — 请求计数（按 method/endpoint/status）
- `http_request_duration_seconds` — 请求延迟分布
- `documents_indexed_total` — 已索引文档数
- `llm_requests_total` — LLM 调用计数

### 结构化日志

所有服务输出 JSON 格式日志，每条日志包含 `request_id` 用于链路追踪：

```json
{"timestamp":"2026-05-08 12:00:00,000","level":"INFO","logger":"app.main","message":"startup","request_id":"-"}
```

### Docker 资源限制

所有服务已配置 CPU 和内存限制，`docker compose up` 直接生效：

| 服务 | CPU | 内存 |
|------|-----|------|
| postgres | 2.0 | 2G |
| redis | 0.5 | 256M |
| backend | 1.0 | 512M |
| worker | 2.0 | 1G |
| frontend | 0.5 | 256M |
| nginx | 0.25 | 128M |

## 目录结构

```
knowflow/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/           # REST 路由
│   │   ├── core/             # LLM、Celery、安全、日志、指标
│   │   ├── models/           # SQLAlchemy ORM
│   │   ├── pipeline/         # 文档处理（分块 + 索引）
│   │   ├── services/         # 业务逻辑（检索、聊天、Agent）
│   │   └── tasks/            # Celery 异步任务
│   ├── tests/                # pytest 测试
│   └── requirements.txt
├── frontend/                 # Next.js 前端
│   ├── app/                  # 路由页面
│   ├── components/           # UI 组件
│   └── lib/                  # API 客户端 + 状态管理
├── nginx/                    # nginx 配置
│   ├── nginx.conf
│   ├── conf.d/default.conf   # 路由 + SSL
│   └── entrypoint.sh         # 自签名证书生成
├── docker-compose.yml        # 开发环境
├── docker-compose.prod.yml   # 生产环境（certbot）
└── DEPLOY.md                 # 部署指南
```

## 测试

```bash
# 一键验证（推荐）
sh scripts/verify-docker.sh

# 后端测试
docker compose build backend
docker compose up -d postgres redis
docker compose run --rm backend sh -c "TESTING=1 pytest tests/ -v"
docker compose down

# 前端测试
docker build --target test -t knowflow-frontend-test ./frontend
docker run --rm knowflow-frontend-test sh -c "npm run test"

# 前端构建
docker compose build frontend
```

## 私有化交付

- [私有化部署指南](docs/private_deployment.md) — 服务器配置、环境变量、首次部署
- [升级与回滚](docs/upgrade_rollback.md) — 升级流程、回滚步骤、版本记录
- [备份与恢复](docs/backup_restore.md) — 数据库备份、文件备份、恢复演练
- [发布检查清单](docs/release_checklist.md) — 发布前检查、发布步骤、回滚预案
- [客户交付包](docs/delivery_package.md) — 交付包结构、必备文件、验收清单
- [版本策略](docs/versioning.md) — SemVer 规则、migration 兼容性、镜像 tag
- [UAT 验收清单](docs/uat_checklist.md) — 功能验收项、操作步骤、预期结果
- [生产就绪检查](docs/production_readiness.md) — 安全/权限/审计/备份/监控检查

## 版本与发布

```bash
# 查看版本信息
bash scripts/print-version.sh

# 构建发布清单
bash scripts/build-release-manifest.sh
# 输出：dist/release-manifest.json

# UAT 交付材料检查
bash scripts/uat-smoke.sh
```

- [CHANGELOG.md](./CHANGELOG.md) — 版本变更记录
- [Release Notes 模板](./RELEASE_NOTES_TEMPLATE.md) — 发布说明模板
