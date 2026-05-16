# KnowFlow Code Wiki

> 企业知识库 RAG 问答系统 — 完整代码结构与架构文档

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [技术栈](#3-技术栈)
4. [目录结构](#4-目录结构)
5. [模块详解](#5-模块详解)
   - [5.1 后端核心模块](#51-后端核心模块)
   - [5.2 API 路由层](#52-api-路由层)
   - [5.3 数据模型层](#53-数据模型层)
   - [5.4 业务服务层](#54-业务服务层)
   - [5.5 管道与异步任务](#55-管道与异步任务)
   - [5.6 前端架构](#56-前端架构)
6. [核心流程](#6-核心流程)
   - [6.1 RAG 检索流程](#61-rag-检索流程)
   - [6.2 文档索引流程](#62-文档索引流程)
   - [6.3 认证流程](#63-认证流程)
7. [依赖关系](#7-依赖关系)
8. [数据库设计](#8-数据库设计)
9. [运行与部署](#9-运行与部署)
10. [测试](#10-测试)
11. [配置说明](#11-配置说明)

---

## 1. 项目概述

**KnowFlow** 是一套企业级的知识库 RAG（Retrieval-Augmented Generation）问答系统。用户可上传各类文档（TXT / Markdown / PDF / DOCX / XLSX），系统自动进行文本提取、分块、向量化并建立索引；随后通过向量检索 + BM25 全文检索 + RRF 融合 + 可选精排的多路召回策略，结合 LLM 流式生成，实现高质量的知识问答。

### 核心能力

| 能力 | 说明 |
|------|------|
| RAG 问答 | 向量检索 + BM25 全文检索 + RRF 融合 + 可选精排，LLM 流式生成 |
| 多知识库 | 按业务场景隔离文档和对话 |
| 文档管理 | 多格式支持、拖拽上传、批量操作 |
| Agent 对话 | 可配置系统提示词、关联知识库的独立对话 Agent |
| 管理后台 | 用户管理、文档权限、数据统计、审计日志、Prompt 模板 |
| 可观测性 | Prometheus 指标、结构化 JSON 日志、Langfuse LLM 追踪 |
| 生产就绪 | nginx 反代 + SSL、Docker 资源限制、CI 测试流水线 |

---

## 2. 系统架构

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

### 组件职责

| 组件 | 端口 | 职责 |
|------|------|------|
| **nginx** | 80/443 | 统一入口、SSL 终止、路由分发 |
| **frontend** | 3000 | Next.js 前端，提供用户界面 |
| **backend** | 8000 | FastAPI 后端，REST API + SSE 流式响应 |
| **PostgreSQL + pgvector** | 5432 | 关系型数据存储 + 向量索引 |
| **Redis** | 6379 | 缓存 + Celery broker + 限流 |
| **Worker (Celery)** | — | 异步文档索引任务 |

---

## 3. 技术栈

### 后端

| 分类 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL + pgvector + TSVECTOR |
| 迁移 | Alembic |
| 缓存/队列 | Redis + Celery |
| LLM | litellm (兼容 SiliconFlow / OpenAI / DeepSeek) |
| Embedding | litellm 统一接口 |
| 分词 | jieba |
| 文档解析 | pdfplumber, python-docx, openpyxl |
| 认证 | python-jose (JWT) + passlib (bcrypt) |
| 可观测性 | prometheus-client, Langfuse |
| 测试 | pytest + pytest-asyncio + httpx |

### 前端

| 分类 | 技术 |
|------|------|
| 框架 | Next.js 15 + React 19 |
| 样式 | Tailwind CSS |
| 状态管理 | Zustand |
| Markdown 渲染 | react-markdown |
| 图标 | lucide-react |
| 测试 | Vitest + Testing Library |
| 构建 | TypeScript 5.6 |
| 格式化 | Prettier + ESLint |

---

## 4. 目录结构

```
knowflow/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/                   # REST 路由
│   │   │   ├── admin.py              # 管理员 API
│   │   │   ├── agents.py             # Agent 管理 API
│   │   │   ├── audit.py              # 审计日志 API
│   │   │   ├── auth.py               # 认证 API
│   │   │   ├── chat.py               # 聊天 API
│   │   │   ├── documents.py          # 文档 API
│   │   │   ├── feedback.py           # 反馈 API
│   │   │   ├── knowledge_bases.py    # 知识库 API
│   │   │   ├── mcp.py                # MCP 协议 API
│   │   │   ├── plugins.py            # 插件 API
│   │   │   ├── prompt_templates.py   # Prompt 模板 API
│   │   │   └── webhooks.py           # Webhook API
│   │   ├── connectors/               # 数据源连接器
│   │   │   ├── base.py               # 连接器基类
│   │   │   └── local.py              # 本地文件连接器
│   │   ├── core/                     # 核心基础设施
│   │   │   ├── celery.py             # Celery 配置
│   │   │   ├── deps.py               # 依赖注入工具
│   │   │   ├── hooks.py              # 事件钩子系统
│   │   │   ├── llm.py                # LLM / Embedding 服务
│   │   │   ├── logging.py            # 结构化日志
│   │   │   ├── metrics.py            # Prometheus 指标
│   │   │   ├── observability.py      # Langfuse 集成
│   │   │   ├── plugins.py            # 插件系统
│   │   │   ├── prompts.py            # Prompt 模板构建
│   │   │   ├── ratelimit.py          # 速率限制
│   │   │   └── security.py           # JWT 认证、密码哈希
│   │   ├── models/                   # SQLAlchemy ORM 模型
│   │   │   ├── agent.py              # Agent 模型
│   │   │   ├── agent_session.py      # Agent 会话模型
│   │   │   ├── audit_log.py          # 审计日志模型
│   │   │   ├── conversation.py       # 对话/消息模型
│   │   │   ├── document.py           # 文档/数据源/分块模型
│   │   │   ├── feedback.py           # 反馈模型
│   │   │   ├── knowledge_base.py     # 知识库模型
│   │   │   ├── permission.py         # 权限模型
│   │   │   ├── prompt_template.py    # Prompt 模板模型
│   │   │   ├── user.py               # 用户模型
│   │   │   └── webhook.py            # Webhook 模型
│   │   ├── mq/                       # 消息队列
│   │   │   ├── connection.py         # 连接管理
│   │   │   ├── consumer.py           # 消费者
│   │   │   ├── idempotency.py        # 幂等性控制
│   │   │   └── protocol.py           # 协议定义
│   │   ├── pipeline/                 # 文档处理管道
│   │   │   ├── chunker.py            # 结构感知分块
│   │   │   └── indexer.py            # 索引构建
│   │   ├── plugins/                  # 插件实现
│   │   │   └── log_plugin.py         # 日志插件
│   │   ├── schemas/                  # Pydantic 请求/响应模型
│   │   │   ├── chat.py               # 聊天 Schema
│   │   │   ├── document.py           # 文档 Schema
│   │   │   └── user.py               # 用户 Schema
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── agent.py              # Agent 服务
│   │   │   ├── audit.py              # 审计服务
│   │   │   ├── auth.py               # 认证服务
│   │   │   ├── chat.py               # 聊天/流式生成服务
│   │   │   ├── reranker.py           # 精排服务
│   │   │   ├── retrieval.py          # 检索服务
│   │   │   ├── rewriter.py           # 查询改写服务
│   │   │   └── webhook.py            # Webhook 分发服务
│   │   ├── tasks/                    # Celery 异步任务
│   │   │   └── indexing.py           # 文档索引任务
│   │   ├── config.py                 # 配置管理 (pydantic-settings)
│   │   ├── database.py               # 数据库连接 + 会话
│   │   ├── main.py                   # FastAPI 应用入口
│   │   └── mcp_server.py             # MCP 服务器
│   ├── alembic/                      # 数据库迁移
│   ├── scripts/                      # 辅助脚本
│   ├── tests/                        # pytest 测试
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                         # Next.js 前端
│   ├── app/                          # 路由页面
│   │   ├── admin/page.tsx            # 管理后台
│   │   ├── agents/                   # Agent 页面
│   │   ├── chat/                     # 聊天页面
│   │   ├── documents/page.tsx        # 文档管理
│   │   ├── login/page.tsx            # 登录
│   │   ├── layout.tsx                # 根布局
│   │   ├── page.tsx                  # 首页
│   │   └── not-found.tsx             # 404 页面
│   ├── components/                   # UI 组件
│   │   ├── ChatWindow.tsx            # 聊天窗口
│   │   ├── InputBox.tsx              # 输入框
│   │   ├── MessageBubble.tsx         # 消息气泡
│   │   ├── Sidebar.tsx               # 侧边栏
│   │   ├── DocList.tsx               # 文档列表
│   │   ├── SourceViewer.tsx          # 来源查看器
│   │   ├── UploadDialog.tsx          # 上传对话框
│   │   ├── Toast.tsx                 # 提示组件
│   │   └── ConfirmDialog.tsx         # 确认对话框
│   ├── lib/
│   │   ├── api.ts                    # HTTP API 客户端
│   │   └── store.ts                  # Zustand 状态管理
│   ├── tests/                        # Vitest 测试
│   ├── Dockerfile
│   └── package.json
├── nginx/                            # nginx 配置
│   ├── nginx.conf
│   ├── conf.d/default.conf
│   ├── conf.d/ssl.conf
│   └── entrypoint.sh                 # 自签名证书生成
├── docker-compose.yml                # 开发环境
├── docker-compose.prod.yml           # 生产环境
├── .env.example                      # 环境变量模板
├── DEPLOY.md                         # 部署指南
└── README.md
```

---

## 5. 模块详解

### 5.1 后端核心模块

#### 5.1.1 应用入口 — `main.py`

[main.py](file:///workspace/backend/app/main.py) 是 FastAPI 应用的启动入口，负责：

- **生命周期管理**：`lifespan` 上下文管理器依次执行日志初始化 → 数据库初始化 → Langfuse 初始化 → 插件加载 → 应用运行 → 关闭时清理 Redis 连接
- **中间件注册**：RequestID 中间件 → CORS 中间件 → Prometheus 指标
- **路由注册**：挂载所有 v1 API 路由到 `/api/v1` 前缀下
- **全局异常处理**：捕获所有未处理异常，返回 500 JSON 响应
- **健康检查**：`GET /health` 返回 `{"status": "ok"}`

#### 5.1.2 配置管理 — `config.py`

[config.py](file:///workspace/backend/app/config.py) 使用 pydantic-settings 加载 `.env` 文件，提供：

- 数据库连接、Redis 连接
- JWT 密钥与过期时间（未设置时自动生成随机密钥）
- LLM / Embedding 模型配置（支持独立配置 API 地址）
- CORS 白名单（逗号分隔，解析为列表）
- 文件上传限制（大小 20MB、允许扩展名）
- 分块参数（512 token / 64 overlap）
- 检索参数（RRF_K=60, TOP_K=5, 阈值=0.3, 精排 TOP_K=3）
- 中英文停用词集合（EN_STOP / ZH_STOP）

#### 5.1.3 数据库 — `database.py`

[database.py](file:///workspace/backend/app/database.py) 管理异步数据库连接：

- 使用 `asyncpg` 驱动创建异步引擎
- `async_session` 会话工厂，自动提交/回滚
- `get_db()` 依赖注入函数，用于 FastAPI 路由
- `init_db()` 启动时创建 pgvector 扩展和所有表

#### 5.1.4 LLM 服务 — `core/llm.py`

[llm.py](file:///workspace/backend/app/core/llm.py) 提供两个单例服务：

**LLMService**
- 基于 litellm 统一接口，兼容 OpenAI / SiliconFlow / DeepSeek 等
- `stream_chat(messages)` — 异步流式生成，逐 token yield
- `complete(messages)` — 异步非流式生成，返回完整文本
- 自动处理 `api_base` 兼容模式（加 `openai/` 前缀）

**EmbeddingService**
- `embed(texts)` — 批量向量化，返回 embedding 列表
- `embed_single(text)` — 单个文本向量化
- 失败时记录警告，降级为纯 BM25 全文检索

#### 5.1.5 安全模块 — `core/security.py`

[security.py](file:///workspace/backend/app/core/security.py) 提供：

- `hash_password()` / `verify_password()` — bcrypt 密码哈希
- `create_access_token(user_id)` — JWT token 签发（24 小时有效期）
- `decode_token(token)` — JWT token 解析，异常返回 401
- `get_current_user()` — FastAPI 依赖注入，从 Bearer token 获取当前用户

#### 5.1.6 日志模块 — `core/logging.py`

[logging.py](file:///workspace/backend/app/core/logging.py) 提供：

- `RequestIDMiddleware` — 为每个请求生成唯一 `request_id`，注入到响应头和日志上下文
- `init_logging()` — 配置 JSON 格式日志输出，包含 timestamp、level、logger、message、request_id

#### 5.1.7 指标模块 — `core/metrics.py`

[metrics.py](file:///workspace/backend/app/core/metrics.py) 暴露 Prometheus 指标：

- `http_requests_total` — 请求计数（按 method/endpoint/status 标签）
- `http_request_duration_seconds` — 请求延迟分布直方图
- `documents_indexed_total` — 已索引文档计数器
- `llm_requests_total` — LLM 调用计数器
- `setup_metrics(app)` — 注册 FastAPI 中间件自动采集
- `GET /metrics` — 文本格式指标端点

#### 5.1.8 插件系统 — `core/plugins.py`

[plugins.py](file:///workspace/backend/app/core/plugins.py) 提供可扩展的插件架构：

- `BasePlugin` 基类 — 定义 `name`、`on_startup()`、`on_shutdown()` 钩子
- `PluginRegistry` 注册表 — 管理插件注册、获取
- `load_all()` — 扫描已导入插件并执行 `on_startup()`
- 当前内置插件：`LogPlugin`（日志记录插件）

#### 5.1.9 钩子系统 — `core/hooks.py`

[hooks.py](file:///workspace/backend/app/core/hooks.py) 提供事件钩子机制：

- `register(event_name, callback)` — 注册事件回调
- `trigger(event_name, **kwargs)` — 触发事件并异步执行所有回调
- 当前事件点：`after_retrieval`（检索后）、`after_llm`（LLM 生成后）

#### 5.1.10 限流模块 — `core/ratelimit.py`

[ratelimit.py](file:///workspace/backend/app/core/ratelimit.py) 基于 Redis 实现速率限制：

- `auth_rate_limit` — 认证接口限流
- `chat_rate_limit` — 聊天接口限流
- 滑动窗口算法，记录 IP + 时间窗口的请求数

#### 5.1.11 Prompt 管理 — `core/prompts.py`

[prompts.py](file:///workspace/backend/app/core/prompts.py) 定义系统提示和消息构造：

- `RAG_SYSTEM` — 有上下文时的 RAG 系统提示
- `NO_CONTEXT_SYSTEM` — 无上下文时的通用系统提示
- `build_messages(system, context, history, question)` — 组装完整的 LLM 消息列表
- `parse_rag_response(text)` — 解析 LLM 返回的结构化 JSON（answer/sources/confidence）

---

### 5.2 API 路由层

所有路由位于 `backend/app/api/v1/`，挂载到 `/api/v1` 前缀。

| 路由文件 | 前缀 | 主要端点 | 权限 |
|----------|------|----------|------|
| `auth.py` | `/auth` | POST `/register`, POST `/login` | 公开 |
| `chat.py` | `/chat` | POST `/conversations` (创建会话), POST `/{conv_id}/message` (流式消息), GET `/conversations` (列表), GET/DELETE `/{conv_id}` | 需认证 |
| `documents.py` | `/documents` | POST `/upload` (上传), GET `/` (列表), GET `/{id}` (详情), PATCH `/{id}` (更新), DELETE `/{id}` (删除), GET `/{id}/download` (下载) | 需认证 |
| `knowledge_bases.py` | `/knowledge-bases` | CRUD 知识库，POST `/{id}/reindex` 重建索引 | 需认证 |
| `agents.py` | `/agents` | Agent CRUD, 会话管理, 消息发送, 消息评分 | 混合（部分需 admin） |
| `admin.py` | `/admin` | 用户列表/禁用, 数据统计 | 仅 admin |
| `audit.py` | `/audit` | 审计日志查询 | 需认证 |
| `feedback.py` | `/feedback` | 提交/查询反馈 | 需认证 |
| `prompt_templates.py` | `/prompt-templates` | Prompt 模板 CRUD | 混合 |
| `webhooks.py` | `/webhooks` | Webhook CRUD 和测试 | 需认证 |
| `plugins.py` | `/plugins` | 插件状态查询 | 需认证 |
| `mcp.py` | `/mcp` | MCP 协议端点 | 公开 |

#### 关键路由示例

**聊天流式响应** (`chat.py`):
```
POST /api/v1/chat/{conversation_id}/message
Body: {"content": "用户问题"}
Response: SSE 流式 events
  - {"type": "sources", "data": [...]}   // 检索来源
  - {"type": "token", "data": "..."}     // 生成中的 token
  - {"type": "structured", "data": {...}}// 结构化结果
  - {"type": "done"}                     // 完成
  - {"type": "error", "data": "..."}     // 错误
```

**文档上传** (`documents.py`):
```
POST /api/v1/documents/upload
Form: file + kb_id (可选)
Response: {"id": "...", "title": "...", "status": "pending"}
```
上传后触发 Celery 异步索引任务。

---

### 5.3 数据模型层

所有模型定义在 `backend/app/models/`，使用 SQLAlchemy Declarative API。

#### 核心实体关系

```
User (1) ─── (N) KnowledgeBase (创建者)
User (1) ─── (N) Agent (创建者)
User (1) ─── (N) Conversation (所有者)
User (1) ─── (N) AgentSession (所有者)

KnowledgeBase (1) ─── (N) Document (所属知识库)
KnowledgeBase (N) ─── (N) Agent (关联知识库)

DataSource (1) ─── (N) Document (数据来源)
Document (1) ─── (N) DocumentChunk (分块)

Conversation (1) ─── (N) Message (对话消息)
Agent (1) ─── (N) AgentSession (会话)
AgentSession (1) ─── (N) AgentMessage (会话消息)

PromptTemplate ─── (独立，通过 template_id 关联聊天)
AuditLog ─── (独立，记录操作)
Feedback ─── (独立，关联消息)
Webhook ─── (独立，配置推送)
Permission ─── (关联文档/数据源与用户)
```

#### 模型详情

| 模型 | 表名 | 关键字段 | 说明 |
|------|------|----------|------|
| **User** | `users` | id, email, name, hashed_password, role, is_active | 用户表，role 为 admin/member |
| **KnowledgeBase** | `knowledge_bases` | id, name, description, created_by | 知识库，按业务场景隔离 |
| **DataSource** | `data_sources` | id, name, type, config(JSONB), status | 数据源配置（notion/feishu/confluence/local） |
| **Document** | `documents` | id, source_id, kb_id, title, content, content_hash, status | 文档，状态: pending/processing/indexed/failed |
| **DocumentChunk** | `document_chunks` | id, document_id, chunk_index, content, embedding(vector), tsvector_content | 文档分块，含向量和全文搜索索引 |
| **Conversation** | `conversations` | id, user_id, kb_id, title, template_id | 对话会话 |
| **Message** | `messages` | id, conversation_id, role, content, sources(JSONB) | 对话消息，含来源信息 |
| **Agent** | `agents` | id, name, description, system_prompt, knowledge_base_ids(JSONB), top_k, threshold, rerank_top_k | 可配置的 Agent |
| **AgentSession** | `agent_sessions` | id, agent_id, user_id, title | Agent 会话 |
| **AgentMessage** | `agent_messages` | id, session_id, role, content, sources(JSONB), score | Agent 消息，可评分 |
| **PromptTemplate** | `prompt_templates` | id, name, context_prompt, no_context_prompt, top_k, threshold, is_active | Prompt 模板 |
| **AuditLog** | `audit_logs` | id, user_id, action, resource_type, resource_id, details(JSONB) | 审计日志 |
| **Feedback** | `feedback` | id, message_id, user_id, type, comment | 用户反馈 |
| **Webhook** | `webhooks` | id, url, events(JSONB), secret, is_active | Webhook 配置 |
| **DocumentPermission** | `document_permissions` | document_id, user_id, permission | 文档级权限 |
| **SourcePermission** | `source_permissions` | source_id, user_id, permission | 数据源级权限 |

---

### 5.4 业务服务层

#### 5.4.1 检索服务 — `services/retrieval.py`

[retrieval.py](file:///workspace/backend/app/services/retrieval.py) 是 RAG 的核心检索引擎，实现五阶段混合检索：

1. **向量检索** — 计算 query embedding，pgvector cosine 相似度搜索
2. **BM25 全文检索** — jieba 分词 + 停用词过滤，PostgreSQL tsvector/tsquery
3. **RRF 融合** — Reciprocal Rank Fusion，融合两路结果（k=60）
4. **去重** — 同一文档最多 2 个 chunk
5. **LIKE 子串补充** — 中文 CJK 连续子串匹配，处理人名等场景
6. **精排** — 可选 FlagEmbedding bge-reranker-base 重排

权限过滤：非管理员自动附加 SQL 子查询过滤 `document_permissions` 和 `source_permissions`。

#### 5.4.2 聊天服务 — `services/chat.py`

[chat.py](file:///workspace/backend/app/services/chat.py) 实现流式聊天流程：

1. 加载历史消息（最多 10 条）
2. 持久化 user 消息（确保失败时有记录）
3. 查询改写（rewriter 服务，基于对话历史）
4. 检索相关文档（调用 RetrievalService）
5. 推送 sources 事件
6. 根据是否有上下文选择系统提示
7. LLM 流式生成，推送 token 事件
8. 检测并剥离 JSON 结构化输出
9. 推送 structured 事件（answer/sources/confidence）
10. 持久化 assistant 回复
11. 自动生成交谈标题
12. 友好的错误消息映射（余额不足/限流/超时/认证失败等）

#### 5.4.3 Agent 服务 — `services/agent.py`

[agent.py](file:///workspace/backend/app/services/agent.py) 实现独立 Agent 对话逻辑：

- 从 Agent 配置读取 system_prompt、关联知识库、检索参数
- 支持独立于主聊天的会话管理
- 消息评分机制

#### 5.4.4 精排服务 — `services/reranker.py`

[reranker.py](file:///workspace/backend/app/services/reranker.py) 使用 FlagEmbedding bge-reranker-base 模型对检索结果重排（可选，需 `RERANKER_ENABLED=true`）。

#### 5.4.5 查询改写 — `services/rewriter.py`

[rewriter.py](file:///workspace/backend/app/services/rewriter.py) 使用 LLM 对用户查询进行语义改写，结合对话历史摘要，提高召回率。

#### 5.4.6 认证服务 — `services/auth.py`

[auth.py](file:///workspace/backend/app/services/auth.py) 实现：

- `register(UserCreate)` — 注册新用户，密码 bcrypt 哈希
- `login(UserLogin)` — 登录验证，返回 JWT token

#### 5.4.7 审计服务 — `services/audit.py`

[audit.py](file:///workspace/backend/app/services/audit.py) 记录和查询审计日志，追踪用户操作。

#### 5.4.8 Webhook 服务 — `services/webhook.py`

[webhook.py](file:///workspace/backend/app/services/webhook.py) 实现 Webhook 事件分发：

- `dispatch(db, event_type, payload)` — 根据事件类型匹配已配置的 Webhook，发送 HTTP POST
- 当前触发事件：`document.indexed`

---

### 5.5 管道与异步任务

#### 5.5.1 文档分块 — `pipeline/chunker.py`

[chunker.py](file:///workspace/backend/app/pipeline/chunker.py) 实现结构感知分块：

- **Markdown 标题感知** — 按 `##` 等标题分割章节
- **代码块保持完整** — 用 UUID 占位符保护代码块不被标题分割破坏
- **表格保持完整** — 表格结构不跨块
- **滑动窗口** — 长段落按 chunk_size=512 / overlap=64 切分
- **段落优先** — 先按段落边界切分，保留语义完整性

#### 5.5.2 索引构建 — `pipeline/indexer.py`

[indexer.py](file:///workspace/backend/app/pipeline/indexer.py) 实现单文档索引流程：

1. 设置文档状态为 `processing`
2. 调用 chunker 分块
3. 删除旧分块（支持重建索引）
4. 批量向量化（失败时降级为纯全文搜索）
5. 构建 tsvector 全文搜索索引（jieba 分词）
6. 写入 DocumentChunk 表
7. 设置文档状态为 `indexed`
8. 触发 `document.indexed` Webhook

#### 5.5.3 Celery 异步任务 — `tasks/indexing.py`

[indexing.py](file:///workspace/backend/app/tasks/indexing.py) 定义 Celery 任务：

- 文档上传后触发异步索引任务
- Worker 进程独立运行，不阻塞 API 响应

#### 5.5.4 消息队列 — `mq/`

[mq/](file:///workspace/backend/app/mq/) 模块提供消息队列基础设施：

- `connection.py` — 连接管理
- `consumer.py` — 消息消费者
- `idempotency.py` — 幂等性控制（防重复处理）
- `protocol.py` — 消息协议定义

#### 5.5.5 数据源连接器 — `connectors/`

[connectors/](file:///workspace/backend/app/connectors/) 提供外部数据源接入：

- `base.py` — 连接器抽象基类，定义统一接口
- `local.py` — 本地文件系统连接器

---

### 5.6 前端架构

#### 5.6.1 页面路由

| 页面路径 | 文件 | 说明 |
|----------|------|------|
| `/` | `app/page.tsx` | 首页，跳转到聊天或登录 |
| `/login` | `app/login/page.tsx` | 登录页面 |
| `/chat` | `app/chat/page.tsx` | 新建聊天 |
| `/chat/[conversationId]` | `app/chat/[conversationId]/page.tsx` | 查看/继续对话 |
| `/documents` | `app/documents/page.tsx` | 文档管理页 |
| `/agents` | `app/agents/page.tsx` | Agent 列表 |
| `/agents/[agentId]` | `app/agents/[agentId]/page.tsx` | Agent 详情 |
| `/agents/sessions/[sessionId]` | `app/agents/sessions/[sessionId]/page.tsx` | Agent 会话详情 |
| `/admin` | `app/admin/page.tsx` | 管理后台 |

#### 5.6.2 状态管理 — `lib/store.ts`

[store.ts](file:///workspace/frontend/lib/store.ts) 使用 Zustand 管理全局状态：

```typescript
interface Store {
  // 认证
  token: string | null
  user: User | null
  setAuth(token, user)
  logout()

  // 聊天
  conversations: Conversation[]
  currentConversationId: string | null
  messages: Message[]
  sources: Source[]
  isStreaming: boolean
  chatError: string | null
  setConversations()
  addMessage()
  updateLastAssistantMessage()  // 流式更新
  setSources()
  setStreaming()

  // 侧边栏
  sidebarCollapsed: boolean
  toggleSidebar()

  // Agent
  agents: Agent[]
  agentSessions: AgentSession[]
  agentMessages: AgentMessage[]
  setAgentStreaming()
}
```

- 认证状态持久化到 localStorage
- 流式消息通过 `updateLastAssistantMessage()` 增量更新

#### 5.6.3 API 客户端 — `lib/api.ts`

[api.ts](file:///workspace/frontend/lib/api.ts) 封装 HTTP 请求：

- `post()` / `get()` / `put()` / `patch()` / `delete()` — 标准 REST 请求
- `streamChat(conversationId, message, onToken)` — SSE 流式聊天，逐 token 回调
- `uploadFile(file, kbId, onProgress)` — 文件上传，支持进度回调
- 自动附加 JWT token 到请求头
- 统一错误处理

#### 5.6.4 UI 组件

| 组件 | 文件 | 说明 |
|------|------|------|
| ChatWindow | `components/ChatWindow.tsx` | 聊天窗口，渲染消息列表 |
| InputBox | `components/InputBox.tsx` | 消息输入框，支持发送 |
| MessageBubble | `components/MessageBubble.tsx` | 单条消息气泡，支持 Markdown |
| Sidebar | `components/Sidebar.tsx` | 侧边栏导航 |
| DocList | `components/DocList.tsx` | 文档列表展示 |
| SourceViewer | `components/SourceViewer.tsx` | 检索来源查看 |
| UploadDialog | `components/UploadDialog.tsx` | 文件上传弹窗 |
| Toast | `components/Toast.tsx` | 系统提示通知 |
| ConfirmDialog | `components/ConfirmDialog.tsx` | 操作确认弹窗 |

---

## 6. 核心流程

### 6.1 RAG 检索流程

```
用户提问
    │
    ▼
┌─────────────────────────┐
│ 1. 查询改写 (rewriter)   │  LLM 改写查询，结合对话历史摘要
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│ 2. 多路召回                                    │
│                                              │
│  ┌─────────────┐  ┌─────────────┐            │
│  │ 向量检索     │  │ BM25 检索   │            │
│  │ (pgvector)  │  │ (tsvector)  │            │
│  └──────┬──────┘  └──────┬──────┘            │
│         │                │                   │
│         └───────┬────────┘                   │
│                 ▼                            │
│         ┌─────────────┐                      │
│         │ RRF 融合     │  k=60, 倒序排名倒数   │
│         └──────┬──────┘                      │
│                ▼                             │
│         ┌─────────────┐                      │
│         │ LIKE 补充    │  CJK 子串匹配         │
│         └──────┬──────┘                      │
│                ▼                             │
│         ┌─────────────┐                      │
│         │ 去重过滤     │  同一文档最多2个chunk │
│         └──────┬──────┘                      │
└───────────────┼──────────────────────────────┘
                │
                ▼
┌─────────────────────────┐
│ 3. 精排 (可选 reranker)  │  bge-reranker-base
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. Prompt 组装           │  系统提示 + 上下文 + 历史 + 问题
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 5. LLM 流式生成          │  SSE 推送 token
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 6. 结构化解析            │  提取 answer/sources/confidence
└────────┬────────────────┘
         │
         ▼
    返回给用户
```

### 6.2 文档索引流程

```
用户上传文件
    │
    ▼
┌─────────────────────────┐
│ 1. 文件接收              │  校验格式/大小，保存到 upload/
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. 文本提取              │  pdfplumber/python-docx/openpyxl
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. 创建 Document 记录     │  status = "pending"
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. 触发 Celery 任务       │  异步处理，不阻塞响应
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 5. 分块 (chunker)        │  结构感知分块，512/64
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 6. 向量化 (embedding)    │  litellm → 批量 embedding
│    (失败则跳过)           │  降级为纯全文搜索
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 7. 写入 document_chunks  │  embedding + tsvector
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 8. 更新状态              │  status = "indexed"
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 9. 触发 Webhook          │  document.indexed 事件
└─────────────────────────┘
```

### 6.3 认证流程

```
用户注册/登录
    │
    ▼
┌─────────────────────────┐
│ POST /api/v1/auth/login  │
│  或 /register            │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ AuthService              │  验证密码 (bcrypt)
│  签发 JWT token           │  HS256, 24h 过期
└────────┬────────────────┘
         │
         ▼
    返回 token
         │
         ▼
┌─────────────────────────┐
│ 前端存储到 localStorage  │
│ 后续请求附加 Bearer       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 后端 get_current_user()  │  解码 token → 查数据库 → 返回 User
│  (依赖注入)               │  401 如果无效/过期/禁用
└─────────────────────────┘
```

---

## 7. 依赖关系

### 模块依赖图

```
main.py
├── api/v1/* (路由)
│   ├── services/* (业务逻辑)
│   │   ├── core/llm.py (LLM/Embedding)
│   │   ├── retrieval.py (检索)
│   │   │   ├── core/llm.py (Embedding)
│   │   │   ├── reranker.py (精排)
│   │   │   └── config.py (参数)
│   │   ├── rewriter.py (查询改写)
│   │   │   └── core/llm.py
│   │   ├── chat.py (流式聊天)
│   │   │   ├── retrieval.py
│   │   │   ├── rewriter.py
│   │   │   ├── core/llm.py
│   │   │   ├── core/prompts.py
│   │   │   └── core/hooks.py
│   │   ├── agent.py (Agent)
│   │   ├── auth.py (认证)
│   │   │   └── core/security.py
│   │   └── webhook.py
│   ├── models/* (ORM)
│   ├── schemas/* (Pydantic)
│   └── core/security.py (权限验证)
├── core/logging.py (中间件)
├── core/metrics.py (中间件)
├── core/plugins.py
├── database.py
└── config.py

pipeline/
├── chunker.py (分块)
│   └── config.py
└── indexer.py (索引)
    ├── chunker.py
    ├── core/llm.py (Embedding)
    └── models/document.py

tasks/
└── indexing.py (Celery 任务)
    ├── pipeline/indexer.py
    └── database.py

mq/
├── connection.py
├── consumer.py
├── idempotency.py
└── protocol.py
```

### 外部依赖

```
PostgreSQL + pgvector
    ↑
    ├── SQLAlchemy ORM (models)
    ├── 向量检索 (retrieval)
    └── 全文检索 (tsvector/tsquery)

Redis
    ↑
    ├── Celery broker (异步任务)
    └── 速率限制 (ratelimit)

LLM API (litellm)
    ↑
    ├── 流式生成 (chat)
    ├── 查询改写 (rewriter)
    ├── Embedding (retrieval/indexer)
    └── 自动标题 (chat)

Langfuse (可选)
    ↑
    └── LLM 调用追踪 (observability)

Prometheus
    ↑
    └── /metrics 端点
```

---

## 8. 数据库设计

### 主要表结构

#### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| email | VARCHAR(255) | 唯一索引 |
| name | VARCHAR(100) | 用户名 |
| hashed_password | VARCHAR(255) | bcrypt 哈希 |
| role | VARCHAR(20) | admin / member |
| is_active | BOOLEAN | 是否启用 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

#### knowledge_bases
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(100) | 名称 |
| description | TEXT | 描述 |
| created_by | UUID | 外键 → users |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### documents
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| source_id | UUID | 外键 → data_sources |
| kb_id | UUID | 外键 → knowledge_bases |
| external_id | VARCHAR(255) | 外部源 ID |
| title | VARCHAR(500) | 标题 |
| content | TEXT | 全文内容 |
| content_hash | VARCHAR(64) | MD5 哈希索引 |
| metadata | JSONB | 元数据 |
| status | VARCHAR(20) | pending/processing/indexed/failed |
| indexed_at | TIMESTAMPTZ | 索引完成时间 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZZ | |

#### document_chunks
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| document_id | UUID | 外键 → documents (CASCADE) |
| chunk_index | INTEGER | 块序号 |
| content | TEXT | 块内容 |
| embedding | Vector(EMBEDDING_DIM) | pgvector 向量 |
| tsvector_content | TSVECTOR | 全文搜索索引 (GIN) |
| metadata | JSONB | 元数据 |
| created_at | TIMESTAMPTZ | |

#### conversations
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| kb_id | UUID | 外键 → knowledge_bases (可选) |
| title | VARCHAR(200) | 会话标题 |
| template_id | UUID | 外键 → prompt_templates (可选) |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### messages
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| conversation_id | UUID | 外键 → conversations |
| role | VARCHAR(10) | user / assistant |
| content | TEXT | 消息内容 |
| sources | JSONB | 检索来源数组 |
| created_at | TIMESTAMPTZ | |

#### agents
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(100) | 名称 |
| description | TEXT | 描述 |
| system_prompt | TEXT | 系统提示词 |
| knowledge_base_ids | JSONB | 关联知识库 ID 列表 |
| top_k | INTEGER | 检索 TOP_K |
| threshold | INTEGER | 检索阈值 |
| rerank_top_k | INTEGER | 精排 TOP_K |
| is_active | BOOLEAN | 是否启用 |
| created_by | UUID | 外键 → users |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

## 9. 运行与部署

### 9.1 开发环境

#### 后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

#### 测试
```bash
# 后端
cd backend && TESTING=1 pytest tests/ -v

# 前端
cd frontend && npm test
```

### 9.2 Docker 一键部署

```bash
# 配置环境变量
cp .env.example .env
vim .env   # 填入 LLM_API_KEY, SECRET_KEY 等

# 启动
docker compose up -d --build

# 访问
# https://localhost (自签名证书)
```

### 9.3 生产部署

使用生产 Compose 文件（含 Let's Encrypt certbot）：

```bash
# 申请证书
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot -d your-domain.com

# 启动生产环境
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

详见 [DEPLOY.md](file:///workspace/DEPLOY.md)。

### 9.4 服务端口

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| nginx | — | 80/443 | 统一入口 |
| frontend | 3000 | — | 仅 nginx 内部访问 |
| backend | 8000 | — | 仅 nginx 内部访问 |
| postgres | 5432 | — | 仅内部网络 |
| redis | 6379 | — | 仅内部网络 |

### 9.5 nginx 路由规则

| 路径 | 目标 | 说明 |
|------|------|------|
| `/api/*` | `backend:8000` | 后端 API |
| `/*` | `frontend:3000` | 前端页面 |
| `/health` | `backend:8000/health` | 健康检查 |
| `/metrics` | `backend:8000/metrics` | 仅限 Docker 内部网络 |

### 9.6 资源限制

| 服务 | CPU | 内存 |
|------|-----|------|
| postgres | 2.0 | 2G |
| redis | 0.5 | 256M |
| backend | 1.0 | 512M |
| worker | 2.0 | 1G |
| frontend | 0.5 | 256M |
| nginx | 0.25 | 128M |

---

## 10. 测试

### 后端测试

测试文件位于 `backend/tests/`：

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_auth.py` | 注册、登录、JWT 认证 |
| `test_chat.py` | 对话创建、消息发送、流式响应 |
| `test_documents.py` | 文档上传、列表、详情、删除 |
| `test_retrieval.py` | 向量检索、BM25、RRF 融合 |
| `test_regression.py` | 回归测试 |
| `conftest.py` | 测试 fixture（数据库 mock、认证 token 等） |

```bash
cd backend && TESTING=1 pytest tests/ -v
```

### 前端测试

测试文件位于 `frontend/tests/`：

| 测试文件 | 覆盖范围 |
|----------|----------|
| `components/InputBox.test.tsx` | 输入框组件渲染、用户交互 |
| `components/Toast.test.tsx` | Toast 组件显示、关闭 |
| `lib/store.test.ts` | 状态管理操作、流式更新 |

```bash
cd frontend && npm test
```

---

## 11. 配置说明

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | 是 | — | LLM API 密钥 |
| `LLM_MODEL` | 是 | `gpt-4o-mini` | 模型名称 |
| `LLM_BASE_URL` | 否 | — | API 地址 |
| `EMBEDDING_MODEL` | 是 | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_API_KEY` | 否 | 同 LLM_API_KEY | Embedding API 密钥 |
| `EMBEDDING_BASE_URL` | 否 | 同 LLM_BASE_URL | Embedding API 地址 |
| `EMBEDDING_DIM` | 否 | 1024 | 向量维度 |
| `SECRET_KEY` | 是 | 自动生成 | JWT 签名密钥 |
| `DB_PASSWORD` | 否 | `knowflow` | 数据库密码 |
| `DATABASE_URL` | 否 | `postgresql+asyncpg://knowflow:knowflow@localhost:5432/knowflow` | 数据库连接 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接 |
| `CORS_ORIGINS` | 否 | `http://localhost:3000` | CORS 白名单 |
| `UPLOAD_DIR` | 否 | `./uploads` | 上传目录 |
| `MAX_FILE_SIZE` | 否 | `20MB` | 最大上传大小 |
| `ALLOWED_EXTENSIONS` | 否 | `.txt,.md,.markdown,.pdf,.docx,.xlsx` | 允许格式 |
| `CHUNK_SIZE` | 否 | 512 | 分块大小 |
| `CHUNK_OVERLAP` | 否 | 64 | 分块重叠 |
| `RERANKER_ENABLED` | 否 | `false` | 启用精排 |
| `RRF_K` | 否 | 60 | RRF 融合参数 |
| `RETRIEVAL_TOP_K` | 否 | 5 | 检索返回数量 |
| `RETRIEVAL_THRESHOLD` | 否 | 0.3 | 检索相似度阈值 |
| `RETRIEVAL_RERANK_TOP_K` | 否 | 3 | 精排返回数量 |
| `EMBEDDING_TIMEOUT` | 否 | 10 | Embedding 超时(秒) |
| `LANGFUSE_PUBLIC_KEY` | 否 | — | Langfuse 公钥 |
| `LANGFUSE_SECRET_KEY` | 否 | — | Langfuse 私钥 |
| `LANGFUSE_HOST` | 否 | `https://cloud.langfuse.com` | Langfuse 地址 |

### 安全注意事项

1. **SECRET_KEY**：生产环境必须使用 `openssl rand -hex 32` 生成强密钥，否则重启后所有 token 失效
2. **DB_PASSWORD**：修改默认密码，防止未授权访问
3. **CORS_ORIGINS**：生产环境设置为具体域名，不要使用 `*`
4. **LLM_API_KEY**：妥善保管，不要提交到版本控制
