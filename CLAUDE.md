# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 开发命令

```bash
# 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000        # 开发启动
pytest                                           # 运行所有测试
black app/ tests/ && isort app/ tests/           # 格式化
black --check app/ tests/ --diff                 # 格式检查
flake8 app/ tests/ --statistics                  # lint
alembic upgrade head                             # 数据库迁移

# 前端
cd frontend && npm install
npm run dev                                      # 开发启动
npm run lint                                     # lint
npm run format                                   # 格式化（prettier）
npm run build                                    # 构建

# Docker
docker compose up -d --build                     # 全量部署
docker compose build --parallel                  # 并行构建
```

## 架构总览

企业知识库 RAG 问答系统。核心流程：上传 → 文本提取 → 分块 → embedding → pgvector → 检索 → LLM → SSE 流式推送到前端。

```
frontend/          Next.js 15 + Tailwind + Zustand
  app/             路由页面：chat/ agents/ admin/ documents/ login/
  components/      通用组件：ChatWindow, Sidebar, InputBox, MessageBubble 等
  lib/             api.ts（HTTP 客户端）+ store.ts（全局状态）

backend/           FastAPI + SQLAlchemy async + pgvector + Celery/Redis
  app/
    api/v1/        路由层：auth, chat, documents, admin, agents, mcp, webhooks 等
    services/      业务逻辑：chat（RAG流式）, retrieval（向量+BM25+RRF+LIKE）, reranker, rewriter, webhook, agent, audit
    pipeline/      文档处理：chunker（结构化分块）+ indexer（向量化写入）
    models/        ORM：User, Document, DocumentChunk, Conversation, Message 等
    core/          LLM(litellm), Celery, security(JWT+bcrypt), prompts, hooks, ratelimit, observability(Langfuse)
    connectors/    数据源抽象（local/notion/feishu）
    tasks/         Celery 异步任务（文档索引）
    schemas/       Pydantic 请求/响应模型
```

## 关键模式

### RAG 检索管道
`RetrievalService.search()` 五阶段：向量检索(cosine) → BM25 全文检索 → RRF 融合 → LIKE 子串补充 → 可选 FlagEmbedding 精排。同一文档最多取 2 个 chunk。

### 流式聊天
`/api/v1/chat/conversations/{id}/messages` POST → SSE 事件流。事件类型：`sources`（检索来源）→ `token`（逐 token）→ `structured`（结构化解析）→ `done`。

### 文档索引
上传后 Celery 异步处理：提取文本 → `DocumentChunker.chunk()`（Markdown 标题感知分块，512 token/64 overlap）→ embedding → 写入 `document_chunks` 表（含向量+tsvector）。embedding 失败时降级为纯全文搜索。

### 数据库
SQLAlchemy 异步，`get_db()` yield session（自动 commit/rollback）。所有模型用 UUID 主键。pgvector 存储向量，PG TSVECTOR 支持全文检索。

### 权限
JWT token 认证，两角色（admin/member）。文档级权限表 `document_permissions` + 数据源级 `source_permissions`。非管理员只能访问有权限的文档。

### 基础设施
- Celery worker 消费索引任务（Redis broker）
- Langfuse 可观测性（可选）
- 可扩展数据源 Connector 模式
- 事件驱动 Webhook 系统
- 可插拔 Hook 系统
- Rate limiting（聊天+上传）
