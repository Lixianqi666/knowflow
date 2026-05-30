# KnowFlow 生产落地审计报告

审计时间：2026-05-29
审计范围：KnowFlow 全量代码（backend + frontend + Docker + CI/CD）
审计方法：逐文件静态代码审查，未启动任何服务

---

## 1. 总体判断

KnowFlow 是一个功能完整度较高的企业知识库 RAG 问答系统。核心功能链路（文档上传→分块→索引→混合检索→LLM 生成）已经跑通，前端具备聊天、文档管理、Agent、管理后台四大模块，后端有 Celery 异步任务、Prometheus 指标、Langfuse 追踪、审计日志、Webhook 等运维基础设施雏形。在个人/小团队试用场景下已基本可用。

**但距离真正的生产可交付还有明确差距。** 首先，安全层面存在多个阻断项：Docker 容器以 root 运行、JWT 存储在 localStorage（XSS 可窃取）、注册接口泄露邮箱枚举、Webhook URL 无 SSRF 防护、文档权限模型不区分 read/write 等级。其次，运维基础设施缺失严重：docker-compose.yml 引用的 nginx.conf、prometheus.yml、backup.sh 三个关键文件在仓库中不存在，意味着反向代理、监控采集、数据库备份在当前代码状态下均无法工作。第三，RAG 质量闭环尚未建立——没有检索质量评估手段、没有用户反馈→标注→优化的循环机制、Prompt 模板与检索参数的调优缺少数据支撑。

**从工程成熟度看**，后端代码结构清晰、职责分离合理（api/services/core/pipeline/tasks 分层），前端状态管理和 API 封装也有基本规范。但缺乏系统性的安全加固：Token 无刷新/撤销机制、密码无复杂度要求、管理接口无限流、SQL 拼接存在于 webhook 服务。测试覆盖仅停留在单元/集成测试层面，无端到端测试、无性能基准、无安全扫描集成到部署流程。

**从可运维性看**，日志（JSON 结构化 + request_id）、指标（Prometheus）、审计日志三个支柱已有骨架，但告警规则、仪表盘配置、备份验证均缺失。数据库备份依赖容器内 crond，无加密、无异地、无成功通知。整体而言，项目处于"功能开发完成、生产硬化未开始"的阶段。

---

## 2. 风险分级清单

| 等级 | 模块 | 问题 | 影响 | 建议 |
|------|------|------|------|------|
| P0 | Docker | backend/Frontend 容器以 root 运行（Dockerfile 无 USER 指令） | 容器逃逸时获得宿主机 root 权限 | 后端 `USER app`，前端 `USER node` |
| P0 | Docker | docker-compose.yml 未挂载自定义 nginx 代理配置，当前 nginx 默认配置无法代理前后端；prometheus.yml 和 backup.sh 在仓库中不存在 | nginx 反向代理不工作、Prometheus 无法启动、备份任务失败 | 补齐配置文件并挂载到容器 |
| P0 | 安全 | JWT 存储在 localStorage，XSS 可直接窃取 Token | 攻击者获取用户完整会话权限 | 改为 httpOnly Secure Cookie 或短期 Token + 刷新机制 |
| P0 | 安全 | Webhook URL 无 SSRF 防护，管理员可构造指向内网的 URL | 通过 Webhook 探测内网服务、访问云元数据端点 | URL 白名单校验 + 禁止私有 IP/域名 |
| P0 | 权限 | `_require_doc_permission` 只检查权限记录是否存在，不区分 read/write | 拥有 read 权限的用户可以删除文档 | 按 action 参数校验 permission 字段值 |
| P0 | 安全 | Webhook 服务 f-string 拼接 SQL（`events ~ '(^|,){event}(,|$)'`） | 虽然当前调用方传入硬编码字符串，但模式本身是 SQL 注入 | 改为参数化查询或使用 ORM |
| P0 | 安全 | Git 历史中泄露 .env 敏感信息（SECRET_KEY、LLM_API_KEY、EMBEDDING_API_KEY） | 任何有仓库访问权的人可从 git history 提取真实密钥 | 使用 BFG Repo-Cleaner 清除历史 + 立即轮换所有泄露密钥 |
| P0 | 后端 | Request ID 使用 `threading.local` 而非 `contextvars`（`logging.py:9`） | 异步并发场景下 request_id 互相覆盖，链路追踪完全失效 | 改为 `contextvars.ContextVar` |
| P1 | 认证 | 无 Refresh Token 机制，Token 24h 过期后无法撤销 | Token 泄露后 24 小时内持续有效，无法主动失效 | 增加 Refresh Token + Token 黑名单 |
| P1 | 认证 | 注册接口返回"邮箱已注册"，允许用户枚举 | 攻击者可遍历邮箱列表 | 注册成功时统一返回"请查收邮件" |
| P1 | 认证 | 密码仅要求 min_length=8，无复杂度要求 | 弱密码易被暴力破解 | 增加大小写+数字+特殊字符要求 |
| P1 | Docker | 无 backend/.dockerignore，COPY . . 会将 .env、.venv、测试文件打包进镜像 | 镜像体积膨胀、可能泄露敏感文件 | 创建 backend/.dockerignore |
| P1 | 部署 | 无 restart 策略，容器崩溃或主机重启后不自动恢复 | 服务中断需人工干预 | 所有服务添加 `restart: unless-stopped` |
| P1 | 部署 | Alembic 迁移在 backend 启动 command 中执行，多副本会竞争 | 并发部署时迁移冲突 | 抽离为独立 init 容器或部署前步骤 |
| P1 | 部署 | Redis 无密码认证 | Docker 网络内任意容器可访问 Redis | 添加 `requirepass` |
| P1 | 数据库 | 默认 DB 密码为 `knowflow`，docker-compose 和代码中硬编码 | 未修改 .env 时数据库无密码保护 | 生产环境强制要求设置 DB_PASSWORD |
| P1 | 前端 | 无 Next.js middleware，/admin 页面无服务端路由保护 | 未认证用户可访问管理页面 HTML | 添加 middleware.ts 进行 token 校验 |
| P1 | 前端 | 无 SSE 重连机制，网络中断后用户需手动重发 | 对话体验差，长文本生成可能丢失 | 增加指数退避重试逻辑 |
| P1 | 管理后台 | 知识库无访问控制，任何用户可创建/删除任何知识库 | 普通用户可破坏其他用户的知识库 | 知识库增加 owner 字段 + 权限校验 |
| P1 | 监控 | `/metrics` 端点无认证 | 泄露系统内部指标和请求模式 | 限制为内网访问或添加认证 |
| P1 | 日志 | 无 Docker 日志轮转配置 | 磁盘空间无限增长 | 添加 logging options: max-size/max-file |
| P1 | 后端 | LLM 调用无超时设置（`llm.py`、`rewriter.py`、`common.py`） | LLM 服务响应慢时请求无限挂起，阻塞 Celery worker | 所有 litellm.acompletion 调用添加 timeout 参数 |
| P1 | 后端 | Celery 无 task_time_limit，卡住的任务永久占用 worker | 一个异常索引任务可阻塞整个 worker 进程 | 配置 task_time_limit=300 + task_soft_time_limit=240 |
| P1 | 后端 | Prometheus 指标使用原始 URL 路径作为 label（`metrics.py:47`） | `/api/documents/{uuid}` 每个 UUID 创建新指标系列，Prometheus 内存爆炸 | 路径模板化：`/api/documents/{id}` |
| P1 | 后端 | Agent 服务未验证 session 归属（`agent.py` stream_chat） | 用户可通过猜测 session_id 访问其他用户的 Agent 会话 | stream_chat 中增加 session.user_id == user.id 校验 |
| P1 | 后端 | 文档索引任务无幂等保护（`indexing.py`） | 同一文档并发索引时 chunk 数据被覆盖损坏 | 添加 Redis 分布式锁（document_id 粒度） |
| P2 | RAG | 无检索质量评估机制（无召回率/准确率基准） | 无法量化优化效果 | 建立评测数据集 + 自动化评估流水线 |
| P2 | RAG | 分块策略仅按字符数切分，无语义边界感知 | 长段落被截断导致上下文丢失 | 引入语义分块（按段落/句子/嵌入相似度） |
| P2 | RAG | LIKE 搜索的 ILIKE 子串匹配无性能保障 | 大数据量下全表扫描 | 添加 pg_trgm 索引或 GIN 索引 |
| P2 | Agent | Agent Runtime 使用规则引擎而非 LLM 决策 | Agent 能力受限，无法处理复杂多步推理 | 升级为 LLM-based Planner |
| P2 | Agent | Agent 会话无消息数限制 | 超长对话耗尽上下文窗口 | 添加消息数上限 + 历史摘要 |
| P2 | 前端 | ChatWindow 订阅 16 个 store 字段，流式更新触发全量重渲染 | 低端设备卡顿 | 使用 Zustand selector + React.memo |
| P2 | 前端 | `maximumScale: 1` 禁止用户缩放 | 违反 WCAG 无障碍标准 | 移除或改为 `maximumScale: 5` |
| P2 | 前端 | Google Fonts 从外部 CDN 加载 | 隐私合规风险 + 可用性依赖 | 自托管字体 |
| P2 | 管理后台 | 管理接口无独立限流 | 管理员 Token 泄露后可批量操作 | 添加管理接口限流 |
| P2 | 审计 | 审计日志未覆盖登录/注册/知识库操作 | 合规审计不完整 | 扩展审计事件覆盖范围 |
| P2 | 测试 | 无端到端测试、无性能测试 | 无法验证完整用户路径和性能基线 | 补充 Playwright E2E + k6 性能测试 |
| P2 | CI/CD | Trivy 扫描 exit-code: '0'，即使发现高危漏洞也不阻断构建 | 安全漏洞可能进入生产 | 改为 exit-code: '1' |
| P2 | 部署 | 无 SSL 证书配置（docker-compose 中无 certbot） | HTTP 明文传输 | 集成 Let's Encrypt 或前置证书 |
| P2 | 前端 | next.config.ts 无安全头配置（CSP/HSTS/X-Frame-Options） | 缺乏浏览器安全防护 | 在 next.config 或 nginx 中添加安全头 |
| P2 | 后端 | Prompt 注入风险：文档内容直接注入 LLM prompt（`prompts.py:33`） | 恶意文档可操纵 LLM 行为 | 对检索内容做边界标记 + LLM 输出校验 |
| P2 | 后端 | 日志中记录用户邮箱（`auth.py:32,42`） | PII 泄露到日志文件 | 改为记录 user_id 而非 email |
| P2 | 后端 | tsquery 特殊字符未转义（`retrieval.py:204`） | jieba 分词含 `\|`、`&` 等字符时 PostgreSQL 语法错误 | 转义 tsquery 元字符 |
| P2 | 后端 | Webhook 投递无重试机制（`webhook.py`） | 投递失败时静默丢失 | 添加指数退避重试 + 死信队列 |
| P2 | 后端 | 缓存 tag TTL 与缓存项相同（`cache.py:33`） | 过期后 tag 失效，无法批量清理 | tag TTL 设为缓存 TTL 的 2 倍 |
| P2 | Agent | `search_policy` 工具返回硬编码文本（`business_tools.py:16`） | Agent 政策查询能力为假 | 接入实际知识库检索 |
| P2 | 前端 | 无输入长度限制（所有 textarea/input 无 maxLength） | 超长输入导致后端处理超时或 OOM | 关键输入添加 maxLength 约束 |
| P2 | 前端 | SourceViewer 下载链接无 Bearer Token（`SourceViewer.tsx:59`） | 新窗口打开下载链接时认证缺失 | 改为通过 api.download() 方法下载 |
| P3 | 前端 | 管理后台 6 个 Tab 组件同步加载 | 首屏加载体积偏大 | 改为 dynamic import 按需加载 |
| P3 | 前端 | 搜索输入框固定 220px 宽度 | 极窄屏幕溢出 | 改为响应式宽度 |
| P3 | 后端 | Celery worker concurrency=1 | 高并发文档索引瓶颈 | 根据 CPU 核数调整 |
| P3 | 后端 | Embedding 失败仅降级为 BM25，无告警通知 | 管理员不知道向量索引已失效 | 添加告警指标/通知 |
| P3 | RAG | 无 Query 质量评估（用户意图识别准确率） | 改写质量不可量化 | 建立改写质量评测集 |
| P3 | 运维 | 备份无加密、无异地、无成功验证 | 灾难恢复不可靠 | 添加 GPG 加密 + 异地同步 + 健康检查 |
| P3 | 后端 | Agent Runtime 无 checkpoint/persistence，进程崩溃丢失全部状态 | 长任务中断无法恢复 | 添加 InMemorySaver 或 Redis checkpointer |
| P3 | 后端 | Celery 任务每次创建新 DB 引擎（`indexing.py:29`） | 高并发时连接池反复创建/销毁 | 改为模块级引擎复用 |
| P3 | 后端 | Prometheus MetricsMiddleware 的 status 变量使用 `dir()` 检查（`metrics.py:46`） | 异常路径下 status 可能未定义 | 改为 try/finally + 默认值 |

---

## 3. 第一阶段必须修复项

### 3.1 Docker 容器非 root 运行

- **目标**：消除容器以 root 权限运行的安全风险
- **涉及文件**：`backend/Dockerfile`、`frontend/Dockerfile`
- **验收标准**：`docker run --rm <image> whoami` 返回 `app`/`node` 而非 `root`
- **推荐实现方式**：在 backend/Dockerfile 的 CMD 前添加 `USER app`；frontend/Dockerfile 添加 `USER node`

### 3.2 补齐缺失的部署配置文件

- **目标**：nginx 反向代理、Prometheus 监控、数据库备份可正常工作
- **涉及文件**：新建 `nginx/nginx.conf`、`monitoring/prometheus.yml`、`monitoring/backup.sh`
- **验收标准**：`docker compose up -d` 后 nginx 正确代理 /api/* 和 /*；Prometheus 可抓取 /metrics；备份脚本可执行 pg_dump
- **推荐实现方式**：nginx.conf 配置 upstream + SSL 终止 + 安全头；prometheus.yml 抓取 backend:8000/metrics；backup.sh 使用 pg_dump + 日期轮转

### 3.3 Webhook SSRF 防护

- **目标**：阻止管理员创建指向内网/元数据端点的 Webhook
- **涉及文件**：`backend/app/api/v1/webhooks.py`、新建 `backend/app/core/url_validator.py`
- **验收标准**：创建 Webhook 时，URL 指向 127.0.0.1/10.0.0.0/169.254.169.254 等私有地址返回 400
- **推荐实现方式**：使用 `ipaddress` 模块解析 URL host，校验是否为私有/保留地址

### 3.4 文档权限 read/write 区分

- **目标**：read 权限用户只能查看文档，不能删除
- **涉及文件**：`backend/app/api/v1/documents.py`（`_require_doc_permission` 函数和 delete/batch-delete 端点）
- **验收标准**：拥有 read 权限的用户调用 DELETE /documents/{id} 返回 403
- **推荐实现方式**：`_require_doc_permission` 增加 `required_permission` 参数，delete 端点传入 `"write"`

### 3.5 Webhook SQL 注入修复

- **目标**：消除 f-string 拼接 SQL 的注入风险
- **涉及文件**：`backend/app/services/webhook.py`
- **验收标准**：`events` 字段查询改为参数化或 ORM 方式
- **推荐实现方式**：将 `text(f"events ~ ...")` 改为使用 `Webhook.events.ilike(f"%{event}%")` 或 Python 层过滤

### 3.6 创建 backend/.dockerignore

- **目标**：避免 .env、.venv、测试文件等被打包进 Docker 镜像
- **涉及文件**：新建 `backend/.dockerignore`
- **验收标准**：`docker build` 后镜像中不含 .env、.venv、tests/、__pycache__
- **推荐实现方式**：排除 `.env*`、`.venv`、`tests/`、`__pycache__`、`*.pyc`、`.pytest_cache`、`scripts/`、`docs/`

### 3.7 Token 刷新与撤销机制

- **目标**：支持 Token 主动失效和无感刷新
- **涉及文件**：`backend/app/core/security.py`、`backend/app/api/v1/auth.py`、`frontend/lib/api.ts`、`frontend/lib/store.ts`
- **验收标准**：调用 logout 后旧 Token 失效；Token 过期前自动刷新；用户禁用后 Token 立即失效
- **推荐实现方式**：短期 Access Token（15min）+ 长期 Refresh Token（7d），Redis 存储 Token 黑名单；前端 401 时自动尝试 refresh

### 3.8 Docker 服务 restart 策略 + 日志轮转

- **目标**：容器崩溃自动恢复，日志不撑爆磁盘
- **涉及文件**：`docker-compose.yml`
- **验收标准**：所有服务设置 `restart: unless-stopped`；日志驱动配置 max-size=10m、max-file=3
- **推荐实现方式**：在每个 service 下添加 `restart: unless-stopped` 和 `logging:` 配置

### 3.9 注册接口防用户枚举

- **目标**：不泄露邮箱是否已注册
- **涉及文件**：`backend/app/api/v1/auth.py`、`backend/app/services/auth.py`
- **验收标准**：注册已存在邮箱时返回与其他错误相同的消息和状态码
- **推荐实现方式**：注册失败时统一返回"注册信息已提交，请查收邮件"或类似模糊提示

### 3.10 Redis 认证 + 默认密码变更

- **目标**：防止未授权访问 Redis 和 PostgreSQL
- **涉及文件**：`docker-compose.yml`、`.env.example`
- **验收标准**：生产环境 Redis 需密码认证；.env.example 中无硬编码密码
- **推荐实现方式**：Redis 添加 `requirepass` 配置；.env.example 中密码字段留空并注释说明

### 3.11 Next.js middleware 添加服务端路由保护

- **目标**：未认证用户无法访问 /admin、/documents、/agents 等页面
- **涉及文件**：新建 `frontend/middleware.ts`
- **验收标准**：未携带有效 Token 访问 /admin 页面时重定向到 /login
- **推荐实现方式**：middleware.ts 检查 cookie/localStorage 中的 Token，验证 JWT 有效性后放行

### 3.12 SSE 断线重连

- **目标**：网络中断后自动恢复对话流
- **涉及文件**：`frontend/components/ChatWindow.tsx`、`frontend/app/(main)/agents/sessions/[sessionId]/page.tsx`
- **验收标准**：流式输出中断后 3 秒内自动重试，最多重试 3 次
- **推荐实现方式**：在 SSE 读取循环中捕获网络错误，指数退避重试（1s/2s/4s）

### 3.13 知识库访问控制

- **目标**：普通用户只能操作自己创建的知识库
- **涉及文件**：`backend/app/api/v1/knowledge_bases.py`、`backend/app/models/knowledge_base.py`
- **验收标准**：非 admin 用户无法修改/删除非自己创建的知识库
- **推荐实现方式**：KnowledgeBase 模型已有 `created_by` 字段，所有修改/删除操作增加 owner 校验

### 3.14 LLM 调用超时 + Celery 任务超时

- **目标**：防止 LLM 服务慢响应或异常任务阻塞整个系统
- **涉及文件**：`backend/app/core/llm.py`、`backend/app/services/rewriter.py`、`backend/app/services/common.py`、`backend/app/core/celery.py`
- **验收标准**：LLM 调用超过 30s 自动超时；Celery 单任务超过 5 分钟自动终止
- **推荐实现方式**：litellm.acompletion 添加 `timeout=30`；Celery 配置 `task_time_limit=300`、`task_soft_time_limit=240`

### 3.15 Request ID 改用 contextvars

- **目标**：修复异步场景下 request_id 互相覆盖导致链路追踪失效
- **涉及文件**：`backend/app/core/logging.py`
- **验收标准**：并发请求的日志中 request_id 各不相同
- **推荐实现方式**：将 `_request_id = threading.local()` 改为 `request_id_ctx: contextvars.ContextVar = contextvars.ContextVar('request_id', default='-')`

### 3.16 Git 历史密钥清理

- **目标**：从 git 历史中永久移除泄露的 API 密钥和 SECRET_KEY
- **涉及文件**：git 历史（.env、backend/.env）
- **验收标准**：`git log --all -p | grep -i "api_key\|secret_key"` 无敏感值输出
- **推荐实现方式**：使用 BFG Repo-Cleaner 清除 .env 文件历史 → 轮换所有泄露密钥 → 通知协作者重新 clone

---

## 4. 建议路线图

### 阶段一：生产硬化（1-2 周）

修复全部 P0 项和关键 P1 项，使系统达到最低安全和运维基线：

1. Git 历史密钥清理 + 轮换（3.16）
2. Docker 容器非 root 运行（3.1）
3. 补齐 nginx.conf / prometheus.yml / backup.sh（3.2）
4. Request ID 改用 contextvars（3.15）
5. LLM 调用超时 + Celery 任务超时（3.14）
6. Webhook SSRF 防护（3.3）
7. 文档权限 read/write 区分（3.4）
8. SQL 注入修复（3.5）
9. backend/.dockerignore（3.6）
10. Token 刷新与撤销（3.7）
11. restart 策略 + 日志轮转（3.8）
12. 注册防枚举（3.9）
13. Redis 认证 + 默认密码（3.10）
14. Next.js middleware（3.11）
15. 知识库访问控制（3.13）

### 阶段二：RAG 质量闭环（2-3 周）

建立可量化、可迭代的 RAG 质量体系：

1. 建立评测数据集（50-100 个 QA 对）
2. 分块策略优化（语义分块 / 滑动窗口改进）
3. 检索质量评估自动化（召回率、MRR、NDCG 指标）
4. Query Rewriter 效果评估
5. LIKE 搜索性能优化（pg_trgm 索引）
6. Reranker 效果对比实验
7. Prompt 模板 A/B 测试框架

### 阶段三：企业管理能力（2-3 周）

满足企业级多用户场景需求：

1. 用户角色体系扩展（admin/member/viewer）
2. 知识库级别权限控制
3. 审计日志全量覆盖（登录/注册/CRUD 全操作）
4. 管理后台用户批量操作（导入/导出/批量禁用）
5. 文档水印 / 下载管控
6. 操作日志查询界面
7. 数据保留策略（自动清理过期对话/文档）

### 阶段四：Agent 产品化（3-4 周）

将 Agent 从 Demo 级提升到产品级：

1. Agent Runtime 从规则引擎升级为 LLM-based Planner
2. Agent 会话历史持久化 + 长期记忆
3. Agent 工具权限控制（工具级别的用户授权）
4. Agent 执行过程可视化（时间线 + 思维链展示）
5. Agent 评估体系（任务完成率、步骤效率、用户满意度）
6. MCP 工具生态扩展（接入企业内部 API）
7. 多 Agent 协作（Agent 编排 / 路由）

### 阶段五：交付与运维体系（持续）

建立可靠的交付和运维能力：

1. CI/CD 流水线：测试→构建→扫描→部署→验证
2. 蓝绿/金丝雀部署策略
3. 数据库备份加密 + 异地存储 + 恢复演练
4. 告警规则配置（错误率、延迟、资源使用）
5. Grafana 仪表盘（业务指标 + 系统指标）
6. 性能压测基线（并发对话、文档索引吞吐）
7. 安全扫描自动化（Trivy + pip-audit + npm audit）
8. 灾难恢复预案文档

---

## 5. 暂不建议做的事

1. **微服务拆分**：当前单体架构（backend + worker）对中小规模部署完全够用，微服务拆分会引入分布式事务、服务发现、链路追踪等复杂度，投入产出比极低。

2. **自建 Embedding/Reranker 模型**：当前使用 API 调用 + 可选本地 FlagEmbedding 的方案已经足够灵活，自建模型需要大量标注数据和 GPU 资源，不适合作为当前优先级。

3. **多语言国际化（i18n）**：系统面向国内企业场景，中文是唯一目标语言。过早引入 i18n 会增加翻译维护成本，建议等产品稳定后再考虑。

4. **前端 SSR 渲染优化**：当前 Next.js standalone 模式 + Client Components 的方案对内部工具足够，SSR/SSG 的性能收益在内部场景下不明显。

5. **GraphQL API**：REST API 已覆盖所有功能，GraphQL 的灵活性在当前场景下是过度设计，且增加了前端查询复杂度。

6. **实时协作编辑**：对话和文档管理的实时协作需求优先级极低，WebSocket 长连接的运维成本远高于收益。

7. **大规模文件存储方案（S3/MinIO）**：当前本地文件存储 + Docker volume 对中小规模够用，引入对象存储需要额外的运维组件，建议文档量超过 10 万时再考虑。

8. **完全重写前端**：现有前端代码质量尚可，组件拆分合理，状态管理清晰。重写只会丢失已验证的业务逻辑，建议渐进式优化而非推倒重来。
