# KnowFlow

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
                           ┌─────────────┐
                           │   nginx     │
                           │  :80 / :443 │
                           └──┬──────┬───┘
                              │      │
                    /api/*    │      │   /*
                              ▼      ▼
                    ┌────────┐  ┌────────┐
                    │backend │  │frontend│
                    │ :8000  │  │ :3000  │
                    └───┬────┘  └────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌──────────┐
    │PostgreSQL│   │  Redis  │   │  Worker  │
    │+pgvector │   │         │   │ Celery   │
    │  :5432   │   │  :6379  │   │          │
    └─────────┘   └─────────┘   └──────────┘
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

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
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
# 后端测试
cd backend && TESTING=1 pytest tests/ -v

# 前端测试
cd frontend && npm test
```

## 文档

- [用户手册](./docs/USER_GUIDE.md) — 功能使用说明
- [部署指南](./DEPLOY.md) — 生产环境部署、SSL、备份、升级
