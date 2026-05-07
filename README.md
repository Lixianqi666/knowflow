# KnowFlow

企业知识库 RAG 问答系统。上传文档，基于检索增强生成进行流式问答。

## 架构

```
┌──────────┐     ┌──────────┐     ┌─────────────┐
│ Frontend │────▶│ FastAPI  │────▶│ PostgreSQL  │
│ :3000    │     │ :8000    │     │ +pgvector   │
│ Next.js  │     │ AI Core  │     ├─────────────┤
└──────────┘     │          │     │ Redis       │
                 │ Auth     │     ├─────────────┤
                 │ Chat/SSE │     │ RabbitMQ    │
                 │ Document │     └─────────────┘
                 │ Agent    │            │
                 │ Admin    │     ┌──────▼──────┐
                 └──────────┘     │  ai-worker  │
                                  │ MQ consumer │
                                  └─────────────┘
```

## 快速开始

```bash
# 启动全部服务
docker compose up -d --build

# 初始化数据库（自动建表）
# 访问 http://localhost:3000
```

### 本地开发

```bash
# 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` | Redis 连接串 |
| `LLM_API_KEY` | LLM API 密钥 |
| `LLM_MODEL` | LLM 模型名 |
| `EMBEDDING_MODEL` | 向量嵌入模型 |
| `EMBEDDING_API_KEY` | Embedding API 密钥 |
| `SECRET_KEY` | JWT 签名密钥 |

## 核心流程

```
上传 → 文本提取(pdfplumber/python-docx/openpyxl)
     → 分块(512 token, 64 overlap)
     → embedding(litellm)
     → pgvector 存储

提问 → embedding
     → pgvector cosine 检索
     → RAG prompt 组装
     → LLM 流式生成
     → SSE 推送
```

## 技术栈

- **后端**: Python FastAPI, SQLAlchemy, pgvector, Redis, RabbitMQ
- **前端**: Next.js, Tailwind CSS, Zustand
- **队列**: RabbitMQ (替代 Celery)
- **LLM**: litellm 统一接口（支持 OpenAI/DeepSeek 等）
