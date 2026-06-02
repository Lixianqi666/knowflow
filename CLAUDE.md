# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

KnowFlow 是企业知识库 RAG 问答系统。支持文档上传（TXT/Markdown/PDF/DOCX/XLSX）、向量检索+BM25+RRF 混合检索、LLM 流式生成、Agent 对话、管理后台。

## 开发命令

### Docker 部署（首选）

```bash
# 首次部署
cp .env.example .env   # 填入 LLM_API_KEY 等
docker compose up -d --build

# 重建后端
docker compose build backend worker && docker compose up -d backend worker

# 重建前端
docker compose build frontend && docker compose up -d frontend

# 重启 nginx（后端容器重建后必须重启，因 DNS 缓存）
docker compose restart nginx

# 查看日志
docker compose logs -f backend
docker compose logs -f worker
```

### 后端开发（Python 3.12）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "描述"
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 测试

```bash
# 后端（pytest，asyncio_mode=auto，需要 PostgreSQL 运行）
cd backend && pytest
cd backend && pytest tests/test_auth.py              # 单文件
cd backend && pytest -k "test_login"                  # 按名称过滤

# 前端（vitest，jsdom 环境）
cd frontend && npm test
cd frontend && npm run test:watch
```

### 代码质量

```bash
cd backend && black . && isort . && flake8   # black line-length=100
cd frontend && npm run lint
cd frontend && npm run format                 # prettier 自动格式化
```

## 架构

### 系统拓扑

```
nginx (SSL) → frontend (:3000) + backend (:8000)
backend → PostgreSQL+pgvector (:5432) + Redis (:6379)
worker  → Celery（异步文档索引）→ 同上 PostgreSQL + Redis
```

### 后端结构（backend/app/）

- `api/v1/` — 15 个路由模块（auth, chat, documents, knowledge_bases, agents, admin, audit, feedback, mcp, plugins, prompt_templates, rag_debug, rag_evals, rag_quality, webhooks），统一挂载在 `/api/v1`
- `models/` — SQLAlchemy 模型，全部继承自 `database.Base`
- `services/` — 业务逻辑（chat/retrieval/reranker/rewriter/auth/audit/agent/rag_config/rag_eval/rag_quality/webhook）
- `core/` — 基础设施（celery, cache, security, ratelimit, llm, metrics, logging）
- `agent_runtime/` — LangGraph agent 系统（runtime, graph, nodes, tools, memory）
- `pipeline/` — 文档摄入（chunker 分块 + indexer 索引）
- `tasks/` — Celery 任务（indexing 文档索引）
- `schemas/` — Pydantic 请求/响应模型
- `plugins/` — 插件系统（`core/plugins.py` 加载，内置 `log_plugin`）
- `alembic/` — 数据库迁移版本

关键模型关系：User → Conversation → Message；Agent ↔ KnowledgeBase（多对多通过 agent_knowledge_bases）；Document → DataSource + KnowledgeBase；DocumentChunk（pgvector embedding + tsvector 全文索引）

### 前端结构（frontend/）

- Next.js 15 App Router，`output: 'standalone'`
- `app/page.tsx` — 根路径，根据 token 跳转 /chat 或 /login
- `app/login/` — 登录/注册页（独立布局，无侧边栏）
- `app/(main)/` — 主布局路由组（含 Sidebar），包含 chat/documents/agents/admin
- `components/` — 全部 client components（Sidebar, ChatWindow, InputBox, MessageBubble, DocList, SourceViewer, UploadDialog, FormModal, ConfirmDialog, Toast）
- `lib/store.ts` — Zustand 5 单 store，管理所有状态（auth, conversations, messages, agents, admin, kbs）。消息按对话 ID 缓存（LRU 50 条）
- `lib/api.ts` — ApiClient 单例，401 时自动 logout，`streamChat` 返回 ReadableStream

### 认证流程

- 后端：JWT（jose），`get_current_user` 依赖注入
- 前端：无中间件，客户端 localStorage 存储 token/user，`MainLayout` hydrate 后检查 token

### RAG 检索管线

文档上传 → Celery 异步处理 → 文本提取 → 分块（512 token / 64 overlap，Markdown 感知） → Embedding → pgvector 存储
查询 → Query Rewriter（可选 LLM 改写） → Vector 检索 + BM25（tsvector） → RRF 融合 → 可选 Reranker → LLM 流式生成

## 部署规范

遵循严格的部署流程：**本地开发调试 → 提交代码 → Docker 构建并部署到服务器**。所有环境（包括依赖服务）都通过 Docker Compose 运行。

生产环境必须在 `.env` 中设置 `SECRET_KEY`（`openssl rand -hex 32`）和 `ENVIRONMENT=production`，否则后端拒绝启动。

## 关键配置项

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL async URL（asyncpg） |
| `REDIS_URL` | Redis 连接 |
| `SECRET_KEY` | JWT 签名密钥 |
| `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | LLM 配置 |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | Embedding 配置 |
| `EMBEDDING_DIM` | Embedding 向量维度（默认 1024） |
| `RERANKER_ENABLED` | 是否启用本地 Reranker |
| `NEXT_PUBLIC_API_URL` | 前端 API 地址（Docker 内为 /api/v1） |
